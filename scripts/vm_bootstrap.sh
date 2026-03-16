#!/bin/bash
###############################################################################
# VM Bootstrap Script for CloudShare Ubuntu Template
#
# Bake this into your CloudShare blueprint/VM template.
# It runs on first boot and sets up the Infoblox lab environment.
#
# BEFORE creating the template:
#   1. Clone the repo onto the VM
#   2. Install dependencies
#   3. Configure this script to run on boot (systemd or rc.local)
#   4. Set the required variables below or via CloudShare custom data
#
# The script uses the VM's machine-id as a unique participant identifier
# (replacing Instruqt's INSTRUQT_PARTICIPANT_ID).
###############################################################################

set -euo pipefail

LOG_FILE="/var/log/infoblox-lab-setup.log"
SCRIPTS_DIR="/opt/cloudshare-lab/scripts"
STATE_DIR="/opt/cloudshare-lab/state"
LOCK_FILE="/tmp/lab-setup.lock"

exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== Lab setup started at $(date) ==="

# Prevent double execution
if [ -f "$LOCK_FILE" ]; then
    echo "Setup already running or completed. Remove $LOCK_FILE to re-run."
    exit 0
fi
touch "$LOCK_FILE"

mkdir -p "$STATE_DIR"

# ── Configuration ───────────────────────────────────────────────────
# These can be set as environment variables, or hardcoded for the template.
# CloudShare custom data / environment variables take precedence.

INFOBLOX_BASE_URL="${INFOBLOX_BASE_URL:-https://csp.infoblox.com}"
Infoblox_Token="${Infoblox_Token:-}"
INFOBLOX_EMAIL="${INFOBLOX_EMAIL:-}"
INFOBLOX_PASSWORD="${INFOBLOX_PASSWORD:-}"
USER_EMAIL="${USER_EMAIL:-}"

# Use machine-id as unique participant identifier
# Each CloudShare VM clone gets a unique machine-id
PARTICIPANT_ID="${PARTICIPANT_ID:-$(cat /etc/machine-id)}"

echo "Participant ID: $PARTICIPANT_ID"

# ── Step 1: Create Infoblox Sandbox ─────────────────────────────────
echo "--- Step 1: Creating Infoblox Sandbox ---"
cd "$SCRIPTS_DIR"

PARTICIPANT_ID="$PARTICIPANT_ID" \
Infoblox_Token="$Infoblox_Token" \
INFOBLOX_EMAIL="$INFOBLOX_EMAIL" \
INFOBLOX_BASE_URL="$INFOBLOX_BASE_URL" \
    python3 create_sandbox.py \
        --participant-id "$PARTICIPANT_ID" \
        --sandbox-id-file "$STATE_DIR/sandbox_id.txt" \
        --external-id-file "$STATE_DIR/external_id.txt"

echo "Sandbox created. ID: $(cat $STATE_DIR/sandbox_id.txt)"

# ── Step 2: Create User ────────────────────────────────────────────
if [ -n "$USER_EMAIL" ] && [ -n "$INFOBLOX_PASSWORD" ]; then
    echo "--- Step 2: Creating User ---"

    SANDBOX_ID_FILE="$STATE_DIR/sandbox_id.txt" \
    USER_ID_FILE="$STATE_DIR/user_id.txt" \
    INFOBLOX_EMAIL="$INFOBLOX_EMAIL" \
    INFOBLOX_PASSWORD="$INFOBLOX_PASSWORD" \
    INFOBLOX_BASE_URL="$INFOBLOX_BASE_URL" \
        python3 create_user.py \
            --participant-id "$PARTICIPANT_ID" \
            --user-email "$USER_EMAIL" \
            --sandbox-id-file "$STATE_DIR/sandbox_id.txt" \
            --user-id-file "$STATE_DIR/user_id.txt"

    echo "User created. ID: $(cat $STATE_DIR/user_id.txt)"
else
    echo "--- Step 2: Skipped (USER_EMAIL or INFOBLOX_PASSWORD not set) ---"
fi

# ── Step 3: Custom setup (add your lab-specific commands here) ──────
echo "--- Step 3: Custom lab setup ---"

# Example: Write lab info to a file the student can see
cat > /home/ubuntu/lab-info.txt <<INFO
====================================
  Infoblox Lab Environment
====================================
Participant ID:  $PARTICIPANT_ID
Sandbox ID:      $(cat $STATE_DIR/sandbox_id.txt 2>/dev/null || echo 'N/A')
External ID:     $(cat $STATE_DIR/external_id.txt 2>/dev/null || echo 'N/A')
Setup completed: $(date)
====================================
INFO

echo "=== Lab setup completed at $(date) ==="
