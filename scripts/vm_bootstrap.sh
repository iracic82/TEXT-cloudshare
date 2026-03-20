#!/bin/bash
###############################################################################
# VM Bootstrap Script for CloudShare Ubuntu Template
#
# Runs on boot via systemd. Creates Infoblox sandbox with a unique ID.
# Student completes setup by running 'setup-my-lab' to enter their email.
###############################################################################

set -euo pipefail

LOG_FILE="/var/log/infoblox-lab-setup.log"
SCRIPTS_DIR="/opt/cloudshare-lab/scripts"
STATE_DIR="/opt/cloudshare-lab/state"
LOCK_FILE="/tmp/lab-setup.lock"

exec > >(tee -a "$LOG_FILE") 2>&1
echo "=== Lab setup started at $(date) ==="

# Prevent concurrent execution
if [ -f "$LOCK_FILE" ]; then
    echo "Setup already running. Remove $LOCK_FILE to re-run."
    exit 0
fi
touch "$LOCK_FILE"

mkdir -p "$STATE_DIR"
chmod 755 "$STATE_DIR"

# ── Load credentials from lab.env ───────────────────────────────────
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

# ── Generate unique participant ID ──────────────────────────────────
# Use saved ID if exists (survives revert), otherwise generate new UUID
if [ -f "$STATE_DIR/participant_id.txt" ]; then
    PARTICIPANT_ID=$(cat "$STATE_DIR/participant_id.txt")
    echo "Using existing participant ID: $PARTICIPANT_ID"
else
    SHORT_UUID=$(uuidgen | cut -c1-12)
    PARTICIPANT_ID="cloudshare-${SHORT_UUID}"
    echo "$PARTICIPANT_ID" > "$STATE_DIR/participant_id.txt"
    echo "Generated new participant ID: $PARTICIPANT_ID"
fi

# ── Check if sandbox already exists (handles VM reset/revert) ───────
echo "Checking if sandbox already exists for $PARTICIPANT_ID..."
cd "$SCRIPTS_DIR"
EXISTING_SANDBOX=$(python3 -c "
from sandbox_api import SandboxAccountAPI
import os
api = SandboxAccountAPI(base_url=os.environ.get('INFOBLOX_BASE_URL', 'https://csp.infoblox.com'), token='$Infoblox_Token')
sid = api.get_sandbox_account_id_by_name('$PARTICIPANT_ID')
if sid:
    if sid.startswith('identity/accounts/'):
        sid = sid.split('/')[-1]
    print(sid)
" 2>/dev/null)

if [ -n "$EXISTING_SANDBOX" ]; then
    echo "Sandbox already exists: $EXISTING_SANDBOX"
    echo "$EXISTING_SANDBOX" > "$STATE_DIR/sandbox_id.txt"
    echo "$PARTICIPANT_ID" > "$STATE_DIR/sandbox_name.txt"
fi

# ── Create sandbox if it doesn't exist ──────────────────────────────
if [ ! -f "$STATE_DIR/sandbox_id.txt" ]; then
    echo "--- Creating Infoblox Sandbox ---"

    PARTICIPANT_ID="$PARTICIPANT_ID" \
    Infoblox_Token="$Infoblox_Token" \
    INFOBLOX_EMAIL="$INFOBLOX_EMAIL" \
    INFOBLOX_BASE_URL="$INFOBLOX_BASE_URL" \
        python3 create_sandbox.py \
            --participant-id "$PARTICIPANT_ID" \
            --sandbox-id-file "$STATE_DIR/sandbox_id.txt" \
            --external-id-file "$STATE_DIR/external_id.txt"

    echo "$PARTICIPANT_ID" > "$STATE_DIR/sandbox_name.txt"
    echo "Sandbox created: $PARTICIPANT_ID"
else
    echo "Sandbox already exists, skipping creation."
fi

# ── Create MOTD banner ──────────────────────────────────────────────
SANDBOX_NAME=$(cat "$STATE_DIR/sandbox_name.txt" 2>/dev/null || echo "$PARTICIPANT_ID")

cat > /usr/local/bin/lab-info << 'LABEOF'
#!/bin/bash
echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║           Infoblox Lab Environment                   ║"
echo "  ╠══════════════════════════════════════════════════════╣"
LABEOF
echo "  echo \"  ║  Sandbox Name: $SANDBOX_NAME\"" >> /usr/local/bin/lab-info
echo "  echo \"  ║  Portal:       https://portal.infoblox.com/\"" >> /usr/local/bin/lab-info
if [ -f "$STATE_DIR/user_id.txt" ]; then
    echo "  echo \"  ║  Status:       Ready\"" >> /usr/local/bin/lab-info
else
    echo "  echo \"  ║  Status:       Run 'setup-my-lab' to complete setup\"" >> /usr/local/bin/lab-info
fi
cat >> /usr/local/bin/lab-info << 'LABEOF'
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  To find your sandbox in Infoblox Portal:             ║"
echo "  ║  Top-left menu → Find Account → paste Sandbox Name   ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""
LABEOF
chmod +x /usr/local/bin/lab-info
cp /usr/local/bin/lab-info /etc/update-motd.d/99-lab-info
chmod +x /etc/update-motd.d/99-lab-info
chmod -x /etc/update-motd.d/10-help-text 2>/dev/null || true
chmod -x /etc/update-motd.d/50-motd-news 2>/dev/null || true
chmod -x /etc/update-motd.d/91-contract-ua-esm-status 2>/dev/null || true

# ── Install setup-my-lab command ────────────────────────────────────
cp "$SCRIPTS_DIR/setup_my_lab.sh" /usr/local/bin/setup-my-lab
chmod +x /usr/local/bin/setup-my-lab
chmod +x "$SCRIPTS_DIR/create_user_wrapper.sh"

# Allow student user to run the wrapper as root (no password)
echo "student ALL=(root) NOPASSWD: /opt/cloudshare-lab/scripts/create_user_wrapper.sh" > /etc/sudoers.d/student-lab
chmod 440 /etc/sudoers.d/student-lab

# Auto-prompt setup-my-lab on student's first login if not yet completed
if id student &>/dev/null; then
    if ! grep -q "setup-my-lab" /home/student/.bashrc 2>/dev/null; then
        cat >> /home/student/.bashrc << 'BASHRC'

# Auto-run lab setup if not yet completed
if [ ! -f /opt/cloudshare-lab/state/user_id.txt ]; then
    setup-my-lab
fi
BASHRC
    fi
fi

# ── Heartbeat cron - sends "I'm alive" every 5 min to GitHub Gist ───
chmod +x "$SCRIPTS_DIR/heartbeat.sh"
if [ -n "${GITHUB_TOKEN:-}" ]; then
    # Run first heartbeat immediately
    "$SCRIPTS_DIR/heartbeat.sh"
    # Schedule every 5 minutes
    (crontab -l 2>/dev/null; echo "*/5 * * * * /opt/cloudshare-lab/scripts/heartbeat.sh") | sort -u | crontab -
    echo "Heartbeat cron installed (every 5 min)"
fi

rm -f "$LOCK_FILE"
echo "=== Lab bootstrap completed at $(date) ==="
echo "=== Student needs to run 'setup-my-lab' to complete setup ==="
