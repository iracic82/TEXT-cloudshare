#!/bin/bash
#####################################################################
# Root-owned wrapper for create_user.py
# Called by setup-my-lab with student email as argument
# This script runs as root via sudoers - student never sees credentials
#####################################################################

STATE_DIR="/opt/cloudshare-lab/state"
SCRIPTS_DIR="/opt/cloudshare-lab/scripts"
STUDENT_EMAIL="$1"
PARTICIPANT_ID="$2"

if [ -z "$STUDENT_EMAIL" ] || [ -z "$PARTICIPANT_ID" ]; then
    echo "Usage: $0 <email> <participant_id>"
    exit 1
fi

# Validate email format
if ! echo "$STUDENT_EMAIL" | grep -qE '^[^@]+@[^@]+\.[^@]+$'; then
    echo "Invalid email"
    exit 1
fi

# Load credentials
source /opt/cloudshare-lab/lab.env

sleep 60

cd "$SCRIPTS_DIR"

SANDBOX_ID_FILE="$STATE_DIR/sandbox_id.txt" \
USER_ID_FILE="$STATE_DIR/user_id.txt" \
INFOBLOX_EMAIL="${INFOBLOX_EMAIL}" \
INFOBLOX_PASSWORD="${INFOBLOX_PASSWORD}" \
INFOBLOX_BASE_URL="${INFOBLOX_BASE_URL:-https://csp.infoblox.com}" \
    python3 create_user.py \
        --participant-id "$PARTICIPANT_ID" \
        --user-email "$STUDENT_EMAIL" \
        --sandbox-id-file "$STATE_DIR/sandbox_id.txt" \
        --user-id-file "$STATE_DIR/user_id.txt"
