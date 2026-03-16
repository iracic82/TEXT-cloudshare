#!/bin/bash
###############################################################################
# Install lab scripts onto a CloudShare Ubuntu VM
#
# Run this ONCE on the VM before saving it as a CloudShare blueprint/template.
# It installs dependencies, copies scripts, and sets up auto-run on boot.
#
# Usage:
#   # From your machine, push to the VM via CloudShare executePath:
#   python run_on_vm.py --env-id EN123 --script install_on_vm.sh
#
#   # Or SSH into the VM and run directly:
#   curl -sL https://raw.githubusercontent.com/iracic82/Infoblox-PoC/main/scripts/install_on_vm.sh | bash
###############################################################################

set -euo pipefail

INSTALL_DIR="/opt/cloudshare-lab"
SCRIPTS_DIR="$INSTALL_DIR/scripts"
STATE_DIR="$INSTALL_DIR/state"
REPO_URL="https://github.com/iracic82/TEXT-cloudshare.git"

echo "=== Installing CloudShare lab scripts ==="

# Install Python dependencies
apt-get update -qq
apt-get install -y -qq python3 python3-pip git
pip3 install requests cloudshare

# Clone or update the repo
if [ -d "$INSTALL_DIR/.git" ]; then
    cd "$INSTALL_DIR" && git pull
else
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Copy CloudShare-specific scripts (overwrite Instruqt versions)
# This assumes you've pushed the CloudShare scripts to the repo
mkdir -p "$SCRIPTS_DIR" "$STATE_DIR"

# Set up the bootstrap service (runs on first boot of each clone)
cat > /etc/systemd/system/infoblox-lab-setup.service <<'EOF'
[Unit]
Description=Infoblox Lab Setup
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/opt/cloudshare-lab/scripts/vm_bootstrap.sh
RemainAfterExit=yes
EnvironmentFile=-/opt/cloudshare-lab/lab.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable infoblox-lab-setup.service

# Create the env file template (edit before saving as blueprint)
cat > "$INSTALL_DIR/lab.env" <<'EOF'
# Edit these before saving the VM as a CloudShare blueprint
Infoblox_Token=YOUR_TOKEN_HERE
INFOBLOX_EMAIL=admin@infoblox.com
INFOBLOX_PASSWORD=YOUR_PASSWORD_HERE
USER_EMAIL=student@example.com
EOF

chmod 600 "$INSTALL_DIR/lab.env"

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit /opt/cloudshare-lab/lab.env with your Infoblox credentials"
echo "  2. Test by running: /opt/cloudshare-lab/scripts/vm_bootstrap.sh"
echo "  3. Save this VM as a CloudShare blueprint/template"
echo "  4. Each clone will auto-run setup on first boot"
echo ""
