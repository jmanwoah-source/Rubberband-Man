#!/usr/bin/env bash
# ==============================================================================
# Rubberband Man - 1-Command ASUS GX10 Remote Update & Deploy Script
# Performs:
#   1. Fast-forward git pull
#   2. Conditional pip install (if requirements.txt changed or --force-deps)
#   3. Conditional React PWA build (if web/ changed, web/dist missing, or --force-build)
#   4. Online SQLite backup via diary_db.backup_diary_db('pre_deploy')
#   5. Restart of rubberbandman.service & rubberbandman-daemon.service
#   6. HTTP health verification against /api/health
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

FORCE_DEPS=0
FORCE_BUILD=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --force-deps)
            FORCE_DEPS=1
            ;;
        --force-build)
            FORCE_BUILD=1
            ;;
        -h|--help)
            sed -n '2,10p' "$0"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $1"
            echo "Usage: ./deploy_gx10.sh [--force-deps] [--force-build]"
            exit 1
            ;;
    esac
    shift
done

VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python"

# Resolve configured PORT from .env if not overridden in environment
APP_PORT="${PORT:-}"
if [ -z "$APP_PORT" ] && [ -f "${SCRIPT_DIR}/.env" ]; then
    APP_PORT="$(grep -E '^[[:space:]]*(export[[:space:]]+)?PORT=' "${SCRIPT_DIR}/.env" | tail -n 1 | cut -d= -f2- | tr -d "\"'[:space:]\r" || true)"
fi
APP_PORT="${APP_PORT:-8080}"

echo "===================================================================="
echo "Rubberband Man | ASUS GX10 Deploy"
echo "  Repo: ${SCRIPT_DIR}"
echo "  Port: ${APP_PORT}"
echo "===================================================================="

# 1. Pull latest commits cleanly (fast-forward only)
OLD_HEAD="$(git rev-parse HEAD)"
echo "[1/6] Pulling latest commits (git pull --ff-only)..."
git pull --ff-only
NEW_HEAD="$(git rev-parse HEAD)"

CHANGED_FILES=""
if [ "$OLD_HEAD" != "$NEW_HEAD" ]; then
    CHANGED_FILES="$(git diff --name-only "$OLD_HEAD" "$NEW_HEAD")"
    echo "Updated HEAD: ${OLD_HEAD:0:8} -> ${NEW_HEAD:0:8}"
else
    echo "Repository already up to date at ${NEW_HEAD:0:8}."
fi

# 2. Ensure .venv exists and update Python deps if requirements.txt changed
echo "[2/6] Checking Python dependencies..."
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Creating missing .venv..."
    python3 -m venv "${SCRIPT_DIR}/.venv"
    FORCE_DEPS=1
fi

if [ "$FORCE_DEPS" -eq 1 ] || printf '%s\n' "$CHANGED_FILES" | grep -qx "requirements.txt"; then
    echo "Installing/updating Python packages from requirements.txt..."
    "$VENV_PYTHON" -m pip install -r "${SCRIPT_DIR}/requirements.txt"
else
    echo "OK: requirements.txt unchanged; skipping pip install."
fi

# 3. Rebuild React PWA if web/ changed or web/dist is missing
echo "[3/6] Checking React PWA frontend build..."
if [ "$FORCE_BUILD" -eq 1 ] || [ ! -f "${SCRIPT_DIR}/web/dist/index.html" ] || printf '%s\n' "$CHANGED_FILES" | grep -q "^web/"; then
    if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
        echo "ERROR: Node.js (>= 20.19 / 22 LTS) and npm are required to build web/dist."
        exit 1
    fi
    NODE_VER="$(node -v | sed 's/^v//')"
    NODE_MAJOR="$(echo "$NODE_VER" | cut -d. -f1)"
    NODE_MINOR="$(echo "$NODE_VER" | cut -d. -f2)"
    if [ "$NODE_MAJOR" -lt 20 ] || { [ "$NODE_MAJOR" -eq 20 ] && [ "$NODE_MINOR" -lt 19 ]; }; then
        echo "ERROR: Node v${NODE_VER} detected; Vite 8 requires Node >= 20.19 (recommended: Node 22 LTS)."
        exit 1
    fi
    echo "Building React PWA with Node v${NODE_VER}..."
    npm --prefix "${SCRIPT_DIR}/web" ci
    npm --prefix "${SCRIPT_DIR}/web" run build
else
    echo "OK: web/ unchanged and web/dist present; skipping npm build."
fi

# 4. Take an online SQLite backup BEFORE restarting services
echo "[4/6] Taking online SQLite backup (tag: pre_deploy)..."
"$VENV_PYTHON" -c "import diary_db; p = diary_db.backup_diary_db('pre_deploy'); print('Backup saved:', p)"

# 5. Restart systemd services (refresh unit files first if templates changed)
echo "[5/6] Restarting systemd user services..."
if printf '%s\n' "$CHANGED_FILES" | grep -Eq "^(rubberbandman\.service|rubberbandman-daemon\.service)$"; then
    echo "Service unit templates changed; running ./setup_systemd.sh to refresh units..."
    bash "${SCRIPT_DIR}/setup_systemd.sh"
else
    systemctl --user daemon-reload
    systemctl --user restart rubberbandman.service rubberbandman-daemon.service
fi

# 6. Verify API health endpoint (with short startup retry window)
echo "[6/6] Verifying http://127.0.0.1:${APP_PORT}/api/health ..."
HEALTH_OK=0
HEALTH_BODY=""
for attempt in $(seq 1 15); do
    if HEALTH_BODY="$(curl -fsS -m 3 "http://127.0.0.1:${APP_PORT}/api/health" 2>/dev/null)"; then
        HEALTH_OK=1
        break
    fi
    sleep 1
done

if [ "$HEALTH_OK" -ne 1 ]; then
    echo "ERROR: Health check failed after 15s on http://127.0.0.1:${APP_PORT}/api/health"
    echo "Recent API logs:"
    journalctl --user -u rubberbandman -n 30 --no-pager || true
    exit 1
fi

echo "OK: Health check passed -> ${HEALTH_BODY}"
systemctl --user --no-pager --lines=0 status rubberbandman.service rubberbandman-daemon.service || true
echo "===================================================================="
echo "Deploy complete."
echo "===================================================================="
