"""
Create an Infoblox CSP user within a sandbox account.

CloudShare adaptation of the Instruqt version. Replaces:
  - INSTRUQT_PARTICIPANT_ID -> CloudShare VM ID or --participant-id
  - INSTRUQT_EMAIL -> --user-email or USER_EMAIL env var

This script runs AFTER create_sandbox.py (needs sandbox_id.txt).

Usage:
    # With explicit args
    python create_user.py --participant-id VM12345ABC --user-email student@example.com

    # With env vars
    PARTICIPANT_ID=VM12345 USER_EMAIL=student@example.com python create_user.py

    # Auto-discover from CloudShare environment
    python create_user.py --env-id EN12345ABC --user-email student@example.com

Required env vars:
    INFOBLOX_EMAIL     - Admin email for CSP login
    INFOBLOX_PASSWORD  - Admin password for CSP login
"""

import argparse
import json
import os
import sys
import time
import random

import requests

from cloudshare_client import CloudShareClient


def authenticate(base_url, email, password):
    """Sign in to Infoblox CSP and return JWT token."""
    auth_url = f"{base_url}/v2/session/users/sign_in"
    resp = requests.post(auth_url, json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["jwt"]


def switch_account(base_url, jwt, sandbox_id):
    """Switch to a sandbox account and return new JWT."""
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    switch_url = f"{base_url}/v2/session/account_switch"
    resp = requests.post(
        switch_url, headers=headers,
        json={"id": f"identity/accounts/{sandbox_id}"}
    )
    resp.raise_for_status()
    return resp.json()["jwt"]


def get_group_ids(base_url, jwt):
    """Fetch group IDs for 'user' and 'act_admin' groups."""
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    resp = requests.get(f"{base_url}/v2/groups", headers=headers)
    resp.raise_for_status()
    groups = resp.json().get("results", [])

    user_group_id = next((g["id"] for g in groups if g.get("name") == "user"), None)
    admin_group_id = next((g["id"] for g in groups if g.get("name") == "act_admin"), None)

    return user_group_id, admin_group_id


def create_user_request(base_url, jwt, user_name, user_email, group_ids, max_retries=5):
    """Create a user in the sandbox account with retry logic."""
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    payload = {
        "name": user_name,
        "email": user_email,
        "type": "interactive",
        "group_ids": group_ids,
    }
    user_url = f"{base_url}/v2/users"

    for attempt in range(max_retries):
        try:
            print(f"Creating user '{user_name}' (attempt {attempt + 1})...", flush=True)
            resp = requests.post(user_url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}", flush=True)
            time.sleep((2 ** attempt) + random.random())

    print("User creation failed after retries", flush=True)
    sys.exit(1)


def resolve_participant_id(args):
    """Get participant ID from args, env, or CloudShare VM discovery."""
    if args.participant_id:
        return args.participant_id

    if args.env_id:
        cs = CloudShareClient()
        machines = cs.get_env_machines(args.env_id)
        if not machines:
            print(f"No machines found in environment {args.env_id}")
            sys.exit(1)
        vm_id = machines[0]["id"]
        print(f"Auto-discovered VM ID: {vm_id} ({machines[0].get('name', 'unknown')})")
        return vm_id

    env_id = os.environ.get("PARTICIPANT_ID") or os.environ.get("INSTRUQT_PARTICIPANT_ID")
    if env_id:
        return env_id

    print("Error: provide --participant-id, --env-id, or set PARTICIPANT_ID env var")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Create Infoblox CSP user in sandbox")
    parser.add_argument("--participant-id", help="Participant/VM identifier")
    parser.add_argument("--env-id", help="CloudShare environment ID (auto-discovers VM)")
    parser.add_argument("--user-email", help="Email for the new user")
    parser.add_argument("--sandbox-id-file", default="sandbox_id.txt")
    parser.add_argument("--user-id-file", default="user_id.txt")
    args = parser.parse_args()

    base_url = os.environ.get("INFOBLOX_BASE_URL", "https://csp.infoblox.com")
    admin_email = os.environ.get("INFOBLOX_EMAIL")
    admin_password = os.environ.get("INFOBLOX_PASSWORD")
    user_email = args.user_email or os.environ.get("USER_EMAIL") or os.environ.get("INSTRUQT_EMAIL")

    if not admin_email or not admin_password:
        print("Error: INFOBLOX_EMAIL and INFOBLOX_PASSWORD env vars are required")
        sys.exit(1)

    if not user_email:
        print("Error: provide --user-email or set USER_EMAIL env var")
        sys.exit(1)

    participant_id = resolve_participant_id(args)

    # Read sandbox ID from previous step
    if not os.path.isfile(args.sandbox_id_file):
        print(f"Error: {args.sandbox_id_file} not found. Run create_sandbox.py first.")
        sys.exit(1)

    with open(args.sandbox_id_file) as f:
        sandbox_id = f.read().strip()

    print(f"Participant ID: {participant_id}")
    print(f"Sandbox ID: {sandbox_id}")
    print(f"User email: {user_email}")

    # Step 1: Authenticate
    print("Authenticating to Infoblox CSP...", flush=True)
    jwt = authenticate(base_url, admin_email, admin_password)
    print("Logged in and obtained JWT", flush=True)

    # Step 2: Switch to sandbox account
    print(f"Switching to sandbox account {sandbox_id}...", flush=True)
    jwt = switch_account(base_url, jwt, sandbox_id)
    print(f"Switched to sandbox account {sandbox_id}", flush=True)
    time.sleep(3)

    # Step 3: Get group IDs
    print("Fetching group IDs...", flush=True)
    user_group_id, admin_group_id = get_group_ids(base_url, jwt)

    if not user_group_id or not admin_group_id:
        print(f"Error: could not find required groups. user={user_group_id}, admin={admin_group_id}")
        sys.exit(1)

    print(f"Found user group: {user_group_id}", flush=True)
    print(f"Found admin group: {admin_group_id}", flush=True)

    # Step 4: Create user
    user_data = create_user_request(
        base_url, jwt, participant_id, user_email,
        [user_group_id, admin_group_id]
    )
    print("User created successfully.", flush=True)
    print(json.dumps(user_data, indent=2), flush=True)

    # Step 5: Save user ID
    user_id = user_data.get("result", {}).get("id")
    if user_id and user_id.startswith("identity/users/"):
        user_id = user_id.split("/")[-1]
        with open(args.user_id_file, "w") as f:
            f.write(user_id)
        print(f"User ID saved to {args.user_id_file}: {user_id}", flush=True)
    else:
        print("User ID not found or unexpected format. Aborting.", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
