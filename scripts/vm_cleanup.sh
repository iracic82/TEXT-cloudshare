#!/bin/bash
###############################################################################
# VM Cleanup Script for CloudShare
#
# Run this when the lab environment is being torn down.
# Can be triggered via CloudShare webhook or manually.
###############################################################################

set -euo pipefail

LOG_FILE="/var/log/infoblox-lab-cleanup.log"
SCRIPTS_DIR="/opt/cloudshare-lab/scripts"
STATE_DIR="/opt/cloudshare-lab/state"

exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== Lab cleanup started at $(date) ==="

cd "$SCRIPTS_DIR"

INFOBLOX_BASE_URL="${INFOBLOX_BASE_URL:-https://csp.infoblox.com}"

# ── Step 1: Delete User ────────────────────────────────────────────
if [ -f "$STATE_DIR/user_id.txt" ]; then
    echo "--- Step 1: Deleting user ---"
    SANDBOX_ID_FILE="$STATE_DIR/sandbox_id.txt" \
    USER_ID_FILE="$STATE_DIR/user_id.txt" \
    INFOBLOX_BASE_URL="$INFOBLOX_BASE_URL" \
        python3 delete_user.py || echo "Warning: user deletion failed"
else
    echo "--- Step 1: Skipped (no user_id.txt) ---"
fi

# ── Step 2: Delete Sandbox ─────────────────────────────────────────
if [ -f "$STATE_DIR/sandbox_id.txt" ]; then
    echo "--- Step 2: Deleting sandbox ---"
    INFOBLOX_BASE_URL="$INFOBLOX_BASE_URL/v2" \
        python3 delete_sandbox.py \
            --sandbox-id-file "$STATE_DIR/sandbox_id.txt" || echo "Warning: sandbox deletion failed"
else
    echo "--- Step 2: Skipped (no sandbox_id.txt) ---"
fi

# ── Cleanup state ──────────────────────────────────────────────────
rm -f /tmp/lab-setup.lock
rm -f "$STATE_DIR"/*.txt

echo "=== Lab cleanup completed at $(date) ==="
