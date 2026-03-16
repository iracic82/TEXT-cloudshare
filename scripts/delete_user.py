"""
Delete an Infoblox CSP user from a sandbox account (cleanup).

Authenticates via JWT, switches to the sandbox, then deletes the user.

Usage:
    python delete_user.py
    python delete_user.py --sandbox-id-file sandbox_id.txt --user-id-file user_id.txt

Required env vars:
    INFOBLOX_EMAIL     - Admin email for CSP login
    INFOBLOX_PASSWORD  - Admin password for CSP login
"""

import os
import sys
import time
import random

import requests


def main():
    base_url = os.environ.get("INFOBLOX_BASE_URL", "https://csp.infoblox.com")
    email = os.getenv("INFOBLOX_EMAIL")
    password = os.getenv("INFOBLOX_PASSWORD")
    sandbox_id_file = os.environ.get("SANDBOX_ID_FILE", "sandbox_id.txt")
    user_id_file = os.environ.get("USER_ID_FILE", "user_id.txt")

    if not email or not password:
        print("Error: INFOBLOX_EMAIL and INFOBLOX_PASSWORD are required")
        sys.exit(1)

    # Read IDs from files
    try:
        sandbox_id = open(sandbox_id_file).read().strip()
        user_id = open(user_id_file).read().strip()
    except FileNotFoundError:
        print("sandbox_id.txt or user_id.txt not found. Nothing to delete.")
        sys.exit(0)

    if not sandbox_id or not user_id:
        print("Empty sandbox_id or user_id. Nothing to delete.")
        sys.exit(0)

    # Step 1: Authenticate
    print("Authenticating...", flush=True)
    auth_resp = requests.post(
        f"{base_url}/v2/session/users/sign_in",
        json={"email": email, "password": password},
    )
    auth_resp.raise_for_status()
    jwt = auth_resp.json()["jwt"]
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    print("Authenticated.", flush=True)

    # Step 2: Switch to sandbox account
    print(f"Switching to sandbox account {sandbox_id}...", flush=True)
    switch_resp = requests.post(
        f"{base_url}/v2/session/account_switch",
        headers=headers,
        json={"id": f"identity/accounts/{sandbox_id}"},
    )
    switch_resp.raise_for_status()
    jwt = switch_resp.json()["jwt"]
    headers["Authorization"] = f"Bearer {jwt}"

    # Step 3: Delete user with retries
    endpoint = f"{base_url}/v2/users/{user_id}"
    for attempt in range(5):
        try:
            print(f"Deleting user {user_id} (attempt {attempt + 1})...", flush=True)
            resp = requests.delete(endpoint, headers=headers)
            if resp.status_code == 204:
                print(f"User {user_id} deleted.", flush=True)
                os.remove(user_id_file)
                return
            print(f"Status {resp.status_code}: {resp.text}", flush=True)
        except Exception as e:
            print(f"Error: {e}", flush=True)
        time.sleep((2 ** attempt) + random.random())

    print("User deletion failed after retries")
    sys.exit(1)


if __name__ == "__main__":
    main()
