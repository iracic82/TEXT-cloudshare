#!/bin/bash
#####################################################################
# Student self-service lab setup
# Creates Infoblox Portal user with the student's email
#####################################################################

STATE_DIR="/opt/cloudshare-lab/state"
SCRIPTS_DIR="/opt/cloudshare-lab/scripts"

# Handle --reset flag
if [ "${1:-}" = "--reset" ]; then
    echo "  Resetting user setup..."
    sudo rm -f "$STATE_DIR/user_id.txt" "$STATE_DIR/student_email.txt"
fi

# Check if already completed
if [ -f "$STATE_DIR/user_id.txt" ]; then
    SANDBOX_NAME=$(cat "$STATE_DIR/sandbox_name.txt" 2>/dev/null || echo "unknown")
    STUDENT_EMAIL=$(cat "$STATE_DIR/student_email.txt" 2>/dev/null || echo "unknown")
    echo ""
    echo "  Lab is already set up!"
    echo "  Sandbox Name: $SANDBOX_NAME"
    echo "  Student:      $STUDENT_EMAIL"
    echo ""
    echo "  To find your sandbox in Infoblox Portal:"
    echo "  Top-left menu → Find Account → paste: $SANDBOX_NAME"
    echo ""
    echo "  To create a new user: setup-my-lab --reset"
    echo ""
    exit 0
fi

# Check if sandbox exists
if [ ! -f "$STATE_DIR/sandbox_id.txt" ]; then
    echo ""
    echo "  Lab sandbox is not ready yet."
    echo "  Please wait a few minutes and try again."
    echo ""
    exit 1
fi

SANDBOX_NAME=$(cat "$STATE_DIR/sandbox_name.txt" 2>/dev/null || echo "unknown")
PARTICIPANT_ID=$(cat "$STATE_DIR/participant_id.txt" 2>/dev/null || echo "unknown")

echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║         Infoblox Lab - Account Setup                 ║"
echo "  ╠══════════════════════════════════════════════════════╣"
echo "  ║  Sandbox Name: $SANDBOX_NAME"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""

# Ask for email
read -p "  Enter your email address: " STUDENT_EMAIL

if [ -z "$STUDENT_EMAIL" ] || ! echo "$STUDENT_EMAIL" | grep -q "@"; then
    echo "  Invalid email address. Please try again."
    exit 1
fi

echo ""
echo "  Creating your Infoblox Portal account..."
echo "  This takes about 60 seconds, please wait..."
echo ""

# Create user via sudo wrapper (student never sees credentials)
sudo /opt/cloudshare-lab/scripts/create_user_wrapper.sh "$STUDENT_EMAIL" "$PARTICIPANT_ID"

if [ $? -eq 0 ] && [ -f "$STATE_DIR/user_id.txt" ]; then
    # Save student email
    echo "$STUDENT_EMAIL" | sudo tee "$STATE_DIR/student_email.txt" > /dev/null

    # Update MOTD banner with student email
    sudo bash -c "
cat > /usr/local/bin/lab-info << 'LABEOF'
#!/bin/bash
echo ''
echo '  ╔══════════════════════════════════════════════════════╗'
echo '  ║           Infoblox Lab Environment                   ║'
echo '  ╠══════════════════════════════════════════════════════╣'
LABEOF
echo \"  echo \\\"  ║  Sandbox Name: $SANDBOX_NAME\\\"\" >> /usr/local/bin/lab-info
echo \"  echo \\\"  ║  Student:      $STUDENT_EMAIL\\\"\" >> /usr/local/bin/lab-info
echo \"  echo \\\"  ║  Portal:       https://portal.infoblox.com/\\\"\" >> /usr/local/bin/lab-info
echo \"  echo \\\"  ║  Status:       Ready\\\"\" >> /usr/local/bin/lab-info
cat >> /usr/local/bin/lab-info << 'LABEOF'
echo '  ╠══════════════════════════════════════════════════════╣'
echo '  ║  To find your sandbox in Infoblox Portal:             ║'
echo '  ║  Top-left menu → Find Account → paste Sandbox Name   ║'
echo '  ╚══════════════════════════════════════════════════════╝'
echo ''
LABEOF
chmod +x /usr/local/bin/lab-info
cp /usr/local/bin/lab-info /etc/update-motd.d/99-lab-info
"

    echo ""
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║  Setup complete!                                     ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  Sandbox Name: $SANDBOX_NAME"
    echo "  ║  Student:      $STUDENT_EMAIL"
    echo "  ║  Portal:       https://portal.infoblox.com/"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  Next steps:                                         ║"
    echo "  ║  1. Check your email for 'Account Activation'        ║"
    echo "  ║  2. Set your password                                ║"
    echo "  ║  3. Log into Infoblox Portal                         ║"
    echo "  ║  4. Find Account → paste: $SANDBOX_NAME"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo ""
else
    echo ""
    echo "  Error: Setup failed. Please try again or contact support."
    echo ""
    exit 1
fi
