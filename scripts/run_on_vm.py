"""
Run setup/cleanup scripts on a CloudShare Ubuntu VM.

This replaces Instruqt's built-in lifecycle scripts (setup, check, cleanup)
by using CloudShare's executePath API to remotely execute commands on VMs.

Usage:
    # Run a single command
    python run_on_vm.py --vm-id VM12345 --command "echo hello"

    # Run a script file (uploads and executes it)
    python run_on_vm.py --vm-id VM12345 --script setup.sh

    # Run with custom environment variables injected
    python run_on_vm.py --vm-id VM12345 --script setup.sh \
        --var PARTICIPANT_ID=abc123 \
        --var Infoblox_Token=mytoken \
        --var INFOBLOX_EMAIL=user@example.com

    # Auto-discover VM from environment
    python run_on_vm.py --env-id EN12345 --command "whoami"
"""

import argparse
import os
import sys

from cloudshare_client import CloudShareClient


def build_env_prefix(variables: list[str]) -> str:
    """Build an 'export VAR=value;' prefix string from --var KEY=VALUE pairs."""
    if not variables:
        return ""
    exports = []
    for var in variables:
        if "=" not in var:
            print(f"Warning: skipping invalid --var '{var}' (expected KEY=VALUE)")
            continue
        key, value = var.split("=", 1)
        # Escape single quotes in value for safe shell injection
        escaped = value.replace("'", "'\\''")
        exports.append(f"export {key}='{escaped}'")
    return "; ".join(exports) + "; " if exports else ""


def resolve_vm_id(args, cs: CloudShareClient) -> str:
    """Get VM ID from args or by discovering from environment."""
    if args.vm_id:
        return args.vm_id

    if args.env_id:
        machines = cs.get_env_machines(args.env_id)
        if not machines:
            print(f"No machines found in environment {args.env_id}")
            sys.exit(1)

        # If vm_name specified, find by name
        if args.vm_name:
            for m in machines:
                if m.get("name") == args.vm_name:
                    print(f"Found VM: {m['id']} ({m['name']})")
                    return m["id"]
            print(f"VM named '{args.vm_name}' not found. Available: {[m['name'] for m in machines]}")
            sys.exit(1)

        # Default to first machine
        vm = machines[0]
        print(f"Using VM: {vm['id']} ({vm.get('name', 'unknown')})")
        return vm["id"]

    print("Error: provide --vm-id or --env-id")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run commands/scripts on a CloudShare VM")
    parser.add_argument("--vm-id", help="CloudShare VM ID")
    parser.add_argument("--env-id", help="CloudShare environment ID (discovers VM)")
    parser.add_argument("--vm-name", help="VM name within environment (used with --env-id)")
    parser.add_argument("--command", help="Command to execute on the VM")
    parser.add_argument("--script", help="Local script file to execute on the VM")
    parser.add_argument("--var", action="append", help="Environment variable as KEY=VALUE (repeatable)")
    parser.add_argument("--timeout", type=int, default=300, help="Execution timeout in seconds")
    args = parser.parse_args()

    if not args.command and not args.script:
        print("Error: provide --command or --script")
        sys.exit(1)

    cs = CloudShareClient()
    vm_id = resolve_vm_id(args, cs)
    env_prefix = build_env_prefix(args.var)

    if args.script:
        # Read the script file and execute it inline via bash
        if not os.path.isfile(args.script):
            print(f"Error: script file not found: {args.script}")
            sys.exit(1)
        with open(args.script) as f:
            script_content = f.read()
        # Wrap in bash -c with env vars
        command = f"bash -c '{env_prefix}{script_content}'"
        # For long scripts, use heredoc approach instead
        if len(script_content) > 500:
            # Write script to temp file on VM and execute
            escaped_content = script_content.replace("'", "'\\''")
            command = (
                f"bash -c '"
                f"{env_prefix}"
                f"cat > /tmp/_cs_setup.sh << '\"'\"'CLOUDSHARE_SCRIPT_EOF'\"'\"'\n"
                f"{script_content}\n"
                f"CLOUDSHARE_SCRIPT_EOF\n"
                f"chmod +x /tmp/_cs_setup.sh && /tmp/_cs_setup.sh && rm -f /tmp/_cs_setup.sh'"
            )
    else:
        command = f"bash -c '{env_prefix}{args.command}'"

    print(f"Executing on VM {vm_id}...")
    print(f"Command: {args.command or args.script}")

    try:
        output = cs.run_command_sync(vm_id, command, timeout=args.timeout)
        print(f"\n--- Output ---\n{output}")
    except TimeoutError as e:
        print(f"Execution timed out: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
