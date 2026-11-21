#!/usr/bin/env bash
# ==============================================================================
# Rubberband Man - Systemd Background Service Installer
# Installs Rubberband Man as an auto-starting user service on Linux
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_DIR="${HOME}/.config/systemd/user"

echo "===================================================================="
echo "🏹 Rubberband Man | Systemd Service Setup"
echo "===================================================================="

# Ensure directory exists
mkdir -p "$SERVICE_DIR"

# Generate customized service file for this specific installation path
SERVICE_FILE="${SERVICE_DIR}/rubberbandman.service"
cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Rubberband Man - AI Options Divergence Terminal
After=network.target

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${SCRIPT_DIR}/.venv/bin/python -m streamlit run rubberband.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=default.target
EOF

echo "✅ Generated service unit at: $SERVICE_FILE"

# Reload systemd and enable service
systemctl --user daemon-reload
systemctl --user enable rubberbandman.service
systemctl --user restart rubberbandman.service

# Enable lingering so service persists after SSH logout
if command -v loginctl &>/dev/null; then
    loginctl enable-linger "$USER" 2>/dev/null || true
    echo "✅ Enabled user lingering via loginctl (keeps running after logout)."
fi

echo "--------------------------------------------------------------------"
echo "🚀 Rubberband Man is now running in the background as a systemd service!"
echo "   Status:   systemctl --user status rubberbandman"
echo "   Logs:     journalctl --user -u rubberbandman -f"
echo "   Stop:     systemctl --user stop rubberbandman"
echo "   Restart:  systemctl --user restart rubberbandman"
echo "===================================================================="
