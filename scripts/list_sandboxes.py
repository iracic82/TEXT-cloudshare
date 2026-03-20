#!/usr/bin/env python3
"""
List all Infoblox CSP sandbox accounts (spaces).

Usage:
    python list_sandboxes.py
    python list_sandboxes.py --verbose

Required env vars:
    INFOBLOX_EMAIL     - Admin email for CSP login
    INFOBLOX_PASSWORD  - Admin password for CSP login
    INFOBLOX_BASE_URL  - Optional, defaults to https://csp.infoblox.com
"""

import argparse
import json
import os
import sys

import requests


def authenticate(base_url, email, password):
    """Sign in to Infoblox CSP and return JWT token."""
    auth_url = f"{base_url}/v2/session/users/sign_in"
    resp = requests.post(auth_url, json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["jwt"]


def list_sandboxes(base_url, jwt):
    """Fetch all sandbox accounts (spaces)."""
    headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
    resp = requests.get(f"{base_url}/v2/accounts", headers=headers)
    resp.raise_for_status()
    return resp.json().get("results", [])


def main():
    parser = argparse.ArgumentParser(description="List Infoblox CSP sandboxes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed info")
    args = parser.parse_args()

    base_url = os.environ.get("INFOBLOX_BASE_URL", "https://csp.infoblox.com")
    email = os.environ.get("INFOBLOX_EMAIL")
    password = os.environ.get("INFOBLOX_PASSWORD")

    if not email or not password:
        print("Error: INFOBLOX_EMAIL and INFOBLOX_PASSWORD env vars are required")
        sys.exit(1)

    print("Authenticating to Infoblox CSP...", flush=True)
    jwt = authenticate(base_url, email, password)

    print("Fetching sandboxes...", flush=True)
    sandboxes = list_sandboxes(base_url, jwt)

    print(f"\nTotal sandboxes: {len(sandboxes)}\n")

    if args.verbose:
        print(json.dumps(sandboxes, indent=2))
    else:
        for sandbox in sandboxes:
            sandbox_id = sandbox.get("id", "").split("/")[-1]
            name = sandbox.get("name", "unknown")
            print(f"  {sandbox_id:30} {name}")


if __name__ == "__main__":
    main()
