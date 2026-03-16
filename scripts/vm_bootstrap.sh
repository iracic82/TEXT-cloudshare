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

# ── Load credentials from lab.env ───────────────────────────────────
# Works whether or not lines start with "export"
if [ -f /opt/cloudshare-lab/lab.env ]; then
    set -a
    source /opt/cloudshare-lab/lab.env
    set +a
fi

# ── Configuration ───────────────────────────────────────────────────
INFOBLOX_BASE_URL="${INFOBLOX_BASE_URL:-https://csp.infoblox.com}"
Infoblox_Token="${Infoblox_Token:-}"
INFOBLOX_EMAIL="${INFOBLOX_EMAIL:-}"
INFOBLOX_PASSWORD="${INFOBLOX_PASSWORD:-}"

# ── Auto-discover from CloudShare API ───────────────────────────────
# Discovers: student email, environment ID, VM ID
# Uses VM ID as unique participant identifier (machine-id is same on clones)
if [ -n "${CLOUDSHARE_API_ID:-}" ] && [ -n "${CLOUDSHARE_API_KEY:-}" ]; then
    echo "Discovering environment from CloudShare..."
    DISCOVER_OUTPUT=$(cd "$SCRIPTS_DIR" && python3 discover_owner.py 2>/tmp/discover_debug.log)
    DISCOVER_EXIT=$?
    cat /tmp/discover_debug.log

    if [ $DISCOVER_EXIT -eq 0 ] && [ -n "$DISCOVER_OUTPUT" ]; then
        DISCOVERED_EMAIL=$(echo "$DISCOVER_OUTPUT" | awk '{print $1}')
        DISCOVERED_ENV_ID=$(echo "$DISCOVER_OUTPUT" | awk '{print $2}')
        DISCOVERED_VM_ID=$(echo "$DISCOVER_OUTPUT" | awk '{print $3}')

        if echo "$DISCOVERED_EMAIL" | grep -q "@"; then
            USER_EMAIL="$DISCOVERED_EMAIL"
            echo "Discovered student email: $USER_EMAIL"
        fi

        # Use VM ID for unique participant ID (each clone gets a different VM ID)
        if [ -n "$DISCOVERED_VM_ID" ]; then
            SHORT_VM_ID=$(echo "$DISCOVERED_VM_ID" | cut -c1-12)
            PARTICIPANT_ID="cloudshare-${SHORT_VM_ID}"
            echo "Using VM-based participant ID: $PARTICIPANT_ID"
        fi
    else
        echo "Warning: CloudShare discovery failed"
    fi
fi

# Fallback if discovery didn't set participant ID
if [ -z "${PARTICIPANT_ID:-}" ]; then
    MACHINE_ID=$(cat /etc/machine-id)
    SHORT_ID="${MACHINE_ID:0:8}"
    PARTICIPANT_ID="cloudshare-${SHORT_ID}"
fi

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

echo "Waiting 60 seconds for sandbox provisioning..."
sleep 60

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
cat > /root/lab-info.txt <<INFO
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
