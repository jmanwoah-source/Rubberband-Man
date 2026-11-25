#!/usr/bin/env bash
# ==============================================================================
# Rubberband Man - Production Linux / ASUS GX10 Launcher
# Serves FastAPI + React PWA on ${PORT:-8080} (default) or legacy Streamlit (--streamlit).
#
# Flags:
#   --setup      Force Python dependency installation/update in .venv
#   --build      Force React PWA rebuild (web/dist) via npm ci && npm run build
#   --streamlit  Launch legacy Streamlit UI on ${STREAMLIT_PORT:-8501}
#   -h, --help   Show this usage message
# ==============================================================================

set -euo pipefail

# Detect repository root dynamically regardless of invocation directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

FORCE_SETUP=0
FORCE_BUILD=0
LEGACY_STREAMLIT=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --setup)
            FORCE_SETUP=1
            ;;
        --build)
            FORCE_BUILD=1
            ;;
        --streamlit)
            LEGACY_STREAMLIT=1
            ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $1"
            echo "Usage: ./start_linux.sh [--setup] [--build] [--streamlit]"
            exit 1
            ;;
    esac
    shift
done

# Safely parse .env without executing arbitrary shell code; preserves caller env overrides
load_dotenv_file() {
    local env_file="$1"
    [ -f "$env_file" ] || return 0
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%$'\r'}"
        case "$line" in
            ''|\#*) continue ;;
        esac
        if [[ "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            local key="${BASH_REMATCH[2]}"
            local val="${BASH_REMATCH[3]}"
            if [[ "$val" =~ ^\"(.*)\"$ ]]; then
                val="${BASH_REMATCH[1]}"
            elif [[ "$val" =~ ^\'(.*)\'$ ]]; then
                val="${BASH_REMATCH[1]}"
            fi
            if [ -z "${!key+x}" ]; then
                export "${key}=${val}"
            fi
        fi
    done < "$env_file"
}

check_node_version() {
    if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
        echo "ERROR: Node.js (>= 20.19 or 22 LTS) and npm are required to build web/dist."
        echo "       Install Node 22 LTS on Ubuntu/Debian/GX10:"
        echo "         curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -"
        echo "         sudo apt-get install -y nodejs"
        return 1
    fi
    local ver major minor
    ver="$(node -v | sed 's/^v//')"
    major="$(echo "$ver" | cut -d. -f1)"
    minor="$(echo "$ver" | cut -d. -f2)"
    if [ "$major" -lt 20 ] || { [ "$major" -eq 20 ] && [ "$minor" -lt 19 ]; }; then
        echo "ERROR: Node.js v${ver} detected, but Vite 8 requires Node >= 20.19 (recommended: Node 22 LTS)."
        return 1
    fi
    echo "OK: Node.js runtime v${ver}"
    return 0
}

echo "===================================================================="
echo "Rubberband Man | Production Launcher (Linux / ASUS GX10 ARM64)"
echo "===================================================================="

# 1. Python runtime check
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo "ERROR: Python 3 is not installed or not in PATH."
    echo "       Install with: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi
echo "OK: Python runtime: $($PY_BIN --version 2>&1 || true)"

# 2. Ensure .env exists and load it safely
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "INFO: .env not found. Creating from .env.example (edit it to add API keys)..."
        cp .env.example .env
        chmod 600 .env 2>/dev/null || true
    fi
fi
load_dotenv_file "${SCRIPT_DIR}/.env"

# Ensure persistent directories exist
mkdir -p "${SCRIPT_DIR}/data/backups" "${SCRIPT_DIR}/intel_bus"

# 3. Hardware & Local LLM probe (non-blocking, bounded timeouts)
echo "--------------------------------------------------------------------"
if command -v nvidia-smi &>/dev/null; then
    GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1 || echo "NVIDIA GPU")"
    GPU_MEM="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -n 1 || echo "Unified")"
    echo "GPU: ${GPU_NAME} (${GPU_MEM})"
else
    echo "INFO: nvidia-smi not detected; running without local GPU telemetry."
fi

LLM_BASE="${LOCAL_LLM_URL:-http://127.0.0.1:11434/v1}"
LLM_PROBE="${LLM_BASE%/v1}/v1/models"
if command -v curl &>/dev/null && curl -fsS -m 2 "$LLM_PROBE" &>/dev/null; then
    echo "Local LLM endpoint ONLINE: ${LLM_BASE}"
else
    echo "INFO: Local LLM endpoint not responding at ${LLM_BASE} (Cloud Gemini standby ready)."
fi

# 4. Python virtual environment (install deps ONLY when .venv missing or --setup passed)
echo "--------------------------------------------------------------------"
CREATED_VENV=0
if [ ! -x ".venv/bin/python" ]; then
    echo "Creating Python virtual environment (.venv)..."
    "$PY_BIN" -m venv .venv
    CREATED_VENV=1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ "$CREATED_VENV" -eq 1 ] || [ "$FORCE_SETUP" -eq 1 ]; then
    echo "Installing Python dependencies from requirements.txt..."
    python -m pip install -r requirements.txt
else
    echo "OK: Using existing .venv (pass --setup to refresh Python dependencies)."
fi

# 5. Build React PWA bundle if missing or --build passed (skipped for --streamlit unless --build)
if [ "$LEGACY_STREAMLIT" -eq 0 ] || [ "$FORCE_BUILD" -eq 1 ]; then
    if [ "$FORCE_BUILD" -eq 1 ] || [ ! -f "${SCRIPT_DIR}/web/dist/index.html" ]; then
        echo "--------------------------------------------------------------------"
        echo "Building React PWA frontend (web/dist)..."
        check_node_version
        npm --prefix "${SCRIPT_DIR}/web" ci
        npm --prefix "${SCRIPT_DIR}/web" run build
    else
        echo "OK: Using prebuilt React PWA at web/dist (pass --build to rebuild)."
    fi
fi

# 6. Launch server
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")"

if [ "$LEGACY_STREAMLIT" -eq 1 ]; then
    ST_PORT="${STREAMLIT_PORT:-8501}"
    echo "===================================================================="
    echo "Launching Legacy Streamlit Terminal..."
    echo "  Local URL:   http://127.0.0.1:${ST_PORT}"
    echo "  Network URL: http://${LAN_IP}:${ST_PORT}"
    echo "===================================================================="
    exec python -m streamlit run rubberband.py \
        --server.port "${ST_PORT}" \
        --server.address 0.0.0.0 \
        --server.headless true \
        --browser.gatherUsageStats false
fi

APP_PORT="${PORT:-8080}"
echo "===================================================================="
echo "Launching Rubberband Man FastAPI + React PWA..."
echo "  Local URL:   http://127.0.0.1:${APP_PORT}"
echo "  Network URL: http://${LAN_IP}:${APP_PORT}"
echo "  Health URL:  http://127.0.0.1:${APP_PORT}/api/health"
echo "===================================================================="

exec python -m uvicorn api_server:app --host 0.0.0.0 --port "${APP_PORT}"
