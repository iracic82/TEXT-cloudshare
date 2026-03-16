"""
Lab setup orchestrator for CloudShare.

Replaces Instruqt's track lifecycle by:
1. Finding/creating a CloudShare environment
2. Getting the Ubuntu VM's unique ID
3. Creating an Infoblox CSP sandbox using that VM ID
4. Running setup scripts on the VM with the sandbox credentials

Usage:
    # Full lab setup for an existing environment
    python lab_setup.py --env-id EN12345ABC

    # With custom variables passed to setup scripts
    python lab_setup.py --env-id EN12345ABC \
        --var CUSTOM_VAR1=value1 \
        --var CUSTOM_VAR2=value2

Required env vars:
    CLOUDSHARE_API_ID   - CloudShare API credentials
    CLOUDSHARE_API_KEY
    Infoblox_Token      - Infoblox CSP API token
    INFOBLOX_EMAIL      - Admin email for sandbox
"""

import argparse
import os
import sys
import time
import random

from cloudshare_client import CloudShareClient
from sandbox_api import SandboxAccountAPI


def wait_for_env_ready(cs: CloudShareClient, env_id: str, timeout=600):
    """Wait until the CloudShare environment status is Ready."""
    start = time.time()
    while True:
        extended = cs.get_env_extended(env_id)
        status = extended.get("statusText", "")
        print(f"  Environment status: {status}")
        if status == "Ready":
            return extended
        if time.time() - start > timeout:
            raise TimeoutError(f"Environment not ready after {timeout}s (status: {status})")
        time.sleep(10)


def create_infoblox_sandbox(participant_id: str, base_url: str, token: str, email: str):
    """Create an Infoblox CSP sandbox account. Returns (sandbox_id, external_id)."""
    sandbox_request = {
        "name": participant_id,
        "description": "Created via CloudShare lab automation",
        "state": "active",
        "tags": {"cloudshare": "lab"},
        "admin_user": {
            "email": email,
            "name": participant_id,
        },
    }

    api = SandboxAccountAPI(base_url=base_url, token=token)

    for attempt in range(5):
        response = api.create_sandbox_account(sandbox_request)
        if response.get("status") == "success":
            break
        print(f"  Retry {attempt + 1}: {response.get('error')}")
        time.sleep((2 ** attempt) + random.random())
    else:
        raise RuntimeError("Sandbox creation failed after retries")

    data = response["data"]

    # Extract sandbox_id
    sandbox_id = None
    if isinstance(data, dict):
        if "result" in data and "id" in data["result"]:
            sandbox_id = data["result"]["id"]
        elif "id" in data:
            sandbox_id = data["id"]
    if sandbox_id and sandbox_id.startswith("identity/accounts/"):
        sandbox_id = sandbox_id.split("/")[-1]

    # Extract external_id
    external_id = None
    admin_user = data.get("result", {}).get("admin_user")
    if admin_user and "account_id" in admin_user:
        external_id = admin_user["account_id"].split("/")[-1]

    return sandbox_id, external_id


def run_setup_scripts(cs: CloudShareClient, vm_id: str, variables: dict, timeout=300):
    """Run setup commands on the VM, injecting variables as env vars."""
    # Build export prefix
    exports = "; ".join(
        f"export {k}='{v}'" for k, v in variables.items()
    )

    # The setup command: export vars, then run whatever setup is needed
    # Users can customize this or point to a script on the VM
    setup_cmd = (
        f"bash -c '{exports}; "
        f"echo \"Lab variables set:\"; env | grep -E \"SANDBOX_ID|EXTERNAL_ID|PARTICIPANT_ID\"; "
        f"echo \"Setup complete\"'"
    )

    print(f"  Running setup on VM {vm_id}...")
    output = cs.run_command_sync(vm_id, setup_cmd, timeout=timeout)
    print(f"  Output: {output}")
    return output


