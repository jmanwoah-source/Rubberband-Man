# Rubberband Man — ASUS GX10 (ARM64) & Standalone Linux Operations Guide

Complete runbook for migrating, running 24/7, updating remotely over Tailscale + SSH, and troubleshooting Rubberband Man on an **ASUS GX10 Linux Pro workstation (NVIDIA Grace Blackwell GB10 ARM64, 128 GB Unified Memory)** or any Ubuntu/Debian/Fedora/Arch Linux server—100% standalone with no Antigravity dependency.

---

## 1. System Prerequisites (One-Time Setup)

> **Critical Node.js Version Requirement:** The React PWA uses Vite 8 (`web/package.json`), which requires **Node.js `>= 20.19` or `22 LTS`**. Ubuntu's default `apt install nodejs` (Node 18) will fail. `web/package-lock.json` ships full `linux-arm64` and `linux-x64` native bindings.

### Ubuntu / Debian / ASUS GX10 (ARM64 or x64)
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl git ca-certificates

# Install Node.js 22 LTS (NodeSource supports both arm64 and amd64)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verify versions
python3 --version   # 3.11+
node -v             # v22.x.x (must be >= v20.19)
npm -v
```

### Fedora / RHEL / Rocky Linux
```bash
sudo dnf install -y python3 python3-pip curl git nodejs npm
```

---

## 2. Standalone Migration Checklist (Windows / Old Host -> ASUS GX10)

### Step A: Prepare Clean Transfer Artifacts on Source Machine
Never copy a live SQLite WAL database directly without checkpointing or using `.backup()`. On the source machine:

```bash
# Create a clean, self-contained SQLite backup (flushes WAL safely while app is online)
python -c "import diary_db; print(diary_db.backup_diary_db('migration'))"
```

### Step B: What to Transfer vs. What NOT to Transfer

| Transfer to GX10 (Preserve State) | Destination on GX10 | Notes |
| :--- | :--- | :--- |
| `.env` | `~/RubberbandMan/.env` | Run `chmod 600 ~/RubberbandMan/.env` immediately |
| Latest `data/backups/simulated_diary_*_migration.db` | `~/RubberbandMan/data/simulated_diary.db` | Standalone backup avoids corrupt/missing `-wal` frames |
| `data/watchlist.json` *(or legacy root `watchlist.json`)* | `~/RubberbandMan/data/watchlist.json` | Personal watchlist (auto-migrated if placed at root) |
| `intel_bus/intel_bus.db` & `intel_bus/signals_bridge.json` | `~/RubberbandMan/intel_bus/` | Only needed if custom Qwen Wiki signals exist |

| Do NOT Transfer (Rebuild Natively on GX10 ARM64) | Why |
| :--- | :--- |
| `.venv/` | Platform-specific Python binaries & shebangs |
| `web/node_modules/` | ~163 MB of x64/Windows binaries; rebuild via `npm --prefix web ci` |
| `web/dist/` | Rebuilt cleanly on GX10 via `npm --prefix web run build` |
| `data/fmp_cache.db`, `data/marketdata_cache.db` | Ephemeral HTTP caches; auto-recreated cleanly on first run |

### Step C: Clone & Bootstrap on ASUS GX10
```bash
git clone <your-repo-url> ~/RubberbandMan
cd ~/RubberbandMan

# Copy transferred state files into place, then lock down .env permissions
mkdir -p data/backups intel_bus
chmod 600 .env

# Ensure executable bits (preserved by Git if committed, safe to enforce)
chmod +x start_linux.sh setup_systemd.sh deploy_gx10.sh

# One-time setup test: create .venv, install Python deps, build React PWA, launch on :8080
./start_linux.sh --setup --build
# Verify http://127.0.0.1:8080/api/health in another terminal, then Ctrl+C before enabling systemd.
```

---

## 3. Running 24/7 with Systemd (Recommended Native GX10 Mode)

`./setup_systemd.sh` dynamically renders and installs **both** systemd user services using your actual repository path, username, and `.venv/bin/python`:
1. **`rubberbandman.service`** — FastAPI backend + compiled React PWA (`0.0.0.0:${PORT:-8080}`)
2. **`rubberbandman-daemon.service`** — `daily_tracker_daemon.py --daemon --interval 1800` (weekday Top-5 snapshots, daily online SQLite backups, WAL checkpoints, heartbeat at `data/.daemon_heartbeat`)

```bash
cd ~/RubberbandMan
./setup_systemd.sh

