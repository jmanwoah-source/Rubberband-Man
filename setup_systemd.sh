#!/usr/bin/env bash
# ==============================================================================
# Rubberband Man - Systemd User Service Installer (FastAPI + PWA & 24/7 Daemon)
# Dynamically renders and enables:
#   1. rubberbandman.service        (FastAPI + React PWA on ${PORT:-8080})
#   2. rubberbandman-daemon.service (daily_tracker_daemon.py 24/7 tracker/backup)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CURRENT_USER="${USER:-$(id -un)}"
SERVICE_DIR="${HOME}/.config/systemd/user"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

echo "===================================================================="
echo "Rubberband Man | Systemd 24/7 Service Setup"
echo "  Repo: ${SCRIPT_DIR}"
echo "  User: ${CURRENT_USER}"
echo "===================================================================="

# 1. Verify or bootstrap Python virtual environment (.venv)
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creating Python virtual environment at ${SCRIPT_DIR}/.venv..."
    if command -v python3 &>/dev/null; then
        python3 -m venv "${SCRIPT_DIR}/.venv"
    elif command -v python &>/dev/null; then
        python -m venv "${SCRIPT_DIR}/.venv"
    else
        echo "ERROR: python3 is not installed. Install with:"
        echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
        exit 1
    fi
    "$VENV_PYTHON" -m pip install -r "${SCRIPT_DIR}/requirements.txt"
elif ! "$VENV_PYTHON" -c "import fastapi, uvicorn" &>/dev/null; then
    echo "Installing missing Python dependencies into .venv..."
    "$VENV_PYTHON" -m pip install -r "${SCRIPT_DIR}/requirements.txt"
else
    echo "OK: Verified .venv Python runtime (${VENV_PYTHON})."
fi

# 2. Ensure runtime data directories exist
mkdir -p "${SCRIPT_DIR}/data/backups" "${SCRIPT_DIR}/intel_bus" "$SERVICE_DIR"

# 3. Verify React PWA bundle exists (build automatically if Node >= 20.19 is available)
if [ ! -f "${SCRIPT_DIR}/web/dist/index.html" ]; then
    echo "INFO: web/dist/index.html not found. Checking Node.js to build React PWA..."
    if command -v node &>/dev/null && command -v npm &>/dev/null; then
        NODE_VER="$(node -v | sed 's/^v//')"
        NODE_MAJOR="$(echo "$NODE_VER" | cut -d. -f1)"
        NODE_MINOR="$(echo "$NODE_VER" | cut -d. -f2)"
        if [ "$NODE_MAJOR" -gt 20 ] || { [ "$NODE_MAJOR" -eq 20 ] && [ "$NODE_MINOR" -ge 19 ]; }; then
            echo "Building React PWA with Node v${NODE_VER}..."
            npm --prefix "${SCRIPT_DIR}/web" ci
            npm --prefix "${SCRIPT_DIR}/web" run build
        else
            echo "WARNING: Node v${NODE_VER} is too old (Vite 8 requires Node >= 20.19 / 22 LTS)."
            echo "         FastAPI API will run, but PWA UI requires building web/dist with Node 22+."
        fi
    else
        echo "WARNING: Node.js/npm not found. Install Node 22 LTS and run:"
        echo "         npm --prefix web ci && npm --prefix web run build"
    fi
fi

# 4. Render systemd unit templates with actual repo path, user, and .venv Python
render_unit() {
    local template_name="$1"
    local src="${SCRIPT_DIR}/${template_name}"
    local dst="${SERVICE_DIR}/${template_name}"

    if [ ! -f "$src" ]; then
        echo "ERROR: Missing template unit file: ${src}"
        exit 1
    fi

    "$VENV_PYTHON" - "$src" "$dst" "$SCRIPT_DIR" "$CURRENT_USER" "$VENV_PYTHON" <<'PY'
import sys
from pathlib import Path

src, dst, repo_dir, user, py_bin = sys.argv[1:6]
content = Path(src).read_text(encoding="utf-8")
content = (
    content.replace("@REPO_DIR@", repo_dir)
    .replace("@USER@", user)
    .replace("@PYTHON_BIN@", py_bin)
)
Path(dst).write_text(content, encoding="utf-8", newline="\n")
PY
    echo "Installed unit: ${dst}"
}

render_unit "rubberbandman.service"
render_unit "rubberbandman-daemon.service"

# 5. Reload systemd user daemon and enable + start both services
systemctl --user daemon-reload
systemctl --user enable rubberbandman.service rubberbandman-daemon.service
systemctl --user restart rubberbandman.service rubberbandman-daemon.service

# 6. Enable lingering so user services survive SSH logout and unattended reboots
if command -v loginctl &>/dev/null; then
    LINGER_STATE="$(loginctl show-user "$CURRENT_USER" -p Linger --value 2>/dev/null || echo "no")"
    if [ "$LINGER_STATE" = "yes" ]; then
        echo "OK: User lingering is already enabled for '${CURRENT_USER}'."
    else
        if loginctl enable-linger "$CURRENT_USER" 2>/dev/null; then
            echo "OK: Enabled user lingering via loginctl (services persist after SSH logout)."
        else
            echo ""
            echo "WARNING: Could not enable systemd lingering without root privileges!"
            echo "         Without lingering, BOTH services will STOP when you log out of SSH."
            echo "         Run this once with sudo to make them truly 24/7 across reboots:"
            echo "           sudo loginctl enable-linger ${CURRENT_USER}"
            echo ""
        fi
    fi
else
    echo "WARNING: loginctl not found; ensure user services persist after logout on this host."
fi

# 7. Quick health check
APP_PORT="8080"
if [ -f "${SCRIPT_DIR}/.env" ]; then
    ENV_PORT="$(grep -E '^[[:space:]]*(export[[:space:]]+)?PORT=' "${SCRIPT_DIR}/.env" | tail -n 1 | cut -d= -f2- | tr -d "\"'[:space:]\r" || true)"
    if [ -n "$ENV_PORT" ]; then
        APP_PORT="$ENV_PORT"
    fi
fi

echo "--------------------------------------------------------------------"
echo "Rubberband Man services are active:"
echo "  API + PWA Status: systemctl --user status rubberbandman"
echo "  Daemon Status:    systemctl --user status rubberbandman-daemon"
echo "  API Logs:         journalctl --user -u rubberbandman -f"
echo "  Daemon Logs:      journalctl --user -u rubberbandman-daemon -f"
echo "  Health Endpoint:  http://127.0.0.1:${APP_PORT}/api/health"
echo "===================================================================="
