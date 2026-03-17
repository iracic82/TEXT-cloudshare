#!/bin/bash
#####################################################################
# Root-owned wrapper for create_user.py
# Called by setup-my-lab with student email as argument
# Handles: user creation, saving email, updating MOTD banner
# Runs as root via sudoers - student never sees credentials
#####################################################################

STATE_DIR="/opt/cloudshare-lab/state"
SCRIPTS_DIR="/opt/cloudshare-lab/scripts"
ACTION="${1:-create}"
STUDENT_EMAIL="$2"
PARTICIPANT_ID="$3"

case "$ACTION" in
    create)
        if [ -z "$STUDENT_EMAIL" ] || [ -z "$PARTICIPANT_ID" ]; then
            echo "Usage: $0 create <email> <participant_id>"
            exit 1
        fi

        # Validate email format
        if ! echo "$STUDENT_EMAIL" | grep -qE '^[^@]+@[^@]+\.[^@]+$'; then
            echo "Invalid email"
            exit 1
        fi

        # Load credentials
        source /opt/cloudshare-lab/lab.env

        sleep 20

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

        if [ $? -eq 0 ] && [ -f "$STATE_DIR/user_id.txt" ]; then
            # Save student email
            echo "$STUDENT_EMAIL" > "$STATE_DIR/student_email.txt"
            chmod 644 "$STATE_DIR/student_email.txt"

            # Update MOTD banner
            SANDBOX_NAME=$(cat "$STATE_DIR/sandbox_name.txt" 2>/dev/null || echo "$PARTICIPANT_ID")
            cat > /usr/local/bin/lab-info << LABEOF
#!/bin/bash
echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║           Infoblox Lab Environment                   ║"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  Sandbox Name: $SANDBOX_NAME"
echo "  ║  Student:      $STUDENT_EMAIL"
echo "  ║  Portal:       https://portal.infoblox.com/"
echo "  ║  Status:       Ready"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  To find your sandbox in Infoblox Portal:             ║"
echo "  ║  Top-left menu → Find Account → paste Sandbox Name   ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""
LABEOF
            chmod +x /usr/local/bin/lab-info
            cp /usr/local/bin/lab-info /etc/update-motd.d/99-lab-info
        fi
        ;;

    reset)
        rm -f "$STATE_DIR/user_id.txt" "$STATE_DIR/student_email.txt"
        echo "User reset complete."
        ;;

    *)
        echo "Usage: $0 {create|reset} [email] [participant_id]"
        exit 1
        ;;
esac