# IMPORTANT: If setup_systemd.sh warns about linger permissions, run this once:
sudo loginctl enable-linger "$USER"
```

### Daily Operations Commands
```bash
# Status of both services
systemctl --user status rubberbandman rubberbandman-daemon

# Live log tail
journalctl --user -u rubberbandman -f
journalctl --user -u rubberbandman-daemon -f

# Restart or stop both
systemctl --user restart rubberbandman rubberbandman-daemon
systemctl --user stop rubberbandman rubberbandman-daemon

# Health check
curl -fsS http://127.0.0.1:8080/api/health
```

---

## 4. Tailscale + SSH Remote-Edit & 1-Command Deploy Workflow

Keep Rubberband Man private off the public internet by accessing the GX10 over your Tailscale tailnet.

### A. Install & Enable Tailscale on ASUS GX10
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh

# Retrieve your private Tailscale IP / MagicDNS hostname
tailscale ip -4
tailscale status
```
Access the PWA from your phone or laptop on Tailscale at:
- `http://<gx10-tailscale-ip>:8080` (or `http://<gx10-hostname>:8080`)

If UFW firewall is enabled on the GX10, allow `:8080` **only** on `tailscale0` (and LAN if desired):
```bash
sudo ufw allow in on tailscale0 to any port 8080 proto tcp
sudo ufw reload
```
If accessing through a custom hostname/proxy with cross-origin requests, add it to `CORS_ORIGINS` in `.env` and restart `rubberbandman.service`.

### B. Remote Editing & 1-Command Deploy (`deploy_gx10.sh`)
- **Workflow 1 (Git Push -> GX10 Pull):** Edit locally, push to Git, then run over SSH:
  ```bash
  ssh <user>@<gx10-tailscale-host> 'cd ~/RubberbandMan && ./deploy_gx10.sh'
  ```
- **Workflow 2 (VS Code / Cursor Remote-SSH):** Open `~/RubberbandMan` directly over SSH, edit files, and run `./deploy_gx10.sh` in the remote terminal.

`./deploy_gx10.sh` safely automates:
1. `git pull --ff-only`
2. `pip install -r requirements.txt` *(only when `requirements.txt` changed or `--force-deps`)*
3. `npm --prefix web ci && npm --prefix web run build` *(only when `web/` changed, `web/dist` missing, or `--force-build`)*
4. Online SQLite backup via `diary_db.backup_diary_db('pre_deploy')`
5. Restart of `rubberbandman.service` and `rubberbandman-daemon.service`
6. Live verification of `http://127.0.0.1:${PORT:-8080}/api/health`

---

## 5. Docker Compose Deployment (Alternative Container Mode)

Uses a multi-stage `Dockerfile` (`node:22-slim` -> `python:3.11-slim`), runs as non-root `appuser` (UID `1000`), mounts `./data` and `./intel_bus` cleanly (no single-file `watchlist.json` mount), and runs separate healthchecks for the API and daemon.

```bash
cd ~/RubberbandMan
mkdir -p data/backups intel_bus

# Build and start FastAPI+PWA (:8080) and 24/7 Tracker Daemon
docker compose up -d --build

# Check container health status
docker compose ps

# Follow logs
docker compose logs -f rubberband_api rubberband_daemon

# Optional: start legacy Streamlit UI on :8501
docker compose --profile legacy up -d rubberband_streamlit

# Stop all containers cleanly (triggers graceful SIGTERM WAL checkpoint)
docker compose down
```

---

## 6. Local LLM Acceleration on ASUS GX10 (Ollama / vLLM)

Rubberband Man's `llm_router.py` routes between Cloud Gemini 2.5 Flash and your local GX10 models with automatic failover.

- **Ollama (port `11434`):**
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ollama pull qwen2.5:7b
  ```
  Set in `.env`: `LLM_BACKEND=local`, `LOCAL_LLM_URL=http://localhost:11434/v1` (or `http://host.docker.internal:11434/v1` inside Docker).
- **vLLM (port `8000`):**
  Rubberband Man defaults to **`PORT=8080`**, keeping `:8000` completely free for vLLM (`LOCAL_LLM_URL=http://localhost:8000/v1`).

---

## 7. ASUS GX10 Autonomous Dual-Write Handoff (Qwen Wiki Intel Bus)

