# 🏹 Rubberband Man: Linux Deployment & Supercomputer Guide

This guide ensures **100% frictionless placement and operation** on any Linux system (Ubuntu, Debian, Fedora, Arch, Rocky Linux, or WSL2), including high-performance workstations with **ASUS GTX 10 / RTX NVIDIA GPUs**.

---

## ⚡ 1. Quick Start (Direct Native Launcher)

The launcher script automatically creates the Python virtual environment (`.venv`), installs all dependencies, detects your NVIDIA GPU, verifies your local model engine (Ollama/vLLM), and launches the terminal bound to `0.0.0.0` for full LAN access.

```bash
# 1. Enter the project directory
cd RubberbandMan

# 2. Make the launcher executable (if permissions were lost during copy)
chmod +x start_linux.sh

# 3. Launch
./start_linux.sh
```

> **Access URL**:
> - Local workstation: `http://localhost:8501`
> - LAN / Remote network: `http://<LINUX_IP>:8501`

---

## 📦 2. System Prerequisites (One-Time Setup)

On a fresh Linux installation, ensure Python 3, venv, and curl are installed:

### Ubuntu / Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl git
```

### Fedora / RHEL / Rocky Linux:
```bash
sudo dnf install -y python3 python3-pip curl git
```

### Arch Linux:
```bash
sudo pacman -S python python-pip curl git
```

---

## 🖥️ 3. ASUS GTX 10 / GPU Acceleration with Local Open-Source Models (Qwen 3.8 / 2.5)

Rubberband Man features an automated **Universal LLM Router** that seamlessly switches between Cloud (Gemini 2.5 Flash) and Local GPU acceleration.

### Step 1: Install Ollama (Single command on Linux)
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Pull your preferred model
```bash
# High-speed reasoning model (great for GTX 10 series)
ollama pull qwen2.5:3b

# Or larger models if VRAM permits (e.g. 8GB+ VRAM)
ollama pull qwen2.5:7b
```

### Step 3: Connect inside the Terminal
In the Rubberband Man UI:
1. Open the **Left Sidebar**.
2. Under **AI Compute Engine**, toggle **Local GPU / Supercomputer**.
3. Select your model (`qwen2.5:3b`) and click **Test Endpoint**.
4. The status pill will display: `🟢 Online · ~15ms latency`.

---

## 🔄 4. Running 24/7 in the Background (Systemd Service)

To keep Rubberband Man running continuously in the background—even after you close your terminal or disconnect from SSH—use the automated systemd installer:

```bash
chmod +x setup_systemd.sh
./setup_systemd.sh
```

### Useful Management Commands:
```bash
# Check service status
systemctl --user status rubberbandman

# View live real-time logs
journalctl --user -u rubberbandman -f

# Restart service
systemctl --user restart rubberbandman

# Stop service
systemctl --user stop rubberbandman
```

---

## 🐳 5. Containerized Deployment (Docker & Compose)

If you prefer running in an isolated container:

```bash
# Start in background
docker compose up -d --build

# View logs
docker compose logs -f

# Stop container
docker compose down
```

---

## 🛡️ 6. Firewall & Remote LAN Access

If you cannot access the terminal from another PC on your local network, allow port `8501`:

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 8501/tcp
sudo ufw reload

# Firewalld (Fedora/RHEL)
sudo firewall-cmd --add-port=8501/tcp --permanent
sudo firewall-cmd --reload
```

---

## 🛰️ 8. ASUS GX10 Autonomous Dual-Write Handoff Architecture (Qwen 3.8 Wiki Bridge)

When running on the **ASUS GX10 Linux Pro workstation** (128GB Unified Memory), Rubberband Man operates hand-in-hand with an upstream deep research wiki agent (Qwen 3.8 continuous research program modeled after Karpathy's wiki).

### Autonomous Handoff Schema (`signals_bridge.json` & `intel_bus.db` WAL)
The Qwen 3.8 agent updates its human-readable markdown lists (`golden_tier_list.md`, `emerging_edge_list.md`, `mirage_short_list.md`) while atomically committing to the shared directory (`/shared/intel_bus/` or `/mnt/gx10_shared/intel_bus/`):

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

### Track Calibrations Executed by Rubberband Man:
| Dimension | Track A: Golden Fortress (Score ≥ 75) | Track B: Emerging Bottleneck (Score ≥ 75) | Track C: Mirage Breakdown (Score ≤ 35) |
| :--- | :--- | :--- | :--- |
| **Core Edge** | Institutional Liquidity Vacuum | Sympathy Lag vs Anchor Whale (`parent_whale`) | Squeeze Exhaustion + Active ATM Dilution Wall |
| **Fundamental Gate** | Altman Z > 3.0 & TTM FCF > 0 | Bypasses TTM P/E; Checks Cash Runway ≥ 6 Qtrs & Deferred Rev | Inverts Gate: Confirms Runway < 4 Qtrs, Declining Margin, or Dilution |
| **Z-Score Trigger** | 5D Residual Z ≤ -1.75σ | 5D Residual Z ≤ -2.10σ **OR** Whale Residual Z ≤ -1.80σ | 5D Residual Z ≥ +1.85σ (or 3D Z ≥ +2.0σ) |
| **Microstructure** | CLV ≥ 0.0, RVOL ≥ 1.2x | Intraday 4H CLV ≥ +0.35 Tail Sweep | CLV ≤ -0.25 on heavy dumping volume (RVOL ≥ 1.5x) |
| **30–45 DTE Play** | 0.55–0.60Δ Call (or Aggressive OTM Call) | 0.45–0.50Δ Call (Explosive Convexity OTM) | 0.50Δ Put (or Bear Put Spread) |

### Environment Variable Override:
To specify a custom shared directory path on the GX10:
```bash
export INTEL_BUS_DIR="/mnt/gx10_shared/intel_bus"
./start_linux.sh
```
Rubberband Man will automatically discover and monitor `signals_bridge.json` and initialize the high-concurrency SQLite WAL database `intel_bus.db` at that location.

---

## 🔍 9. Verification Checklist

- [x] **Zero Windows Paths**: All file paths use `os.path.join()` or forward slashes `/`.
- [x] **POSIX LF Line Endings**: All `.sh` scripts use standard Unix `\n` line breaks.
- [x] **Folder Name**: `RubberbandMan` contains no spaces or special characters for seamless bash execution.
- [x] **Dynamic Port**: Override the port anytime via `PORT=8502 ./start_linux.sh`.
- [x] **Automatic `.env` Creation**: Generates `.env` from `.env.example` if not already present.
- [x] **Autonomous GX10 Handoff**: Dual-write SQLite WAL + atomic JSON bridge (`signals_bridge.json`).
- [x] **Track A/B/C Engine Calibration**: Dual-residual elasticity against Sector ETF and Tier-1 Anchor Whale.

