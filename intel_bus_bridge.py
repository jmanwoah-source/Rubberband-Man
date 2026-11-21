"""
Intel Bus Bridge - Autonomous Handoff Architecture for ASUS GX10 Linux Pro
Connects Qwen 3.8 Continuous Deep Research Karpathy Wiki Agent with Rubberband Man v3.5
Supports dual-mode communication:
1. Shared SQLite WAL (Write-Ahead Logging) database: intel_bus.db
2. Atomic JSON bridge: signals_bridge.json

Schema:
- symbol: Ticker string (e.g. 'ONTO')
- track: Enum ['TRACK_A_FORTRESS', 'TRACK_B_BOTTLENECK', 'TRACK_C_MIRAGE']
- wiki_score: Integer (0-100)
- primary_benchmark: Sector ETF in sympathy (e.g. 'SMH', 'BOTZ', 'URA', 'XLU')
- parent_whale: Tier-1 customer or bottleneck anchor (e.g. 'TSM', 'NVDA', 'MSFT', 'AMZN')
- dilution_risk: Boolean (True if active ATM/shelf or < 4 qtrs cash)
- thesis_hook: 1-sentence Karpathy Wiki breakthrough / moat / catalyst summary for options desk card
- last_updated: ISO-8601 timestamp string
"""

import os
import sys
import json
import uuid
import sqlite3
import datetime
import threading
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

_BUS_JSON_LOCK = threading.Lock()

