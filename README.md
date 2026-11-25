# Rubberband Man

Institutional options divergence scanner, quantitative options pricing telemetry, Charles Schwab practice order desk, and autonomous Top-5 daily ledger.

## Architecture

| Component | Entrypoint / Path | Default Port | Role |
| :--- | :--- | :--- | :--- |
| **FastAPI Backend + PWA Server** | `api_server.py` (serves `web/dist`) | `8080` | Primary production HTTP API & compiled React 19 / Vite 8 PWA |
| **React PWA Frontend** | `web/` (Vite 8 + TypeScript + Tailwind v4) | `5173` (dev) | Mobile-first institutional scanner, elasticity chart, ledger & practice desk |
| **24/7 Tracker Daemon** | `daily_tracker_daemon.py --daemon` | — | Captures weekday Top-5 sector snapshots, runs daily online DB backups & WAL checkpoints, writes `data/.daemon_heartbeat` |
| **Practice Diary & Ledger DB** | `data/simulated_diary.db` (SQLite WAL) | — | Persistent simulated trades, Top-5 recommendation ledger & OPRA IV history (`synchronous=FULL`) |
| **Legacy Streamlit Terminal** | `rubberband.py` | `8501` | Optional fallback desktop UI |

> **Port Separation Note:** FastAPI defaults to **`PORT=8080`** so it never collides with local vLLM inference servers listening on `:8000`.

---

## Quick Start — Local Development

### Prerequisites
- **Python 3.11+** (`python3`, `python3-venv`, `pip`)
- **Node.js `>= 20.19` or `22 LTS`** (required by Vite 8; Ubuntu's default apt Node 18 will fail)

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env and add FMP_API_KEY, MARKETDATA_API_KEY, and GEMINI_API_KEY
```

### 2. Python Virtual Environment
```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Run Dev Servers (Hot Reload)
In terminal 1 (API on `:8000` to match `web/vite.config.ts` dev proxy):
```bash
python -m uvicorn api_server:app --reload --port 8000
```
In terminal 2 (React PWA dev server on `:5173`):
```bash
npm --prefix web ci
npm --prefix web run dev
```
Open `http://localhost:5173`.

### 4. Run Automated Verification
```bash
python -m unittest discover -s tests
npm --prefix web run build
npm --prefix web run lint
```

---

## Production Deployment (FastAPI + Compiled PWA)

### Option A: Native Linux / ASUS GX10 (Recommended for 24/7 Workstation)
```bash
# Build PWA + install venv on first run, then launch FastAPI on :8080
./start_linux.sh --setup --build

# Install & enable BOTH 24/7 systemd services (API+PWA + Tracker Daemon)
./setup_systemd.sh

# Future 1-command updates over SSH (git pull, conditional deps/build, DB backup, restart, healthcheck)
./deploy_gx10.sh
```
See [README_LINUX.md](README_LINUX.md) for the complete ASUS GX10 ARM64 migration, Tailscale + SSH workflow, and standalone troubleshooting runbook.

### Option B: Docker Compose (Multi-Stage Node 22 + Python 3.11 Non-Root)
```bash
mkdir -p data/backups intel_bus
docker compose up -d --build
```
Services started by default:
- `rubberband_api` on `http://localhost:${PORT:-8080}` (healthcheck: `GET /api/health`)
- `rubberband_daemon` running `daily_tracker_daemon.py --daemon --interval 1800` (healthcheck: `/app/data/.daemon_heartbeat` age `< 3600s`)

Verify health:
```bash
curl -fsS http://127.0.0.1:${PORT:-8080}/api/health
docker compose ps
```

---

## Backup & Restore (`data/simulated_diary.db`)

All practice trades and daily ledger snapshots live in `data/simulated_diary.db` (SQLite WAL mode with `PRAGMA synchronous=FULL`). Never copy a live WAL database with plain `cp` without taking an online backup or checkpointing the WAL first.

### Taking a Safe Online Backup
1. **CLI / Script (safe while API and daemon are running):**
   ```bash
   .venv/bin/python -c "import diary_db; print(diary_db.backup_diary_db('manual'))"
   ```
   Creates a consistent standalone snapshot under `data/backups/simulated_diary_<YYYYMMDD_HHMMSS>_manual.db` (automatically retaining the latest 14 backups).
2. **HTTP API / UI Export:**
   - Trigger server-side backup: `curl -X POST http://127.0.0.1:8080/api/diary/backup`
   - Download full JSON archive: `curl -fsS "http://127.0.0.1:8080/api/diary/export?format=json" -o diary_export.json`
   - Download full CSV archive: `curl -fsS "http://127.0.0.1:8080/api/diary/export?format=csv" -o diary_export.csv`
3. **Automatic Backups:** `daily_tracker_daemon.py` creates a `daily` online backup + WAL checkpoint after daily snapshot capture, and `./deploy_gx10.sh` takes a `pre_deploy` backup before restarting services.

### Restoring from a Backup
```bash
# 1. Stop writers first
systemctl --user stop rubberbandman rubberbandman-daemon   # or: docker compose stop

# 2. Preserve current files before overwriting
mv data/simulated_diary.db data/simulated_diary.db.before_restore
rm -f data/simulated_diary.db-wal data/simulated_diary.db-shm

# 3. Copy chosen backup into place and verify SQLite integrity
cp data/backups/simulated_diary_<TIMESTAMP>_<TAG>.db data/simulated_diary.db
.venv/bin/python -c "import sqlite3; print(sqlite3.connect('data/simulated_diary.db').execute('PRAGMA integrity_check;').fetchone())"

# 4. Restart services
systemctl --user start rubberbandman rubberbandman-daemon  # or: docker compose start
```

---

## Environment Variables

Copy `.env.example` to `.env` (`chmod 600 .env`). Every Python module loads `.env` relative to the repository root (CWD-independent).

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PORT` | `8080` | FastAPI + PWA port (kept off `:8000` to avoid vLLM conflict) |
| `CORS_ORIGINS` | *(empty)* | Optional comma-separated allowed CORS origins for remote proxies |
| `FMP_API_KEY` | *(required)* | Financial Modeling Prep Ultra API key (quotes, fundamentals, macro) |
| `MARKETDATA_API_KEY` | *(required)* | MarketData.app API key (live OPRA options chains, Greeks, IV, candles) |
| `MARKETDATA_BASE_URL` | `https://api.marketdata.app/v1` | Optional MarketData API base URL override |
| `GEMINI_API_KEY` | *(recommended)* | Google Gemini API key (cloud arbiter & standby fallback) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Primary Gemini model name |
| `LLM_BACKEND` | `gemini` | `gemini` (cloud) or `local` (ASUS GX10 Ollama / vLLM / SGLang) |
| `LOCAL_LLM_URL` | `http://localhost:11434/v1` | OpenAI-compatible local LLM endpoint (`:11434` Ollama, `:8000` vLLM) |
| `LOCAL_LLM_MODEL` | `qwen2.5:3b` | Default local model ID |
| `LOCAL_LLM_API_KEY` | `ollama` | Bearer token for local LLM server |
| `INTEL_BUS_DIR` | *(auto)* | Optional shared path for Qwen Wiki `signals_bridge.json` & `intel_bus.db` |

---

## Legacy Streamlit Fallback

The original multi-page Streamlit terminal (`rubberband.py`) remains available as a fallback UI:

```bash
# Native Linux
./start_linux.sh --streamlit

# Docker Compose (legacy profile on :8501)
docker compose --profile legacy up -d rubberband_streamlit
```
