"""
Cleanup orphaned Infoblox sandboxes using GitHub Gist heartbeats.

Each running VM sends a heartbeat every 5 minutes to a GitHub Gist.
This script reads all Gists, finds sandboxes with stale heartbeats
(no update in 15+ minutes), and deletes them from Infoblox CSP.

No CloudShare API calls needed - purely Gist + Infoblox CSP.

Usage:
    python cleanup_orphans.py              # dry run
    python cleanup_orphans.py --delete     # actually delete

Env vars:
    GITHUB_TOKEN      - GitHub token (same as VMs use for Gists)
    INFOBLOX_TOKEN    - Infoblox CSP API token
"""

import argparse
import os
import sys
import json
from datetime import datetime, timezone

import requests


def get_heartbeat_gists(github_token):
    """Find all CloudShare Lab Heartbeat gists."""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(
        "https://api.github.com/gists",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()

    heartbeat_gists = []
    for gist in resp.json():
        if "CloudShare Lab Heartbeats" in (gist.get("description") or ""):
            heartbeat_gists.append(gist)

    return heartbeat_gists


def parse_heartbeats(github_token, gists):
    """Parse heartbeat data from all gists."""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    heartbeats = []

    for gist in gists:
        # Get full gist content
        resp = requests.get(
            f"https://api.github.com/gists/{gist['id']}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        full_gist = resp.json()

        for filename, file_data in full_gist.get("files", {}).items():
            content = file_data.get("content", "").strip()
            if not content or "|" not in content:
                continue

            parts = content.split("|")
            if len(parts) >= 3:
                heartbeats.append({
                    "sandbox_name": parts[0],
                    "sandbox_id": parts[1],
                    "timestamp": parts[2],
                    "gist_id": gist["id"],
                    "filename": filename,
                })

    return heartbeats


def is_stale(timestamp_str, max_age_minutes=15):
    """Check if a heartbeat timestamp is older than max_age_minutes."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_minutes = (now - ts).total_seconds() / 60
        return age_minutes > max_age_minutes, round(age_minutes, 1)
    except Exception:
        return True, -1


def delete_sandbox(token, sandbox_id):
    """Delete a sandbox from Infoblox CSP."""
    headers = {"Authorization": f"token {token}", "Accept": "application/json"}
    try:
        resp = requests.delete(
            f"https://csp.infoblox.com/v2/sandbox/accounts/{sandbox_id}",
            headers=headers,
            timeout=30,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def delete_gist_file(github_token, gist_id, filename):
    """Remove a file from a gist (cleanup after sandbox deletion)."""
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        requests.patch(
            f"https://api.github.com/gists/{gist_id}",
            headers=headers,
            json={"files": {filename: None}},
            timeout=30,
        )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Cleanup orphaned Infoblox sandboxes")
    parser.add_argument("--delete", action="store_true", help="Actually delete orphans")
    parser.add_argument("--stale-minutes", type=int, default=15,
                        help="Consider stale after N minutes (default: 15)")
    args = parser.parse_args()

    github_token = os.environ.get("GITHUB_TOKEN")
    infoblox_token = os.environ.get("INFOBLOX_TOKEN") or os.environ.get("Infoblox_Token")

    if not github_token or not infoblox_token:
        print("Error: Set GITHUB_TOKEN and INFOBLOX_TOKEN")
        sys.exit(1)

    print(f"Cleanup run: {datetime.now(timezone.utc).isoformat()}")
    print(f"Stale threshold: {args.stale_minutes} minutes")
    print()

    # Get heartbeats
    print("Reading heartbeat gists...")
    gists = get_heartbeat_gists(github_token)
    print(f"  Found {len(gists)} heartbeat gists")

    heartbeats = parse_heartbeats(github_token, gists)
    print(f"  Found {len(heartbeats)} sandbox heartbeats")
    print()

    # Classify
    alive = []
    stale = []

    for hb in heartbeats:
        is_old, age_min = is_stale(hb["timestamp"], args.stale_minutes)
        hb["age_minutes"] = age_min
        if is_old:
            stale.append(hb)
        else:
            alive.append(hb)

    print(f"Alive ({len(alive)}):")
    for h in alive:
        print(f"  {h['sandbox_name']:30s} | last seen {h['age_minutes']}min ago")

    print(f"\nStale ({len(stale)}):")
    for h in stale:
        print(f"  {h['sandbox_name']:30s} | last seen {h['age_minutes']}min ago")

    if not stale:
        print("\nAll sandboxes alive. Nothing to clean up!")
        return

    if not args.delete:
        print(f"\nDry run - would delete {len(stale)} sandboxes.")
        print("Run with --delete to actually delete them.")
        return

    print(f"\nDeleting {len(stale)} stale sandboxes...")
    for h in stale:
        ok = delete_sandbox(infoblox_token, h["sandbox_id"])
        if ok:
            print(f"  Deleted: {h['sandbox_name']} (sandbox)")
            delete_gist_file(github_token, h["gist_id"], h["filename"])
            print(f"  Cleaned: {h['sandbox_name']} (heartbeat)")
        else:
            print(f"  FAILED:  {h['sandbox_name']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
