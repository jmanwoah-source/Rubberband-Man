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
import time
import json
import uuid
import sqlite3
import datetime
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

_BUS_JSON_LOCK = threading.Lock()
_BUS_INIT_LOCK = threading.Lock()
_INIT_BUS_PATHS: Set[str] = set()

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


def _parse_iso_ts(ts_val: Any) -> float:
    """Converts ISO-8601 timestamp strings into UTC epoch seconds for conflict resolution."""
    if not ts_val:
        return 0.0
    try:
        s = str(ts_val).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.timestamp()
    except Exception:
        return 0.0


def _normalize_signal_dict(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalizes a signal dict from SQLite or JSON into a canonical schema."""
    if not isinstance(raw, dict):
        return None
    sym = str(raw.get("symbol") or "").strip().upper()
    if not sym:
        return None
    bench = str(raw.get("primary_benchmark") or "SMH").strip().upper()
    if bench in ("XLE", "XLI"):
        bench = "URA"
    try:
        score = int(raw.get("wiki_score", 75))
    except (TypeError, ValueError):
        score = 75
    return {
        "symbol": sym,
        "track": str(raw.get("track") or "TRACK_A_FORTRESS"),
        "wiki_score": score,
        "primary_benchmark": bench,
        "parent_whale": str(raw.get("parent_whale") or "NVDA").strip().upper(),
        "dilution_risk": bool(raw.get("dilution_risk", False)),
        "thesis_hook": str(raw.get("thesis_hook") or ""),
        "last_updated": str(raw.get("last_updated") or ""),
    }


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
    """
    Opens a SQLite connection to intel_bus.db and runs DDL + WAL setup once per DB path
    instead of taking write locks on every read.
    """
    db_path = os.path.abspath(get_sqlite_db_path(bus_dir))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    needs_init = (db_path not in _INIT_BUS_PATHS) or (not os.path.exists(db_path))
    if needs_init:
        with _BUS_INIT_LOCK:
            if (db_path not in _INIT_BUS_PATHS) or (not os.path.exists(db_path)):
                conn = sqlite3.connect(db_path, timeout=15.0)
                conn.execute("PRAGMA busy_timeout=15000;")
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
                _INIT_BUS_PATHS.add(db_path)
                return conn

    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.execute("PRAGMA busy_timeout=15000;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _load_sqlite_signals(b_dir: str) -> Dict[str, Dict[str, Any]]:
    """Loads all signals from intel_bus.db into a symbol-keyed dict."""
    out: Dict[str, Dict[str, Any]] = {}
    db_path = get_sqlite_db_path(b_dir)
    if not os.path.exists(db_path):
        return out
    conn: Optional[sqlite3.Connection] = None
    try:
        conn = init_sqlite_bus(b_dir)
        rows = conn.execute(
            "SELECT symbol, track, wiki_score, primary_benchmark, parent_whale, dilution_risk, thesis_hook, last_updated "
            "FROM intel_signals ORDER BY wiki_score DESC;"
        ).fetchall()
        for r in rows:
            item = _normalize_signal_dict({
                "symbol": r[0],
                "track": r[1],
                "wiki_score": r[2],
                "primary_benchmark": r[3],
                "parent_whale": r[4],
                "dilution_risk": bool(r[5]),
                "thesis_hook": r[6],
                "last_updated": r[7],
            })
            if item:
                out[item["symbol"]] = item
    except Exception as e:
        print(f"Warning reading SQLite bus: {e}")
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    return out


def _quarantine_corrupt_json(json_path: str) -> Optional[str]:
    """Moves an unreadable/corrupt signals_bridge.json aside for forensics without silently deleting it."""
    if not os.path.exists(json_path):
        return None
    quarantine_path = f"{json_path}.corrupt.{int(time.time())}.{uuid.uuid4().hex[:6]}"
    try:
        os.replace(json_path, quarantine_path)
        print(f"Quarantined corrupt JSON bridge file to {quarantine_path}")
        return quarantine_path
    except OSError as e:
        print(f"Warning quarantining corrupt JSON bridge file {json_path}: {e}")
        return None


def write_signal_to_bus(signal: Dict[str, Any], bus_dir: Optional[str] = None) -> bool:
    """
    Atomically writes a signal payload into both SQLite WAL and signals_bridge.json.
    Callable by Qwen 3.8 Karpathy Wiki Agent or ingestion worker.
    Never overwrites signals_bridge.json with {} on parse failure (quarantines corrupt file
    and rebuilds from SQLite).
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

    # 2. Write to atomic JSON bridge (synchronized + fsync + corrupt-file quarantine + try/finally cleanup)
    json_ok = False
    tmp_path: Optional[str] = None
    try:
        json_path = get_json_bridge_path(b_dir)
        with _BUS_JSON_LOCK:
            existing: Dict[str, Dict[str, Any]] = {}
            json_corrupt = False
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        curr_list = json.load(f)
                    if not isinstance(curr_list, list):
                        raise ValueError("signals_bridge.json root is not a JSON list")
                    for item in curr_list:
                        norm = _normalize_signal_dict(item)
                        if norm:
                            existing[norm["symbol"]] = norm
                except Exception as parse_err:
                    print(f"Warning parsing {json_path} ({parse_err}); quarantining and rebuilding from SQLite.")
                    json_corrupt = True
                    _quarantine_corrupt_json(json_path)

            # Backfill from SQLite (critical on corrupt-JSON rebuild and prevents split-brain loss)
            sqlite_signals = _load_sqlite_signals(b_dir)
            if json_corrupt:
                existing = dict(sqlite_signals)
            else:
                for s_sym, s_val in sqlite_signals.items():
                    if s_sym not in existing or _parse_iso_ts(s_val.get("last_updated")) > _parse_iso_ts(
                        existing[s_sym].get("last_updated")
                    ):
                        existing[s_sym] = s_val

            existing[sym] = {
                "symbol": sym,
                "track": track,
                "wiki_score": wiki_score,
                "primary_benchmark": primary_benchmark,
                "parent_whale": parent_whale,
                "dilution_risk": bool(dilution_risk),
                "thesis_hook": thesis_hook,
                "last_updated": last_updated,
            }

            tmp_path = f"{json_path}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(list(existing.values()), f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, json_path)
                json_ok = True
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
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
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for s in DEFAULT_SEED_SIGNALS:
            seed_copy = dict(s)
            seed_copy["last_updated"] = now_iso
            write_signal_to_bus(seed_copy, b_dir)


def read_intel_bus_signals(bus_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Reads all available Track A, B, and C signals from BOTH SQLite WAL and signals_bridge.json,
    merging by newest `last_updated` per symbol to eliminate split-brain drift.
    Automatically normalizes legacy XLE/XLI benchmark references to URA.
    """
    b_dir = bus_dir or resolve_intel_bus_dir()
    seed_intel_bus_if_empty(b_dir, force_upgrade=False)

    merged: Dict[str, Dict[str, Any]] = _load_sqlite_signals(b_dir)

    json_path = get_json_bridge_path(b_dir)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for raw_item in data:
                    norm = _normalize_signal_dict(raw_item)
                    if not norm:
                        continue
                    sym = norm["symbol"]
                    if sym not in merged:
                        merged[sym] = norm
                    else:
                        if _parse_iso_ts(norm.get("last_updated")) > _parse_iso_ts(
                            merged[sym].get("last_updated")
                        ):
                            merged[sym] = norm
        except Exception as e:
            print(f"Warning reading JSON bridge: {e}")

    if merged:
        return sorted(merged.values(), key=lambda x: int(x.get("wiki_score", 0) or 0), reverse=True)

    return DEFAULT_SEED_SIGNALS