def main():
    parser = argparse.ArgumentParser(description="Full lab setup orchestrator")
    parser.add_argument("--env-id", required=True, help="CloudShare environment ID")
    parser.add_argument("--vm-name", help="Specific VM name (defaults to first VM)")
    parser.add_argument("--var", action="append", help="Extra variable as KEY=VALUE")
    parser.add_argument("--skip-sandbox", action="store_true", help="Skip Infoblox sandbox creation")
    parser.add_argument("--setup-script", help="Path to setup script to run on VM")
    args = parser.parse_args()

    # Infoblox config
    infoblox_base_url = os.environ.get("INFOBLOX_BASE_URL", "https://csp.infoblox.com")
    infoblox_token = os.environ.get("Infoblox_Token")
    infoblox_email = os.environ.get("INFOBLOX_EMAIL")

    cs = CloudShareClient()

    # Step 1: Wait for environment to be ready
    print(f"[1/4] Waiting for environment {args.env_id} to be ready...")
    wait_for_env_ready(cs, args.env_id)

    # Step 2: Discover VM
    print(f"[2/4] Discovering VMs...")
    machines = cs.get_env_machines(args.env_id)
    if not machines:
        print("No machines found!")
        sys.exit(1)

    target_vm = None
    if args.vm_name:
        for m in machines:
            if m.get("name") == args.vm_name:
                target_vm = m
                break
        if not target_vm:
            print(f"VM '{args.vm_name}' not found. Available: {[m['name'] for m in machines]}")
            sys.exit(1)
    else:
        target_vm = machines[0]

    vm_id = target_vm["id"]
    participant_id = vm_id  # Use VM ID as unique participant identifier
    print(f"  Target VM: {target_vm.get('name', 'unknown')} (ID: {vm_id})")

    # Step 3: Create Infoblox sandbox
    sandbox_id = None
    external_id = None

    if not args.skip_sandbox:
        if not infoblox_token:
            print("Error: Infoblox_Token env var required (or use --skip-sandbox)")
            sys.exit(1)

        print(f"[3/4] Creating Infoblox sandbox for participant: {participant_id}...")
        sandbox_id, external_id = create_infoblox_sandbox(
            participant_id, infoblox_base_url, infoblox_token, infoblox_email
        )
        print(f"  Sandbox ID: {sandbox_id}")
        print(f"  External ID: {external_id}")

        # Save to files
        if sandbox_id:
            with open("sandbox_id.txt", "w") as f:
                f.write(sandbox_id)
        if external_id:
            with open("external_id.txt", "w") as f:
                f.write(external_id)
    else:
        print("[3/4] Skipping Infoblox sandbox creation")

    # Step 4: Run setup on the VM
    print(f"[4/4] Running setup on VM...")
    variables = {
        "PARTICIPANT_ID": participant_id,
    }
    if sandbox_id:
        variables["SANDBOX_ID"] = sandbox_id
    if external_id:
        variables["EXTERNAL_ID"] = external_id
    if infoblox_token:
        variables["Infoblox_Token"] = infoblox_token
    if infoblox_email:
        variables["INFOBLOX_EMAIL"] = infoblox_email

    # Add custom variables from --var flags
    if args.var:
        for v in args.var:
            if "=" in v:
                key, value = v.split("=", 1)
                variables[key] = value

    if args.setup_script:
        # Read and execute the setup script with variables
        with open(args.setup_script) as f:
            script_content = f.read()
        exports = "; ".join(f"export {k}='{v}'" for k, v in variables.items())
        command = f"bash -c '{exports}; {script_content}'"
        print(f"  Running script: {args.setup_script}")
        output = cs.run_command_sync(vm_id, command, timeout=600)
        print(f"  Output:\n{output}")
    else:
        run_setup_scripts(cs, vm_id, variables)

    print("\nLab setup complete!")
    print(f"  Environment: {args.env_id}")
    print(f"  VM ID: {vm_id}")
    if sandbox_id:
        print(f"  Sandbox ID: {sandbox_id}")
    if external_id:
        print(f"  External ID: {external_id}")


if __name__ == "__main__":
    main()
