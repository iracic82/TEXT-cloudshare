"""
Discover the CloudShare environment owner email for this VM.

Called during bootstrap on the VM. Uses the CloudShare API to:
1. List all environments
2. Find which environment contains this VM (matched by internal IP)
3. If multiple matches, pick the student env (not the instructor/original)
4. Return the ownerEmail and environment ID

Usage:
    python3 discover_owner.py
    # prints: ownerEmail envId vmId (space-separated) to stdout

Required env vars:
    CLOUDSHARE_API_ID
    CLOUDSHARE_API_KEY
"""

import os
import sys
import socket
import subprocess
import cloudshare


def get_local_ips():
    """Get all local IP addresses on this machine."""
    ips = set()
    try:
        hostname = socket.gethostname()
        ips.add(socket.gethostbyname(hostname))
    except socket.error:
        pass

    try:
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
    """Find the environment that contains this VM.

    If multiple environments match (e.g. original + clone both running),
    prefer the one that is NOT the instructor/blueprint-source environment
    (i.e. the one with a student ownerEmail).
    """
    local_ips = get_local_ips()

    if not local_ips:
        print("Warning: could not determine local IPs", file=sys.stderr)
        return None, None

    print(f"Local IPs: {local_ips}", file=sys.stderr)

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
        return None, None

    # Collect ALL matching environments
    matches = []

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

            d = detail.content
            for vm in d.get("vms", []):
                vm_ips = set()
                if vm.get("externalAddress"):
                    vm_ips.add(vm["externalAddress"])
                for ip in vm.get("internalAddresses", []):
                    vm_ips.add(ip)

                if local_ips & vm_ips:
                    matches.append({
                        "env": d,
                        "vm_id": vm["id"],
                        "owner": d.get("ownerEmail", ""),
                        "name": d.get("name", ""),
                        "env_id": env_id,
                    })
                    print(f"  Match: {d.get('name')} owner={d.get('ownerEmail')} vm={vm['id']}", file=sys.stderr)

        except Exception as e:
            print(f"Error checking env {env_id}: {e}", file=sys.stderr)
            continue

    if not matches:
        return None, None

    if len(matches) == 1:
        return matches[0]["env"], matches[0]["vm_id"]

    # Multiple matches - prefer the student environment (not the instructor's)
    # The instructor's env is typically named differently or is the blueprint source
    # Student envs are named after the blueprint (e.g. "Infoblox-CloudShare-Lab")
    # or have a different ownerEmail than the instructor
    print(f"Found {len(matches)} matching environments, picking student env...", file=sys.stderr)

    # Get instructor email from class API to filter it out
    instructor_email = None
    try:
        classes_res = cloudshare.req(
            hostname="use.cloudshare.com",
            method="GET",
            path="class",
            apiId=api_id,
            apiKey=api_key,
        )
        if classes_res.status // 100 == 2 and classes_res.content:
            instructor_email = classes_res.content[0].get("instructorEmail")
            print(f"  Instructor email: {instructor_email}", file=sys.stderr)
    except Exception:
        pass

    # Prefer non-instructor environment
    if instructor_email:
        student_matches = [m for m in matches if m["owner"] != instructor_email]
        if student_matches:
            return student_matches[0]["env"], student_matches[0]["vm_id"]

    # Fallback: pick the most recently created (last in list)
    return matches[-1]["env"], matches[-1]["vm_id"]


def main():
    api_id = os.environ.get("CLOUDSHARE_API_ID")
    api_key = os.environ.get("CLOUDSHARE_API_KEY")

    if not api_id or not api_key:
        print("Error: CLOUDSHARE_API_ID and CLOUDSHARE_API_KEY required", file=sys.stderr)
        sys.exit(1)

    env_data, vm_id = find_my_environment(api_id, api_key)

    if not env_data:
        print("Could not find my environment", file=sys.stderr)
        sys.exit(1)

    owner_email = env_data.get("ownerEmail", "")
    env_name = env_data.get("name", "")
    env_id = env_data.get("id", "")

    print(f"Environment: {env_name}", file=sys.stderr)
    print(f"Owner: {owner_email}", file=sys.stderr)
    print(f"VM ID: {vm_id}", file=sys.stderr)

    # Print email, env_id, vm_id to stdout (space-separated for capture)
    print(f"{owner_email} {env_id} {vm_id}")


if __name__ == "__main__":
    main()
