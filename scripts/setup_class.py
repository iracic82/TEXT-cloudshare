"""
Set up Infoblox labs for all students in a CloudShare class.

Runs from YOUR MACHINE (not on VMs). For each student environment:
  1. Gets the student's email from CloudShare (ownerEmail)
  2. Runs the bootstrap on the student's VM via executePath
  3. Passes the student email as USER_EMAIL

Usage:
    python setup_class.py --project "Infoblox-TME"
    python setup_class.py --env-ids EN123 EN456 EN789
    python setup_class.py --all

Required env vars:
    CLOUDSHARE_API_ID   - CloudShare API credentials
    CLOUDSHARE_API_KEY
    Infoblox_Token      - Infoblox CSP API token (written to VM)
    INFOBLOX_EMAIL      - Infoblox admin email
    INFOBLOX_PASSWORD   - Infoblox admin password
"""

import argparse
import os
import sys
import time

from cloudshare_client import CloudShareClient


def get_env_details(cs, env_id):
    """Get extended environment info including ownerEmail and VMs."""
    return cs.get_env_extended(env_id)


def find_ubuntu_vm(vms):
    """Find the Ubuntu/Linux VM in an environment."""
    for vm in vms:
        if vm.get("os") == "Linux" or "ubuntu" in vm.get("name", "").lower():
            return vm
    return None


def setup_single_env(cs, env_id, infoblox_token, infoblox_email, infoblox_password):
    """Set up one student environment."""
    print(f"\n{'='*60}")
    print(f"Setting up environment: {env_id}")

    # Get environment details
    details = get_env_details(cs, env_id)
    env_name = details.get("name", "unknown")
    owner_email = details.get("ownerEmail", "")
    status = details.get("statusText", "")

    print(f"  Name: {env_name}")
    print(f"  Owner: {owner_email}")
    print(f"  Status: {status}")

    if status != "Ready":
        print(f"  SKIPPING - environment not ready (status: {status})")
        return False

    if not owner_email:
        print("  SKIPPING - no ownerEmail found")
        return False

    # Find the Ubuntu VM
    vms = details.get("vms", [])
    vm = find_ubuntu_vm(vms)
    if not vm:
        print(f"  SKIPPING - no Linux VM found. VMs: {[v['name'] for v in vms]}")
        return False

    vm_id = vm["id"]
    print(f"  VM: {vm['name']} ({vm_id})")

    # Write lab.env and run bootstrap on the VM
    env_file_content = (
        f"Infoblox_Token={infoblox_token}\\n"
        f"INFOBLOX_EMAIL={infoblox_email}\\n"
        f"INFOBLOX_PASSWORD={infoblox_password}\\n"
        f"USER_EMAIL={owner_email}\\n"
    )

    # Step 1: Write credentials
    print("  Writing lab.env...")
    try:
        cs.run_command_sync(
            vm_id,
            f"sudo bash -c 'printf \"{env_file_content}\" > /opt/cloudshare-lab/lab.env && chmod 600 /opt/cloudshare-lab/lab.env'",
            timeout=30
        )
    except Exception as e:
        print(f"  FAILED to write lab.env: {e}")
        return False

    # Step 2: Pull latest scripts
    print("  Pulling latest scripts...")
    try:
        cs.run_command_sync(vm_id, "cd /opt/cloudshare-lab && sudo git pull", timeout=60)
    except Exception as e:
        print(f"  Warning: git pull failed: {e}")

    # Step 3: Run bootstrap
    print("  Running bootstrap (this takes ~2 minutes with the 60s delay)...")
    try:
        output = cs.run_command_sync(
            vm_id,
            "sudo bash -c 'source /opt/cloudshare-lab/lab.env && rm -f /tmp/lab-setup.lock && /opt/cloudshare-lab/scripts/vm_bootstrap.sh'",
            timeout=300
        )
        print(f"  Output:\n{output}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Set up Infoblox labs for CloudShare class")
    parser.add_argument("--env-ids", nargs="+", help="Specific environment IDs to set up")
    parser.add_argument("--project", help="Set up all environments in a project")
    parser.add_argument("--all", action="store_true", help="Set up all visible environments")
    parser.add_argument("--skip-ready-check", action="store_true", help="Skip checking if env is ready")
    args = parser.parse_args()

    infoblox_token = os.environ.get("Infoblox_Token")
    infoblox_email = os.environ.get("INFOBLOX_EMAIL")
    infoblox_password = os.environ.get("INFOBLOX_PASSWORD")

    if not all([infoblox_token, infoblox_email, infoblox_password]):
        print("Error: Set Infoblox_Token, INFOBLOX_EMAIL, INFOBLOX_PASSWORD env vars")
        sys.exit(1)

    cs = CloudShareClient()

    # Collect environment IDs
    env_ids = []

    if args.env_ids:
        env_ids = args.env_ids
    elif args.all or args.project:
        envs = cs.list_envs()
        env_ids = [e["id"] for e in envs]
        print(f"Found {len(env_ids)} environments")
    else:
        print("Error: provide --env-ids, --project, or --all")
        sys.exit(1)

    # Set up each environment
    success = 0
    failed = 0
    skipped = 0

    for env_id in env_ids:
        try:
            result = setup_single_env(cs, env_id, infoblox_token, infoblox_email, infoblox_password)
            if result:
                success += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"Done! Success: {success}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
