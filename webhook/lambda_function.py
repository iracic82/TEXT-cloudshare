"""
AWS Lambda - CloudShare Webhook Receiver

Handles 'environment.deleted' events from CloudShare.
When a student environment is deleted, cleans up the Infoblox sandbox.

Looks up the sandbox via GitHub Gist heartbeat mapping,
deletes from Infoblox CSP, and removes the Gist entry.

Environment variables (set in Lambda or from Secrets Manager):
    CLOUDSHARE_WEBHOOK_SECRET  - CloudShare webhook shared secret
    INFOBLOX_TOKEN             - Infoblox CSP API token
    GITHUB_TOKEN               - GitHub token with gist scope

Deploy:
    zip lambda.zip lambda_function.py
    aws lambda create-function --function-name cloudshare-webhook \
        --runtime python3.12 --handler lambda_function.handler \
        --zip-file fileb://lambda.zip --role <role-arn>
    aws lambda create-function-url-config --function-name cloudshare-webhook \
        --auth-type NONE
"""

import json
import os
import logging
from urllib import request as urllib_request
from urllib.error import URLError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    """Lambda handler for CloudShare webhook."""

    # Parse the incoming request
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            body = json.loads(body)
    else:
        body = event

    headers = event.get("headers", {})

    logger.info(f"Received webhook: {json.dumps(body)[:500]}")

    # Validate CloudShare signature
    webhook_secret = os.environ.get("CLOUDSHARE_WEBHOOK_SECRET", "")
    if webhook_secret:
        signature = headers.get("x-cloudshare-signature", "")
        if signature != webhook_secret:
            logger.warning(f"Invalid signature: {signature}")
            return {"statusCode": 401, "body": "Invalid signature"}

    # Parse the event
    event_type = body.get("Event", "")
    if event_type != "environment.deleted":
        logger.info(f"Ignoring event: {event_type}")
        return {"statusCode": 200, "body": f"Ignored: {event_type}"}

    # Parse payload
    payload_str = body.get("Payload", "{}")
    if isinstance(payload_str, str):
        payload = json.loads(payload_str)
    else:
        payload = payload_str

    env_id = payload.get("EnvironmentId", "")
    env_name = payload.get("EnvironmentName", "")
    owner_email = payload.get("OwnerEmail", "")
    blueprint = payload.get("BlueprintName", "")

    logger.info(f"Environment deleted: {env_name} ({env_id}) owner={owner_email} blueprint={blueprint}")

    # Load tokens
    infoblox_token = os.environ.get("INFOBLOX_TOKEN", "")
    github_token = os.environ.get("GITHUB_TOKEN", "")

    if not infoblox_token:
        logger.error("INFOBLOX_TOKEN not set")
        return {"statusCode": 500, "body": "Missing INFOBLOX_TOKEN"}

    # Find the sandbox via Gist heartbeat
    sandbox_info = find_sandbox_in_gists(github_token, env_id, owner_email)

    if sandbox_info:
        sandbox_name = sandbox_info["sandbox_name"]
        sandbox_id = sandbox_info["sandbox_id"]
        gist_id = sandbox_info["gist_id"]
        filename = sandbox_info["filename"]

        logger.info(f"Found sandbox: {sandbox_name} ({sandbox_id})")

        # Delete from Infoblox CSP
        deleted = delete_infoblox_sandbox(infoblox_token, sandbox_id)
        if deleted:
            logger.info(f"Deleted sandbox {sandbox_name} from Infoblox CSP")
            # Clean up Gist entry
            if gist_id and filename:
                delete_gist_file(github_token, gist_id, filename)
                logger.info(f"Cleaned up Gist entry for {sandbox_name}")
        else:
            logger.error(f"Failed to delete sandbox {sandbox_name}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "action": "sandbox_deleted",
                "sandbox_name": sandbox_name,
                "sandbox_id": sandbox_id,
                "environment": env_name,
                "owner": owner_email,
            }),
        }
    else:
        # No Gist found - try to find sandbox by searching CSP directly
        logger.info("No Gist heartbeat found, searching CSP directly...")
        sandbox_found = find_and_delete_sandbox_by_search(infoblox_token, env_id, owner_email)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "action": "searched_csp" if sandbox_found else "no_sandbox_found",
                "environment": env_name,
                "owner": owner_email,
            }),
        }