On an ASUS GX10 workstation running an upstream research wiki agent, both systems share `signals_bridge.json` and `intel_bus.db` (SQLite WAL). Set `INTEL_BUS_DIR` in `.env` to override auto-discovery (`/shared/intel_bus`, `/mnt/gx10_shared/intel_bus`, or `./intel_bus`).

```json
{
  "symbol": "ONTO",
  "track": "TRACK_B_BOTTLENECK",
  "wiki_score": 88,
  "primary_benchmark": "SMH",
  "parent_whale": "TSM",
  "dilution_risk": false,
  "thesis_hook": "Sole-source acoustic metrology for advanced CoWoS packaging; TSMC backlog accelerating QoQ.",
  "last_updated": "2026-10-18T21:30:00Z"
}
```

| Dimension | Track A: Golden Fortress (Score >= 75) | Track B: Emerging Bottleneck (Score >= 75) | Track C: Mirage Breakdown (Score <= 35) |
| :--- | :--- | :--- | :--- |
| **Core Edge** | Institutional Liquidity Vacuum | Sympathy Lag vs Anchor Whale (`parent_whale`) | Squeeze Exhaustion + Active ATM Dilution Wall |
| **Fundamental Gate** | Altman Z > 3.0 & TTM FCF > 0 | Cash Runway >= 6 Qtrs & Deferred Rev | Runway < 4 Qtrs, Declining Margin, or Dilution |
| **Z-Score Trigger** | 5D Residual Z <= -1.75 | 5D Residual Z <= -2.10 or Whale Z <= -1.80 | 5D Residual Z >= +1.85 (or 3D Z >= +2.0) |
| **Microstructure** | CLV >= 0.0, RVOL >= 1.2x | Intraday 4H CLV >= +0.35 Tail Sweep | CLV <= -0.25 on RVOL >= 1.5x |
| **30-45 DTE Play** | 0.55-0.60 Delta Call | 0.45-0.50 Delta Call | 0.50 Delta Put / Bear Put Spread |

---

## 8. Standalone Troubleshooting (Without Antigravity)

| Symptom | Diagnosis | Fix |
| :--- | :--- | :--- |
| **Services stop when SSH closes** | Systemd user lingering disabled | Run `sudo loginctl enable-linger "$USER"` and verify `loginctl show-user "$USER" -p Linger` returns `Linger=yes`. |
| **Port already in use on startup** | Another process (or vLLM) occupies `PORT` | Check `ss -tulpn \| grep 8080`. Keep vLLM on `:8000` and Rubberband Man on `PORT=8080` (or change `PORT` in `.env`). |
| **`/api/health` shows `pwa_built: false`** | `web/dist` not compiled yet | Ensure `node -v` is `>= 20.19` (Node 22 LTS), then run `npm --prefix web ci && npm --prefix web run build` and restart `rubberbandman`. |
| **`npm run build` fails with syntax/engine error** | Ubuntu apt installed Node 18 | Install Node 22 LTS via NodeSource (Section 1) and verify `which node && node -v`. |
| **Daemon marked unhealthy in Docker** | `data/.daemon_heartbeat` missing or > 3600s old | Check `docker compose logs --tail=50 rubberband_daemon` or `journalctl --user -u rubberbandman-daemon -n 50`. Verify `data/` is writable by UID 1000 (`chown -R 1000:1000 data intel_bus`). |
| **FMP / MarketData / Gemini 401 or rate limits** | Expired key or upstream throttling | Inspect `curl -fsS http://127.0.0.1:8080/api/health`, update keys in `.env`, then `systemctl --user restart rubberbandman rubberbandman-daemon`. Stale SQLite cache serves fallback data during transient outages. |
| **SQLite lock or suspected DB corruption** | Interrupted power loss or bad file copy | Run `.venv/bin/python -c "import sqlite3; print(sqlite3.connect('data/simulated_diary.db').execute('PRAGMA integrity_check;').fetchone())"`. If not `ok`, restore the newest snapshot from `data/backups/` per `README.md`. Ephemeral caches (`data/fmp_cache.db`, `data/marketdata_cache.db`) can safely be deleted while stopped and will auto-rebuild. |
| **`$'\\r': command not found` in `.sh` scripts** | File edited with Windows CRLF | `.gitattributes` enforces LF; strip locally with `sed -i 's/\r$//' *.sh *.service` and `chmod +x *.sh`. |
| **Offline boot delays or pip errors** | Running `./start_linux.sh --setup` without internet | Normal `./start_linux.sh` and systemd **never** run `pip install` when `.venv` already exists. Omit `--setup` when offline. |
