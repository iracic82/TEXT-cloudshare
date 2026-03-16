"""
Create an Infoblox CSP Sandbox account for a CloudShare lab VM.

This replaces the Instruqt version. Instead of INSTRUQT_PARTICIPANT_ID,
it uses the CloudShare VM ID as the unique sandbox identifier.

Usage:
    # Option 1: Pass VM ID directly (e.g. from CloudShare environment)
    python create_sandbox.py --vm-id VM12345ABC

    # Option 2: Auto-discover from a running CloudShare environment
    python create_sandbox.py --env-id EN12345ABC

    # Option 3: Use a custom identifier (e.g. machine-id from the VM itself)
    python create_sandbox.py --participant-id my-custom-uuid

Required env vars:
    CLOUDSHARE_API_ID   - CloudShare API ID
    CLOUDSHARE_API_KEY  - CloudShare API Key
    Infoblox_Token      - Infoblox CSP API token
    INFOBLOX_EMAIL      - Admin email for sandbox account
"""

import argparse
import os
import sys
import time
import random

from sandbox_api import SandboxAccountAPI
from cloudshare_client import CloudShareClient


def get_participant_id(args):
    """Determine the unique participant ID from CLI args or CloudShare VM."""

    # Explicit participant ID takes priority
    if args.participant_id:
        return args.participant_id

    # Explicit VM ID
    if args.vm_id:
        return args.vm_id

    # Auto-discover: find the first VM in the given environment
    if args.env_id:
        cs = CloudShareClient()
        machines = cs.get_env_machines(args.env_id)
        if not machines:
            print("No machines found in environment", args.env_id)
            sys.exit(1)
        vm_id = machines[0]["id"]
        print(f"Auto-discovered VM ID: {vm_id} ({machines[0].get('name', 'unknown')})")
        return vm_id

    # Fallback: check legacy env var
    fallback = os.environ.get("INSTRUQT_PARTICIPANT_ID") or os.environ.get("PARTICIPANT_ID")
    if fallback:
        return fallback

    print("Error: provide --vm-id, --env-id, --participant-id, or set PARTICIPANT_ID env var")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create Infoblox CSP sandbox for CloudShare lab")
    parser.add_argument("--vm-id", help="CloudShare VM ID to use as participant identifier")
    parser.add_argument("--env-id", help="CloudShare environment ID (auto-discovers first VM)")
    parser.add_argument("--participant-id", help="Custom participant/sandbox identifier")
    parser.add_argument("--sandbox-id-file", default="sandbox_id.txt")
    parser.add_argument("--external-id-file", default="external_id.txt")
    args = parser.parse_args()

    # Config
    base_url = os.environ.get("INFOBLOX_BASE_URL", "https://csp.infoblox.com/v2")
    token = os.environ.get("Infoblox_Token")
    email = os.environ.get("INFOBLOX_EMAIL")

    if not token:
        print("Error: Infoblox_Token env var is required")
        sys.exit(1)

    participant_id = get_participant_id(args)
    print(f"Using participant ID: {participant_id}")

    # Build sandbox request
    sandbox_request_body = {
        "name": participant_id,
        "description": "Created via CloudShare lab automation",
        "state": "active",
        "tags": {"cloudshare": "lab"},
        "admin_user": {
            "email": email,
            "name": participant_id,
        },
    }

    # Create sandbox with retry
    api = SandboxAccountAPI(base_url=base_url, token=token)
    max_retries = 5
    create_response = None

    for attempt in range(max_retries):
        create_response = api.create_sandbox_account(sandbox_request_body)
        if create_response.get("status") == "success":
            break
        print(f"Attempt {attempt + 1} failed: {create_response.get('error')}", flush=True)
        time.sleep((2 ** attempt) + random.random())
    else:
        print("Sandbox creation failed after retries", flush=True)
        sys.exit(1)

    print("Sandbox created successfully.", flush=True)
    sandbox_data = create_response["data"]

    # Extract sandbox_id
    sandbox_id = None
    if isinstance(sandbox_data, dict):
        if "result" in sandbox_data and "id" in sandbox_data["result"]:
            sandbox_id = sandbox_data["result"]["id"]
        elif "id" in sandbox_data:
            sandbox_id = sandbox_data["id"]

    if sandbox_id and sandbox_id.startswith("identity/accounts/"):
        sandbox_id = sandbox_id.split("/")[-1]

    if not sandbox_id:
        print("Sandbox ID not found in response. Aborting.", flush=True)
        sys.exit(1)

    with open(args.sandbox_id_file, "w") as f:
        f.write(sandbox_id)
    print(f"Sandbox ID saved to {args.sandbox_id_file}: {sandbox_id}", flush=True)

    # Extract external_id
    admin_user = sandbox_data.get("result", {}).get("admin_user")
    external_id = None
    if admin_user and "account_id" in admin_user:
        external_id = admin_user["account_id"].split("/")[-1]

    if not external_id:
        print("External ID not found in admin_user.account_id. Aborting.", flush=True)
        sys.exit(1)

    with open(args.external_id_file, "w") as f:
        f.write(external_id)
    print(f"External ID saved to {args.external_id_file}: {external_id}", flush=True)


if __name__ == "__main__":
    main()
