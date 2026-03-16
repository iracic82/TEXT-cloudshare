"""
Prepare a CloudShare Ubuntu VM as an Infoblox lab blueprint.

Run this from YOUR MACHINE (not on the VM). It uses the CloudShare API
to remotely execute commands on the VM that:
  1. Install git, python3, pip
  2. Git clone the lab scripts repo
  3. Install Python dependencies
  4. Set up systemd service for auto-run on boot
  5. Inject your Infoblox credentials

After this completes, save the VM as a CloudShare blueprint/template.
Every clone of that blueprint will auto-setup the Infoblox lab on boot.

Usage:
    export CLOUDSHARE_API_ID="your-id"
    export CLOUDSHARE_API_KEY="your-key"

    python prepare_blueprint.py \
        --env-id EN12345ABC \
        --infoblox-token "your-csp-token" \
        --infoblox-email "admin@infoblox.com" \
        --infoblox-password "your-password" \
        --repo "https://github.com/iracic82/Infoblox-PoC.git"
"""

import argparse
import os
import sys

from cloudshare_client import CloudShareClient


def run_step(cs, vm_id, description, command, timeout=120):
    """Run a command on the VM and print the result."""
    print(f"\n--- {description} ---")
    try:
        output = cs.run_command_sync(vm_id, command, timeout=timeout)
        print(output if output else "(no output)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Prepare CloudShare VM as Infoblox lab blueprint")
    parser.add_argument("--env-id", required=True, help="CloudShare environment ID")
    parser.add_argument("--vm-name", help="Target VM name (defaults to first VM)")
    parser.add_argument("--repo", default="https://github.com/iracic82/TEXT-cloudshare.git",
                        help="Git repo URL with lab scripts")
    parser.add_argument("--branch", default="main", help="Git branch to clone")
    parser.add_argument("--infoblox-token", help="Infoblox CSP API token")
    parser.add_argument("--infoblox-email", help="Infoblox admin email")
    parser.add_argument("--infoblox-password", help="Infoblox admin password")
    args = parser.parse_args()

    cs = CloudShareClient()

    # Find the target VM
    print(f"Finding VMs in environment {args.env_id}...")
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
    print(f"Target VM: {target_vm.get('name', 'unknown')} ({vm_id})")

    # Step 1: Install system dependencies
    ok = run_step(cs, vm_id,
        "Step 1/5: Installing system packages",
        "apt-get update -qq && apt-get install -y -qq python3 python3-pip git",
        timeout=180)
    if not ok:
        sys.exit(1)

    # Step 2: Clone the repo
    ok = run_step(cs, vm_id,
        "Step 2/5: Cloning lab scripts from Git",
        f"rm -rf /opt/cloudshare-lab && git clone -b {args.branch} {args.repo} /opt/cloudshare-lab",
        timeout=120)
    if not ok:
        sys.exit(1)

    # Step 3: Install Python dependencies
    ok = run_step(cs, vm_id,
        "Step 3/5: Installing Python dependencies",
        "pip3 install requests cloudshare",
        timeout=120)
    if not ok:
        sys.exit(1)

    # Step 4: Create state directory and systemd service
    systemd_unit = (
        "[Unit]\\n"
        "Description=Infoblox Lab Setup\\n"
        "After=network-online.target\\n"
        "Wants=network-online.target\\n"
        "\\n"
        "[Service]\\n"
        "Type=oneshot\\n"
        "ExecStart=/opt/cloudshare-lab/scripts/vm_bootstrap.sh\\n"
        "RemainAfterExit=yes\\n"
        "EnvironmentFile=-/opt/cloudshare-lab/lab.env\\n"
        "\\n"
        "[Install]\\n"
        "WantedBy=multi-user.target"
    )
    ok = run_step(cs, vm_id,
        "Step 4/5: Setting up systemd service for auto-run on boot",
        (
            f'mkdir -p /opt/cloudshare-lab/state && '
            f'chmod +x /opt/cloudshare-lab/scripts/vm_bootstrap.sh && '
            f'chmod +x /opt/cloudshare-lab/scripts/vm_cleanup.sh && '
            f'printf "{systemd_unit}" > /etc/systemd/system/infoblox-lab-setup.service && '
            f'systemctl daemon-reload && '
            f'systemctl enable infoblox-lab-setup.service'
        ))
    if not ok:
        sys.exit(1)

    # Step 5: Write credentials to lab.env
    token = args.infoblox_token or os.environ.get("Infoblox_Token", "YOUR_TOKEN_HERE")
    email = args.infoblox_email or os.environ.get("INFOBLOX_EMAIL", "admin@infoblox.com")
    password = args.infoblox_password or os.environ.get("INFOBLOX_PASSWORD", "YOUR_PASSWORD_HERE")

    env_content = (
        f"Infoblox_Token={token}\\n"
        f"INFOBLOX_EMAIL={email}\\n"
        f"INFOBLOX_PASSWORD={password}\\n"
        f"USER_EMAIL=\\n"
    )
    ok = run_step(cs, vm_id,
        "Step 5/5: Writing credentials to lab.env",
        f'printf "{env_content}" > /opt/cloudshare-lab/lab.env && chmod 600 /opt/cloudshare-lab/lab.env')
    if not ok:
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Blueprint preparation complete!")
    print("=" * 60)
    print()
    print("What's on the VM now:")
    print("  /opt/cloudshare-lab/scripts/  - All lab Python scripts")
    print("  /opt/cloudshare-lab/lab.env   - Infoblox credentials")
    print("  /opt/cloudshare-lab/state/    - Runtime state (sandbox_id, etc)")
    print("  systemd service              - Auto-runs vm_bootstrap.sh on boot")
    print()
    print("NEXT STEPS:")
    print("  1. (Optional) Test: run vm_bootstrap.sh on the VM manually")
    print("  2. Save this VM as a CloudShare blueprint/template")
    print("  3. Every clone will auto-create an Infoblox sandbox on boot!")
    print()


if __name__ == "__main__":
    main()