DEFAULT_SEED_SIGNALS = [
    {
        "symbol": "ONTO",
        "track": "TRACK_B_BOTTLENECK",
        "wiki_score": 88,
        "primary_benchmark": "SMH",
        "parent_whale": "TSM",
        "dilution_risk": False,
        "thesis_hook": "[Karpathy Wiki · Physics Moat] Sole-source sub-nanometer acoustic metrology for CoWoS-L 3D HBM packaging; TSMC yield bottleneck anchor.",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    },
    {
        "symbol": "CRDO",
        "track": "TRACK_B_BOTTLENECK",
        "wiki_score": 85,
        "primary_benchmark": "SMH",
        "parent_whale": "MSFT",
        "dilution_risk": False,
        "thesis_hook": "[Karpathy Wiki · Interconnect Breakthrough] Proprietary DSP SerDes powering Active Electrical Cables (AEC); 800G/1.6T AI cluster copper monopoly.",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    },
    {
        "symbol": "VRT",
        "track": "TRACK_A_FORTRESS",
        "wiki_score": 92,
        "primary_benchmark": "SMH",
        "parent_whale": "NVDA",
        "dilution_risk": False,
        "thesis_hook": "[Karpathy Wiki · Thermal Moat] Direct-to-chip two-phase liquid cooling & high-voltage busway architecture co-engineered for Blackwell/Rubin racks.",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    },
    {
        "symbol": "MPWR",
        "track": "TRACK_A_FORTRESS",
        "wiki_score": 89,
        "primary_benchmark": "SMH",
        "parent_whale": "NVDA",
        "dilution_risk": False,
        "thesis_hook": "[Karpathy Wiki · Silicon Process Moat] Proprietary BCD process technology enabling ultra-dense vertical power delivery (VPD) beneath AI accelerators.",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    },
    {
        "symbol": "OKLO",
        "track": "TRACK_B_BOTTLENECK",
        "wiki_score": 82,
        "primary_benchmark": "URA",
        "parent_whale": "MSFT",
        "dilution_risk": False,
        "thesis_hook": "[Karpathy Wiki · Fission Breakthrough] Aurora liquid-metal fast neutron reactor utilizing recycled HALEU fuel; multi-GW hyperscaler PPA pipeline.",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    },
    {
        "symbol": "SYM",
        "track": "TRACK_B_BOTTLENECK",
        "wiki_score": 81,
        "primary_benchmark": "BOTZ",
        "parent_whale": "WMT",
        "dilution_risk": False,
        "thesis_hook": "[Karpathy Wiki · Autonomous Swarm Moat] High-speed autonomous mobile bot orchestration with $22B+ contracted backlog across US supply chain hubs.",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    },
    {
        "symbol": "PLUG",
        "track": "TRACK_C_MIRAGE",
        "wiki_score": 22,
        "primary_benchmark": "URA",
        "parent_whale": "AMZN",
        "dilution_risk": True,
        "thesis_hook": "[Karpathy Wiki · Mirage Flag] Negative gross margin hydrogen electrolyzer model trapped under active $1B ATM equity dilution wall & severe cash burn.",
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
]


def resolve_intel_bus_dir() -> str:
    """
    Resolves the shared Intel Bus directory across Asus GX10 Linux and local development.
    Priority:
    1. INTEL_BUS_DIR environment variable
    2. /shared/intel_bus/ (standard Linux GX10 production path)
    3. /mnt/gx10_shared/intel_bus/ (NVMe workstation mount path)
    4. ./intel_bus/ (local fallback inside RubberbandMan root)
    """
    env_dir = os.getenv("INTEL_BUS_DIR", "").strip()
    if env_dir:
        os.makedirs(env_dir, exist_ok=True)
        return env_dir

    if os.path.exists("/shared/intel_bus"):
        return "/shared/intel_bus"
    if os.path.exists("/mnt/gx10_shared/intel_bus"):
        return "/mnt/gx10_shared/intel_bus"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_dir = os.path.join(base_dir, "intel_bus")
    os.makedirs(local_dir, exist_ok=True)
    return local_dir


def get_sqlite_db_path(bus_dir: Optional[str] = None) -> str:
    b_dir = bus_dir or resolve_intel_bus_dir()
    return os.path.join(b_dir, "intel_bus.db")


def get_json_bridge_path(bus_dir: Optional[str] = None) -> str:
    b_dir = bus_dir or resolve_intel_bus_dir()
    return os.path.join(b_dir, "signals_bridge.json")


def init_sqlite_bus(bus_dir: Optional[str] = None) -> sqlite3.Connection:
    """Initializes SQLite database with Write-Ahead Logging (WAL) for high-concurrency GX10 IPC."""
    db_path = get_sqlite_db_path(bus_dir)
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS intel_signals (
            symbol TEXT PRIMARY KEY,
            track TEXT NOT NULL,
            wiki_score INTEGER NOT NULL,
            primary_benchmark TEXT NOT NULL,
            parent_whale TEXT NOT NULL,
            dilution_risk INTEGER NOT NULL DEFAULT 0,
            thesis_hook TEXT,
            last_updated TEXT NOT NULL
        );
    """)
    conn.commit()
    return conn


def write_signal_to_bus(signal: Dict[str, Any], bus_dir: Optional[str] = None) -> bool:
    """
    Atomically writes a signal payload into both SQLite WAL and signals_bridge.json.
    Callable by Qwen 3.8 Karpathy Wiki Agent or ingestion worker.
    """
    b_dir = bus_dir or resolve_intel_bus_dir()
    os.makedirs(b_dir, exist_ok=True)

    sym = signal.get("symbol", "").strip().upper()
    if not sym:
        return False

    track = signal.get("track", "TRACK_A_FORTRESS")
    wiki_score = int(signal.get("wiki_score", 75))
    primary_benchmark = signal.get("primary_benchmark", "SMH").strip().upper()
    if primary_benchmark in ["XLE", "XLI"]:
        primary_benchmark = "URA"
    parent_whale = signal.get("parent_whale", "NVDA").strip().upper()
    dilution_risk = 1 if signal.get("dilution_risk") else 0
    thesis_hook = signal.get("thesis_hook", "High-conviction Karpathy Wiki technological moat setup.")
    last_updated = signal.get("last_updated") or datetime.datetime.now(datetime.timezone.utc).isoformat()

    # 1. Write to SQLite WAL
    sqlite_ok = False
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = init_sqlite_bus(b_dir)
        with conn:
            conn.execute("""
                INSERT INTO intel_signals (symbol, track, wiki_score, primary_benchmark, parent_whale, dilution_risk, thesis_hook, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    track=excluded.track,
                    wiki_score=excluded.wiki_score,
                    primary_benchmark=excluded.primary_benchmark,
                    parent_whale=excluded.parent_whale,
                    dilution_risk=excluded.dilution_risk,
                    thesis_hook=excluded.thesis_hook,
                    last_updated=excluded.last_updated;
            """, (sym, track, wiki_score, primary_benchmark, parent_whale, dilution_risk, thesis_hook, last_updated))
        sqlite_ok = True
    except Exception as e:
        print(f"Error writing signal {sym} to SQLite bus: {e}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    # 2. Write to atomic JSON bridge (synchronized + unique PID/UUID tmp file)
    json_ok = False
    try:
        json_path = get_json_bridge_path(b_dir)
        with _BUS_JSON_LOCK:
            existing: Dict[str, Any] = {}
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        curr_list = json.load(f)
                        if isinstance(curr_list, list):
                            for item in curr_list:
                                if isinstance(item, dict) and item.get("symbol"):
                                    existing[str(item["symbol"]).upper()] = item
                except Exception:
                    pass

            existing[sym] = {
                "symbol": sym,
                "track": track,
                "wiki_score": wiki_score,
                "primary_benchmark": primary_benchmark,
                "parent_whale": parent_whale,
                "dilution_risk": bool(dilution_risk),
                "thesis_hook": thesis_hook,
                "last_updated": last_updated
            }

            tmp_path = f"{json_path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(list(existing.values()), f, indent=2)
            os.replace(tmp_path, json_path)
            json_ok = True
    except Exception as e:
        print(f"Error updating signals_bridge.json for {sym}: {e}")

    return sqlite_ok and json_ok


def seed_intel_bus_if_empty(bus_dir: Optional[str] = None, force_upgrade: bool = False):
    """Populates initial Track A, Track B, and Track C seeds only when both SQLite and JSON are empty."""
    b_dir = bus_dir or resolve_intel_bus_dir()
    json_path = get_json_bridge_path(b_dir)
    db_path = get_sqlite_db_path(b_dir)

    has_json = False
    if os.path.exists(json_path) and os.path.getsize(json_path) > 10:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                has_json = isinstance(data, list) and len(data) > 0
        except Exception:
            has_json = False

    has_db = False
    if os.path.exists(db_path) and os.path.getsize(db_path) > 0:
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = init_sqlite_bus(b_dir)
            cnt = conn.execute("SELECT COUNT(*) FROM intel_signals;").fetchone()[0]
            has_db = cnt > 0
        except Exception:
            has_db = False
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    if (not has_json and not has_db) or force_upgrade:
        for s in DEFAULT_SEED_SIGNALS:
            write_signal_to_bus(s, b_dir)


def read_intel_bus_signals(bus_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Reads all available Track A, B, and C signals from the shared GX10 Intel Bus.
    Automatically normalizes any legacy XLE/XLI benchmark references to URA.
    Never overwrites live signals with hardcoded seed records.
    """
    b_dir = bus_dir or resolve_intel_bus_dir()
    seed_intel_bus_if_empty(b_dir, force_upgrade=False)

    signals: List[Dict[str, Any]] = []

    db_path = get_sqlite_db_path(b_dir)
    if os.path.exists(db_path):
        conn: Optional[sqlite3.Connection] = None
        try:
            conn = init_sqlite_bus(b_dir)
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, track, wiki_score, primary_benchmark, parent_whale, dilution_risk, thesis_hook, last_updated FROM intel_signals ORDER BY wiki_score DESC")
            rows = cursor.fetchall()
            for r in rows:
                bench = r[3] if r[3] not in ["XLE", "XLI"] else "URA"
                signals.append({
                    "symbol": r[0],
                    "track": r[1],
                    "wiki_score": r[2],
                    "primary_benchmark": bench,
                    "parent_whale": r[4],
                    "dilution_risk": bool(r[5]),
                    "thesis_hook": r[6],
                    "last_updated": r[7]
                })
            if signals:
                return signals
        except Exception as e:
            print(f"Warning reading SQLite bus: {e}")
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    json_path = get_json_bridge_path(b_dir)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if item.get("primary_benchmark") in ["XLE", "XLI"]:
                            item["primary_benchmark"] = "URA"
                    return sorted(data, key=lambda x: x.get("wiki_score", 0), reverse=True)
        except Exception as e:
            print(f"Warning reading JSON bridge: {e}")

    return DEFAULT_SEED_SIGNALS
