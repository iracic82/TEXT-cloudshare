"""
Discover the CloudShare environment owner email for this VM.

Called during bootstrap on the VM. Uses the CloudShare API to:
1. List all environments
2. Find which environment contains this VM (matched by internal IP)
3. Return the ownerEmail

Usage:
    python3 discover_owner.py
    # prints the owner email to stdout

Required env vars:
    CLOUDSHARE_API_ID
    CLOUDSHARE_API_KEY
"""

import os
import sys
import socket
import cloudshare


def get_local_ips():
    """Get all local IP addresses on this machine."""
    ips = set()
    try:
        # Get hostname-based IP
        hostname = socket.gethostname()
        ips.add(socket.gethostbyname(hostname))
    except socket.error:
        pass

    # Get all interface IPs
    try:
        import subprocess
        result = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for ip in result.stdout.strip().split():
                ips.add(ip)
    except Exception:
        pass

    return ips


def find_my_environment(api_id, api_key):
    """Find the environment that contains this VM."""
    local_ips = get_local_ips()
    hostname = socket.gethostname()

    if not local_ips:
        print(f"Warning: could not determine local IPs", file=sys.stderr)
        return None

    print(f"Local IPs: {local_ips}", file=sys.stderr)
    print(f"Hostname: {hostname}", file=sys.stderr)

    # List all environments
    res = cloudshare.req(
        hostname="use.cloudshare.com",
        method="GET",
        path="envs",
        apiId=api_id,
        apiKey=api_key,
    )
    if res.status // 100 != 2:
        print(f"Failed to list environments: {res.status}", file=sys.stderr)
        return None

    # Check each environment for our VM
    for env in res.content:
        env_id = env["id"]
        try:
            detail = cloudshare.req(
                hostname="use.cloudshare.com",
                method="GET",
                path="envs/actions/getextended",
                queryParams={"envId": env_id},
                apiId=api_id,
                apiKey=api_key,
            )
            if detail.status // 100 != 2:
                continue

            for vm in detail.content.get("vms", []):
                vm_ips = set()
                if vm.get("externalAddress"):
                    vm_ips.add(vm["externalAddress"])
                for ip in vm.get("internalAddresses", []):
                    vm_ips.add(ip)

                # Match by IP
                if local_ips & vm_ips:
                    return detail.content

        except Exception as e:
            print(f"Error checking env {env_id}: {e}", file=sys.stderr)
            continue

    return None


def main():
    api_id = os.environ.get("CLOUDSHARE_API_ID")
    api_key = os.environ.get("CLOUDSHARE_API_KEY")

    if not api_id or not api_key:
        print("Error: CLOUDSHARE_API_ID and CLOUDSHARE_API_KEY required", file=sys.stderr)
        sys.exit(1)

    env_data = find_my_environment(api_id, api_key)

    if not env_data:
        print("Could not find my environment", file=sys.stderr)
        sys.exit(1)

    owner_email = env_data.get("ownerEmail", "")
    env_name = env_data.get("name", "")

    print(f"Environment: {env_name}", file=sys.stderr)
    print(f"Owner: {owner_email}", file=sys.stderr)

    # Print just the email to stdout (for capture by bootstrap script)
    print(owner_email)


if __name__ == "__main__":
    main()
