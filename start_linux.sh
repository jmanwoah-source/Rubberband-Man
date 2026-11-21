#!/usr/bin/env bash
# ==============================================================================
# Rubberband Man - AI Options Divergence Terminal (Linux Production Launcher)
# Optimized for Linux Workstations, Ubuntu/Debian Servers & ASUS GTX 10 GPU Rigs
# ==============================================================================

set -o pipefail

# Script directory (handles symlinks and any launch location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "===================================================================="
echo "🏹 Rubberband Man | AI Options Divergence Terminal"
echo "   POSIX / Linux Deployment Suite"
echo "===================================================================="

# 1. Python Environment Check
if command -v python3 &>/dev/null; then
    PY_BIN="python3"
elif command -v python &>/dev/null; then
    PY_BIN="python"
else
    echo "❌ ERROR: Python 3 is not installed or not in PATH."
    echo "   Install it with: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    exit 1
fi

PY_VER=$($PY_BIN --version 2>&1 || true)
echo "✅ Python runtime: $PY_VER"

# 2. Environment Configuration Check (.env)
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "⚠️  .env file not detected. Generating .env from .env.example..."
        cp .env.example .env
        echo "   👉 Note: Edit .env to add your FMP_API_KEY and GEMINI_API_KEY."
    else
        touch .env
    fi
fi

# 3. NVIDIA GPU / CUDA Detection (ASUS GTX 10 / RTX Workstations)
echo "--------------------------------------------------------------------"
if command -v nvidia-smi &>/dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n 1 || echo "NVIDIA GPU")
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -n 1 || echo "")
    echo "🚀 GPU Acceleration: $GPU_NAME ($GPU_MEM)"
    echo "   Ready for local high-throughput inference (Qwen 3.8 / 2.5, Llama 3.2)."
else
    echo "ℹ️  NVIDIA GPU not detected via nvidia-smi. Running in CPU mode for local models."
fi

# 4. Open-Source Local Model Server Check (Ollama on port 11434)
echo "--------------------------------------------------------------------"
OLLAMA_PORT="${LOCAL_LLM_PORT:-11434}"
if curl -s -m 2 "http://127.0.0.1:${OLLAMA_PORT}/api/tags" &>/dev/null; then
    echo "🟢 Local Model Engine: ONLINE on port ${OLLAMA_PORT}"
    MODELS_FOUND=$(curl -s "http://127.0.0.1:${OLLAMA_PORT}/api/tags" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ' ' || true)
    if [ -n "$MODELS_FOUND" ]; then
        echo "   Installed local model(s): $MODELS_FOUND"
    fi
else
    echo "ℹ️  Local model daemon not detected on port ${OLLAMA_PORT}."
    echo "   Cloud Gemini 2.5 Flash is ready as primary arbiter."
    echo "   To start Ollama with local open-source models (e.g. Qwen 2.5 / 3.8):"
    echo "     curl -fsSL https://ollama.com/install.sh | sh"
    echo "     ollama run qwen2.5:3b"
fi

# 5. Virtual Environment & Dependencies
echo "--------------------------------------------------------------------"
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment (.venv)..."
    $PY_BIN -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "✅ Virtual environment active (.venv)."

echo "🔍 Verifying Python packages from requirements.txt..."
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

# 6. Port and LAN Address Configuration
APP_PORT="${PORT:-8501}"
LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo "===================================================================="
echo "🎯 Launching Rubberband Man Terminal..."
echo "   Local Access:    http://localhost:${APP_PORT}"
echo "   Network Access:  http://${LAN_IP}:${APP_PORT}"
echo "   Binding:         0.0.0.0 (Accessible across your LAN / Workstation)"
echo "===================================================================="

# Execute Streamlit using virtual environment python
exec python -m streamlit run rubberband.py \
    --server.port "${APP_PORT}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