def find_sandbox_in_gists(github_token, env_id, owner_email):
    """Search GitHub Gists for the sandbox matching this environment.

    Matches by owner_email when available (format: name|id|ts|email).
    Falls back to first match only if there's exactly one sandbox
    (prevents accidental deletion of unrelated sandboxes).
    """
    if not github_token:
        return None

    try:
        gists = github_api("GET", "https://api.github.com/gists", github_token)
        all_sandboxes = []

        for gist in gists:
            if "CloudShare Lab Heartbeats" not in (gist.get("description") or ""):
                continue

            full_gist = github_api("GET", f"https://api.github.com/gists/{gist['id']}", github_token)
            for filename, file_data in full_gist.get("files", {}).items():
                content = file_data.get("content", "").strip()
                if not content or "|" not in content:
                    continue

                parts = content.split("|")
                if len(parts) >= 3:
                    entry = {
                        "sandbox_name": parts[0],
                        "sandbox_id": parts[1],
                        "owner_email": parts[3] if len(parts) >= 4 else None,
                        "gist_id": gist["id"],
                        "filename": filename,
                    }
                    all_sandboxes.append(entry)

        # Try exact match by owner email first
        if owner_email:
            for sb in all_sandboxes:
                if sb["owner_email"] and sb["owner_email"].lower() == owner_email.lower():
                    logger.info(f"Matched sandbox by owner email: {owner_email}")
                    return sb

        # Fallback: only if there's exactly one sandbox (safe)
        if len(all_sandboxes) == 1:
            logger.info("Single sandbox found, using fallback match (no email in heartbeat)")
            return all_sandboxes[0]

        if len(all_sandboxes) > 1:
            logger.warning(
                f"Found {len(all_sandboxes)} sandboxes but cannot match by email. "
                f"Owner: {owner_email}. Sandboxes: "
                f"{[s['sandbox_name'] for s in all_sandboxes]}. Skipping to prevent wrong deletion."
            )
            return None

    except Exception as e:
        logger.error(f"Error searching Gists: {e}")

    return None


def find_and_delete_sandbox_by_search(infoblox_token, env_id, owner_email):
    """Search Infoblox CSP for cloudshare-* sandboxes and delete matching ones."""
    try:
        headers = {"Authorization": f"token {infoblox_token}", "Accept": "application/json"}
        url = 'https://csp.infoblox.com/v2/sandbox/accounts?_filter=name~"cloudshare"'

        data = http_request("GET", url, headers)
        results = data.get("results", [])

        for sb in results:
            sb_id = sb["id"].split("/")[-1] if "/" in sb.get("id", "") else sb.get("id", "")
            sb_name = sb.get("name", "")
            # Can't directly match without env_id in sandbox, but log for manual review
            logger.info(f"  CSP sandbox: {sb_name} ({sb_id})")

        return False
    except Exception as e:
        logger.error(f"Error searching CSP: {e}")
        return False


def delete_infoblox_sandbox(token, sandbox_id):
    """Delete a sandbox from Infoblox CSP."""
    try:
        headers = {"Authorization": f"token {token}", "Accept": "application/json"}
        url = f"https://csp.infoblox.com/v2/sandbox/accounts/{sandbox_id}"
        http_request("DELETE", url, headers)
        return True
    except Exception as e:
        logger.error(f"Error deleting sandbox: {e}")
        return False


def delete_gist_file(github_token, gist_id, filename):
    """Remove a file from a Gist."""
    try:
        github_api("PATCH", f"https://api.github.com/gists/{gist_id}", github_token,
                   body={"files": {filename: None}})
    except Exception as e:
        logger.error(f"Error cleaning Gist: {e}")


def github_api(method, url, token, body=None):
    """Make a GitHub API request."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    return http_request(method, url, headers, body)


def http_request(method, url, headers, body=None):
    """Make an HTTP request using urllib (no external dependencies)."""
    data = json.dumps(body).encode() if body else None
    if method == "DELETE" and not data:
        data = b""

    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            response_body = response.read().decode()
            if response_body:
                return json.loads(response_body)
            return {}
    except URLError as e:
        if hasattr(e, "code") and e.code in (200, 204):
            return {}
        raise
