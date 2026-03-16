"""
Delete an Infoblox CSP sandbox account (cleanup script).

Replaces Instruqt's cleanup lifecycle hook.

Usage:
    # Delete by sandbox ID from file
    python delete_sandbox.py

    # Delete by explicit sandbox ID
    python delete_sandbox.py --sandbox-id abc123

    # Delete by participant/VM ID (looks up sandbox by name)
    python delete_sandbox.py --participant-id VM12345
"""

import argparse
import os
import sys

from sandbox_api import SandboxAccountAPI


def main():
    parser = argparse.ArgumentParser(description="Delete Infoblox CSP sandbox")
    parser.add_argument("--sandbox-id", help="Sandbox ID to delete")
    parser.add_argument("--participant-id", help="Participant ID (looks up sandbox by name)")
    parser.add_argument("--sandbox-id-file", default="sandbox_id.txt")
    args = parser.parse_args()

    base_url = os.environ.get("INFOBLOX_BASE_URL", "https://csp.infoblox.com")
    token = os.environ.get("Infoblox_Token")

    if not token:
        print("Error: Infoblox_Token env var required")
        sys.exit(1)

    api = SandboxAccountAPI(base_url=base_url, token=token)

    sandbox_id = args.sandbox_id

    # Try participant ID lookup
    if not sandbox_id and args.participant_id:
        sandbox_id = api.get_sandbox_account_id_by_name(args.participant_id)
        if sandbox_id and sandbox_id.startswith("identity/accounts/"):
            sandbox_id = sandbox_id.split("/")[-1]

    # Try file
    if not sandbox_id and os.path.isfile(args.sandbox_id_file):
        with open(args.sandbox_id_file) as f:
            sandbox_id = f.read().strip()

    if not sandbox_id:
        print("No sandbox ID found. Nothing to delete.")
        sys.exit(0)

    print(f"Deleting sandbox: {sandbox_id}")
    if api.delete_sandbox_account(sandbox_id):
        print("Sandbox deleted successfully.")
        # Clean up local files
        for f in [args.sandbox_id_file, "external_id.txt"]:
            if os.path.isfile(f):
                os.remove(f)
    else:
        print("Failed to delete sandbox.")
        sys.exit(1)


if __name__ == "__main__":
    main()
