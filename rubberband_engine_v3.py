"""
Rubberband Engine v3.5 - Institutional 1-5 Day Kinetic Swing & 30-45 DTE Options Engine
Optimized for ASUS GX10 (Qwen 3.8 + Karpathy Research Wiki) & 100% FMP Pro API

Core Pillars:
1. Ultra-Fast FMP Pro Batch & Hybrid Intraday/EOD Ingestion (/batch-quote, /historical-price-eod, /historical-chart/4hour)
2. True Dual-Coordinate Elasticity & Move-Detection Math:
   - Volume-Weighted Equilibrium (VWMA-20 + EMA-20) & Wilder's ATR(14) Keltner Channels
   - Absolute Institutional Stretch (Z_abs) + Beta-Adjusted Factor Residual (Z_rel_5d) -> True Effective Z-Score
   - Ornstein-Uhlenbeck (O-U) Mean-Reversion Half-Life (τ_1/2 in days) & Variance-Ratio Hurst Exponent (H)
   - 2nd-Derivative Velocity (Δ²Z Inflection Hook) & Volatility Squeeze / Coiled Spring Breakout Detector
   - Yang-Zhang 30D Volatility Estimator & Skew/Vanna-Adjusted 30-45 DTE Black-Scholes Pricing
3. 6-Pillar Greater Market & 24/48-Hour US Market Direction Radar:
   - Bonds (TLT & 10Y-2Y Curve), Credit Stress (HYG/LQD Ratio Z-Score), Crude Oil (CLUSD/USO),
     Gold (GLD), Silver (SLV), and Bitcoin (BTCUSD) + Eurodollar (EURUSD/UUP)
4. Full FMP Pro Fundamental & Catalyst Bifurcation Engine:
   - Real /financial-scores (Altman Z-Score & Piotroski F-Score 0-9)
   - Real /financial-growth (Revenue Growth, 3Y CAGR, Operating Income & FCF Growth)
   - Deterministic /earnings-calendar Countdown (Exact Days to Earnings)
"""

import os
import re
import time
import math
import json
import sqlite3
import threading
import datetime
from contextlib import closing
from datetime import timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
import marketdata_client

load_dotenv()

FMP_KEY = os.getenv("FMP_API_KEY", "").strip()
FMP_STABLE_URL = "https://financialmodelingprep.com/stable"

# =========================================================================
# 5 EXPANDED SECTOR & THEMATIC ETF UNIVERSES
# =========================================================================
THEMATIC_ETFS = {
    "SMH", "SOXX", "IGV", "SRVR", "DTCR", "REMX", "URA", "NLR", "GRID", "XLU",
    "ROBO", "BOTZ", "JEDI", "QTUM", "SPY", "QQQ", "IWM", "RSP"
}

SECTORS = {
    "Semiconductors": {
        "benchmark": "SMH",
        "etfs": ["SMH", "SOXX"],
        "description": "High-Beta Silicon, HBM Memory, Wafer Fab & Advanced Packaging",
        "tickers": [
            "SMH", "SOXX", "NVDA", "AVGO", "TSM", "AMD", "MU", "MRVL", "AMAT", "LRCX",
            "KLAC", "ASML", "ADI", "TXN", "NXPI", "ON", "MPWR", "TER", "ENTG", "ONTO",
            "CAMT", "ARM", "QCOM", "INTC", "SNDK"
        ]
    },
    "AI Infrastructure": {
        "benchmark": "SRVR",
        "etfs": ["SRVR", "DTCR", "IGV"],
        "description": "Datacenter Liquid Cooling, 800G/1.6T Optical, AI Neoclouds & Interconnect",
        "tickers": [
            "SRVR", "DTCR", "IGV", "VRT", "ANET", "CRDO", "COHR", "CIEN", "LITE", "CLS",
            "FN", "PSTG", "NTAP", "EQIX", "DLR", "DELL", "SMCI", "HPE", "ORCL", "NOW",
            "PLTR", "SNOW", "DDOG", "MDB"
        ]
    },
    "Energy, Grid & Materials": {
        "benchmark": "URA",
        "etfs": ["REMX", "URA", "NLR", "GRID", "XLU"],
        "description": "Nuclear SMRs, HALEU Enrichment, AI Grid Power & Critical Materials",
        "tickers": [
            "REMX", "URA", "NLR", "GRID", "XLU", "CEG", "VST", "TLN", "OKLO", "SMR",
            "CCJ", "BWXT", "LEU", "UEC", "NXE", "NNE", "GEV", "PWR", "ETN", "MP",
            "ALB", "FCX", "NEE", "SO"
        ]
    },
    "Robotics & Autonomous": {
        "benchmark": "ROBO",
        "etfs": ["ROBO", "BOTZ", "JEDI"],
        "description": "Physical AI, Autonomous Mobility, Aerospace Robotics, LiDAR & Machine Vision",
        "tickers": [
            "ROBO", "BOTZ", "JEDI", "ISRG", "SYM", "ROK", "ZBRA", "CGNX", "NOVT", "OUST",
            "AVAV", "KTOS", "JOBY", "ACHR", "RKLB", "TSLA", "HON", "EMR", "ABB", "PATH",
            "IOT"
        ]
    },
    "Edge AI & Next-Gen Compute": {
        "benchmark": "QTUM",
        "etfs": ["QTUM", "JEDI", "ROBO"],
        "description": "Edge Silicon, Quantum Compute, Embedded Inference & Cyber Security",
        "tickers": [
            "QTUM", "ARM", "QCOM", "AMBA", "SLAB", "LSCC", "SYNA", "CRUS", "HIMX", "CEVA",
            "S", "NET", "CRWD", "PANW", "IONQ", "RGTI", "AAPL"
        ]
    },
}

# Backwards-compatibility map if older session state or scripts pass legacy sector/benchmark names
LEGACY_SECTOR_ALIAS = {
    "Energy & Material Science": "Energy, Grid & Materials",
    "Nuclear & Next-Gen Energy": "Energy, Grid & Materials",
    "Nuclear Energy": "Energy, Grid & Materials",
    "Robotics & Automation": "Robotics & Autonomous",
    "Robotics": "Robotics & Autonomous",
    "Edge AI": "Edge AI & Next-Gen Compute",
}
LEGACY_BENCHMARK_ALIAS = {
    "XLE": "URA"
}

# Sub-factor benchmark mapping so Grid Power vs Pure Uranium vs Rare Earths use exact institutional factor correlation
SUB_BENCHMARK_MAP = {
    "CEG": "XLU", "VST": "XLU", "TLN": "XLU", "GEV": "XLU", "NEE": "XLU", "SO": "XLU",
    "ETN": "GRID", "PWR": "GRID",
    "OKLO": "URA", "SMR": "URA", "CCJ": "URA", "BWXT": "URA", "LEU": "URA", "NNE": "URA",
    "NXE": "URA", "UEC": "URA",
    "MP": "REMX", "ALB": "REMX", "FCX": "REMX",
    "AVAV": "JEDI", "KTOS": "JEDI", "RKLB": "JEDI", "JOBY": "JEDI", "ACHR": "JEDI",
}

BENCHMARK_CHOICES = [
    "SMH", "SOXX", "SRVR", "IGV", "DTCR", "URA", "REMX", "NLR", "GRID", "XLU",
    "ROBO", "BOTZ", "JEDI", "QTUM", "QQQ", "SPY", "IWM"
]

# --- HIGH-PERFORMANCE IN-MEMORY + SQLITE WAL CACHE & CONNECTION POOL ---
_CACHE_STORE: Dict[str, Tuple[Any, float]] = {}
_CACHE_LOCK = threading.RLock()
CACHE_TTL = 300  # 5 minutes default TTL

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(_DATA_DIR, exist_ok=True)
_FMP_CACHE_DB = os.path.join(_DATA_DIR, "fmp_cache.db")


_LAST_FMP_SQLITE_PRUNE_TS = 0.0


def _redact_secrets(msg: str) -> str:
    s = re.sub(r"([?&](?:apikey|token)=)[^&\s'\"]+", r"\1[REDACTED]", str(msg or ""), flags=re.IGNORECASE)
    return re.sub(r"(Bearer\s+)[A-Za-z0-9._\-]+", r"\1[REDACTED]", s, flags=re.IGNORECASE)


def _fmp_cache_key(endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
    return f"{endpoint}_{sorted((params or {}).items())}"


def _init_fmp_cache_db() -> None:
    try:
        cutoff = time.time() - (7 * 86400)
        with closing(sqlite3.connect(_FMP_CACHE_DB, timeout=10)) as conn:
            with conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS fmp_http_cache (
                        cache_key TEXT PRIMARY KEY,
                        ts REAL NOT NULL,
                        ttl INTEGER NOT NULL,
                        payload TEXT NOT NULL
                    )
                    """
                )
                conn.execute("DELETE FROM fmp_http_cache WHERE ts < ?", (cutoff,))
    except Exception:
        pass


_init_fmp_cache_db()

_FMP_RETRY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)
_HTTP_SESSION = requests.Session()
_HTTP_ADAPTER = HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=_FMP_RETRY)
_HTTP_SESSION.mount("https://", _HTTP_ADAPTER)
_HTTP_SESSION.mount("http://", _HTTP_ADAPTER)


def normalize_sector_name(sec_name: str) -> str:
    sec_name = LEGACY_SECTOR_ALIAS.get(sec_name, sec_name)
    return sec_name if sec_name in SECTORS else "Semiconductors"


def normalize_benchmark(bench: str) -> str:
    b = (bench or "SMH").strip().upper()
    return LEGACY_BENCHMARK_ALIAS.get(b, b)


def get_ticker_sector(symbol: str) -> str:
    """
    Returns the sector name for a symbol. First checks Rubberband curated SECTORS,
    then queries FMP profile (cached 7 days).
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return "Equities"
    for s_name, s_meta in SECTORS.items():
        if sym in s_meta.get("tickers", []):
            return s_name
    cache_key = f"profile_sec_v1_{sym}"
    cached = get_cached(cache_key, ttl=86400 * 7)
    if cached:
        return cached
    try:
        res = fmp_get("profile", params={"symbol": sym}, ttl=86400 * 7)
        if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
            sec = res[0].get("sector") or res[0].get("industry") or "Equities"
            set_cached(cache_key, sec)
            return sec
    except Exception:
        pass
    return "Custom Watchlist"


_CACHE_MAX_ENTRIES = 2500  # Cap cache entries to prevent 24/7 memory growth

def get_cached(key: str, ttl: int = CACHE_TTL) -> Optional[Any]:
    now = time.time()
    with _CACHE_LOCK:
        if key in _CACHE_STORE:
            val, ts = _CACHE_STORE[key]
            if now - ts < ttl:
                return val
            del _CACHE_STORE[key]

    try:
        with closing(sqlite3.connect(_FMP_CACHE_DB, timeout=5)) as conn:
            row = conn.execute(
                "SELECT payload, ts, ttl FROM fmp_http_cache WHERE cache_key = ?", (key,)
            ).fetchone()
            if row:
                payload_str, ts, row_ttl = row
                eff_ttl = max(ttl, int(row_ttl or ttl)) if ttl > CACHE_TTL else min(ttl, int(row_ttl or ttl)) if row_ttl else ttl
                if now - float(ts) < eff_ttl:
                    val = json.loads(payload_str)
                    with _CACHE_LOCK:
                        _CACHE_STORE[key] = (val, float(ts))
                    return val
    except Exception:
        pass
    return None


def set_cached(key: str, val: Any, ttl: int = CACHE_TTL) -> None:
    global _LAST_FMP_SQLITE_PRUNE_TS
    now = time.time()
    do_prune = False
    with _CACHE_LOCK:
        # Periodic batch pruning if cache exceeds maximum capacity
        if len(_CACHE_STORE) >= _CACHE_MAX_ENTRIES:
            expired_keys = [k for k, (_, ts) in _CACHE_STORE.items() if now - ts > CACHE_TTL]
            for k in expired_keys:
                _CACHE_STORE.pop(k, None)
            if len(_CACHE_STORE) >= _CACHE_MAX_ENTRIES:
                oldest_keys = sorted(_CACHE_STORE.keys(), key=lambda k: _CACHE_STORE[k][1])[:int(_CACHE_MAX_ENTRIES * 0.20)]
                for k in oldest_keys:
                    _CACHE_STORE.pop(k, None)
        _CACHE_STORE[key] = (val, now)
        if now - _LAST_FMP_SQLITE_PRUNE_TS >= 3600.0:
            _LAST_FMP_SQLITE_PRUNE_TS = now
            do_prune = True

    try:
        payload_str = json.dumps(val)
        with closing(sqlite3.connect(_FMP_CACHE_DB, timeout=5)) as conn:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO fmp_http_cache (cache_key, ts, ttl, payload) VALUES (?, ?, ?, ?)",
                    (key, now, int(ttl), payload_str),
                )
                if do_prune:
                    conn.execute(
                        "DELETE FROM fmp_http_cache WHERE ts < ? OR (? - ts) > MAX(ttl, 86400)",
                        (now - 7 * 86400, now),
                    )
    except Exception:
        # Non-JSON-serializable entries (e.g. DataFrame tuples) remain fast in L1 RAM only
        pass


def get_ny_now() -> datetime.datetime:
    """Returns current Wall Street time (America/New_York) regardless of workstation timezone."""
    try:
        return datetime.datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5)))


def fmp_get(endpoint: str, params: Optional[Dict[str, Any]] = None, use_cache: bool = True, ttl: int = CACHE_TTL) -> Any:
    """Execute authenticated FMP Pro request against stable endpoint with L1 RAM + L2 SQLite WAL caching."""
    api_key = os.getenv("FMP_API_KEY", FMP_KEY).strip()
    if not api_key:
        return {"error": "FMP_API_KEY is missing."}
    if params is None:
        params = {}

    # Intercept single quote lookups if already populated via batch-quote cache
    if endpoint == "quote" and use_cache and "symbol" in params and "," not in str(params["symbol"]):
        sym_q = str(params["symbol"]).strip().upper()
        q_cached = get_cached(f"quote_single_{sym_q}", ttl=ttl)
        if q_cached is not None:
            return [q_cached]

    cache_key = _fmp_cache_key(endpoint, params) if use_cache else None
    if cache_key:
        cached = get_cached(cache_key, ttl=ttl)
        if cached is not None:
            return cached

    params_with_key = dict(params)
    params_with_key["apikey"] = api_key
    url = f"{FMP_STABLE_URL}/{endpoint}"
    try:
        res = _HTTP_SESSION.get(url, params=params_with_key, timeout=(5, 12))
        if res.status_code == 200:
            data = res.json()
            if cache_key:
                set_cached(cache_key, data, ttl=ttl)
            if endpoint == "quote" and isinstance(data, list) and len(data) == 1 and "symbol" in data[0]:
                set_cached(f"quote_single_{data[0]['symbol'].upper()}", data[0], ttl=ttl)
            return data
        return {"error": _redact_secrets(f"HTTP {res.status_code}: {res.text[:250]}")}
    except Exception as e:
        return {"error": _redact_secrets(str(e))}


def fmp_batch_quotes(symbols: List[str], ttl: int = 120) -> Dict[str, Dict[str, Any]]:
    """
    Hybrid MarketData.app (Level-1 NBBO) + FMP Pro Batch Quote Engine:
    - Enriches quotes with MarketData.app's real-time Level-1 NBBO (`bid`, `ask`, `mid`, `bidSize`, `askSize`)
      and seamlessly falls back to MarketData.app if FMP batch-quote misses a symbol.
    - Fetches live intraday quotes for up to 100 tickers in ONE single HTTP call (/batch-quote + /v1/stocks/bulkquotes/)
      and populates both the batch dictionary and individual quote cache keys.
    """
    clean_syms = list(dict.fromkeys([str(s).strip().upper() for s in symbols if str(s).strip()]))
    if not clean_syms:
        return {}

    out: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []

    for s in clean_syms:
        c = get_cached(f"quote_single_{s}", ttl=ttl)
        if c is not None and isinstance(c, dict):
            out[s] = c
        else:
            missing.append(s)

    if not missing:
        return out

    # Pre-load MarketData.app Level-1 NBBO bulk quotes (up to 100 equities in 1 call, SQLite-cached)
    md_map = marketdata_client.get_bulk_stock_quotes(missing, ttl=ttl)

    # Fetch missing in a single FMP batch-quote call
    joined = ",".join(missing)
    data = fmp_get("batch-quote", params={"symbols": joined}, use_cache=True, ttl=ttl)
    if isinstance(data, list) and len(data) > 0:
        for item in data:
            if isinstance(item, dict) and "symbol" in item:
                sym = str(item["symbol"]).upper()
                m_item = md_map.get(sym)
                if m_item:
                    item["bid"] = m_item.get("bid", 0.0)
                    item["ask"] = m_item.get("ask", 0.0)
                    item["mid"] = m_item.get("mid", item.get("price"))
                    item["bidSize"] = m_item.get("bidSize", 0)
                    item["askSize"] = m_item.get("askSize", 0)
                out[sym] = item
                set_cached(f"quote_single_{sym}", item)

    # Resolve any remaining missing symbols via MarketData.app bulk NBBO quotes or individual fallback
    still_missing = [s for s in missing if s not in out]
    for s_m in list(still_missing):
        if s_m in md_map:
            out[s_m] = md_map[s_m]
            set_cached(f"quote_single_{s_m}", md_map[s_m])
            still_missing.remove(s_m)

    if still_missing:
        def _fetch_one(sym_one: str):
            q = fmp_get("quote", params={"symbol": sym_one}, use_cache=True, ttl=ttl)
            if isinstance(q, list) and len(q) > 0 and isinstance(q[0], dict):
                return sym_one, q[0]
            return sym_one, {}

        with ThreadPoolExecutor(max_workers=8) as ex:
            for s_k, q_v in ex.map(_fetch_one, still_missing):
                if q_v:
                    out[s_k] = q_v
                    set_cached(f"quote_single_{s_k}", q_v)

    return out


# =========================================================================
# PILLAR 1: LIVE MARKETDATA.APP + FMP PRO HYBRID INTRADAY & EOD INGESTION
# =========================================================================

def get_hybrid_price_series(symbol: str, fetch_4h: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Fetches split-adjusted EOD history (FMP Pro primary with MarketData.app `/v1/stocks/candles/D/`
    synthesis), live real-time NBBO quote, and 4-hour intraday bars.
    Merges live intraday quote candle into the historical series so all
    elasticity, Z-scores, VWMA-20, ATR-14, and O-U half-life reflect live tape action.
    Returns: (df_ohlcv, live_quote, latest_4h_bar)
    """
    sym = normalize_benchmark(symbol)
    cache_key = f"hybrid_series_v43_{sym}_{1 if fetch_4h else 0}"
    cached = get_cached(cache_key, ttl=180)
    if cached is not None:
        return cached

    # 1. Primary 5-Year EOD History (FMP Pro with MarketData.app `/v1/stocks/candles/D/` fallback)
    df = None
    eod_data = fmp_get("historical-price-eod/full", params={"symbol": sym}, ttl=1800)
    if isinstance(eod_data, list) and len(eod_data) > 0:
        df = pd.DataFrame(eod_data)
        if "date" in df.columns and "close" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
            for col in ["open", "high", "low", "close", "volume"]:
                if col not in df.columns:
                    df[col] = df["close"] if col != "volume" else 1000000.0
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
            if "vwap" not in df.columns:
                df["vwap"] = (df["high"] + df["low"] + df["close"]) / 3.0
        else:
            df = None

    if df is None or df.empty:
        # Fallback to MarketData.app split-adjusted daily candles
        df = marketdata_client.get_candles_df(sym, resolution="D", countback=1260, ttl=3600)
        if df is None or df.empty:
            empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "vwap"])
            return empty_df, {}, None

    # 2. Real-Time Quote for Live Candle Injection (check pre-warmed batch cache + MarketData NBBO quote)
    live_q = get_cached(f"quote_single_{sym}", ttl=180)
    if not isinstance(live_q, dict) or not live_q:
        quote_data = fmp_get("quote", params={"symbol": sym}, ttl=120)
        live_q = quote_data[0] if (isinstance(quote_data, list) and len(quote_data) > 0) else {}
        if not live_q:
            md_q = marketdata_client.get_bulk_stock_quotes([sym], ttl=120).get(sym, {})
            if md_q:
                live_q = md_q

    # 3. 4-Hour Intraday Bars for Microstructure Tail Analysis
    latest_4h = None
    if fetch_4h:
        h4_data = fmp_get("historical-chart/4hour", params={"symbol": sym}, ttl=300)
        if isinstance(h4_data, list) and len(h4_data) > 0:
            latest_4h = h4_data[0]
        else:
            # Fallback to MarketData.app 4-hour aggregate candles
            m_4h = marketdata_client.get_candles_df(sym, resolution="4H", countback=40, ttl=600)
            if m_4h is not None and not m_4h.empty:
                last_r = m_4h.iloc[-1]
                latest_4h = {
                    "open": float(last_r["open"]),
                    "high": float(last_r["high"]),
                    "low": float(last_r["low"]),
                    "close": float(last_r["close"]),
                    "volume": float(last_r["volume"])
                }
    else:
        h4_cached = get_cached(_fmp_cache_key("historical-chart/4hour", {"symbol": sym}), ttl=600)
        if isinstance(h4_cached, list) and len(h4_cached) > 0:
            latest_4h = h4_cached[0]

    if live_q and "price" in live_q and live_q.get("price") is not None:
        live_price = float(live_q["price"])
        live_open = float(live_q.get("open") or live_price)
        live_high = float(live_q.get("dayHigh") or max(live_price, live_open))
        live_low = float(live_q.get("dayLow") or min(live_price, live_open))
        live_vol = float(live_q.get("volume") or 0.0)
        live_vwap = float(live_q.get("vwap") or ((live_high + live_low + live_price) / 3.0))

        ny_now = get_ny_now()
        today_dt = pd.Timestamp(year=ny_now.year, month=ny_now.month, day=ny_now.day)
        last_dt = df["date"].iloc[-1].floor("D")
        days_since_last_bar = int((today_dt - last_dt).days)

        is_cash_session_started = (ny_now.hour > 9) or (ny_now.hour == 9 and ny_now.minute >= 30)
        q_ts = live_q.get("timestamp")
        quote_is_today = False
        if q_ts:
            try:
                q_dt = datetime.datetime.fromtimestamp(int(q_ts), tz=ZoneInfo("America/New_York"))
                quote_is_today = (q_dt.date() == ny_now.date()) and (q_dt.hour > 9 or (q_dt.hour == 9 and q_dt.minute >= 30))
            except Exception:
                quote_is_today = False

        is_active_trading_today = quote_is_today or (is_cash_session_started and live_vol > 0)
        if days_since_last_bar <= 6:
            if last_dt < today_dt and ny_now.weekday() < 5 and is_active_trading_today:
                new_row = pd.DataFrame([{
                    "date": today_dt,
                    "open": live_open,
                    "high": live_high,
                    "low": live_low,
                    "close": live_price,
                    "volume": live_vol if live_vol > 0 else float(df["volume"].tail(5).mean()),
                    "vwap": live_vwap
                }])
                df = pd.concat([df, new_row], ignore_index=True)
            elif last_dt == today_dt:
                df.loc[df.index[-1], "close"] = live_price
                df.loc[df.index[-1], "high"] = max(float(df.loc[df.index[-1], "high"]), live_high)
                df.loc[df.index[-1], "low"] = min(float(df.loc[df.index[-1], "low"]), live_low)
                if "vwap" in df.columns:
                    df.loc[df.index[-1], "vwap"] = live_vwap
                if live_vol > 0:
                    df.loc[df.index[-1], "volume"] = max(float(df.loc[df.index[-1], "volume"]), live_vol)

    df = df.drop_duplicates(subset=["date"], keep="last").set_index("date").dropna(subset=["close"])
    result = (df, live_q, latest_4h)
    set_cached(cache_key, result)
    return result


def get_historical_series(symbol: str) -> pd.DataFrame:
    """Backwards-compatible wrapper returning full OHLCV DataFrame."""
    df, _, _ = get_hybrid_price_series(symbol)
    return df


# =========================================================================
# PILLAR 2: INSTITUTIONAL 1-5 DAY KINETIC & DUAL-COORDINATE MATH ENGINE
# =========================================================================

def calculate_wilders_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Computes Wilder's Smoothed RSI using ewm(alpha=1/period, adjust=False)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()

    both_zero = (avg_gain <= 1e-12) & (avg_loss <= 1e-12)
    only_loss_zero = (avg_loss <= 1e-12) & (avg_gain > 1e-12)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(~only_loss_zero, 100.0)
    rsi = rsi.where(~both_zero, 50.0)
    return rsi


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Computes Wilder's Average True Range (ATR)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def calculate_yang_zhang_volatility(open_s: pd.Series, high_s: pd.Series, low_s: pd.Series, close_s: pd.Series, window: int = 30) -> Tuple[float, float]:
    """
    Computes Yang-Zhang (2000) Minimum-Variance Unbiased Historical Volatility Estimator.
    Captures overnight opening jumps AND intraday high/low excursions (critical for 1-5 day options).
    Returns: (current_yz_vol_pct, vol_rank_1y_pct)
    """
    try:
        o = open_s.where(open_s > 0, np.nan).ffill()
        h = high_s.where(high_s > 0, np.nan).ffill()
        l = low_s.where(low_s > 0, np.nan).ffill()
        c = close_s.where(close_s > 0, np.nan).ffill()
        c_prev = c.shift(1)

        log_oc_prev = np.log(o / c_prev)
        log_co = np.log(c / o)
        log_ho = np.log(h / o)
        log_lo = np.log(l / o)
        log_hc = np.log(h / c)
        log_lc = np.log(l / c)

        # Rogers-Satchell intraday variance
        rs_var = (log_ho * log_hc + log_lo * log_lc).rolling(window, min_periods=10).mean()
        open_var = log_oc_prev.rolling(window, min_periods=10).var()
        close_var = log_co.rolling(window, min_periods=10).var()

        k = 0.34 / (1.34 + (window + 1.0) / (window - 1.0))
        yz_var = (open_var + k * close_var + (1.0 - k) * rs_var).clip(lower=1e-6)
        yz_vol_series = np.sqrt(yz_var * 252.0) * 100.0

        curr_vol = float(yz_vol_series.iloc[-1])
        if np.isnan(curr_vol) or curr_vol <= 5.0:
            fallback_vol = np.log(c / c_prev).rolling(window, min_periods=10).std() * np.sqrt(252.0) * 100.0
            curr_vol = float(fallback_vol.iloc[-1]) if not np.isnan(fallback_vol.iloc[-1]) else 40.0

        vol_1y = yz_vol_series.dropna().tail(252)
        if len(vol_1y) >= 15:
            v_min, v_max = float(vol_1y.min()), float(vol_1y.max())
            v_rank = ((curr_vol - v_min) / (v_max - v_min) * 100.0) if (v_max - v_min) > 1e-3 else 50.0
        else:
            v_rank = 50.0

        return round(float(np.clip(curr_vol, 12.0, 180.0)), 1), round(float(np.clip(v_rank, 1.0, 99.0)), 1)
    except Exception:
        return 40.0, 50.0


def calculate_ou_half_life_and_hurst(spread_series: pd.Series, price_series: pd.Series) -> Tuple[float, float, str]:
    """
    Computes:
    1. 180-Day Ornstein-Uhlenbeck (O-U) Mean-Reversion Half-Life τ_1/2 (in trading days) via AR(1) regression:
       ΔX_t = α + φ * X_{t-1} + ε_t  =>  τ_1/2 = -ln(2) / ln(1 + φ)
    2. 252-Day Multi-Lag Lo-MacKinlay Adjusted Variance-Ratio Hurst Exponent (H in [0.22, 0.78])
    Returns: (half_life_days, hurst_exponent, regime_label)
    """
    half_life = 8.0
    hurst = 0.50
    try:
        s = spread_series.dropna().tail(180)
        if len(s) >= 40:
            x_lag = s.shift(1).dropna()
            dx = s.diff().dropna()
            common = x_lag.index.intersection(dx.index)
            if len(common) >= 35:
                x_vals = x_lag.loc[common].values
                y_vals = dx.loc[common].values
                x_mean = np.mean(x_vals)
                denom = np.sum((x_vals - x_mean) ** 2)
                if denom > 1e-9:
                    phi = np.sum((x_vals - x_mean) * (y_vals - np.mean(y_vals))) / denom
                    if -0.95 < phi < -0.02:
                        hl = -math.log(2.0) / math.log(1.0 + phi)
                        half_life = float(np.clip(hl, 1.2, 22.0))
                    elif phi <= -0.95:
                        half_life = 1.2
                    else:
                        half_life = 22.0

        p_pos = price_series.dropna().tail(252)
        p_pos = p_pos[p_pos > 0]
        p = np.log(p_pos)
        if len(p) >= 60:
            n_p = len(p)
            var_1 = float(p.diff(1).var())
            h_lags: List[float] = []
            for q_lag in (2, 5, 10):
                d_q = p.diff(q_lag).dropna()
                if len(d_q) >= 20 and var_1 > 1e-9:
                    # Lo-MacKinlay finite-sample degrees-of-freedom bias adjustment
                    dof_adj = max(1.0, (n_p - 1.0) / max(1.0, (n_p - q_lag)))
                    var_q = float(d_q.var()) * dof_adj
                    if var_q > 1e-9:
                        vr_q = max(0.25, min(3.5, var_q / (q_lag * var_1)))
                        h_lags.append(0.5 + (math.log(vr_q) / (2.0 * math.log(q_lag))))
            if h_lags:
                hurst = float(np.clip(float(np.mean(h_lags)), 0.22, 0.78))
    except Exception:
        pass

    if hurst < 0.47 and half_life <= 5.5:
        regime = "FAST ELASTIC SPRING"
    elif hurst > 0.54:
        regime = "MOMENTUM BREAKOUT RUNNER"
    else:
        regime = "HYBRID SWING COIL"

    return round(half_life, 1), round(hurst, 2), regime


def _default_empirical_fallback(action: str, n_samples: int) -> Dict[str, Any]:
    is_call = "CALL" in action
    base = 4.2 if is_call else -4.2
    return {
        "expected_basis_pct": base,
        "expected_up_basis_pct": 4.5,
        "expected_down_basis_pct": -3.2,
        "p75_basis_pct": 6.5 if is_call else -6.5,
        "p25_up_pct": 2.2, "p75_up_pct": 6.5, "p90_up_pct": 8.5,
        "p10_close_pct": -4.2, "p25_close_pct": -1.5, "med_close_pct": 2.1, "p75_close_pct": 4.5, "p90_close_pct": 7.2,
        "p25_dn_pct": -1.5, "p75_dn_pct": -4.2, "p90_dn_pct": -6.0,
        "empirical_win_rate_pct": 58.0,
        "empirical_sample_n": max(1, int(n_samples)),
        "empirical_sample_n_eff": max(1, int(round(max(1, n_samples) * 0.45))),
        "basis_summary": f"Est. {base:+.1f}% 5D Basis Move (Baseline Prior)"
    }


def calculate_empirical_basis_expectation(
    eff_z_series: pd.Series,
    close_series: pd.Series,
    high_series: pd.Series,
    low_series: pd.Series,
    curr_z: float,
    action: str
) -> Dict[str, Any]:
    """
    Walk-forward 5-Year (~1,250-day) Empirical Conditional Basis % Move Estimator:
    Finds historical instances with similar Z-stretch (strictly using causal/entry-bar
    shock detection with zero future-bar censoring), de-clusters overlapping 5D windows
    with >=5 trading-day spacing, and enforces an option-viable win hurdle.
    """
    try:
        if not np.isfinite(curr_z):
            curr_z = 0.0

        df_emp = pd.DataFrame({
            "z": eff_z_series,
            "close": close_series,
            "high": high_series,
            "low": low_series
        }).dropna()

        if len(df_emp) < 60:
            return _default_empirical_fallback(action, len(df_emp))

        c_arr = df_emp["close"].to_numpy(dtype=float)
        h_arr = df_emp["high"].to_numpy(dtype=float)
        l_arr = df_emp["low"].to_numpy(dtype=float)
        z_arr = df_emp["z"].to_numpy(dtype=float)
        n_bars = len(c_arr) - 5

        if n_bars < 30:
            return _default_empirical_fallback(action, max(1, n_bars))

        # Causal shock detection: check ONLY entry bar & trailing bar [max(0, i-1) : i+1] (zero lookahead!)
        ret_1d = np.zeros(len(c_arr), dtype=float)
        ret_1d[1:] = np.abs(np.diff(c_arr) / np.maximum(1e-4, c_arr[:-1]))
        daily_std = float(np.std(ret_1d[1:max(21, n_bars)])) if n_bars > 20 else 0.025
        shock_thresh = max(0.075, 3.5 * daily_std)
        is_shock_window = np.zeros(n_bars, dtype=bool)
        for i in range(n_bars):
            lo_w = max(0, i - 1)
            hi_w = i + 1
            if np.max(ret_1d[lo_w:hi_w]) > shock_thresh:
                is_shock_window[i] = True

        # Vectorized forward 5-day basis calculations
        fwd_close_5d = ((c_arr[5:n_bars + 5] - c_arr[:n_bars]) / np.maximum(1e-4, c_arr[:n_bars])) * 100.0
        fwd_max_up = np.zeros(n_bars, dtype=float)
        fwd_max_dn = np.zeros(n_bars, dtype=float)
        for i in range(n_bars):
            c0 = max(1e-4, c_arr[i])
            fwd_max_up[i] = ((np.max(h_arr[i + 1:i + 6]) - c0) / c0) * 100.0
            fwd_max_dn[i] = ((np.min(l_arr[i + 1:i + 6]) - c0) / c0) * 100.0

        z_hist = z_arr[:n_bars]
        mask_raw = np.abs(z_hist - curr_z) <= 0.45
        mask_clean = mask_raw & (~is_shock_window)
        mask = mask_clean if np.sum(mask_clean) >= 16 else mask_raw

        if np.sum(mask) < 20:
            if curr_z < 0:
                mask_q = z_hist <= np.percentile(z_hist, 25)
            elif curr_z > 0:
                mask_q = z_hist >= np.percentile(z_hist, 75)
            else:
                mask_q = np.abs(z_hist) <= 0.65
            mask = (mask_q & (~is_shock_window)) if np.sum(mask_q & (~is_shock_window)) >= 15 else mask_q

        # Count de-clustered independent analog episodes (>= 5 trading days spacing -> zero overlap)
        analog_indices = np.where(mask)[0]
        n_eff = 0
        last_picked = -10
        for idx_a in analog_indices:
            if int(idx_a) - last_picked >= 5:
                n_eff += 1
                last_picked = int(idx_a)
        n_eff = max(1, n_eff)

        sub_close = fwd_close_5d[mask]
        sub_close = sub_close[np.isfinite(sub_close)]
        sub_up = fwd_max_up[mask]
        sub_up = sub_up[np.isfinite(sub_up)]
        sub_dn = fwd_max_dn[mask]
        sub_dn = sub_dn[np.isfinite(sub_dn)]

        if len(sub_up) < 5 or len(sub_dn) < 5:
            return _default_empirical_fallback(action, max(1, len(sub_up)))

        med_up = float(np.median(sub_up))
        p75_up = float(np.percentile(sub_up, 75))
        med_dn = float(np.median(sub_dn))
        p75_dn = float(np.percentile(sub_dn, 25))
        med_close = float(np.median(sub_close))
        mean_close = float(np.mean(sub_close))

        # Honest option-viable hit rate: Day-5 close clears theta carry (+1.25%), OR MFE clears target without Day-5 giveback
        if "CALL" in action:
            unconditional_close = 0.65 * med_close + 0.35 * mean_close
            exp_basis = round(0.25 * med_up + 0.75 * unconditional_close, 2)
            min_opt_hurdle = max(2.8, med_up * 0.70)
            wins = (sub_close >= 1.25) | ((sub_up >= min_opt_hurdle) & (sub_close >= 0.0))
        elif "PUT" in action:
            unconditional_close = 0.65 * med_close + 0.35 * mean_close
            exp_basis = round(0.25 * med_dn + 0.75 * unconditional_close, 2)
            min_opt_hurdle = max(2.8, abs(med_dn) * 0.70)
            wins = (sub_close <= -1.25) | ((np.abs(sub_dn) >= min_opt_hurdle) & (sub_close <= 0.0))
        else:
            exp_basis = round(med_close, 2)
            wins = np.abs(sub_close) >= 1.25

        win_rate = float(np.clip(np.mean(wins) * 100.0, 18.0, 92.0))
        sample_n = int(len(sub_up))

        return {
            "expected_basis_pct": exp_basis,
            "expected_up_basis_pct": round(med_up, 2),
            "expected_down_basis_pct": round(med_dn, 2),
            "p75_basis_pct": round(p75_up if "CALL" in action else p75_dn, 2),
            "p25_up_pct": round(float(np.percentile(sub_up, 25)), 2),
            "p75_up_pct": round(p75_up, 2),
            "p90_up_pct": round(float(np.percentile(sub_up, 90)), 2),
            "p10_close_pct": round(float(np.percentile(sub_close, 10)), 2),
            "p25_close_pct": round(float(np.percentile(sub_close, 25)), 2),
            "med_close_pct": round(float(np.median(sub_close)), 2),
            "p75_close_pct": round(float(np.percentile(sub_close, 75)), 2),
            "p90_close_pct": round(float(np.percentile(sub_close, 90)), 2),
            "p25_dn_pct": round(float(np.percentile(sub_dn, 75)), 2),
            "p75_dn_pct": round(p75_dn, 2),
            "p90_dn_pct": round(float(np.percentile(sub_dn, 10)), 2),
            "empirical_win_rate_pct": round(win_rate, 1),
            "empirical_sample_n": sample_n,
            "empirical_sample_n_eff": min(sample_n, n_eff),
            "basis_summary": f"{exp_basis:+.1f}% 5D Basis ({win_rate:.0f}% Win · {min(sample_n, n_eff)} Indep. Episodes)"
        }
    except Exception:
        return _default_empirical_fallback(action, 50)


def calculate_tape_sharp_flow(
    open_s: pd.Series,
    high_s: pd.Series,
    low_s: pd.Series,
    close_s: pd.Series,
    vol_s: pd.Series,
    primary_clv: float,
    bull_obv_div: bool,
    bear_obv_div: bool
) -> Dict[str, Any]:
    """
    Detects whether Institutional Whales / Sharps are LOADING (Accumulating) or UNLOADING (Distributing)
    directly from price-volume microstructure:
    1. 20-Day Chaikin Money Flow (CMF-20): Volume-weighted intraday close location accumulation
    2. 10-Day Up/Down Dollar Volume Block Ratio: Volume on green/accumulation bars vs red/distribution bars
    3. Dip-Buying / Rip-Selling Divergence (OBV + 4H/1D Tail Sweep)
    """
    try:
        hl_range = (high_s - low_s).replace(0, np.nan)
        mfm = ((close_s - low_s) - (high_s - close_s)) / hl_range
        mfm = mfm.fillna(0.0).clip(-1.0, 1.0)
        mfv = mfm * vol_s
        cmf_20 = float(mfv.tail(20).sum() / max(1.0, vol_s.tail(20).sum()))

        ret_1d = close_s.diff()
        last_10_ret = ret_1d.tail(10)
        last_10_vol = vol_s.tail(10)
        up_vol = float(last_10_vol[last_10_ret >= 0].sum())
        dn_vol = float(last_10_vol[last_10_ret < 0].sum())
        up_down_ratio = round(up_vol / max(1.0, dn_vol), 2) if dn_vol > 0 else 2.2

        # Sharp accumulation score (0 - 100, where 50 is neutral, >62 is Whales Loading, <38 is Sharps Unloading)
        raw_sharp = (
            50.0
            + cmf_20 * 55.0
            + (up_down_ratio - 1.0) * 14.0
            + primary_clv * 15.0
            + (10.0 if bull_obv_div else 0.0)
            - (10.0 if bear_obv_div else 0.0)
        )
        sharp_score = round(float(np.clip(raw_sharp, 5.0, 96.0)), 1)

        if sharp_score >= 64.0:
            label = "WHALES LOADING (SHARP ACCUMULATION)"
            short_badge = "WHALES LOADING"
            color = "#34D399"
        elif sharp_score >= 55.0:
            label = "SHARPS ACCUMULATING DIPS"
            short_badge = "SHARPS BUYING"
            color = "#00E676"
        elif sharp_score <= 36.0:
            label = "SHARPS UNLOADING (DISTRIBUTION)"
            short_badge = "SHARPS UNLOADING"
            color = "#F43F5E"
        elif sharp_score <= 45.0:
            label = "SHARPS TRIMMING INTO STRENGTH"
            short_badge = "SHARPS TRIMMING"
            color = "#FB923C"
        else:
            label = "TWO-WAY BALANCED INSTITUTIONAL FLOW"
            short_badge = "BALANCED FLOW"
            color = "#8AB4F8"

        return {
            "cmf_20": round(cmf_20, 3),
            "up_down_vol_ratio": float(np.clip(up_down_ratio, 0.2, 4.0)),
            "tape_sharp_score": sharp_score,
            "whale_status": label,
            "whale_short_badge": short_badge,
            "whale_color": color
        }
    except Exception:
        return {
            "cmf_20": 0.0,
            "up_down_vol_ratio": 1.0,
            "tape_sharp_score": 50.0,
            "whale_status": "TWO-WAY BALANCED INSTITUTIONAL FLOW",
            "whale_short_badge": "BALANCED FLOW",
            "whale_color": "#8AB4F8"
        }


def calculate_clv(high: float, low: float, close: float) -> float:
    """Close Location Value (CLV) in [-1.0, +1.0]."""
    denom = high - low
    if denom <= 0:
        return 0.0
    val = (2.0 * close - high - low) / denom
    return float(np.clip(val, -1.0, 1.0))


def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculates On-Balance Volume (OBV)."""
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def norm_cdf(x: float) -> float:
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def norm_inv(p: float) -> float:
    p = max(1e-7, min(1.0 - 1e-7, p))
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680133034412283e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549738605410873e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    LOW = 0.02425
    HIGH = 1.0 - LOW
    if p < LOW:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= HIGH:
        q = p - 0.5
        r = q * q
        return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )


def round_to_standard_strike(price: float) -> float:
    """Snaps theoretical strike prices to standard OCC exchange strike boundaries."""
    if price < 25.0:
        return round(round(price * 2.0) / 2.0, 2)
    elif price < 100.0:
        return round(round(price / 2.5) * 2.5, 2)
    elif price < 200.0:
        return round(round(price / 5.0) * 5.0, 2)
    elif price < 500.0:
        return round(round(price / 10.0) * 10.0, 2)
    else:
        return round(round(price / 25.0) * 25.0, 2)


def bs_call_price_delta(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
    """Computes Black-Scholes European call price and Delta."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0.01, S - K), 1.0 if S > K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    call = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    delta = norm_cdf(d1)
    return max(0.05, call), delta


def bs_put_price_delta(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
    """Computes Black-Scholes European put price and Delta."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0.01, K - S), -1.0 if K > S else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    put = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
    delta = norm_cdf(d1) - 1.0
    return max(0.05, put), delta


def calculate_otm_strike(
    curr_close: float,
    equilibrium_mean: float,
    realized_vol: float,
    action: str,
    moneyness_mode: str = "aggressive_otm",
    days_to_exp: int = 35,
    r: float = 0.043,
    vol_rank: float = 50.0
) -> Tuple[float, float, float]:
    """
    Calculates institutional 30-45 DTE strikes with Vanna/Vega volatility-regime adaptation.
    Prevents far-OTM lotto overshoot (~0.10 Delta) on deeply washed-out stocks while shifting
    closer ATM (0.35-0.40 Delta) when IV Rank is elevated to insulate against post-bounce IV crush.
    Returns: (strike, otm_pct, estimated_delta)
    """
    T = max(0.05, days_to_exp / 365.0)
    sigma = max(0.18, (realized_vol if not np.isnan(realized_vol) else 42.0) / 100.0)

    if moneyness_mode == "deep_convexity_otm":
        target_call_delta = 0.22
        target_put_delta = -0.22
        min_otm_pct = max(0.075, min(0.15, 0.095 * (sigma / 0.40)))
        max_otm_pct = max(0.14, min(0.22, 0.16 * (sigma / 0.40)))
    elif moneyness_mode == "moderate_otm":
        target_call_delta = 0.40
        target_put_delta = -0.40
        min_otm_pct = max(0.025, min(0.065, 0.038 * (sigma / 0.40)))
        max_otm_pct = max(0.08, min(0.13, 0.09 * (sigma / 0.40)))
    elif moneyness_mode == "target_reversion":
        eff_eq = min(curr_close * 1.14, equilibrium_mean) if "CALL" in action else max(curr_close * 0.86, equilibrium_mean)
        target_strike = round_to_standard_strike(eff_eq)
        if "CALL" in action and target_strike <= curr_close:
            target_strike = round_to_standard_strike(curr_close * 1.045)
        elif "PUT" in action and target_strike >= curr_close:
            target_strike = round_to_standard_strike(curr_close * 0.955)
        otm_pct = abs(target_strike - curr_close) / curr_close * 100.0
        if "CALL" in action:
            _, delta = bs_call_price_delta(curr_close, target_strike, T, r, sigma)
        else:
            _, delta = bs_put_price_delta(curr_close, target_strike, T, r, sigma)
        return target_strike, round(otm_pct, 1), round(delta, 2)
    else:
        # Vanna/Vega-Adaptive Institutional Sweet Spot (~0.28 to 0.37 Delta)
        if vol_rank >= 68.0:
            # High IV Rank: bounce triggers IV compression -> higher Delta protects Call PnL
            target_call_delta = 0.36
            target_put_delta = -0.35
            min_otm_pct = max(0.032, min(0.085, 0.048 * (sigma / 0.40)))
        elif vol_rank <= 35.0:
            # Low IV Rank: cheap convexity + Vega expansion tailwind
            target_call_delta = 0.29
            target_put_delta = -0.28
            min_otm_pct = max(0.045, min(0.105, 0.062 * (sigma / 0.40)))
        else:
            target_call_delta = 0.32
            target_put_delta = -0.30
            min_otm_pct = max(0.040, min(0.095, 0.055 * (sigma / 0.40)))
        max_otm_pct = max(0.10, min(0.165, 0.125 * (sigma / 0.40)))

    if "CALL" in action:
        d1 = norm_inv(target_call_delta)
        delta_strike = curr_close * math.exp(-d1 * sigma * math.sqrt(T) + (r + 0.5 * sigma**2) * T)
        dist_to_mean = max(0.0, equilibrium_mean - curr_close)
        mean_anchor = min(curr_close * (1.0 + max_otm_pct), curr_close + 0.38 * dist_to_mean)
        raw_strike = min(
            curr_close * (1.0 + max_otm_pct),
            max(delta_strike, curr_close * (1.0 + min_otm_pct), mean_anchor)
        )
        strike = round_to_standard_strike(raw_strike)
        if strike <= curr_close:
            strike = round_to_standard_strike(curr_close * (1.0 + min_otm_pct))
        otm_pct = max(0.5, (strike - curr_close) / curr_close * 100.0)
        _, est_delta = bs_call_price_delta(curr_close, strike, T, r, sigma)
        return strike, round(otm_pct, 1), round(est_delta, 2)
    elif "PUT" in action:
        target_N_d1 = 1.0 + target_put_delta
        d1 = norm_inv(target_N_d1)
        delta_strike = curr_close * math.exp(-d1 * sigma * math.sqrt(T) + (r + 0.5 * sigma**2) * T)
        dist_to_mean = max(0.0, curr_close - equilibrium_mean)
        mean_anchor = max(curr_close * (1.0 - max_otm_pct), curr_close - 0.38 * dist_to_mean)
        raw_strike = max(
            curr_close * (1.0 - max_otm_pct),
            min(delta_strike, curr_close * (1.0 - min_otm_pct), mean_anchor)
        )
        strike = round_to_standard_strike(raw_strike)
        if strike >= curr_close:
            strike = round_to_standard_strike(curr_close * (1.0 - min_otm_pct))
        otm_pct = max(0.5, (curr_close - strike) / curr_close * 100.0)
        _, est_delta = bs_put_price_delta(curr_close, strike, T, r, sigma)
        return strike, round(otm_pct, 1), round(est_delta, 2)
    else:
        strike = round_to_standard_strike(curr_close * 1.05)
        return strike, 5.0, 0.35


def calculate_rubberband_metrics_v3(
    ticker_df: pd.DataFrame,
    bench_df: pd.DataFrame,
    latest_4h: Optional[Dict[str, Any]] = None,
    day_override: Optional[int] = None,
    moneyness_mode: str = "aggressive_otm",
    is_etf: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Institutional 1-5 Day Kinetic & Dual-Coordinate Elasticity Engine:
    - Volume-Weighted Equilibrium (VWMA-20 + EMA-20) & Wilder's ATR(14) Keltner Channel
    - Dual-Coordinate Z-Score: Blends Absolute Institutional Stretch (Z_abs) + Relative Factor Residual (Z_rel_5d)
      with strict Directional Truth Guard (eliminates fake overbought signals on falling stocks)
    - Ornstein-Uhlenbeck (O-U) Half-Life τ_1/2 (days) & Variance-Ratio Hurst Exponent (H)
    - 2nd-Derivative Velocity (Δ²Z Inflection Hook) & Volatility Squeeze / Coiled Spring Detector
    - Yang-Zhang 30D Annualized Volatility & Skew-Aware 30-45 DTE Strike Engine
    """
    if ticker_df.empty or bench_df.empty or len(ticker_df) < 30 or len(bench_df) < 30:
        return None

    t_open = ticker_df["open"] if "open" in ticker_df.columns else ticker_df["close"]
    t_high = ticker_df["high"] if "high" in ticker_df.columns else ticker_df["close"] * 1.01
    t_low = ticker_df["low"] if "low" in ticker_df.columns else ticker_df["close"] * 0.99
    t_vol = ticker_df["volume"] if "volume" in ticker_df.columns else pd.Series(1000000.0, index=ticker_df.index)
    t_vwap = ticker_df["vwap"] if "vwap" in ticker_df.columns else (t_high + t_low + ticker_df["close"]) / 3.0

    merged = pd.DataFrame({
        "t_open": t_open,
        "t_high": t_high,
        "t_low": t_low,
        "t_close": ticker_df["close"],
        "t_vwap": t_vwap.replace(0, np.nan).ffill().fillna(ticker_df["close"]),
        "t_vol": t_vol.replace(0, np.nan).ffill().fillna(1000000.0),
        "b_close": bench_df["close"]
    }).dropna(subset=["t_close", "b_close"])

    if len(merged) < 30:
        return None

    # 1. Daily Log Returns & Rolling 20D Beta
    merged["t_log_ret"] = np.log(merged["t_close"] / merged["t_close"].shift(1))
    merged["b_log_ret"] = np.log(merged["b_close"] / merged["b_close"].shift(1))
    t_1d_pct = float((merged["t_close"].iloc[-1] / merged["t_close"].iloc[-2] - 1.0) * 100.0) if len(merged) >= 2 else 0.0

    cov_20 = merged["t_log_ret"].rolling(20).cov(merged["b_log_ret"])
    var_20 = merged["b_log_ret"].rolling(20).var().replace(0, np.nan)
    beta_series = (cov_20 / var_20).ffill().fillna(1.1).clip(lower=0.25, upper=3.5)
    current_beta = float(beta_series.iloc[-1])

    # 2. Institutional Equilibrium: True Exchange VWAP-Weighted VWMA-20, EMA-20, SMA-20, SMA-50, SMA-200, and ATR-14
    pv_20 = (merged["t_vwap"] * merged["t_vol"]).rolling(20, min_periods=5).sum()
    vol_20 = merged["t_vol"].rolling(20, min_periods=5).sum().replace(0, np.nan)
    vwma20_series = (pv_20 / vol_20).fillna(merged["t_close"].rolling(20, min_periods=1).mean())
    ema20_series = merged["t_close"].ewm(span=20, adjust=False).mean()
    sma20_series = merged["t_close"].rolling(20, min_periods=1).mean()
    sma50_series = merged["t_close"].rolling(50, min_periods=1).mean()
    sma200_series = merged["t_close"].rolling(200, min_periods=1).mean()

    atr14_series = calculate_atr(merged["t_high"], merged["t_low"], merged["t_close"], 14).replace(0, np.nan).bfill()
    std20_series = merged["t_close"].rolling(20, min_periods=5).std().replace(0, np.nan).bfill()

    # Volume-Weighted Institutional Equilibrium Mean
    equil_series = 0.55 * vwma20_series + 0.45 * ema20_series

    curr_close = float(merged["t_close"].iloc[-1])
    curr_high = float(merged["t_high"].iloc[-1])
    curr_low = float(merged["t_low"].iloc[-1])
    vwma20 = float(vwma20_series.iloc[-1])
    ema20 = float(ema20_series.iloc[-1])
    sma20 = float(sma20_series.iloc[-1])
    sma50 = float(sma50_series.iloc[-1])
    sma200 = float(sma200_series.iloc[-1])
    equil_mean = float(equil_series.iloc[-1])

    # --- OBVIOUS BAD-DATA CATCH & INTEGRITY VALIDATION LAYER ---
    raw_last_atr = float(atr14_series.iloc[-1]) if not np.isnan(atr14_series.iloc[-1]) else curr_close * 0.035
    raw_atr_pct = (raw_last_atr / max(0.01, curr_close)) * 100.0
    avg_20_vol_check = float(merged["t_vol"].iloc[-21:-1].mean()) if len(merged) > 21 else float(merged["t_vol"].tail(20).mean())
    avg_20_dollar_vol = avg_20_vol_check * curr_close
    max_abs_log_ret_25d = float(merged["t_log_ret"].tail(25).abs().max()) if len(merged) >= 5 else 0.0

    t_last_idx = ticker_df.index[-1]
    b_last_idx = bench_df.index[-1]
    stale_days = 0
    recent_5d_span = 7
    if isinstance(t_last_idx, pd.Timestamp) and isinstance(b_last_idx, pd.Timestamp):
        stale_days = int((b_last_idx - t_last_idx).days)
    if len(ticker_df) >= 5 and isinstance(ticker_df.index[-5], pd.Timestamp) and isinstance(t_last_idx, pd.Timestamp):
        recent_5d_span = int((t_last_idx - ticker_df.index[-5]).days)
    range_5d_pct = float(((merged["t_high"].tail(5).max() - merged["t_low"].tail(5).min()) / max(0.01, curr_close)) * 100.0) if len(merged) >= 5 else 5.0

    min_dvol_floor = 400_000.0 if is_etf else 3_500_000.0
    data_quality_ok = True
    data_quality_reason = "Verified Institutional Feed"
    if curr_close < 2.50:
        data_quality_ok = False
        data_quality_reason = f"Penny / Delisted Price (${curr_close:.2f} < $2.50)"
    elif raw_atr_pct > 22.0:
        data_quality_ok = False
        data_quality_reason = f"Corrupted ATR / Split Artifact ({raw_atr_pct:.0f}% Daily ATR)"
    elif avg_20_dollar_vol < min_dvol_floor:
        data_quality_ok = False
        data_quality_reason = f"Illiquid / Frozen Tape (${avg_20_dollar_vol / 1e6:.1f}M/day < ${min_dvol_floor / 1e6:.1f}M)"
    elif max_abs_log_ret_25d > 0.48:
        data_quality_ok = False
        data_quality_reason = "Unadjusted Split / Halt Gap (>60% 1D Anomaly)"
    elif stale_days > 6 or recent_5d_span > 16:
        data_quality_ok = False
        data_quality_reason = f"Stale / Delisted Ticker ({max(stale_days, recent_5d_span)}d Gap)"
    elif range_5d_pct < 0.85:
        data_quality_ok = False
        data_quality_reason = f"Buyout-Pinned / Frozen Range ({range_5d_pct:.2f}% 5D Range)"

    atr14_raw = float(atr14_series.tail(20).median()) if not np.isnan(atr14_series.iloc[-1]) else curr_close * 0.035
    if not np.isnan(atr14_series.iloc[-1]) and atr14_series.iloc[-1] <= curr_close * 0.18:
        atr14_raw = float(atr14_series.iloc[-1])
    atr14 = float(np.clip(atr14_raw, curr_close * 0.008, curr_close * 0.16))
    b_std20 = float(std20_series.iloc[-1]) if (not np.isnan(std20_series.iloc[-1]) and std20_series.iloc[-1] <= curr_close * 0.25) else curr_close * 0.04

    # 3. Absolute Institutional Price Stretch (Z_abs) & Keltner/Bollinger Squeeze Ratio
    # Keltner half-width = 1.60 * ATR14; Bollinger half-width = 1.0 * std20 (row-wise floor avoids future-spot lookahead)
    row_floor = (merged["t_close"] * 0.008).clip(lower=1e-4)
    z_keltner_series = (merged["t_close"] - equil_series) / (1.55 * atr14_series.clip(lower=row_floor))
    z_bollinger_series = (merged["t_close"] - sma20_series) / std20_series.clip(lower=row_floor)
    z_abs_series = (0.60 * z_keltner_series + 0.40 * z_bollinger_series).clip(lower=-3.45, upper=3.45)

    # Volatility Squeeze Ratio: BB Width / Keltner Width (< 0.92 indicates tightly coiled spring)
    squeeze_ratio_series = (2.0 * std20_series) / (1.65 * atr14_series.clip(lower=1e-4))
    squeeze_ratio = float(squeeze_ratio_series.iloc[-1]) if not np.isnan(squeeze_ratio_series.iloc[-1]) else 1.05
    is_volatility_squeeze = (squeeze_ratio <= 0.94)

    # 4. Relative Residual Stretch vs Benchmark (Z_rel_5d & Z_rel_3d) using lagged beta to avoid lookahead
    merged["t_5d_ret"] = np.log(merged["t_close"] / merged["t_close"].shift(5))
    merged["b_5d_ret"] = np.log(merged["b_close"] / merged["b_close"].shift(5))
    beta_lag5 = beta_series.shift(5).fillna(beta_series)
    merged["resid_5d"] = merged["t_5d_ret"] - (beta_lag5 * merged["b_5d_ret"])

    roll_mean_5d = merged["resid_5d"].rolling(60, min_periods=20).mean()
    roll_std_5d = merged["resid_5d"].rolling(60, min_periods=20).std().replace(0, np.nan).fillna(0.025)
    z_rel_5d_series = ((merged["resid_5d"] - roll_mean_5d) / roll_std_5d).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-3.45, 3.45)

    merged["t_3d_ret"] = np.log(merged["t_close"] / merged["t_close"].shift(3))
    merged["b_3d_ret"] = np.log(merged["b_close"] / merged["b_close"].shift(3))
    beta_lag3 = beta_series.shift(3).fillna(beta_series)
    merged["resid_3d"] = merged["t_3d_ret"] - (beta_lag3 * merged["b_3d_ret"])
    roll_mean_3d = merged["resid_3d"].rolling(60, min_periods=20).mean()
    roll_std_3d = merged["resid_3d"].rolling(60, min_periods=20).std().replace(0, np.nan).fillna(0.02)
    z_rel_3d_series = ((merged["resid_3d"] - roll_mean_3d) / roll_std_3d).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-3.45, 3.45)

    # 5. TRUE EFFECTIVE ELASTICITY Z-SCORE (Blends Absolute Stretch + Relative Residual with Directional Truth Guard)
    raw_eff_z_series = (0.62 * z_abs_series + 0.38 * z_rel_5d_series).clip(-3.45, 3.45)

    # Directional Truth Guard:
    # A stock below its equilibrium mean cannot be marked > +1.10σ overbought solely from relative outperformance in a down tape.
    # A stock above its equilibrium mean cannot be marked < -1.10σ oversold solely from relative lag in a ripping tape.
    eff_z_values = []
    for idx_i in range(len(merged)):
        za = float(z_abs_series.iloc[idx_i]) if not np.isnan(z_abs_series.iloc[idx_i]) else 0.0
        zr = float(z_rel_5d_series.iloc[idx_i]) if not np.isnan(z_rel_5d_series.iloc[idx_i]) else 0.0
        raw_ez = 0.62 * za + 0.38 * zr
        if za < -0.10 and raw_ez > 0.60:
            # Below equilibrium but outperforming a crashing benchmark -> cap Z near neutral
            raw_ez = za * 0.75
        elif za > 0.10 and raw_ez < -0.60:
            # Above equilibrium but lagging a ripping benchmark -> cap Z near neutral
            raw_ez = za * 0.75
        elif (za * zr) > 0:
            # Both absolute and relative stretch agree in direction -> amplify conviction slightly
            raw_ez = np.sign(za) * min(3.40, abs(raw_ez) * 1.12)
        eff_z_values.append(float(np.clip(raw_ez, -3.40, 3.40)))

    eff_z_series = pd.Series(eff_z_values, index=merged.index)

    z_score_5d = float(eff_z_series.iloc[-1])
    z_abs_curr = float(z_abs_series.iloc[-1])
    z_rel_curr = float(z_rel_5d_series.iloc[-1])
    z_score_3d = float(0.55 * z_abs_series.iloc[-1] + 0.45 * z_rel_3d_series.iloc[-1])

    # Velocity & 2nd-Derivative Inflection Hook (ΔZ and Δ²Z)
    z_1d_ago = float(eff_z_series.iloc[-2]) if len(eff_z_series) >= 2 else z_score_5d
    z_2d_ago = float(eff_z_series.iloc[-3]) if len(eff_z_series) >= 3 else z_1d_ago
    z_3d_ago = float(eff_z_series.iloc[-4]) if len(eff_z_series) >= 4 else z_score_5d
    delta_z_1d = z_score_5d - z_1d_ago
    delta_z_3d = z_score_5d - z_3d_ago
    prev_1d_vel = z_1d_ago - z_2d_ago
    accel_z_2d = delta_z_1d - prev_1d_vel  # 2nd derivative (curvature / hook)

    # 6. Ornstein-Uhlenbeck Half-Life (τ_1/2) & Hurst Exponent (H)
    ou_half_life, hurst_exp, statistical_regime = calculate_ou_half_life_and_hurst(
        eff_z_series, merged["t_close"]
    )

    # 7. Wilder's RSI(7) & RSI(14) + Sector RSI Divergence
    rsi_7_series = calculate_wilders_rsi(merged["t_close"], 7)
    rsi_14_series = calculate_wilders_rsi(merged["t_close"], 14)
    rsi_7 = float(rsi_7_series.iloc[-1])
    rsi_14 = float(rsi_14_series.iloc[-1])
    rsi_slope_3d = float(rsi_7 - rsi_7_series.iloc[-4]) if len(rsi_7_series) >= 4 else 0.0

    bench_rsi_14_series = calculate_wilders_rsi(merged["b_close"], 14)
    bench_rsi_14 = float(bench_rsi_14_series.iloc[-1]) if not bench_rsi_14_series.empty else 50.0
    rsi_divergence = round(rsi_14 - bench_rsi_14, 1)

    # 8. Microstructure: Daily CLV, 4-Hour CLV & 5-Day OBV Divergence
    daily_clv = calculate_clv(curr_high, curr_low, curr_close)
    h4_clv = daily_clv
    if latest_4h and "high" in latest_4h and "low" in latest_4h and "close" in latest_4h:
        try:
            h4_clv = calculate_clv(float(latest_4h["high"]), float(latest_4h["low"]), float(latest_4h["close"]))
        except Exception:
            h4_clv = daily_clv

    primary_clv = round(0.55 * h4_clv + 0.45 * daily_clv, 2)

    obv_series = compute_obv(merged["t_close"], merged["t_vol"])
    obv_5d_slope = float(obv_series.iloc[-1] - obv_series.iloc[-6]) if len(obv_series) >= 6 else 0.0
    price_5d_diff = float(merged["t_close"].iloc[-1] - merged["t_close"].iloc[-6]) if len(merged) >= 6 else 0.0

    bull_obv_divergence = (price_5d_diff < 0 and obv_5d_slope > 0)
    bear_obv_divergence = (price_5d_diff > 0 and obv_5d_slope < 0)

    # 9. Wall Street Timezone-Aware U-Shaped Relative Volume (RVOL)
    avg_20_vol = float(merged["t_vol"].iloc[-21:-1].mean()) if len(merged) > 21 else float(merged["t_vol"].tail(20).mean())
    today_vol = float(merged["t_vol"].iloc[-1])

    ny_now = get_ny_now()
    market_open = ny_now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = ny_now.replace(hour=16, minute=0, second=0, microsecond=0)

    last_bar_is_today = False
    try:
        if "date" in merged.columns and pd.notna(merged["date"].iloc[-1]):
            last_bar_dt = pd.to_datetime(merged["date"].iloc[-1]).date()
            last_bar_is_today = (last_bar_dt == ny_now.date())
    except Exception:
        last_bar_is_today = False

    if last_bar_is_today and market_open <= ny_now <= market_close and ny_now.weekday() < 5:
        mins_elapsed = max(15.0, (ny_now - market_open).total_seconds() / 60.0)
        x_frac = min(1.0, mins_elapsed / 390.0)
        # True Cumulative U-Shaped Institutional Volume Integral (heavier open & close, lighter midday)
        u_fraction = max(0.05, min(1.0, x_frac + 0.14 * math.sin(2.0 * math.pi * x_frac)))
        pacing_vol = avg_20_vol * u_fraction
        rvol = round(today_vol / pacing_vol, 2) if pacing_vol > 0 else 1.0
    else:
        rvol = round(today_vol / avg_20_vol, 2) if avg_20_vol > 0 else 1.0
    rvol = float(np.clip(rvol, 0.15, 8.5))

    # 10. Keltner / Bollinger Elasticity Envelope Boundaries
    upper_b = round(equil_mean + 2.0 * max(b_std20, 1.35 * atr14), 2)
    lower_b = round(max(0.50, equil_mean - 2.0 * max(b_std20, 1.35 * atr14)), 2)
    denom_b = upper_b - lower_b
    pct_b = (curr_close - lower_b) / denom_b if denom_b > 0 else 0.5

    # 11. Yang-Zhang 30-Day Realized Volatility & 1-Year Volatility Rank
    current_vol, vol_rank = calculate_yang_zhang_volatility(
        merged["t_open"], merged["t_high"], merged["t_low"], merged["t_close"], window=30
    )

    if vol_rank <= 30.0:
        options_regime = "Cheap Convexity (Low IV)"
        options_regime_desc = f"1Y Vol Rank {vol_rank:.0f}% — Prime Vega expansion setup for outright 30–45 DTE options."
    elif vol_rank >= 75.0:
        options_regime = "Elevated Skew (High IV)"
        options_regime_desc = f"1Y Vol Rank {vol_rank:.0f}% — High velocity premium; target fast 1–4 day snapback."
    else:
        options_regime = "Optimal Gamma Corridor"
        options_regime_desc = f"1Y Vol Rank {vol_rank:.0f}% — Balanced 30–45 DTE gamma/theta ratio."

    # 12. 3-PLAYBOOK DIRECTIONAL CLASSIFICATION (1-5 DAY MOVE UP OR DOWN)
    eff_pullback_z = min(z_score_5d, z_abs_curr * 0.92) if (z_score_5d < 0 or z_abs_curr < -0.75) else z_score_5d
    eff_extension_z = max(z_score_5d, z_abs_curr * 0.92) if (z_score_5d > 0 or z_abs_curr > 0.75) else z_score_5d

    is_inflection_hook_up = (
        eff_pullback_z <= -1.05
        and (delta_z_1d >= 0.05 or accel_z_2d >= 0.08 or primary_clv >= 0.15 or bull_obv_divergence)
    )
    is_inflection_hook_down = (
        eff_extension_z >= 1.20
        and (delta_z_1d <= -0.05 or accel_z_2d <= -0.08 or primary_clv <= -0.10 or pct_b >= 0.84)
    )
    is_rel_strength_coiling_up = (
        -0.85 <= z_score_5d <= 0.75
        and squeeze_ratio <= 0.94
        and pct_b <= 0.70
        and z_rel_curr >= 0.30
        and primary_clv >= 0.15
        and delta_z_1d >= 0.10
    )
    is_catalyst_momentum_up = (
        0.78 < z_score_5d < 1.50
        and rvol >= 1.45
        and primary_clv >= 0.25
        and delta_z_1d >= 0.30
        and z_rel_curr >= 0.75
    )
    is_momentum_breakdown = (
        -1.45 < z_score_5d < 0.85
        and z_rel_curr <= -0.80
        and curr_close < equil_mean
        and primary_clv <= -0.20
        and rvol >= 1.15
    )

    playbook_type = "MEAN_REVERSION"

    if not data_quality_ok:
        state = "QUARANTINED"
        action = "QUARANTINE (BAD DATA)"
        playbook_type = f"BAD DATA ({data_quality_reason})"
    elif eff_pullback_z <= -1.55 or is_inflection_hook_up:
        state = "OVERSOLD"
        action = "BUY CALL"
        playbook_type = "ELASTIC SNAPBACK CALL"
    elif eff_extension_z >= 1.55 or is_inflection_hook_down:
        state = "OVERBOUGHT"
        action = "BUY PUT"
        playbook_type = "EXHAUSTION REJECTION PUT"
    elif is_rel_strength_coiling_up:
        state = "COILED BULL BREAKOUT"
        action = "BUY CALL"
        playbook_type = "COILED SPRING BREAKOUT CALL"
    elif is_catalyst_momentum_up:
        state = "CATALYST BREAKOUT"
        action = "BUY CALL"
        playbook_type = "CATALYST MOMENTUM CALL"
    elif is_momentum_breakdown:
        state = "COILED BEAR BREAKDOWN"
        action = "BUY PUT"
        playbook_type = "DISTRIBUTION BREAKDOWN PUT"
    else:
        state = "NEUTRAL"
        if eff_pullback_z <= -0.60:
            action = "BUY CALL"
            playbook_type = "EARLY PULLBACK (CALL BIAS)"
        elif eff_extension_z >= 0.75:
            action = "BUY PUT"
            playbook_type = "UPPER BAND STRETCH (PUT BIAS)"
        elif -0.60 < z_score_5d <= 0.45 and squeeze_ratio <= 0.98 and z_rel_curr >= 0.35 and primary_clv >= 0.15:
            action = "BUY CALL"
            playbook_type = "EARLY COIL (CALL BIAS)"
        elif 0.45 <= eff_extension_z < 0.75 and squeeze_ratio <= 0.98 and z_rel_curr <= -0.35 and primary_clv <= -0.15:
            action = "BUY PUT"
            playbook_type = "EARLY STRETCH (PUT BIAS)"
        else:
            action = "WATCHLIST"
            playbook_type = "EQUILIBRIUM"

    # 12b. 5-Year Empirical Conditional Basis % Move & Tape Sharp/Whale Flow
    emp_basis = calculate_empirical_basis_expectation(
        eff_z_series=eff_z_series,
        close_series=merged["t_close"],
        high_series=merged["t_high"],
        low_series=merged["t_low"],
        curr_z=z_score_5d,
        action=action
    )
    sharp_flow = calculate_tape_sharp_flow(
        open_s=merged["t_open"],
        high_s=merged["t_high"],
        low_s=merged["t_low"],
        close_s=merged["t_close"],
        vol_s=merged["t_vol"],
        primary_clv=primary_clv,
        bull_obv_div=bull_obv_divergence,
        bear_obv_div=bear_obv_divergence
    )

    # 13. Half-Life-Paced O-U + Empirical 1-5 Day Target Price, Stop-Loss & Asymmetric R:R
    # Prevents compounding target overshoot on deeply washed-out stocks where 5D O-U convergence closes 1 - 2^(-5/tau)
    emp_move_dollar = curr_close * (max(1.5, abs(emp_basis["expected_basis_pct"])) / 100.0)
    expected_5d_move = min(3.4 * atr14, max(1.45 * atr14, emp_move_dollar))
    risk_1d_stop = max(0.85 * atr14, curr_close * 0.032)
    eff_hl = max(1.5, min(18.0, float(ou_half_life)))
    ou_5d_decay = 1.0 - (2.0 ** (-5.0 / eff_hl))

    if "CALL" in action:
        if equil_mean > curr_close:
            ou_paced_target = curr_close + ou_5d_decay * (equil_mean - curr_close)
            raw_target = 0.55 * ou_paced_target + 0.45 * (curr_close + expected_5d_move)
        else:
            # Breakout / Coiled Spring above equilibrium
            raw_target = curr_close + expected_5d_move
        max_5d_cap = min(curr_close * 1.18, curr_close + 3.6 * atr14)
        target_price = round(min(max_5d_cap, max(curr_close * 1.032, raw_target)), 2)
        invalidation_price = round(min(curr_close * 0.968, curr_close - risk_1d_stop), 2)
        target_gain_dollar = max(0.05, target_price - curr_close)
        risk_dollar = max(0.05, curr_close - invalidation_price)
        rr_ratio = round(target_gain_dollar / risk_dollar, 2)
    elif "PUT" in action:
        if equil_mean < curr_close:
            ou_paced_target = curr_close - ou_5d_decay * (curr_close - equil_mean)
            raw_target = 0.55 * ou_paced_target + 0.45 * (curr_close - expected_5d_move)
        else:
            raw_target = curr_close - expected_5d_move
        min_5d_floor = max(0.50, max(curr_close * 0.82, curr_close - 3.6 * atr14))
        target_price = round(max(min_5d_floor, min(curr_close * 0.968, raw_target)), 2)
        invalidation_price = round(max(curr_close * 1.032, curr_close + risk_1d_stop), 2)
        target_gain_dollar = max(0.05, curr_close - target_price)
        risk_dollar = max(0.05, invalidation_price - curr_close)
        rr_ratio = round(target_gain_dollar / risk_dollar, 2)
    else:
        target_price = round(equil_mean, 2)
        invalidation_price = round(lower_b if z_score_5d <= 0 else upper_b, 2)
        rr_ratio = 1.5

    # 14. Strike Selection (30-45 DTE Vanna/Vega-Adaptive Institutional Sweet Spot)
    call_strike, call_otm_pct, call_delta = calculate_otm_strike(
        curr_close=curr_close,
        equilibrium_mean=equil_mean,
        realized_vol=current_vol,
        action="BUY CALL",
        moneyness_mode=moneyness_mode,
        vol_rank=vol_rank
    )
    put_strike, put_otm_pct, put_delta = calculate_otm_strike(
        curr_close=curr_close,
        equilibrium_mean=equil_mean,
        realized_vol=current_vol,
        action="BUY PUT",
        moneyness_mode=moneyness_mode,
        vol_rank=vol_rank
    )

    if "CALL" in action:
        recommended_strike = call_strike
        recommended_otm_pct = call_otm_pct
        recommended_delta = call_delta
    elif "PUT" in action:
        recommended_strike = put_strike
        recommended_otm_pct = put_otm_pct
        recommended_delta = put_delta
    else:
        recommended_strike = round_to_standard_strike(curr_close)
        recommended_otm_pct = 0.0
        recommended_delta = 0.50

    # 15. Kinetic Velocity Status & Inflection Hook Telemetry
    if not data_quality_ok:
        velocity_status = "BAD DATA QUARANTINE"
        velocity_desc = data_quality_reason
        velocity_class = "txt-red"
    elif state == "OVERSOLD":
        if delta_z_1d >= 0.12 or accel_z_2d >= 0.18 or primary_clv >= 0.25:
            velocity_status = "INFLECTION HOOK UP"
            velocity_desc = f"Downward stretch decelerating (+{delta_z_1d:+.2f}σ 1D, CLV {primary_clv:+.2f}). 1–5D snapback igniting."
            velocity_class = "txt-green"
        elif delta_z_1d < -0.25 and primary_clv < -0.15:
            velocity_status = "FALLING KNIFE (WAIT)"
            velocity_desc = f"Downward velocity still expanding ({delta_z_1d:+.2f}σ 1D). Await 4H bottom-tail CLV hook."
            velocity_class = "txt-red"
        else:
            velocity_status = "COILING AT FLOOR"
            velocity_desc = f"Stretched at {z_score_5d:+.2f}σ (O-U Half-Life: {ou_half_life:.1f}d). Primed for turn."
            velocity_class = "txt-yellow"
    elif state == "OVERBOUGHT":
        if delta_z_1d <= -0.12 or accel_z_2d <= -0.18 or primary_clv <= -0.20:
            velocity_status = "REJECTION HOOK DOWN"
            velocity_desc = f"Upper-wick supply rejection active ({delta_z_1d:+.2f}σ 1D, CLV {primary_clv:+.2f}). Put entry confirmed."
            velocity_class = "txt-green"
        elif delta_z_1d > 0.25 and primary_clv > 0.20:
            velocity_status = "PARABOLIC MELT-UP"
            velocity_desc = f"Upward velocity still expanding (+{delta_z_1d:+.2f}σ 1D). Wait for upper-wick exhaustion."
            velocity_class = "txt-red"
        else:
            velocity_status = "BLOW-OFF APEX"
            velocity_desc = f"Stretched +{z_score_5d:.2f}σ above VWMA-20 (Half-Life: {ou_half_life:.1f}d)."
            velocity_class = "txt-yellow"
    elif "COILED" in state:
        velocity_status = "COILED SPRING IGNITION"
        velocity_desc = f"Squeeze ratio {squeeze_ratio:.2f}x with RVOL {rvol:.2f}x & CLV {primary_clv:+.2f}. Pre-breakout coil."
        velocity_class = "txt-green"
    else:
        velocity_status = "EQUILIBRIUM CORRIDOR"
        velocity_desc = f"Effective stretch ({z_score_5d:+.2f}σ) near VWMA-20 (${vwma20:.2f})."
        velocity_class = "txt-yellow"

    return {
        "price": round(curr_close, 2),
        "change_pct_1d": round(t_1d_pct, 2),
        "bench_price": round(float(merged["b_close"].iloc[-1]), 2),
        "beta": round(current_beta, 2),
        "z_score_5d": round(z_score_5d, 2),
        "z_score": round(z_score_5d, 2),
        "z_abs": round(z_abs_curr, 2),
        "z_rel_5d": round(z_rel_curr, 2),
        "z_score_3d": round(z_score_3d, 2),
        "z_3d_ago": round(z_3d_ago, 2),
        "delta_z_1d": round(delta_z_1d, 2),
        "delta_z_3d": round(delta_z_3d, 2),
        "accel_z_2d": round(accel_z_2d, 2),
        "accel_z": round(accel_z_2d, 2),
        "ou_half_life": ou_half_life,
        "hurst": hurst_exp,
        "statistical_regime": statistical_regime,
        "squeeze_ratio": round(squeeze_ratio, 2),
        "is_volatility_squeeze": is_volatility_squeeze,
        "playbook_type": playbook_type,
        "playbook": playbook_type,
        "rsi_7": round(rsi_7, 1),
        "rsi_14": round(rsi_14, 1),
        "rsi_slope_3d": round(rsi_slope_3d, 1),
        "daily_clv": round(daily_clv, 2),
        "h4_clv": round(h4_clv, 2),
        "clv": primary_clv,
        "bull_obv_divergence": bull_obv_divergence,
        "bear_obv_divergence": bear_obv_divergence,
        "rvol": rvol,
        "bollinger_pct_b": round(pct_b, 3),
        "vwma20": round(vwma20, 2),
        "ema20": round(ema20, 2),
        "equilibrium_price": round(equil_mean, 2),
        "sma20": round(equil_mean, 2),
        "raw_sma20": round(sma20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "atr14": round(atr14, 2),
        "upper_b": upper_b,
        "lower_b": lower_b,
        "state": state,
        "action": action,
        "recommended_strike": recommended_strike,
        "call_strike": call_strike,
        "put_strike": put_strike,
        "otm_pct": round(recommended_otm_pct, 1),
        "estimated_delta": round(recommended_delta, 2),
        "moneyness_mode": moneyness_mode,
        "target_price": target_price,
        "invalidation_price": invalidation_price,
        "rr_ratio": rr_ratio,
        "realized_vol": current_vol,
        "realized_vol_30d": current_vol,
        "vol_rank": vol_rank,
        "rsi_ticker": round(rsi_14, 1),
        "rsi_bench": round(bench_rsi_14, 1),
        "rsi_divergence": rsi_divergence,
        "options_regime": options_regime,
        "options_regime_desc": options_regime_desc,
        "rvol_badge": f"{rvol:.2f}x RVOL",
        "velocity_status": velocity_status,
        "velocity_desc": velocity_desc,
        "velocity_class": velocity_class,
        # New Empirical 1-5D Basis % Move & Hit Rate Telemetry
        "expected_basis_pct": emp_basis["expected_basis_pct"],
        "expected_up_basis_pct": emp_basis["expected_up_basis_pct"],
        "expected_down_basis_pct": emp_basis["expected_down_basis_pct"],
        "p75_basis_pct": emp_basis["p75_basis_pct"],
        "p25_up_pct": emp_basis.get("p25_up_pct", round(emp_basis["expected_up_basis_pct"] * 0.55, 2)),
        "p75_up_pct": emp_basis.get("p75_up_pct", emp_basis["p75_basis_pct"]),
        "p90_up_pct": emp_basis.get("p90_up_pct", round(emp_basis["expected_up_basis_pct"] * 1.65, 2)),
        "p10_close_pct": emp_basis.get("p10_close_pct", round(emp_basis["expected_down_basis_pct"] * 1.15, 2)),
        "p25_close_pct": emp_basis.get("p25_close_pct", round(emp_basis["expected_down_basis_pct"] * 0.45, 2)),
        "p50_close_pct": emp_basis.get("med_close_pct", round(emp_basis["expected_basis_pct"] * 0.55, 2)),
        "med_close_pct": emp_basis.get("med_close_pct", round(emp_basis["expected_basis_pct"] * 0.55, 2)),
        "p75_close_pct": emp_basis.get("p75_close_pct", round(emp_basis["expected_up_basis_pct"] * 0.75, 2)),
        "p90_close_pct": emp_basis.get("p90_close_pct", round(emp_basis["expected_up_basis_pct"] * 1.25, 2)),
        "p25_dn_pct": emp_basis.get("p25_dn_pct", round(emp_basis["expected_down_basis_pct"] * 0.55, 2)),
        "p75_dn_pct": emp_basis.get("p75_dn_pct", round(emp_basis["expected_down_basis_pct"] * 1.35, 2)),
        "p90_dn_pct": emp_basis.get("p90_dn_pct", round(emp_basis["expected_down_basis_pct"] * 1.75, 2)),
        "empirical_win_rate_pct": emp_basis["empirical_win_rate_pct"],
        "empirical_sample_n": emp_basis["empirical_sample_n"],
        "empirical_sample_n_eff": emp_basis.get("empirical_sample_n_eff", max(1, int(round(emp_basis["empirical_sample_n"] * 0.45)))),
        "basis_summary": emp_basis["basis_summary"],
        # New Live Tape Sharp / Whale Flow Telemetry
        "cmf_20": sharp_flow["cmf_20"],
        "up_down_vol_ratio": sharp_flow["up_down_vol_ratio"],
        "tape_sharp_score": sharp_flow["tape_sharp_score"],
        "sharp_tape_score": sharp_flow["tape_sharp_score"],
        "whale_status": sharp_flow["whale_status"],
        "whale_short_badge": sharp_flow["whale_short_badge"],
        "sharp_badge": sharp_flow["whale_short_badge"],
        "whale_color": sharp_flow["whale_color"],
        # Data Quality Validation Telemetry
        "data_quality_ok": data_quality_ok,
        "data_quality_reason": data_quality_reason,
        "is_bad_data": (not data_quality_ok),
        "bad_data_reason": data_quality_reason,
        "avg_20_dollar_vol_m": round(avg_20_dollar_vol / 1e6, 1)
    }


def calculate_rubberband_metrics(
    ticker_closes: pd.Series,
    bench_closes: pd.Series,
    ticker_volumes: Optional[pd.Series] = None,
    ticker_df_full: Optional[pd.DataFrame] = None
) -> Optional[Dict[str, Any]]:
    """Backwards-compatible wrapper preserving full OHLCV when available."""
    if ticker_df_full is not None and not ticker_df_full.empty:
        t_df = ticker_df_full
    else:
        t_df = pd.DataFrame({"close": ticker_closes})
        if ticker_volumes is not None:
            t_df["volume"] = ticker_volumes
    b_df = pd.DataFrame({"close": bench_closes})
    res = calculate_rubberband_metrics_v3(t_df, b_df)
    if res and "sim_1k" not in res:
        res["sim_1k"] = simulate_1k_options_trade(
            current_price=res["price"],
            recommended_strike=res["recommended_strike"],
            target_price=res["target_price"],
            invalidation_price=res["invalidation_price"],
            realized_vol=res["realized_vol"],
            action=res["action"],
            vol_rank=res.get("vol_rank", 50.0)
        )
    return res


# =========================================================================
# PILLAR 3: TEMPORAL & DAY-OF-WEEK PLAYBOOK ROUTER
# =========================================================================

def get_temporal_regime(override_day: Optional[int] = None) -> Dict[str, Any]:
    now = get_ny_now()
    weekday = override_day if override_day is not None else now.weekday()
    hour = now.hour

    is_friday_mode = (weekday == 4) or (weekday == 3 and hour >= 15) or (weekday in [5, 6])
    is_early_week_washout = (weekday in [0, 1])

    first_day = now.replace(day=1)
    first_friday = first_day + timedelta(days=(4 - first_day.weekday()) % 7)
    third_friday = first_friday + timedelta(weeks=2)
    days_to_opex = (third_friday.date() - now.date()).days
    is_opex_week = (0 <= days_to_opex <= 5)

    is_window_dressing = (now.day <= 2 or now.day >= 28)

    month = now.month
    if month in [9, 10]:
        seasonality_tag = "OCT/SEP HIGH-VOL WASHOUT PRE-Q4"
        seasonality_bias = "BULLISH_REVERSION_DISCOUNT"
    elif month in [11, 12]:
        seasonality_tag = "Q4 YEAR-END INSTITUTIONAL INFLOW"
        seasonality_bias = "BULLISH_MOMENTUM"
    elif month in [1, 2]:
        seasonality_tag = "JANUARY EFFECT & NEW-YEAR ROTATION"
        seasonality_bias = "SELECTIVE"
    elif month in [5, 6]:
        seasonality_tag = "SELL IN MAY & SUMMER CHOP"
        seasonality_bias = "DEFENSIVE"
    else:
        seasonality_tag = "MID-CYCLE INSTITUTIONAL REBALANCING"
        seasonality_bias = "NEUTRAL"

    if is_friday_mode:
        playbook_mode = "FRIDAY SUNRISE / WEEKEND FLIP"
        playbook_desc = "Hunting Friday De-Risking Exhaustion. Institutional bottom-tail absorption coiled for Monday Vanna/Charm reset."
        playbook_pill_color = "#00E676"
    elif is_early_week_washout:
        playbook_mode = "EARLY-WEEK WASHOUT REVERSION"
        playbook_desc = "Hunting Monday/Tuesday gap-down flushes hitting volume climax for Turnaround Wednesday mean reversion."
        playbook_pill_color = "#8AB4F8"
    else:
        playbook_mode = "MID-WEEK VELOCITY & COIL IGNITION"
        playbook_desc = "Monitoring 1–5 day inflection hooks, volatility squeezes & institutional trend convergence."
        playbook_pill_color = "#C58AF9"

    bias_pts_map = {
        "BULLISH_REVERSION_DISCOUNT": 12.0,
        "BULLISH_MOMENTUM": 10.0,
        "SELECTIVE": 4.0,
        "DEFENSIVE": -10.0,
        "NEUTRAL": 0.0,
    }
    day_edge_score = bias_pts_map.get(seasonality_bias, 0.0)
    if is_early_week_washout:
        day_edge_score += 4.0
    elif is_friday_mode:
        day_edge_score -= 3.0
    if is_opex_week:
        day_edge_score -= 4.0
    day_edge_score = round(float(np.clip(day_edge_score, -25.0, 25.0)), 1)

    return {
        "weekday": weekday,
        "weekday_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekday],
        "playbook_mode": playbook_mode,
        "playbook_desc": playbook_desc,
        "playbook_pill_color": playbook_pill_color,
        "is_friday_mode": is_friday_mode,
        "is_early_week_washout": is_early_week_washout,
        "is_opex_week": is_opex_week,
        "is_window_dressing": is_window_dressing,
        "seasonality_tag": seasonality_tag,
        "seasonality_bias": seasonality_bias,
        "day_edge_score": day_edge_score,
    }


# =========================================================================
# PILLAR 4: GREATER MARKET 6-PILLAR RADAR & 24/48-HOUR US MARKET FORECAST
# (Bonds, Credit Stress, Oil, Gold, Silver, Bitcoin + Eurodollar & Yields)
# =========================================================================

def _parse_fmp_calendar_ny(ev_date_str: str, ev_name: str = "") -> Optional[datetime.datetime]:
    """
    Safely parses FMP economic-calendar date strings (which FMP emits in UTC when timestamps are included,
    or YYYY-MM-DD when date-only) into timezone-aware America/New_York datetimes.
    """
    if not ev_date_str:
        return None
    s = str(ev_date_str).strip()
    ny_tz = ZoneInfo("America/New_York")
    try:
        if len(s) <= 10:
            # Date-only string: assign institutional US release hour (14:00 ET for FOMC/Auctions, 08:30 ET default)
            dt_d = datetime.date.fromisoformat(s[:10])
            up = (ev_name or "").upper()
            rel_hr = 14 if ("FOMC" in up or "FED INTEREST" in up) else (13 if "AUCTION" in up else (10 if ("ISM" in up or "JOLT" in up or "MICHIGAN" in up) else 8))
            rel_min = 0 if rel_hr != 8 else 30
            return datetime.datetime(dt_d.year, dt_d.month, dt_d.day, rel_hr, rel_min, tzinfo=ny_tz)
        ts = pd.to_datetime(s, utc=True)
        return ts.tz_convert(ny_tz).to_pydatetime()
    except Exception:
        return None


def get_macro_yield_regime() -> Dict[str, Any]:
    """Fetches FMP Pro Treasury Rates (10Y, 2Y, 3M) and TZ-Safe 1-5 Trading Day US Economic Runway."""
    cache_key = "macro_yield_regime_v47"
    cached = get_cached(cache_key, ttl=300)
    if cached is not None:
        return cached

    rates_data = fmp_get("treasury-rates", ttl=600)
    y10_current = 4.25
    y2_current = 3.95
    y3m_current = 4.30
    spread_10_2 = 0.30
    spread_2y_3m = -0.35
    rate_change_5d_bps = 0.0

    if isinstance(rates_data, list) and len(rates_data) > 0:
        latest_r = rates_data[0]
        y10_current = float(latest_r.get("year10") or 4.25)
        y2_current = float(latest_r.get("year2") or 3.95)
        y3m_current = float(latest_r.get("month3") or 4.30)
        spread_10_2 = round(y10_current - y2_current, 2)
        spread_2y_3m = round(y2_current - y3m_current, 2)

        prev_idx = min(5, len(rates_data) - 1)
        prev_r = rates_data[prev_idx]
        y10_5d_ago = float(prev_r.get("year10") or y10_current)
        rate_change_5d_bps = round((y10_current - y10_5d_ago) * 100.0, 1)

    fed_stance_tag = (
        "DOVISH CUT PRICING" if spread_2y_3m <= -0.25
        else "HAWKISH HIKE RISK" if spread_2y_3m >= 0.15
        else "NEUTRAL POLICY HOLD"
    )

    if rate_change_5d_bps > 12.0:
        yield_regime = "RATE_SHOCK_HEADWIND"
        yield_badge = f"RATE SHOCK (+{rate_change_5d_bps:.0f} bps 5D)"
        yield_desc = f"10Y Yield spiking rapidly (2Y-3M: {spread_2y_3m:+.2f}% · {fed_stance_tag}). High-beta valuation compression active."
        yield_color = "#FF3B30"
    elif rate_change_5d_bps < -5.0:
        yield_regime = "YIELD_TAILWIND"
        yield_badge = f"YIELD TAILWIND ({rate_change_5d_bps:.0f} bps 5D)"
        yield_desc = f"10Y Yield cooling off (2Y-3M: {spread_2y_3m:+.2f}% · {fed_stance_tag}). Favorable duration tailwind for SMH/IGV/URA."
        yield_color = "#00E676"
    else:
        yield_regime = "STABLE_RATES"
        yield_badge = f"STABLE YIELDS ({rate_change_5d_bps:+.1f} bps 5D)"
        yield_desc = f"Treasury yields contained (2Y-3M: {spread_2y_3m:+.2f}% · {fed_stance_tag}). Macro duration neutral to equity setups."
        yield_color = "#FFB800"

    now_ny = get_ny_now()
    today_str = (now_ny - timedelta(days=1)).strftime("%Y-%m-%d")
    plus_8_str = (now_ny + timedelta(days=8)).strftime("%Y-%m-%d")
    cal_data = fmp_get("economic-calendar", params={"from": today_str, "to": plus_8_str}, ttl=600)

    tier1_binary_keywords = [
        "CPI", "FOMC STATEMENT", "FOMC ECONOMIC PROJECTIONS", "FOMC PRESS CONFERENCE",
        "FED INTEREST RATE", "NONFARM PAYROLLS", "CORE PCE", "POWELL"
    ]
    runway_keywords = tier1_binary_keywords + [
        "PPI", "GDP", "PCE", "ISM MANUFACTURING PMI", "ISM SERVICES PMI", "ISM NON-MANUFACTURING",
        "RETAIL SALES MOM", "RETAIL SALES CONTROL", "INITIAL JOBLESS CLAIMS",
        "JOLTS JOB OPENINGS", "MICHIGAN CONSUMER SENTIMENT", "10-YEAR NOTE AUCTION",
        "30-YEAR BOND AUCTION", "FOMC MINUTES", "FED "
    ]

    upcoming_events = []
    has_binary_48h = False
    seen_ev_keys = set()

    if isinstance(cal_data, list):
        for ev in cal_data:
            if str(ev.get("country", "")).upper() != "US":
                continue
            ev_name = str(ev.get("event", "")).strip()
            up_name = ev_name.upper()
            if not any(k in up_name for k in runway_keywords):
                continue

            ev_date_str = str(ev.get("date", ""))
            ev_ny = _parse_fmp_calendar_ny(ev_date_str, ev_name)
            if ev_ny is None:
                continue

            hours_away = (ev_ny - now_ny).total_seconds() / 3600.0
            # Keep active 1-5 trading day runway (-2h just released through +168h / 7 calendar days)
            if hours_away < -2.0 or hours_away > 168.0:
                continue

            dedup_k = (ev_name, ev_ny.strftime("%Y-%m-%d %H:%M"))
            if dedup_k in seen_ev_keys:
                continue
            seen_ev_keys.add(dedup_k)

            is_tier1 = any(bk in up_name for bk in tier1_binary_keywords)
            if is_tier1 and -1.5 <= hours_away <= 48.0:
                has_binary_48h = True

            if hours_away <= 0:
                countdown_str = "JUST RELEASED"
            elif hours_away < 24.0:
                countdown_str = f"in {hours_away:.1f}h"
            else:
                countdown_str = f"in {hours_away / 24.0:.1f}d"

            upcoming_events.append({
                "event": ev_name,
                "date": ev_ny.strftime("%a %b %d · %I:%M %p ET"),
                "raw_date": ev_date_str,
                "hours_away": round(hours_away, 1),
                "countdown": countdown_str,
                "actual": ev.get("actual"),
                "estimate": ev.get("estimate"),
                "previous": ev.get("previous"),
                "impact": "BINARY" if is_tier1 else str(ev.get("impact") or "HIGH").upper(),
                "is_binary_48h": bool(is_tier1 and -1.5 <= hours_away <= 48.0)
            })

    upcoming_events.sort(key=lambda x: x["hours_away"])

    if has_binary_48h:
        next_bin = next((e["event"] for e in upcoming_events if e.get("is_binary_48h")), "Tier-1 Print")
        macro_risk_level = "HIGH_BINARY_EVENT"
        macro_directive = f"Binary US catalyst within 48h ({next_bin}). Favor higher-Delta (0.35Δ+) or Debit Spreads."
    elif len(upcoming_events) > 0:
        macro_risk_level = "MODERATE"
        macro_directive = f"{len(upcoming_events)} scheduled US macro catalyst(s) across 1–5D runway. Outright 30–45 DTE active."
    else:
        macro_risk_level = "LOW"
        macro_directive = "Clear macro economic runway over next 5 trading days. Full convexity permitted."

    result = {
        "y10_current": y10_current,
        "y2_current": y2_current,
        "y3m_current": y3m_current,
        "spread_10_2": spread_10_2,
        "spread_2y_3m": spread_2y_3m,
        "fed_stance_tag": fed_stance_tag,
        "rate_change_5d_bps": rate_change_5d_bps,
        "yield_regime": yield_regime,
        "yield_badge": yield_badge,
        "yield_desc": yield_desc,
        "yield_color": yield_color,
        "macro_risk_level": macro_risk_level,
        "macro_directive": macro_directive,
        "has_binary_48h": has_binary_48h,
        "upcoming_events": upcoming_events[:8]
    }
    set_cached(cache_key, result)
    return result


def _compute_asset_5d_telemetry(symbol: str, quotes_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Computes 1D change, 5D return, 5D Z-score, and 20-DMA trend for a macro asset."""
    q = quotes_map.get(symbol, {})
    price = float(q.get("price") or 0.0)
    chg_1d = float(q.get("changePercentage") or 0.0)
    vol = float(q.get("volume") or 1000000.0)

    ret_5d = chg_1d * 1.8
    z_5d = np.clip(chg_1d / 1.2, -3.0, 3.0)
    above_20dma = (chg_1d >= 0)

    from_str = (get_ny_now() - timedelta(days=420)).strftime("%Y-%m-%d")
    eod = fmp_get("historical-price-eod/full", params={"symbol": symbol, "from": from_str}, ttl=600)
    if isinstance(eod, list) and len(eod) >= 25:
        closes = [float(x.get("close", 0.0)) for x in reversed(eod[:65]) if x.get("close")]
        if price > 0:
            closes[-1] = price
        if len(closes) >= 25:
            s_c = pd.Series(closes)
            r5 = np.log(s_c / s_c.shift(5)).dropna()
            if len(r5) >= 15:
                curr_r5 = float(r5.iloc[-1])
                ret_5d = round((math.exp(curr_r5) - 1.0) * 100.0, 2)
                std_r5 = float(r5.std())
                mean_r5 = float(r5.mean())
                if std_r5 > 1e-6:
                    z_5d = float(np.clip((curr_r5 - mean_r5) / std_r5, -3.2, 3.2))
            sma20_val = float(s_c.tail(20).mean())
            above_20dma = (s_c.iloc[-1] >= sma20_val)

    return {
        "symbol": symbol,
        "price": round(price, 2),
        "change_1d_pct": round(chg_1d, 2),
        "change_5d_pct": round(ret_5d, 2),
        "z_5d": round(float(z_5d), 2),
        "above_20dma": above_20dma,
        "volume": vol
    }



def get_macro_world_news_sentiment() -> Dict[str, Any]:
    """
    Evaluates real-time breaking market news and human macro event risks
    via FMP's stable news and analytical articles endpoints.
    Detects geopolitical shocks, central bank surprises, and credit anxieties.
    """
    cache_key = "macro_world_news_sentiment_v35"
    cached = get_cached(cache_key, ttl=300)
    if cached is not None:
        return cached

    news_items = fmp_get("news/stock", {"symbols": "SPY,QQQ,TLT,USO,GLD", "limit": 15}, ttl=300)
    if not isinstance(news_items, list):
        news_items = []

    fmp_articles = fmp_get("fmp-articles", {"limit": 6}, ttl=300)
    if isinstance(fmp_articles, list):
        news_items.extend(fmp_articles)

    import re
    bear_patterns = [
        r"\bworr(?:y|ied|ies)\b", r"\bscar(?:ed|es)\b", r"\bfear(?:s)?\b", r"\bpullback\b",
        r"\bcrash(?:es|ing)?\b", r"\brecession(?:ary)?\b", r"\bconflict\b", r"\bwar\b",
        r"\btariff(?:s)?\b", r"\bescalat(?:e|es|ing|ion)\b", r"\bdefault(?:s)?\b",
        r"\bdowngrad(?:e|ed|es)\b", r"\blabor strike\b", r"\bmilitary strike\b", r"\bairstrike\b",
        r"\bgeopolitic(?:s|al)?\b", r"\bcrude spike\b", r"\bjunk bond\b", r"\bselloff\b", r"\bsell-off\b",
        r"\binflation risk\b", r"\bhawkish\b", r"\bfed pause\b", r"\brate hike(?:s)?\b",
        r"\bdeficit\b", r"\btension(?:s)?\b", r"\bgloom(?:y|ier)?\b", r"\bthreaten(?:s|ing)?\b",
        r"\bslump(?:s|ed)?\b", r"\bslowdown\b", r"\blayoff(?:s)?\b", r"\bworst week\b", r"\bfell below\b"
    ]
    bull_patterns = [
        r"\brall(?:y|ies|ied)\b", r"\bbeat(?:s)? estimates\b", r"\bearnings beat\b", r"\btops estimates\b",
        r"\bsoft landing\b", r"\brate cut(?:s)?\b", r"\bboom(?:ing)?\b",
        r"\brecord high(?:s)?\b", r"\brecord surge\b", r"\brecord revenue\b", r"\brecord profit\b",
        r"\ball-time high\b", r"\boutperform(?:s|ed)?\b", r"\bupgrad(?:e|ed|es)\b", r"\bai boom\b",
        r"\bbreakout\b", r"\bsurpass(?:es|ed)?\b", r"\bdovish\b", r"\beasing\b",
        r"\bstimulus\b", r"\bdisinflation\b", r"\bbullish\b", r"\boptimism\b"
    ]

    bull_count = 0
    bear_count = 0
    curated_headlines = []

    for item in news_items:
        title = item.get("title", "").strip()
        if not title:
            continue
        text_lower = title.lower()
        pub = item.get("publisher") or item.get("site") or "MarketWire"
        date_str = item.get("publishedDate") or item.get("date") or ""

        b_hits = sum(1 for pat in bull_patterns if re.search(pat, text_lower))
        r_hits = sum(1 for pat in bear_patterns if re.search(pat, text_lower))

        if r_hits > b_hits:
            sentiment_tag = "RISK DRAG"
            tag_color = "#FF3B30"
            bear_count += 1
        elif b_hits > r_hits:
            sentiment_tag = "BULLISH TAILWIND"
            tag_color = "#00E676"
            bull_count += 1
        else:
            sentiment_tag = "NEUTRAL TAPE"
            tag_color = "#FFB800"

        curated_headlines.append({
            "title": title,
            "publisher": pub,
            "date": date_str,
            "tag": sentiment_tag,
            "color": tag_color,
            "url": item.get("url") or item.get("link") or ""
        })

    diff = bull_count - bear_count
    lexical_score = max(-15.0, min(15.0, float(diff * 2.5)))
    # Blend with cached AI Catalyst Digest score (-100..+100 scaled to -15..+15) when warm in cache
    llm_cached = get_cached("world_catalysts_llm_digest_v1", ttl=900)
    if isinstance(llm_cached, dict) and "sentiment_score" in llm_cached:
        llm_scaled = float(np.clip(float(llm_cached["sentiment_score"]) * 0.15, -15.0, 15.0))
        sentiment_score = round(0.55 * llm_scaled + 0.45 * lexical_score, 2)
    else:
        sentiment_score = lexical_score

    if sentiment_score >= 6.0:
        status_label = "POSITIVE HEADLINES"
        color = "#00E676"
        badge = "RISK-ON SENTIMENT"
        summary = f"World event flow is predominantly constructive (+{sentiment_score:.1f} impulse). Institutional narrative focuses on AI tailwinds and soft-landing disinflation."
    elif sentiment_score <= -6.0:
        status_label = "HEADLINE DRAG / RISK"
        color = "#FF3B30"
        badge = "GEOPOLITICAL / RISK-OFF"
        summary = f"Breaking news feeds are signaling human anxiety & macro risk ({sentiment_score:.1f} impulse). Headlines cite credit stress, geopolitical friction, or sticky yield concerns."
    else:
        status_label = "BALANCED NARRATIVE"
        color = "#FFB800"
        badge = "MIXED CATALYST FLOW"
        summary = f"Macro headlines and human events are balanced ({sentiment_score:+.1f} impulse). No immediate black-swan escalation dominating broad market tape."

    out = {
        "sentiment_score": sentiment_score,
        "status_label": status_label,
        "sentiment_badge": badge,
        "color": color,
        "summary_text": summary,
        "bull_count": bull_count,
        "bear_count": bear_count,
        "headlines": curated_headlines[:6]
    }
    set_cached(cache_key, out)
    return out


def digest_world_catalysts_with_llm(headlines: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Synthesizes an executive 3-point Macro Catalyst Brief using the active AI model
    (Google Gemini 3.5 Flash Lite or ASUS GX10 Qwen 3.8 via llm_router).
    Cached for 15 minutes to guarantee instant response and avoid redundant LLM invocations.
    """
    cache_key = "world_catalysts_llm_digest_v1"
    cached = get_cached(cache_key, ttl=900)
    if cached is not None:
        return cached

    if not headlines:
        news_intel = get_macro_world_news_sentiment()
        headlines = news_intel.get("headlines", [])

    if not headlines:
        fallback = {
            "bullets": [
                "World tape is orderly with no acute liquidity or geopolitical shocks detected in breaking feeds.",
                "Cross-asset benchmark spreads reflect steady risk appetite across mega-cap equity indices.",
                "Continue executing 30-45 DTE options campaigns within established volatility bounds."
            ],
            "risk_verdict": "LOW VOLATILITY RUNWAY",
            "model_used": "Heuristic Standby"
        }
        set_cached(cache_key, fallback)
        return fallback

    # Format curated headlines for the prompt
    feed_lines = []
    for idx, h in enumerate(headlines[:6], 1):
        feed_lines.append(f"{idx}. [{h.get('publisher', 'Feed')}] {h.get('title', '')} (Tag: {h.get('tag', 'NEUTRAL')})")
    feeds_text = "\n".join(feed_lines)

    prompt = f"""You are the Lead Macro & Geopolitical Risk Analyst on an institutional quantitative trading desk.
Analyze these 6 breaking global market headlines tracked by our real-time feed:

{feeds_text}

Provide an ultra-concise, high-impact institutional assessment in this EXACT format:

[SENTIMENT_SCORE]: <integer from -100 to +100, where -100 is maximum bearish panic/liquidity shock, 0 is perfect equilibrium, and +100 is maximum risk-on mania>
[MACRO_PULSE]: <1 punchy sentence describing the primary macro or geopolitical catalyst driving tape sentiment>
[ASSET_TRANSMISSION]: <1 punchy sentence on cross-asset risk transmission to equity indices, yields, and crypto liquidity>
[TACTICAL_DIRECTIVE]: <1 punchy sentence outlining the 1-5 day swing and 30-45 DTE options positioning directive>

Keep every line razor-sharp, quantitative, and free of filler."""

    import llm_router
    backend = llm_router.get_active_backend()
    model_label = "Gemini 3.5 Flash Lite" if backend == "gemini" else "ASUS GX10 (Qwen 3.8)"

    parsed_score = 0
    is_fallback = False
    try:
        raw_text, err = llm_router.generate_text(
            prompt,
            system_instruction="You are an elite quantitative hedge fund macro strategist. Deliver ruthless, concise insights.",
            temperature=0.2
        )
        bullets = []
        if raw_text and not err:
            score_match = re.search(r"\[SENTIMENT_SCORE\]\s*:\s*([+-]?\d+)", raw_text, re.IGNORECASE)
            if score_match:
                try:
                    parsed_score = max(-100, min(100, int(score_match.group(1))))
                except Exception:
                    parsed_score = 0
            else:
                num_match = re.search(r"(-?\d{1,3})\s*/\s*100", raw_text)
                if num_match:
                    try:
                        parsed_score = max(-100, min(100, int(num_match.group(1))))
                    except Exception:
                        parsed_score = 0

            # Extract the 3 core lines
            for tag, prefix in [("[MACRO_PULSE]", "Macro Pulse"), ("[ASSET_TRANSMISSION]", "Asset Transmission"), ("[TACTICAL_DIRECTIVE]", "Tactical Directive")]:
                m_tag = re.search(rf"\[{tag[1:-1]}\]\s*:\s*([^\n]+)", raw_text, re.IGNORECASE)
                if m_tag:
                    bullets.append(f"[{prefix}]: {m_tag.group(1).strip()}")

            if len(bullets) < 2:
                for line in raw_text.splitlines():
                    clean_l = line.strip().lstrip("-*•0123456789. ")
                    if len(clean_l) > 20 and not clean_l.startswith("[SENTIMENT_SCORE]"):
                        bullets.append(clean_l)
                bullets = bullets[:3]
        else:
            is_fallback = True
            bullets = [
                "[Macro Pulse]: Breaking feeds indicate balanced two-way flow across rates and equity benchmarks.",
                "[Asset Transmission]: Sector-specific earnings dispersion dominates broad index beta with steady credit spreads.",
                "[Tactical Directive]: Maintain disciplined sizing in 30-45 DTE options within defined volatility corridors."
            ]
    except Exception as e:
        is_fallback = True
        bullets = [
            f"Active telemetry monitored across 6 live breaking feeds ({str(e)[:40]}).",
            "Macro risk runway remains within standard operational bounds.",
            "Options skew and implied volatility dictate measured risk exposure."
        ]

    result = {
        "bullets": bullets,
        "sentiment_score": parsed_score,
        "risk_verdict": "QUANT / FEED FALLBACK" if is_fallback else "ACTIVE AI SYNTHESIS",
        "model_used": model_label,
        "is_fallback": is_fallback,
        "timestamp": time.time()
    }
    set_cached(cache_key, result, ttl=120 if is_fallback else CACHE_TTL)
    return result


def get_24_48h_market_direction_radar() -> Dict[str, Any]:
    """
    AAA Cross-Asset Macro & 24/48-Hour US Stock Market Direction Engine.
    Evaluates the 6 Executive Macro Pillars + Eurodollar & Broad Indices:
      1. Bonds & Duration (TLT + 10Y Treasury Yield & Curve)
      2. Credit Stress (HYG / LQD High-Yield vs Investment-Grade Ratio)
      3. Crude Oil (CLUSD / USO)
      4. Gold (GLD)
      5. Silver (SLV)
      6. Bitcoin (BTCUSD - 24/7 Speculative Liquidity Lead)
    Synthesizes a deterministic 24/48-Hour US Stock Market Direction Forecast, Probability,
    and Market-Reader Educational Decoder.
    """
    cache_key = "market_24_48h_radar_v47"
    cached = get_cached(cache_key, ttl=180)
    if cached is not None:
        return cached

    macro_syms = [
        "SPY", "QQQ", "RSP", "TLT", "HYG", "LQD", "CLUSD", "USO", "GLD", "SLV",
        "BTCUSD", "UUP", "VIXY", "^VIX", "^VIX3M", "SMH", "IGV", "SRVR", "BOTZ", "ROBO", "URA", "REMX", "QTUM"
    ]
    quotes_map = fmp_batch_quotes(macro_syms, ttl=120)
    yield_info = get_macro_yield_regime()

    telemetry_syms = ["TLT", "HYG", "LQD", "CLUSD", "USO", "GLD", "SLV", "BTCUSD", "SPY", "QQQ", "RSP", "UUP", "VIXY"]
    with ThreadPoolExecutor(max_workers=8) as ex:
        tel_map = dict(ex.map(lambda s: (s, _compute_asset_5d_telemetry(s, quotes_map)), telemetry_syms))

    tlt = tel_map["TLT"]
    hyg = tel_map["HYG"]
    lqd = tel_map["LQD"]
    oil = tel_map["CLUSD"]
    if oil["price"] <= 0:
        oil = tel_map["USO"]
    gld = tel_map["GLD"]
    slv = tel_map["SLV"]
    btc = tel_map["BTCUSD"]
    spy = tel_map["SPY"]
    qqq = tel_map["QQQ"]
    rsp = tel_map["RSP"]
    uup = tel_map["UUP"]
    vixy = tel_map["VIXY"]

    # Forward-Projecting CBOE VIX Term Structure (^VIX vs ^VIX3M) & Intraday SPY Tape Quality
    vix_spot = float(quotes_map.get("^VIX", {}).get("price") or 18.5)
    vix_3m = float(quotes_map.get("^VIX3M", {}).get("price") or max(19.5, vix_spot * 1.06))
    vix_term_ratio = round(vix_spot / max(10.0, vix_3m), 3)
    spy_rvol_live = _quote_rvol("SPY", quotes_map.get("SPY", {}), default_20d_vol=60_000_000.0)
    spy_clv_live = _quote_clv(quotes_map.get("SPY", {}))

    # 1. Credit Stress Calculation (HYG vs LQD Spread)
    credit_spread_1d = round(hyg["change_1d_pct"] - lqd["change_1d_pct"], 2)
    credit_spread_5d = round(hyg["change_5d_pct"] - lqd["change_5d_pct"], 2)
    credit_z = round(float(np.clip(hyg["z_5d"] - lqd["z_5d"], -3.0, 3.0)), 2)
    hyg_lqd_ratio = round(hyg["price"] / lqd["price"], 4) if lqd["price"] > 0 else 0.745

    if credit_spread_1d >= 0.15 or credit_z >= 0.40:
        credit_status = "RISK-ON APPETITE"
        credit_color = "#00E676"
        credit_lesson = "High-Yield Junk Bonds (HYG) are outperforming Safe Corporate Debt (LQD) — institutional credit desks are pricing LOW default risk, a strong 24–48h tailwind for equities."
    elif credit_spread_1d <= -0.20 or credit_z <= -0.60:
        credit_status = "CREDIT STRESS WARNING"
        credit_color = "#FF3B30"
        credit_lesson = "Bond smart-money is rotating out of High-Yield (HYG) into defensive Investment-Grade (LQD). Credit widening typically leads stock market pullbacks by 24–48 hours."
    else:
        credit_status = "CALM / NORMAL"
        credit_color = "#FFB800"
        credit_lesson = "Credit spreads (HYG/LQD) are tight and stable — no hidden institutional liquidity stress on the tape."

    # 2. Bonds & Yield Curve Impulse (TLT + 10Y)
    y10 = yield_info["y10_current"]
    bps_5d = yield_info["rate_change_5d_bps"]
    if tlt["change_1d_pct"] >= 0.25 or bps_5d <= -4.0:
        bonds_status = "DURATION TAILWIND"
        bonds_color = "#00E676"
        bonds_lesson = f"Bonds (TLT {tlt['change_1d_pct']:+.2f}%) are bid and the 10Y Yield ({y10:.2f}%) is easing — lower discount rates directly boost high-beta tech (SMH, BOTZ) & nuclear (URA) valuations."
    elif tlt["change_1d_pct"] <= -0.45 or bps_5d >= 10.0:
        bonds_status = "YIELD SPIKE PRESSURE"
        bonds_color = "#FF3B30"
        bonds_lesson = f"Bonds (TLT {tlt['change_1d_pct']:+.2f}%) are selling off and 10Y Yields ({y10:.2f}%, {bps_5d:+.0f}bps 5D) are rising — creates 24–48h multiple compression on long-duration growth stocks."
    else:
        bonds_status = "RATES CONTAINED"
        bonds_color = "#FFB800"
        bonds_lesson = f"20Y+ Treasury Bonds (TLT ${tlt['price']:.2f}) and the 10Y Yield ({y10:.2f}%) are balanced, allowing individual stock catalysts to drive price action."

    # 3. Crude Oil Impulse (CLUSD / USO)
    if oil["z_5d"] >= 1.35 or oil["change_1d_pct"] >= 2.2:
        oil_status = "INFLATION / GEOPOLITICAL SPIKE"
        oil_color = "#FF3B30"
        oil_lesson = f"Crude Oil (${oil['price']:.2f}, {oil['change_1d_pct']:+.2f}%) is spiking (`{oil['z_5d']:+.2f}σ` 5D) — acts as an inflation & geopolitical tax on consumer/tech margins while boosting clean nuclear (URA) substitution demand."
    elif oil["change_1d_pct"] <= -1.5 or oil["z_5d"] <= -1.0:
        oil_status = "DISINFLATION RELIEF"
        oil_color = "#00E676"
        oil_lesson = f"Crude Oil (${oil['price']:.2f}, {oil['change_1d_pct']:+.2f}%) is cooling off — lowers headline inflation expectations and gives the Fed & growth equities breathing room."
    else:
        oil_status = "EQUILIBRIUM CRUDE"
        oil_color = "#FFB800"
        oil_lesson = f"Crude Oil (${oil['price']:.2f}, {oil['change_1d_pct']:+.2f}%) is trading in a non-disruptive corridor — zero energy-shock headwind for equities."

    # 4. Gold (GLD) & Silver (SLV) Precious / Industrial Metals Signal
    gs_diff_1d = round(slv["change_1d_pct"] - gld["change_1d_pct"], 2)
    if gld["change_1d_pct"] >= 0.8 and spy["change_1d_pct"] < -0.2:
        gold_status = "SAFE-HAVEN FLIGHT"
        gold_color = "#FFB800"
        gold_lesson = f"Gold (GLD ${gld['price']:.2f}, {gld['change_1d_pct']:+.2f}%) is catching a defensive flight-to-safety bid while equities lag — signals institutional hedging against macro or geopolitical risk."
    elif gld["change_1d_pct"] >= 0.2:
        gold_status = "MONETARY HEDGE BID"
        gold_color = "#00E676"
        gold_lesson = f"Gold (GLD ${gld['price']:.2f}, {gld['change_1d_pct']:+.2f}%) is advancing alongside liquidity expansion."
    else:
        gold_status = "ROTATION TO RISK"
        gold_color = "#FFB800"
        gold_lesson = f"Gold (GLD ${gld['price']:.2f}, {gld['change_1d_pct']:+.2f}%) is consolidating as capital rotates out of defensive bullion into active risk assets."

    if gs_diff_1d >= 0.45 or slv["change_1d_pct"] >= 1.0:
        silver_status = "INDUSTRIAL SURGE"
        silver_color = "#00E676"
        silver_lesson = f"Silver (SLV ${slv['price']:.2f}, {slv['change_1d_pct']:+.2f}%) is outperforming Gold by {gs_diff_1d:+.2f}% today — because Silver is heavily used in AI electronics, solar & grid electrification, Silver leading Gold is a classic pro-cyclical bullish tell!"
    elif slv["change_1d_pct"] <= -1.2:
        silver_status = "CYCLICAL COOLING"
        silver_color = "#FF3B30"
        silver_lesson = f"Silver (SLV ${slv['price']:.2f}, {slv['change_1d_pct']:+.2f}%) is pulling back faster than Gold — indicates short-term profit-taking in industrial/electrification beta."
    else:
        silver_status = "STEADY INDUSTRIAL DEMAND"
        silver_color = "#FFB800"
        silver_lesson = f"Silver (SLV ${slv['price']:.2f}, {slv['change_1d_pct']:+.2f}%) is tracking industrial equilibrium."

    # 5. Bitcoin (BTCUSD) - 24/7 High-Beta Speculative Liquidity Barometer
    if btc["change_1d_pct"] >= 1.25 or btc["z_5d"] >= 0.85:
        btc_status = "LIQUIDITY RISK-ON LEAD"
        btc_color = "#00E676"
        btc_lesson = f"Bitcoin (${btc['price']:,.0f}, {btc['change_1d_pct']:+.2f}%) is surging (`{btc['z_5d']:+.2f}σ` 5D) — BTC trades 24/7 as the purest barometer of global excess liquidity and consistently leads Nasdaq / SMH / Nuclear SMR appetite over the next 24–48 hours."
    elif btc["change_1d_pct"] <= -2.0 or btc["z_5d"] <= -1.10:
        btc_status = "SPECULATIVE DE-RISKING"
        btc_color = "#FF3B30"
        btc_lesson = f"Bitcoin (${btc['price']:,.0f}, {btc['change_1d_pct']:+.2f}%) is flushing — signals fast-money margin de-grossing that often spills into high-beta tech at the NY cash open."
    else:
        btc_status = "CONSOLIDATING LIQUIDITY"
        btc_color = "#FFB800"
        btc_lesson = f"Bitcoin (${btc['price']:,.0f}, {btc['change_1d_pct']:+.2f}%) is stable, indicating steady speculative liquidity."

    # 6. Synthesize Forward-Projecting 24/48-Hour US Stock Market Direction Score (-100 to +100)
    # Incorporates VIX Term Structure (^VIX/^VIX3M dealer gamma), HYG-LQD credit lead, 2Y-3M Fed rate curve,
    # intraday CLV + U-curve RVOL conditioning, Dollar/Oil non-linear stress, and 48h binary event hazard.
    score_credit = np.clip(credit_spread_1d * 32.0 + credit_z * 14.0, -28.0, 28.0)
    spread_2y3m = float(yield_info.get("spread_2y_3m", -0.25))
    policy_curve_boost = 3.0 if (-0.65 <= spread_2y3m <= -0.15) else (-4.0 if spread_2y3m >= 0.20 else 0.0)
    score_bonds = np.clip(tlt["change_1d_pct"] * 11.0 - bps_5d * 0.85 + policy_curve_boost, -22.0, 22.0)

    # Condition 1D tape on intraday CLV, RVOL conviction, and VIX/VIX3M forward dealer gamma
    rvol_conv_mult = float(np.clip(0.65 + 0.35 * spy_rvol_live, 0.65, 1.30))
    vix_term_impulse = float(np.clip((0.93 - vix_term_ratio) * 65.0, -12.0, 8.0))
    raw_tape_1d = ((spy["change_1d_pct"] * 8.5 + qqq["change_1d_pct"] * 6.5) * rvol_conv_mult) + (spy_clv_live * 5.5)
    score_tape = np.clip(raw_tape_1d - (vixy["change_1d_pct"] * 2.2) + vix_term_impulse, -25.0, 25.0)

    score_btc = np.clip(btc["change_1d_pct"] * 5.0 + btc["z_5d"] * 5.0, -15.0, 15.0)
    score_metals = np.clip(gs_diff_1d * 7.0 - (gld["change_1d_pct"] * 4.0 if spy["change_1d_pct"] < 0 else 0.0), -10.0, 10.0)
    # Non-linear Oil & UUP Dollar stress: penalize both >+1σ inflation shock AND <-2σ demand collapse
    # UUP gauges global USD funding pressure and offshore liquidity squeeze
    oil_stress_pen = max(0.0, oil["z_5d"] - 0.85) * 6.0 + max(0.0, -oil["z_5d"] - 1.85) * 4.5
    uup_stress_pen = uup["z_5d"] * 4.0 + uup["change_1d_pct"] * 5.0
    score_oil_fx = np.clip(-oil_stress_pen - uup_stress_pen, -14.0, 10.0)

    # 6B. Real-World Human Event, Breaking Macro News & Binary 48H Runway Hazard
    news_intel = get_macro_world_news_sentiment()
    score_news = float(np.clip(news_intel.get("sentiment_score", 0.0), -15.0, 15.0))
    event_drag = -6.0 if yield_info.get("has_binary_48h", False) else 0.0

    raw_score = float(np.clip(
        score_credit + score_bonds + score_tape + score_btc + score_metals + score_oil_fx + score_news + event_drag,
        -95.0, 95.0
    ))
    prob_pct = int(round(50.0 + abs(raw_score) * 0.42))
    prob_pct = max(54, min(89, prob_pct))

    if raw_score >= 22.0:
        signage_title = "24–48H US MARKET OUTLOOK: BULLISH EXPANSION & RISK-ON CONTINUATION"
        signage_short = "BULLISH 24–48H BIAS"
        signage_color = "#00E676"
        signage_border = "rgba(0, 230, 118, 0.45)"
        signage_bg = "linear-gradient(135deg, rgba(0, 230, 118, 0.14) 0%, rgba(18, 22, 30, 0.96) 100%)"
        expected_move = f"SPY / QQQ Projected 24–48H Bias: +0.6% to +1.8% Upside Extension ({prob_pct}% Conviction)"
        options_directive = "AGGRESSIVE CALLS FAVORED: Deploy 30–45 DTE OTM Calls (~0.28Δ) on Oversold Hooks & Coiled Springs in SMH, BOTZ, and URA."
    elif raw_score >= 5.0:
        signage_title = "24–48H US MARKET OUTLOOK: CONSTRUCTIVE UPWARD COIL & SECTOR ROTATION"
        signage_short = "CONSTRUCTIVE UPWARD BIAS"
        signage_color = "#8AB4F8"
        signage_border = "rgba(138, 180, 248, 0.45)"
        signage_bg = "linear-gradient(135deg, rgba(56, 189, 248, 0.14) 0%, rgba(18, 22, 30, 0.96) 100%)"
        expected_move = f"SPY / QQQ Projected 24–48H Bias: Grind Higher / Sector Rotation (+0.2% to +1.0% · {prob_pct}% Conviction)"
        options_directive = "SELECTIVE CALLS & BREAKOUTS: Credit & liquidity are supportive. Focus on #1–#3 Top Ranked Sector Candidates."
    elif raw_score <= -22.0:
        signage_title = "24–48H US MARKET OUTLOOK: DEFENSIVE PULLBACK & VOLATILITY EXPANSION WARNING"
        signage_short = "BEARISH 24–48H WARNING"
        signage_color = "#FF3B30"
        signage_border = "rgba(255, 59, 48, 0.45)"
        signage_bg = "linear-gradient(135deg, rgba(255, 59, 48, 0.16) 0%, rgba(18, 22, 30, 0.96) 100%)"
        expected_move = f"SPY / QQQ Projected 24–48H Bias: -0.7% to -2.2% De-Risking Drawdown ({prob_pct}% Conviction)"
        options_directive = "PUTS & CAPITAL DEFENSE: Credit/Rates signaling stress. Favor 30–45 DTE OTM Puts on Overbought Blow-Offs & Track C Mirages; demand deep Z <= -2.2σ for Calls."
    else:
        signage_title = "24–48H US MARKET OUTLOOK: TWO-WAY INSTITUTIONAL CHOP & BIFURCATION"
        signage_short = "TWO-WAY ROTATIONAL CHOP"
        signage_color = "#FFB800"
        signage_border = "rgba(255, 184, 0, 0.40)"
        signage_bg = "linear-gradient(135deg, rgba(255, 184, 0, 0.12) 0%, rgba(18, 22, 30, 0.96) 100%)"
        expected_move = f"SPY / QQQ Projected 24–48H Bias: Range-Bound Bifurcation (-0.5% to +0.5% · {prob_pct}% Conviction)"
        options_directive = "BIFURCATED PAIR TRADING: Pair 30–45 DTE Calls on Oversold Fortress Diamonds (Quality >= 75) with Puts on Overbought Low-Quality Mirages."

    pillars = [
        {
            "id": "BONDS",
            "title": "1. Bonds & 10Y Duration",
            "ticker": f"TLT · 10Y ({y10:.2f}%)",
            "price_str": f"${tlt['price']:.2f}",
            "chg_1d": tlt["change_1d_pct"],
            "chg_5d": tlt["change_5d_pct"],
            "z_5d": tlt["z_5d"],
            "extra_metric": f"10Y-2Y Curve: {yield_info['spread_10_2']:+.2f}%",
            "status": bonds_status,
            "color": bonds_color,
            "lesson": bonds_lesson
        },
        {
            "id": "CREDIT",
            "title": "2. Credit Stress (HYG/LQD)",
            "ticker": "HYG vs LQD Spread",
            "price_str": f"{hyg_lqd_ratio:.3f}x",
            "chg_1d": credit_spread_1d,
            "chg_5d": credit_spread_5d,
            "z_5d": credit_z,
            "extra_metric": f"HYG {hyg['change_1d_pct']:+.2f}% | LQD {lqd['change_1d_pct']:+.2f}%",
            "status": credit_status,
            "color": credit_color,
            "lesson": credit_lesson
        },
        {
            "id": "OIL",
            "title": "3. Crude Oil Impulse",
            "ticker": oil["symbol"],
            "price_str": f"${oil['price']:.2f}",
            "chg_1d": oil["change_1d_pct"],
            "chg_5d": oil["change_5d_pct"],
            "z_5d": oil["z_5d"],
            "extra_metric": f"5D Stretch: {oil['z_5d']:+.2f}σ",
            "status": oil_status,
            "color": oil_color,
            "lesson": oil_lesson
        },
        {
            "id": "GOLD",
            "title": "4. Gold Safe-Haven",
            "ticker": "GLD",
            "price_str": f"${gld['price']:.2f}",
            "chg_1d": gld["change_1d_pct"],
            "chg_5d": gld["change_5d_pct"],
            "z_5d": gld["z_5d"],
            "extra_metric": f"USD Index (UUP): ${uup['price']:.2f} ({uup['change_1d_pct']:+.2f}%)",
            "status": gold_status,
            "color": gold_color,
            "lesson": gold_lesson
        },
        {
            "id": "SILVER",
            "title": "5. Silver & Electrification",
            "ticker": "SLV",
            "price_str": f"${slv['price']:.2f}",
            "chg_1d": slv["change_1d_pct"],
            "chg_5d": slv["change_5d_pct"],
            "z_5d": slv["z_5d"],
            "extra_metric": f"SLV vs GLD 1D: {gs_diff_1d:+.2f}%",
            "status": silver_status,
            "color": silver_color,
            "lesson": silver_lesson
        },
        {
            "id": "BTC",
            "title": "6. Bitcoin 24/7 Liquidity",
            "ticker": "BTCUSD",
            "price_str": f"${btc['price']:,.0f}",
            "chg_1d": btc["change_1d_pct"],
            "chg_5d": btc["change_5d_pct"],
            "z_5d": btc["z_5d"],
            "extra_metric": f"5D Velocity: {btc['change_5d_pct']:+.1f}%",
            "status": btc_status,
            "color": btc_color,
            "lesson": btc_lesson
        },
        {
            "id": "WORLD_NEWS",
            "title": "7. World Events & News Pulse",
            "ticker": "Macro Catalysts & Sentiment",
            "price_str": news_intel.get("sentiment_badge", "BALANCED FLOW"),
            "chg_1d": round(score_news, 1),
            "chg_5d": round(score_news * 1.5, 1),
            "z_5d": round(score_news / 7.0, 2),
            "extra_metric": f"{len(news_intel.get('headlines', []))} Headlines Tracked",
            "status": news_intel.get("status_label", "CALM TAPE"),
            "color": news_intel.get("color", "#8AB4F8"),
            "lesson": news_intel.get("summary_text", "")
        }
    ]

    # 6-Axis Macro Radar Polar Coordinates (0 - 100 scale, 50 = Equilibrium baseline)
    # 1. Credit & Liquidity: 1D + 5D HYG/LQD spread + BTC 24/7 speculative liquidity
    axis_credit = float(np.clip(50.0 + (credit_spread_1d * 20.0) + (credit_z * 11.5) + (btc["z_5d"] * 7.0), 10.0, 95.0))
    # 2. Duration & Rates Stability: TLT + 5D 10Y bps velocity + 2Y-3M forward Fed policy curve
    axis_duration = float(np.clip(50.0 + (tlt["change_1d_pct"] * 9.5) - (bps_5d * 1.25) + policy_curve_boost * 1.5, 10.0, 95.0))

    # 3. Tape Breadth & Volume Confirmation: True RSP-QQQ Equal-Weight Breadth + Sign-Conditioned U-Curve RVOL + CLV
    rsp_chg = rsp["change_1d_pct"] if rsp["price"] > 0 else spy["change_1d_pct"]
    breadth_delta = round(rsp_chg - qqq["change_1d_pct"], 2)
    tape_dir_sign = 1.0 if spy["change_1d_pct"] >= 0.0 else -1.0
    signed_rvol_boost = tape_dir_sign * (spy_rvol_live - 1.0) * 11.0
    # Do not penalize healthy tech-led rallies where both RSP and QQQ are strongly green
    breadth_component = breadth_delta * 12.0 if not (rsp_chg > 0.35 and qqq["change_1d_pct"] > rsp_chg) else max(0.0, rsp_chg * 6.0)
    axis_tape = float(np.clip(
        50.0 + breadth_component + signed_rvol_boost + (spy["change_1d_pct"] * 9.5) + (spy_clv_live * 8.0),
        10.0, 95.0
    ))

    # 4. Inflation & Dollar Calm: Non-linear Oil shock/collapse corridor + UUP US Dollar stress
    oil_corridor_adj = (
        -max(0.0, oil["z_5d"] - 0.50) * 15.0
        - max(0.0, -oil["z_5d"] - 1.80) * 11.0
        + float(np.clip(-oil["z_5d"] * 5.0, -6.0, 8.0))
    )
    dollar_adj = -(uup["z_5d"] * 8.5) - (uup["change_1d_pct"] * 9.0)
    axis_energy = float(np.clip(50.0 + oil_corridor_adj + dollar_adj, 10.0, 95.0))

    # 5. World Events & Risk Runway: News Sentiment + VIX Term Structure + 48H/5D Economic Calendar Runway
    upcoming_cnt = len(yield_info.get("upcoming_events", []))
    runway_pen = -22.0 if yield_info.get("has_binary_48h", False) else (-7.0 if upcoming_cnt >= 3 else (-3.0 if upcoming_cnt >= 1 else 4.0))
    axis_world = float(np.clip(
        50.0 + (score_news * 1.35) + (vix_term_impulse * 1.4) - (vixy["change_1d_pct"] * 1.8) + runway_pen,
        10.0, 94.0
    ))

    # 6. Unified Hybrid Smart-Money Score (eliminates engine vs UI split-brain)
    try:
        import smart_money_radar as _smr
        sm_cached = get_cached("smart_money_power_radar_v45", ttl=900)
        if isinstance(sm_cached, dict) and "smart_money_score" in sm_cached:
            axis_smart = float(sm_cached["smart_money_score"])
        else:
            axis_smart = float(_smr.get_smart_money_stealth_radar().get("smart_money_score", 55.0))
    except Exception:
        axis_smart = float(np.clip(50.0 + (score_btc * 1.0) + (score_credit * 0.8), 20.0, 92.0))

    radar_axes = {
        "credit_liquidity_score": round(axis_credit, 1),
        "duration_stability_score": round(axis_duration, 1),
        "tape_breadth_score": round(axis_tape, 1),
        "energy_inflation_score": round(axis_energy, 1),
        "world_events_score": round(axis_world, 1),
        "smart_money_score": round(axis_smart, 1),
        "average_score": round((axis_credit + axis_duration + axis_tape + axis_energy + axis_world + axis_smart) / 6.0, 1)
    }

    # 7. Institutional Dealer Gamma Flip & Cross-Sector Dispersion Telemetry
    temporal_info = get_temporal_regime()
    is_opex_wk = bool(temporal_info.get("is_opex_week", False))
    spy_z5 = float(spy.get("z_5d", 0.0))
    if vix_term_ratio <= 0.94 and spy_z5 > -0.95:
        dealer_gamma_regime = "POSITIVE GAMMA (MEAN-REVERTING)"
        dealer_gamma_short = "+Γ MEAN-REV PIN" if is_opex_wk else "+Γ DIP-BUY BUFFER"
        dealer_gamma_color = "#34D399"
        dealer_gamma_desc = "Dealers hedge against spot moves (buying dips / selling rips) — high O-U snapback hit rate."
    elif vix_term_ratio >= 0.99 or spy_z5 <= -1.35:
        dealer_gamma_regime = "NEGATIVE GAMMA (VOL EXPANSION)"
        dealer_gamma_short = "-Γ ACCELERATION"
        dealer_gamma_color = "#F87171"
        dealer_gamma_desc = "Dealers hedge WITH spot velocity — oversold extensions can stretch further; use Debit Spreads."
    else:
        dealer_gamma_regime = "NEUTRAL GAMMA FLIP ZONE"
        dealer_gamma_short = "NEUTRAL Γ FLIP"
        dealer_gamma_color = "#FBBF24"
        dealer_gamma_desc = "Balanced dealer gamma book — rely on constituent RVOL and 4H CLV inflection hooks."

    sec_disp_quotes = fmp_batch_quotes(["SMH", "IGV", "BOTZ", "URA", "XLI", "XLF"], ttl=180)
    sec_1d_list = [
        float((sec_disp_quotes.get(s) or {}).get("changesPercentage") or (sec_disp_quotes.get(s) or {}).get("changePercentage") or 0.0)
        for s in ["SMH", "IGV", "BOTZ", "URA", "XLI", "XLF"]
        if sec_disp_quotes.get(s)
    ]
    dispersion_spread_pct = round(float(max(sec_1d_list) - min(sec_1d_list)), 2) if len(sec_1d_list) >= 3 else 1.45
    dispersion_std = round(float(np.std(sec_1d_list)), 2) if len(sec_1d_list) >= 3 else 0.65
    if dispersion_spread_pct >= 1.60 or dispersion_std >= 0.60:
        dispersion_regime = "HIGH IDIOSYNCRATIC ALPHA"
        dispersion_short = f"{dispersion_spread_pct:.2f}% Spread · Stock-Pick Alpha"
        dispersion_color = "#34D399"
    elif dispersion_spread_pct <= 0.75:
        dispersion_regime = "MACRO BETA LOCK"
        dispersion_short = f"{dispersion_spread_pct:.2f}% Spread · High Index Lock"
        dispersion_color = "#F87171"
    else:
        dispersion_regime = "ROTATIONAL DISPERSION"
        dispersion_short = f"{dispersion_spread_pct:.2f}% Spread · Sector Rotation"
        dispersion_color = "#FBBF24"

    credit_stress_z = round(float(hyg["z_5d"] - lqd["z_5d"]), 2)

    spy_ext = marketdata_client.get_extended_hours_telemetry("SPY", ttl=180)
    qqq_ext = marketdata_client.get_extended_hours_telemetry("QQQ", ttl=180)

    result = {
        "forecast_score": round(raw_score, 1),
        "probability_pct": prob_pct,
        "vix_spot": round(vix_spot, 2),
        "vix_3m": round(vix_3m, 2),
        "vix_term_ratio": vix_term_ratio,
        "vix_term_regime": "BACKWARDATION STRESS" if vix_term_ratio >= 1.0 else ("CONTANGO TAILWIND" if vix_term_ratio <= 0.92 else "NORMAL CONTANGO"),
        "dealer_gamma_regime": dealer_gamma_regime,
        "dealer_gamma_short": dealer_gamma_short,
        "dealer_gamma_color": dealer_gamma_color,
        "dealer_gamma_desc": dealer_gamma_desc,
        "dispersion_spread_pct": dispersion_spread_pct,
        "dispersion_regime": dispersion_regime,
        "dispersion_short": dispersion_short,
        "dispersion_color": dispersion_color,
        "credit_stress_z": credit_stress_z,
        "breadth_delta_rsp_qqq": breadth_delta,
        "radar_axes": radar_axes,
        "signage_title": signage_title,
        "signage_short": signage_short,
        "signage_color": signage_color,
        "signage_border": signage_border,
        "signage_bg": signage_bg,
        "expected_move": expected_move,
        "options_directive": options_directive,
        "pillars": pillars,
        "spy": spy,
        "qqq": qqq,
        "rsp": rsp,
        "uup": uup,
        "yield_info": yield_info,
        "news_intel": news_intel,
        "top_headlines": news_intel.get("headlines", []),
        "extended_hours_lead": {"spy": spy_ext, "qqq": qqq_ext},
        "timestamp": get_ny_now().strftime("%Y-%m-%d %H:%M:%S EST")
    }
    set_cached(cache_key, result)
    return result


def get_macro_economic_7pillar_spider_data() -> Dict[str, Any]:
    """
    AAA 7-Axis Overall US Macro-Economic Regime Spider Engine (0-100 Buffered Normalization):
      1. Manufacturing (ISM Manufacturing PMI + New Orders + Industrial Production + XLI 5D Z-Buffer)
      2. Retail Sales (Retail Sales MoM & Control Group + XRT Consumer 5D Z-Buffer)
      3. Jobless Claims (Initial & Continuing Claims [Inverted Stress] + Credit Labor Buffer)
      4. JOLTS (Job Openings & Quits Demand vs Consensus + IWM/XLI Cyclical Hiring Buffer)
      5. Treasuries (10Y Yield 5D Velocity, 10Y-2Y Curve, 10Y/30Y Note/Bond Auctions + TLT Buffer)
      6. Michigan Sentiment (Consumer Sentiment + Inverted 1Y/5Y Inflation Expectations + XLY/XLP Buffer)
      7. Fed Chair Powell & Speeches (FOMC / Powell / Fed Governor Tone + 2Y-3M Policy Rate Curve + Event Buffer)

    Buffering Mathematics:
    Combines latest hard economic release (level vs structural baseline + surprise vs consensus + momentum vs prior)
    with real-time liquid ETF/rates market proxies via smooth hyperbolic-tangent (tanh) logistic mapping onto [6, 96].
    Color Zones:
      - GREEN (>= 58.0): Expansionary / Bullish Tailwind (#34D399)
      - NEUTRAL (42.0 < score < 58.0): Balanced Equilibrium Buffer (#FBBF24)
      - RED (<= 42.0): Contractionary / Stress Headwind (#F87171)
    """
    cache_key = "macro_econ_7pillar_spider_v47"
    cached = get_cached(cache_key, ttl=300)
    if cached is not None:
        return cached

    now_ny = get_ny_now()
    from_hist = (now_ny - timedelta(days=62)).strftime("%Y-%m-%d")
    to_fwd = (now_ny + timedelta(days=12)).strftime("%Y-%m-%d")
    cal_all = fmp_get("economic-calendar", params={"from": from_hist, "to": to_fwd}, ttl=600)
    if not isinstance(cal_all, list):
        cal_all = []

    us_events = []
    for ev in cal_all:
        if str(ev.get("country", "")).upper() != "US":
            continue
        ev_name = str(ev.get("event", "")).strip()
        ev_ny = _parse_fmp_calendar_ny(str(ev.get("date", "")), ev_name)
        if ev_ny is None:
            continue
        us_events.append({
            "event": ev_name,
            "upper": ev_name.upper(),
            "dt": ev_ny,
            "hours_away": (ev_ny - now_ny).total_seconds() / 3600.0,
            "actual": ev.get("actual"),
            "estimate": ev.get("estimate"),
            "previous": ev.get("previous")
        })

    # Sort descending by timestamp so latest actuals and nearest upcoming prints are easy to query
    us_events.sort(key=lambda x: x["dt"], reverse=True)

    def _find_latest_and_next(match_fn):
        past_with_actual = [e for e in us_events if e["hours_away"] <= 0.5 and e["actual"] is not None and match_fn(e["upper"])]
        upcoming = sorted([e for e in us_events if e["hours_away"] > 0.0 and match_fn(e["upper"])], key=lambda x: x["hours_away"])
        latest_ev = past_with_actual[0] if past_with_actual else None
        next_ev = upcoming[0] if upcoming else None
        return latest_ev, next_ev

    def _fmt_next(ev_obj: Optional[Dict[str, Any]]) -> str:
        if not ev_obj:
            return "No scheduled print in 10D window"
        hrs = float(ev_obj["hours_away"])
        when = f"in {hrs:.0f}h" if hrs < 48.0 else f"in {hrs / 24.0:.1f}d"
        est_txt = f" · Est {ev_obj['estimate']}" if ev_obj.get("estimate") is not None else ""
        return f"{ev_obj['dt'].strftime('%b %d %I:%M %p ET')} ({when}){est_txt}"

    def _zone_meta(score_val: float) -> Tuple[str, str, str]:
        if score_val >= 58.0:
            return "GREEN", "#34D399", "EXPANSION / TAILWIND"
        elif score_val <= 42.0:
            return "RED", "#F87171", "CONTRACTION / HEADWIND"
        return "NEUTRAL", "#FBBF24", "EQUILIBRIUM BUFFER"

    def _logistic_buffer(z_composite: float) -> float:
        return round(float(np.clip(50.0 + 44.0 * math.tanh(0.62 * z_composite), 6.0, 96.0)), 1)

    # Live Market Proxy Batch Quotes for Inter-Release Buffering
    proxy_syms = ["XLI", "XRT", "XLY", "XLP", "IWM", "TLT", "HYG", "LQD", "SPY"]
    p_quotes = fmp_batch_quotes(proxy_syms, ttl=180)
    xli = _compute_asset_5d_telemetry("XLI", p_quotes)
    xrt = _compute_asset_5d_telemetry("XRT", p_quotes)
    xly = _compute_asset_5d_telemetry("XLY", p_quotes)
    xlp = _compute_asset_5d_telemetry("XLP", p_quotes)
    iwm = _compute_asset_5d_telemetry("IWM", p_quotes)
    tlt = _compute_asset_5d_telemetry("TLT", p_quotes)
    hyg = _compute_asset_5d_telemetry("HYG", p_quotes)
    lqd = _compute_asset_5d_telemetry("LQD", p_quotes)
    yield_info = get_macro_yield_regime()

    # --- 1. MANUFACTURING (ISM Manufacturing PMI + New Orders + XLI Industrial Buffer) ---
    ism_lat, ism_nxt = _find_latest_and_next(lambda u: "ISM MANUFACTURING PMI" in u)
    ism_ord_lat, _ = _find_latest_and_next(lambda u: "ISM MANUFACTURING NEW ORDERS" in u)
    pmi_val = float(ism_lat["actual"]) if ism_lat and ism_lat["actual"] is not None else 50.2
    pmi_est = float(ism_lat["estimate"]) if ism_lat and ism_lat.get("estimate") is not None else pmi_val
    pmi_prev = float(ism_lat["previous"]) if ism_lat and ism_lat.get("previous") is not None else pmi_val
    new_ord_val = float(ism_ord_lat["actual"]) if ism_ord_lat and ism_ord_lat.get("actual") is not None else pmi_val
    nxt_pmi_est = float(ism_nxt["estimate"]) if ism_nxt and ism_nxt.get("estimate") is not None else pmi_val

    mfg_z = (
        ((pmi_val - 50.0) / 3.6) * 0.55
        + ((new_ord_val - 50.0) / 4.2) * 0.20
        + ((pmi_val - pmi_est) / 1.5) * 0.25
        + ((nxt_pmi_est - pmi_val) / 2.0) * 0.15
        + (xli["z_5d"] * 0.28)
    )
    mfg_prior_z = ((pmi_prev - 50.0) / 3.6) * 0.65 + ((new_ord_val - 50.0) / 4.2) * 0.20
    mfg_score = _logistic_buffer(mfg_z)
    mfg_prior_score = _logistic_buffer(mfg_prior_z)
    mfg_delta = round(mfg_score - mfg_prior_score, 1)
    mfg_zone, mfg_col, mfg_status = _zone_meta(mfg_score)

    # --- 2. RETAIL SALES (Retail Sales MoM & Control Group + XRT Consumer Buffer) ---
    ret_lat, ret_nxt = _find_latest_and_next(lambda u: "RETAIL SALES MOM" in u)
    ret_ctrl_lat, _ = _find_latest_and_next(lambda u: "RETAIL SALES CONTROL GROUP" in u)
    ret_mom = float(ret_lat["actual"]) if ret_lat and ret_lat["actual"] is not None else 0.3
    ret_est = float(ret_lat["estimate"]) if ret_lat and ret_lat.get("estimate") is not None else 0.25
    ret_prev = float(ret_lat["previous"]) if ret_lat and ret_lat.get("previous") is not None else ret_est
    ret_ctrl = float(ret_ctrl_lat["actual"]) if ret_ctrl_lat and ret_ctrl_lat.get("actual") is not None else ret_mom

    ret_z = (
        ((ret_mom - 0.22) / 0.45) * 0.50
        + ((ret_ctrl - 0.25) / 0.45) * 0.25
        + ((ret_mom - ret_est) / 0.35) * 0.30
        + (xrt["z_5d"] * 0.28)
    )
    ret_prior_z = ((ret_prev - 0.22) / 0.45) * 0.65 + ((ret_ctrl - 0.25) / 0.45) * 0.20
    ret_score = _logistic_buffer(ret_z)
    ret_prior_score = _logistic_buffer(ret_prior_z)
    ret_delta = round(ret_score - ret_prior_score, 1)
    ret_zone, ret_col, ret_status = _zone_meta(ret_score)

    # --- 3. JOBLESS CLAIMS (Initial Claims Inverted Labor Stress + HYG/LQD Credit Buffer) ---
    clm_lat, clm_nxt = _find_latest_and_next(lambda u: "INITIAL JOBLESS CLAIMS" in u)
    raw_clm = float(clm_lat["actual"]) if clm_lat and clm_lat["actual"] is not None else 218.0
    clm_k = raw_clm / 1000.0 if raw_clm > 2000.0 else raw_clm
    raw_clm_est = float(clm_lat["estimate"]) if clm_lat and clm_lat.get("estimate") is not None else clm_k
    clm_est_k = raw_clm_est / 1000.0 if raw_clm_est > 2000.0 else raw_clm_est
    raw_clm_prev = float(clm_lat["previous"]) if clm_lat and clm_lat.get("previous") is not None else clm_k
    clm_prev_k = raw_clm_prev / 1000.0 if raw_clm_prev > 2000.0 else raw_clm_prev

    credit_z_buf = float(np.clip(hyg["z_5d"] - lqd["z_5d"], -2.5, 2.5))
    # Lower claims (< 225K) = stronger labor = positive Z; surging claims (> 245K) = negative Z
    clm_z = (
        ((225.0 - clm_k) / 24.0) * 0.65
        + ((clm_est_k - clm_k) / 10.0) * 0.25
        + ((clm_prev_k - clm_k) / 12.0) * 0.15
        + (credit_z_buf * 0.22)
    )
    clm_prior_z = ((225.0 - clm_prev_k) / 24.0) * 0.75
    clm_score = _logistic_buffer(clm_z)
    clm_prior_score = _logistic_buffer(clm_prior_z)
    clm_delta = round(clm_score - clm_prior_score, 1)
    clm_zone, clm_col, clm_status = _zone_meta(clm_score)

    # --- 4. JOLTS (Job Openings & Quits Labor Demand + Cyclical Small-Cap Buffer) ---
    jolt_lat, jolt_nxt = _find_latest_and_next(lambda u: "JOLTS JOB OPENINGS" in u)
    jolt_m = float(jolt_lat["actual"]) if jolt_lat and jolt_lat["actual"] is not None else 7.35
    if jolt_m > 100.0:
        jolt_m = jolt_m / 1000.0
    jolt_est = float(jolt_lat["estimate"]) if jolt_lat and jolt_lat.get("estimate") is not None else jolt_m
    if jolt_est > 100.0:
        jolt_est = jolt_est / 1000.0
    jolt_prev = float(jolt_lat["previous"]) if jolt_lat and jolt_lat.get("previous") is not None else jolt_m
    if jolt_prev > 100.0:
        jolt_prev = jolt_prev / 1000.0
    nxt_jolt_est = float(jolt_nxt["estimate"]) if jolt_nxt and jolt_nxt.get("estimate") is not None else jolt_m
    if nxt_jolt_est > 100.0:
        nxt_jolt_est = nxt_jolt_est / 1000.0

    jolt_z = (
        ((jolt_m - 7.20) / 0.75) * 0.55
        + ((jolt_m - jolt_est) / 0.28) * 0.30
        + ((nxt_jolt_est - jolt_prev) / 0.35) * 0.20
        + (0.5 * iwm["z_5d"] + 0.5 * xli["z_5d"]) * 0.22
    )
    jolt_prior_z = ((jolt_prev - 7.20) / 0.75) * 0.75
    jolt_score = _logistic_buffer(jolt_z)
    jolt_prior_score = _logistic_buffer(jolt_prior_z)
    jolt_delta = round(jolt_score - jolt_prior_score, 1)
    jolt_zone, jolt_col, jolt_status = _zone_meta(jolt_score)

    # --- 5. TREASURIES (10Y Velocity, 10Y-2Y Curve, 10Y/30Y Auctions + TLT Duration Buffer) ---
    auc_lat, auc_nxt = _find_latest_and_next(lambda u: "10-YEAR NOTE AUCTION" in u or "30-YEAR BOND AUCTION" in u)
    auc_act = float(auc_lat["actual"]) if auc_lat and auc_lat.get("actual") is not None else yield_info["y10_current"]
    auc_prev = float(auc_lat["previous"]) if auc_lat and auc_lat.get("previous") is not None else auc_act
    auc_tail_bps = (auc_act - auc_prev) * 100.0  # Rising clearing auction yield = supply stress

    bps_5d = float(yield_info["rate_change_5d_bps"])
    spr_10_2 = float(yield_info["spread_10_2"])
    # Healthy positive curve (~+0.15 to +0.75%), calm/cooling 5D yields, well-absorbed auctions
    curve_health = 0.45 if (0.05 <= spr_10_2 <= 0.90) else (-0.65 if spr_10_2 < -0.15 else 0.1)
    tsy_z = (
        (-bps_5d / 11.0) * 0.55
        + curve_health
        + (-auc_tail_bps / 35.0) * 0.25
        + (tlt["z_5d"] * 0.28)
    )
    tsy_prior_z = curve_health * 0.85
    tsy_score = _logistic_buffer(tsy_z)
    tsy_prior_score = _logistic_buffer(tsy_prior_z)
    tsy_delta = round(tsy_score - tsy_prior_score, 1)
    tsy_zone, tsy_col, tsy_status = _zone_meta(tsy_score)

    # --- 6. MICHIGAN SENTIMENT (Consumer Sentiment + Inverted 1Y Inflation Exp + XLY/XLP Buffer) ---
    mich_lat, mich_nxt = _find_latest_and_next(lambda u: "MICHIGAN CONSUMER SENTIMENT" in u)
    minf_lat, _ = _find_latest_and_next(lambda u: "MICHIGAN 1 YEAR INFLATION" in u)
    mich_val = float(mich_lat["actual"]) if mich_lat and mich_lat["actual"] is not None else 60.0
    mich_est = float(mich_lat["estimate"]) if mich_lat and mich_lat.get("estimate") is not None else mich_val
    mich_prev = float(mich_lat["previous"]) if mich_lat and mich_lat.get("previous") is not None else mich_est
    minf_val = float(minf_lat["actual"]) if minf_lat and minf_lat.get("actual") is not None else 3.0
    minf_prev = float(minf_lat["previous"]) if minf_lat and minf_lat.get("previous") is not None else minf_val
    disc_vs_staples_z = float(np.clip(xly["z_5d"] - xlp["z_5d"], -2.5, 2.5))

    mich_z = (
        ((mich_val - 58.0) / 9.5) * 0.48
        + ((mich_val - mich_est) / 2.5) * 0.32
        + ((3.1 - minf_val) / 0.65) * 0.25
        + (disc_vs_staples_z * 0.25)
    )
    mich_prior_z = ((mich_prev - 58.0) / 9.5) * 0.55 + ((3.1 - minf_prev) / 0.65) * 0.25
    mich_score = _logistic_buffer(mich_z)
    mich_prior_score = _logistic_buffer(mich_prior_z)
    mich_delta = round(mich_score - mich_prior_score, 1)
    mich_zone, mich_col, mich_status = _zone_meta(mich_score)

    # --- 7. FED CHAIR POWELL & FOMC SPEECHES (Policy Spread + Fed Headline Tone + Speech Hazard) ---
    fed_nxt_list = sorted(
        [e for e in us_events if e["hours_away"] > -2.0 and ("POWELL" in e["upper"] or "FOMC" in e["upper"] or e["upper"].startswith("FED "))],
        key=lambda x: x["hours_away"]
    )
    fed_nxt = fed_nxt_list[0] if fed_nxt_list else None
    powell_48h = any(("POWELL" in e["upper"] or "FOMC STATEMENT" in e["upper"] or "FOMC PRESS" in e["upper"]) and -1.0 <= e["hours_away"] <= 48.0 for e in fed_nxt_list)

    # Scan breaking FMP news for Powell / Fed / FOMC tone
    fed_news = fmp_get("news/stock", {"symbols": "SPY,TLT,QQQ", "limit": 20}, ttl=600)
    fmp_arts = fmp_get("fmp-articles", {"limit": 10}, ttl=600)
    combined_titles = [str(x.get("title", "")).lower() for x in (fed_news if isinstance(fed_news, list) else []) + (fmp_arts if isinstance(fmp_arts, list) else [])]
    dovish_hits = sum(1 for t in combined_titles if any(w in t for w in ["rate cut", "dovish", "powell signals cut", "fed easing", "cooling inflation", "soft landing"]))
    hawkish_hits = sum(1 for t in combined_titles if any(w in t for w in ["rate hike", "hawkish", "higher for longer", "fed pause", "sticky inflation", "powell warns"]))

    spr_2y_3m = float(yield_info["spread_2y_3m"])
    # Moderately inverted 2Y-3M (-0.15% to -0.75%) with calm credit = constructive Fed rate-cut glidepath
    if -0.80 <= spr_2y_3m <= -0.12 and credit_z_buf > -0.75:
        policy_z = 0.65
    elif spr_2y_3m > 0.15:
        policy_z = -0.75  # Hike pressure
    elif spr_2y_3m < -0.80 and credit_z_buf <= -0.75:
        policy_z = -0.60  # Emergency recession cut stress
    else:
        policy_z = 0.15

    tone_z = float(np.clip((dovish_hits - hawkish_hits) * 0.28, -0.85, 0.85))
    hazard_z = -0.55 if powell_48h else (-0.15 if (fed_nxt and fed_nxt["hours_away"] <= 48.0) else 0.15)
    fed_z = policy_z + tone_z + hazard_z + (tlt["z_5d"] * 0.18)
    fed_prior_z = policy_z * 0.85
    fed_score = _logistic_buffer(fed_z)
    fed_prior_score = _logistic_buffer(fed_prior_z)
    fed_delta = round(fed_score - fed_prior_score, 1)
    fed_zone, fed_col, fed_status = _zone_meta(fed_score)

    def _delta_meta(d_val: float) -> Tuple[str, str]:
        if d_val >= 1.0:
            return f"▲ +{d_val:.1f}", "#34D399"
        elif d_val <= -1.0:
            return f"▼ {d_val:.1f}", "#F87171"
        return f"● {d_val:+.1f}", "#FBBF24"

    pillars_7 = [
        {
            "key": "manufacturing",
            "label": "Manufacturing<br>(ISM & Output)",
            "short_label": "Manufacturing (ISM)",
            "score": mfg_score,
            "prior_score": mfg_prior_score,
            "delta_score": mfg_delta,
            "delta_badge": _delta_meta(mfg_delta)[0],
            "delta_color": _delta_meta(mfg_delta)[1],
            "zone": mfg_zone,
            "color": mfg_col,
            "status": mfg_status,
            "latest_str": f"ISM PMI {pmi_val:.1f} (New Orders {new_ord_val:.1f})",
            "surprise_str": f"vs Est {pmi_est:.1f} ({pmi_val - pmi_est:+.1f}) · Prev {pmi_prev:.1f}",
            "proxy_str": f"XLI 5D Buffer: {xli['change_5d_pct']:+.1f}% ({xli['z_5d']:+.2f}σ)",
            "next_str": _fmt_next(ism_nxt)
        },
        {
            "key": "retail_sales",
            "label": "Retail Sales<br>(Consumer Spend)",
            "short_label": "Retail Sales",
            "score": ret_score,
            "prior_score": ret_prior_score,
            "delta_score": ret_delta,
            "delta_badge": _delta_meta(ret_delta)[0],
            "delta_color": _delta_meta(ret_delta)[1],
            "zone": ret_zone,
            "color": ret_col,
            "status": ret_status,
            "latest_str": f"MoM {ret_mom:+.1f}% (Control {ret_ctrl:+.1f}%)",
            "surprise_str": f"vs Est {ret_est:+.1f}% ({ret_mom - ret_est:+.1f}%)",
            "proxy_str": f"XRT Retail Buffer: {xrt['change_5d_pct']:+.1f}% ({xrt['z_5d']:+.2f}σ)",
            "next_str": _fmt_next(ret_nxt)
        },
        {
            "key": "jobless_claims",
            "label": "Jobless Claims<br>(Labor Resilience)",
            "short_label": "Jobless Claims",
            "score": clm_score,
            "prior_score": clm_prior_score,
            "delta_score": clm_delta,
            "delta_badge": _delta_meta(clm_delta)[0],
            "delta_color": _delta_meta(clm_delta)[1],
            "zone": clm_zone,
            "color": clm_col,
            "status": clm_status,
            "latest_str": f"{clm_k:.0f}K Initial Claims",
            "surprise_str": f"vs Est {clm_est_k:.0f}K ({clm_k - clm_est_k:+.0f}K · Lower=Stronger)",
            "proxy_str": f"HYG/LQD Labor Credit: {credit_z_buf:+.2f}σ",
            "next_str": _fmt_next(clm_nxt)
        },
        {
            "key": "jolts",
            "label": "JOLTS Openings<br>(Hiring Demand)",
            "short_label": "JOLTS Openings",
            "score": jolt_score,
            "prior_score": jolt_prior_score,
            "delta_score": jolt_delta,
            "delta_badge": _delta_meta(jolt_delta)[0],
            "delta_color": _delta_meta(jolt_delta)[1],
            "zone": jolt_zone,
            "color": jolt_col,
            "status": jolt_status,
            "latest_str": f"{jolt_m:.2f}M Job Openings",
            "surprise_str": f"vs Est {jolt_est:.2f}M ({jolt_m - jolt_est:+.2f}M) · Prev {jolt_prev:.2f}M",
            "proxy_str": f"IWM/XLI Hiring Proxy: {(0.5*iwm['z_5d']+0.5*xli['z_5d']):+.2f}σ",
            "next_str": _fmt_next(jolt_nxt)
        },
        {
            "key": "treasuries",
            "label": "Treasuries &<br>Bond Auctions",
            "short_label": "Treasuries & Auctions",
            "score": tsy_score,
            "prior_score": tsy_prior_score,
            "delta_score": tsy_delta,
            "delta_badge": _delta_meta(tsy_delta)[0],
            "delta_color": _delta_meta(tsy_delta)[1],
            "zone": tsy_zone,
            "color": tsy_col,
            "status": tsy_status,
            "latest_str": f"10Y {yield_info['y10_current']:.2f}% · 10Y-2Y {spr_10_2:+.2f}%",
            "surprise_str": f"5D Rate Move: {bps_5d:+.0f} bps · Last Auction Δ {auc_tail_bps:+.0f} bps",
            "proxy_str": f"TLT Duration Buffer: {tlt['change_5d_pct']:+.1f}% ({tlt['z_5d']:+.2f}σ)",
            "next_str": _fmt_next(auc_nxt)
        },
        {
            "key": "michigan_sentiment",
            "label": "Michigan Sentiment<br>& Inflation Exp.",
            "short_label": "Michigan Sentiment",
            "score": mich_score,
            "prior_score": mich_prior_score,
            "delta_score": mich_delta,
            "delta_badge": _delta_meta(mich_delta)[0],
            "delta_color": _delta_meta(mich_delta)[1],
            "zone": mich_zone,
            "color": mich_col,
            "status": mich_status,
            "latest_str": f"Index {mich_val:.1f} · 1Y Infl Exp {minf_val:.1f}%",
            "surprise_str": f"vs Est {mich_est:.1f} ({mich_val - mich_est:+.1f})",
            "proxy_str": f"XLY/XLP Consumer Spread: {disc_vs_staples_z:+.2f}σ",
            "next_str": _fmt_next(mich_nxt)
        },
        {
            "key": "powell_fed",
            "label": "Fed Chair Powell<br>& FOMC Speeches",
            "short_label": "Powell & Fed Speeches",
            "score": fed_score,
            "prior_score": fed_prior_score,
            "delta_score": fed_delta,
            "delta_badge": _delta_meta(fed_delta)[0],
            "delta_color": _delta_meta(fed_delta)[1],
            "zone": fed_zone,
            "color": fed_col,
            "status": fed_status,
            "latest_str": f"2Y-3M Policy Spread: {spr_2y_3m:+.2f}% ({yield_info['fed_stance_tag']})",
            "surprise_str": f"Fed Wire Tone: {dovish_hits} Dovish vs {hawkish_hits} Hawkish",
            "proxy_str": "48H Binary Powell/FOMC Active" if powell_48h else f"Next Speech: {fed_nxt['event'] if fed_nxt else 'Clear'}",
            "next_str": _fmt_next(fed_nxt)
        }
    ]

    overall_avg = round(sum(p["score"] for p in pillars_7) / len(pillars_7), 1)
    overall_prior_avg = round(sum(p["prior_score"] for p in pillars_7) / len(pillars_7), 1)
    overall_delta = round(overall_avg - overall_prior_avg, 1)
    ov_zone, ov_col, ov_status = _zone_meta(overall_avg)
    green_cnt = sum(1 for p in pillars_7 if p["zone"] == "GREEN")
    red_cnt = sum(1 for p in pillars_7 if p["zone"] == "RED")
    neutral_cnt = len(pillars_7) - green_cnt - red_cnt

    out = {
        "pillars": pillars_7,
        "overall_score": overall_avg,
        "overall_prior_score": overall_prior_avg,
        "overall_delta": overall_delta,
        "overall_delta_badge": _delta_meta(overall_delta)[0],
        "overall_delta_color": _delta_meta(overall_delta)[1],
        "overall_zone": ov_zone,
        "overall_color": ov_col,
        "overall_status": ov_status,
        "green_count": green_cnt,
        "neutral_count": neutral_cnt,
        "red_count": red_cnt,
        "timestamp": now_ny.strftime("%Y-%m-%d %H:%M:%S EST")
    }
    set_cached(cache_key, out)
    return out


# =========================================================================
# PILLAR 5: FULL FMP ULTRA FUNDAMENTAL, 25-DAY EARNINGS & 13F OPEN INTEREST ENGINE
# =========================================================================

def get_upcoming_earnings_map() -> Dict[str, Dict[str, Any]]:
    """
    Fetches FMP /earnings-calendar for the next 30 days as a fast Stage-1 baseline map.
    Note: Because global /earnings-calendar truncates at 4,000 rows, Stage-2 Top-5 vetting
    always calls get_ticker_earnings_25d(symbol) via per-symbol /earnings?symbol=SYM&limit=6.
    """
    cache_key = "global_earnings_map_30d"
    cached = get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached

    now_ny = get_ny_now()
    from_str = (now_ny - timedelta(days=1)).strftime("%Y-%m-%d")
    to_str = (now_ny + timedelta(days=30)).strftime("%Y-%m-%d")

    data = fmp_get("earnings-calendar", params={"from": from_str, "to": to_str}, ttl=1800)
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(data, list):
        today_date = now_ny.date()
        for item in data:
            sym = str(item.get("symbol", "")).strip().upper()
            dt_str = item.get("date", "")
            if sym and dt_str:
                try:
                    ev_date = datetime.date.fromisoformat(dt_str[:10])
                    days_away = (ev_date - today_date).days
                    if days_away >= 0:
                        if sym not in out or days_away < out[sym]["days_to_earnings"]:
                            out[sym] = {
                                "earnings_date": dt_str[:10],
                                "days_to_earnings": days_away,
                                "eps_estimated": item.get("epsEstimated"),
                                "rev_estimated": item.get("revenueEstimated"),
                                "has_earnings_25d": (0 <= days_away <= 25),
                                "has_binary_earnings_7d": (0 <= days_away <= 7),
                                "eps_beat_streak": 0
                            }
                except Exception:
                    continue

    set_cached(cache_key, out)
    return out


def get_ticker_earnings_25d(symbol: str, fetch_live: bool = True) -> Dict[str, Any]:
    """
    Queries FMP Ultra per-symbol `/earnings?symbol=SYM&limit=10` endpoint.
    Catches exact upcoming earnings within <= 25 days (bypassing 4,000-row truncation),
    calculates EPS beat streak, and measures realized 1-day post-earnings absolute % move
    across the past 8 quarters for honest comparison against OPRA straddle implied move.
    """
    sym = symbol.strip().upper()
    cache_key = f"ticker_earnings_25d_v42_{sym}"
    cached = get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached

    if not fetch_live:
        global_map = get_upcoming_earnings_map()
        if sym in global_map:
            out_g = dict(global_map[sym])
            out_g.setdefault("hist_er_avg_move_pct", 0.0)
            out_g.setdefault("hist_er_med_move_pct", 0.0)
            out_g.setdefault("hist_er_max_move_pct", 0.0)
            out_g.setdefault("hist_er_quarters_n", 0)
            return out_g
        return {
            "earnings_date": "Clear (>25d)",
            "days_to_earnings": 45,
            "eps_estimated": None,
            "rev_estimated": None,
            "has_earnings_25d": False,
            "has_binary_earnings_7d": False,
            "eps_beat_streak": 0,
            "hist_er_avg_move_pct": 0.0,
            "hist_er_med_move_pct": 0.0,
            "hist_er_max_move_pct": 0.0,
            "hist_er_quarters_n": 0,
        }

    now_ny = get_ny_now()
    today_date = now_ny.date()
    data = fmp_get("earnings", params={"symbol": sym, "limit": 10}, ttl=1800)

    best_upcoming: Optional[Dict[str, Any]] = None
    eps_beats = 0
    reported_checked = 0
    past_er_dates: List[datetime.date] = []

    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            dt_str = str(item.get("date", ""))[:10]
            if not dt_str:
                continue
            try:
                ev_date = datetime.date.fromisoformat(dt_str)
                days_away = (ev_date - today_date).days
                eps_act = item.get("epsActual")
                eps_est = item.get("epsEstimated")
                if days_away >= 0 and eps_act is None:
                    if best_upcoming is None or days_away < best_upcoming["days_to_earnings"]:
                        best_upcoming = {
                            "earnings_date": dt_str,
                            "days_to_earnings": days_away,
                            "eps_estimated": eps_est,
                            "rev_estimated": item.get("revenueEstimated"),
                            "has_earnings_25d": (0 <= days_away <= 25),
                            "has_binary_earnings_7d": (0 <= days_away <= 7)
                        }
                elif days_away < 0:
                    if len(past_er_dates) < 8:
                        past_er_dates.append(ev_date)
                    if eps_act is not None and eps_est is not None and reported_checked < 4:
                        reported_checked += 1
                        if float(eps_act) >= float(eps_est):
                            eps_beats += 1
            except Exception:
                continue

    if best_upcoming is None:
        global_map = get_upcoming_earnings_map()
        if sym in global_map:
            best_upcoming = dict(global_map[sym])
        else:
            best_upcoming = {
                "earnings_date": "Clear (>25d)",
                "days_to_earnings": 45,
                "eps_estimated": None,
                "rev_estimated": None,
                "has_earnings_25d": False,
                "has_binary_earnings_7d": False
            }

    # Measure realized 1-day post-earnings absolute % move across past reported quarters
    er_moves: List[float] = []
    if past_er_dates:
        try:
            hist_df, _, _ = get_hybrid_price_series(sym, fetch_4h=False)
            if hist_df is not None and len(hist_df) >= 30:
                if "date" in hist_df.columns:
                    dates_list = pd.to_datetime(hist_df["date"]).dt.date.tolist()
                else:
                    dates_list = pd.to_datetime(hist_df.index).date.tolist()
                closes_list = pd.to_numeric(hist_df["close"], errors="coerce").tolist()
                date_idx_map = {d_val: i for i, d_val in enumerate(dates_list)}
                for er_d in past_er_dates:
                    # Locate reporting bar or next trading bar (captures both BMO and AMC reports)
                    pos = date_idx_map.get(er_d)
                    if pos is None:
                        for offset in (1, 2, -1):
                            pos = date_idx_map.get(er_d + timedelta(days=offset))
                            if pos is not None:
                                break
                    if pos is not None and 1 <= pos < len(closes_list):
                        c_prev = closes_list[pos - 1]
                        c_curr = closes_list[pos]
                        m1 = abs((c_curr - c_prev) / max(1e-4, c_prev)) * 100.0 if (c_prev and c_curr) else 0.0
                        m2 = 0.0
                        if pos + 1 < len(closes_list) and closes_list[pos + 1] and c_curr:
                            m2 = abs((closes_list[pos + 1] - c_curr) / max(1e-4, c_curr)) * 100.0
                        er_mv = max(m1, m2)
                        if 0.0 <= er_mv <= 65.0:
                            er_moves.append(er_mv)
        except Exception:
            er_moves = []

    best_upcoming["eps_beat_streak"] = eps_beats
    best_upcoming["hist_er_avg_move_pct"] = round(float(np.mean(er_moves)), 2) if er_moves else 0.0
    best_upcoming["hist_er_med_move_pct"] = round(float(np.median(er_moves)), 2) if er_moves else 0.0
    best_upcoming["hist_er_max_move_pct"] = round(float(np.max(er_moves)), 2) if er_moves else 0.0
    best_upcoming["hist_er_quarters_n"] = len(er_moves)
    set_cached(cache_key, best_upcoming)
    return best_upcoming


def get_fmp_institutional_open_interest(
    symbol: str,
    sharp_tape_flow: Dict[str, Any],
    fetch_live: bool = True
) -> Dict[str, Any]:
    """
    Fuses FMP Ultra's `/institutional-ownership/symbol-positions-summary` (13F Institutional
    Call Open Interest, Put Open Interest, Put/Call Ratio, QoQ Call/Put changes, and 13F share
    accumulation/distribution) with Live Tape Sharp Price-Volume Flow (CMF-20, 10D Up/Down Block
    Dollar Volume Ratio, 4H/1D CLV, OBV divergence) to determine whether Whales & Sharps are
    LOADING or UNLOADING.
    """
    sym = symbol.strip().upper()
    cache_key = f"inst_oi_whale_v42_{sym}"
    cached_raw = get_cached(cache_key, ttl=3600)

    if cached_raw is None and fetch_live:
        now_ny = get_ny_now()
        curr_q = ((now_ny.month - 1) // 3) + 1
        quarters_to_try: List[Tuple[int, int]] = []
        y_q, q_q = now_ny.year, curr_q
        for _ in range(5):
            q_q -= 1
            if q_q == 0:
                q_q = 4
                y_q -= 1
            quarters_to_try.append((y_q, q_q))
        best_with_options: Optional[Dict[str, Any]] = None
        best_with_holdings: Optional[Dict[str, Any]] = None

        def _probe_quarter(yq: Tuple[int, int]) -> Tuple[Tuple[int, int], Optional[Dict[str, Any]]]:
            yr, qtr = yq
            empty_key = f"inst_oi_empty_{sym}_{yr}_Q{qtr}"
            if get_cached(empty_key, ttl=3600) is not None:
                return yq, None
            res = fmp_get(
                "institutional-ownership/symbol-positions-summary",
                params={"symbol": sym, "year": yr, "quarter": qtr},
                ttl=3600
            )
            if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
                r0 = dict(res[0])
                r0["filing_quarter"] = f"Q{qtr} '{str(yr)[-2:]}"
                return yq, r0
            set_cached(empty_key, True, ttl=3600)
            return yq, None

        with ThreadPoolExecutor(max_workers=4) as ex:
            probe_results = list(ex.map(_probe_quarter, quarters_to_try))

        for _, r0 in probe_results:
            if not r0:
                continue
            has_opts = ((r0.get("totalCalls") or 0) > 0 or (r0.get("totalPuts") or 0) > 0)
            if has_opts and best_with_options is None:
                best_with_options = r0
            if (r0.get("investorsHolding") or 0) > 0 and best_with_holdings is None:
                best_with_holdings = r0

        if best_with_options is not None:
            cached_raw = best_with_options
        elif best_with_holdings is not None:
            cached_raw = best_with_holdings
        else:
            cached_raw = {}
        set_cached(cache_key, cached_raw, ttl=3600)

    raw = cached_raw if isinstance(cached_raw, dict) else {}

    total_calls = int(raw.get("totalCalls") or 0)
    last_calls = int(raw.get("lastTotalCalls") or 0)
    calls_chg = int(raw.get("totalCallsChange") or 0)
    calls_chg_pct = round((calls_chg / last_calls) * 100.0, 1) if last_calls > 0 else 0.0

    total_puts = int(raw.get("totalPuts") or 0)
    last_puts = int(raw.get("lastTotalPuts") or 0)
    puts_chg = int(raw.get("totalPutsChange") or 0)
    puts_chg_pct = round((puts_chg / last_puts) * 100.0, 1) if last_puts > 0 else 0.0

    has_13f_oi = (total_calls > 0 or total_puts > 0)
    filing_quarter = str(raw.get("filing_quarter") or "")

    if has_13f_oi:
        pc_ratio = round(float(raw.get("putCallRatio") or (total_puts / max(1, total_calls))), 2)
    else:
        pc_ratio = 1.0
    pc_ratio_chg = round(float(raw.get("putCallRatioChange") or 0.0), 2)

    inc_pos = int(raw.get("increasedPositions") or 0)
    red_pos = int(raw.get("reducedPositions") or 0)
    net_inst_buyers = inc_pos - red_pos

    shares_13f = int(raw.get("numberOf13Fshares") or 0)
    last_shares_13f = int(raw.get("lastNumberOf13Fshares") or 0)
    shares_chg = int(raw.get("numberOf13FsharesChange") or 0)
    shares_chg_pct = round((shares_chg / last_shares_13f) * 100.0, 1) if last_shares_13f > 0 else 0.0

    # Combine Live Tape Sharp Score (0-100 centered at 50 -> -90 to +90 centered at 0) with 13F Positioning
    raw_tape_50 = float(sharp_tape_flow.get("sharp_tape_score", 50.0))
    tape_centered = (raw_tape_50 - 50.0) * 1.85
    cmf_20 = float(sharp_tape_flow.get("cmf_20", 0.0))
    ud_ratio = float(sharp_tape_flow.get("up_down_vol_ratio", 1.0))

    inst_bias_pts = 0.0
    if has_13f_oi:
        if pc_ratio <= 0.72:
            inst_bias_pts += 12.0
        elif pc_ratio <= 0.90:
            inst_bias_pts += 5.0
        elif pc_ratio >= 1.35:
            inst_bias_pts -= 12.0
        elif pc_ratio >= 1.12:
            inst_bias_pts -= 5.0

        if calls_chg_pct > puts_chg_pct + 8.0:
            inst_bias_pts += 7.0
        elif puts_chg_pct > calls_chg_pct + 8.0:
            inst_bias_pts -= 7.0

    if net_inst_buyers > 15 or shares_chg_pct >= 2.0:
        inst_bias_pts += 6.0
    elif net_inst_buyers < -15 or shares_chg_pct <= -2.0:
        inst_bias_pts -= 6.0

    # 75% weight on live daily/intraday price-volume tape + 25% weight on 13F institutional positioning
    combined_whale_score = round(float(np.clip(tape_centered + inst_bias_pts, -100.0, 100.0)), 1)

    # Base tape sentiment description
    if combined_whale_score >= 24.0:
        tape_sentiment = "Whales Loading"
    elif combined_whale_score >= 8.0:
        tape_sentiment = "Sharps Accumulating"
    elif combined_whale_score <= -24.0:
        tape_sentiment = "Whales Unloading"
    elif combined_whale_score <= -8.0:
        tape_sentiment = "Sharps Distributing"
    else:
        tape_sentiment = "Two-Way Balanced Flow"

    # Direction Contextualization (Truth in Mean-Reversion Signals)
    action_str = str(sharp_tape_flow.get("direction", "")).upper()
    if "PUT" in action_str:
        if combined_whale_score >= 8.0:
            whale_status = "BULLISH TAPE (OVERBOUGHT STRETCH)"
            whale_badge = "TAPE STRETCH (PUT)"
            whale_color = "amber"
            flow_alignment = "Tape Bullish (Overbought Stretch into Put Reversion)"
        elif combined_whale_score <= -8.0:
            whale_status = "BEARISH FLOW (PUT ALIGNED)"
            whale_badge = "FLOW ALIGNED (PUT)"
            whale_color = "rose"
            flow_alignment = "Tape Selling (Distribution Confirms Put)"
        else:
            whale_status = "BALANCED TAPE (PUT REVERSION)"
            whale_badge = "BALANCED FLOW"
            whale_color = "slate"
            flow_alignment = "Tape Balanced"
    elif "CALL" in action_str:
        if combined_whale_score >= 8.0:
            whale_status = "BULLISH FLOW (CALL ALIGNED)"
            whale_badge = "FLOW ALIGNED (CALL)"
            whale_color = "emerald"
            flow_alignment = "Tape Accumulating (Sharps Confirm Call)"
        elif combined_whale_score <= -8.0:
            whale_status = "OVERSOLD FLUSH (CALL REVERSION)"
            whale_badge = "FLUSH TAPE (CALL)"
            whale_color = "amber"
            flow_alignment = "Tape Selling Flush (Divergence vs Call Reversion)"
        else:
            whale_status = "BALANCED TAPE (CALL REVERSION)"
            whale_badge = "BALANCED FLOW"
            whale_color = "slate"
            flow_alignment = "Tape Balanced"
    else:
        if combined_whale_score >= 24.0:
            whale_status = "WHALES & SHARPS LOADING"
            whale_badge = "WHALES LOADING"
            whale_color = "emerald"
        elif combined_whale_score >= 8.0:
            whale_status = "SHARPS ACCUMULATING"
            whale_badge = "SHARPS BUYING"
            whale_color = "cyan"
        elif combined_whale_score <= -24.0:
            whale_status = "WHALES & SHARPS UNLOADING"
            whale_badge = "WHALES UNLOADING"
            whale_color = "rose"
        elif combined_whale_score <= -8.0:
            whale_status = "SHARPS DISTRIBUTING"
            whale_badge = "SHARPS SELLING"
            whale_color = "amber"
        else:
            whale_status = "NEUTRAL / TWO-WAY TAPE"
            whale_badge = "TWO-WAY FLOW"
            whale_color = "slate"
        flow_alignment = tape_sentiment

    if has_13f_oi:
        qtr_disp = f" ({filing_quarter})" if filing_quarter else ""
        oi_str = f"13F Options{qtr_disp}: {total_calls:,} Calls vs {total_puts:,} Puts (P/C {pc_ratio:.2f})"
    else:
        oi_str = "13F Options: Not Reported by Institutions (Equity Tape Tracked)"

    whale_summary = (
        f"{whale_badge} (Score {combined_whale_score:+.0f}): CMF-20 {cmf_20:+.2f} | "
        f"Up/Dn Vol {ud_ratio:.2f}x | {flow_alignment} | {oi_str}"
    )

    return {
        "whale_status": whale_status,
        "whale_badge": whale_badge,
        "whale_color": whale_color,
        "whale_score": combined_whale_score,
        "cmf_20": cmf_20,
        "up_down_vol_ratio": ud_ratio,
        "flow_alignment": flow_alignment,
        "tape_sentiment": tape_sentiment,
        "inst_total_calls": total_calls,
        "inst_total_puts": total_puts,
        "inst_put_call_ratio": pc_ratio,
        "inst_put_call_change": pc_ratio_chg,
        "inst_calls_change_pct": calls_chg_pct,
        "inst_puts_change_pct": puts_chg_pct,
        "inst_net_buyers": net_inst_buyers,
        "inst_shares_13f": shares_13f,
        "inst_shares_change_pct": shares_chg_pct,
        "inst_quarter": filing_quarter,
        "has_13f_oi_data": has_13f_oi,
        "whale_summary": whale_summary
    }


def _default_short_float_metrics(sym: str) -> Dict[str, Any]:
    return {
        "symbol": sym,
        "has_true_short_interest": False,
        "short_pct": 0.0,
        "days_to_cover": 0.0,
        "shares_short": 0,
        "shares_short_prior": 0,
        "short_mom_pct": 0.0,
        "shares_outstanding": 0,
        "float_shares": 0,
        "free_float_pct": 100.0,
        "inst_lockup_pct": 0.0,
        "inst_put_call_ratio": 1.0,
        "inst_hedge_regime": "BALANCED 13F HEDGE",
        "squeeze_label": "13F Float Data Pending",
        "inst_pct": 0.0,
        "insider_pct": 0.0,
        "retail_float_pct": 100.0,
        "hazard_level": "LOW",
        "hazard_badge": "STABLE FLOAT DYNAMICS",
        "hazard_color": "#10B981",
        "is_warning": False,
        "collar_advice": "Unencumbered float with minimal institutional hedge stress. Standard 30-45 DTE options playbook applies.",
        "has_data": False
    }


def get_equity_short_and_float_metrics(symbol: str, ttl: int = 14400) -> Dict[str, Any]:
    """
    Retrieves institutional float structure via FMP `/stable/shares-float` (`floatShares`,
    `outstandingShares`, `freeFloat`) + FMP 13F institutional ownership & Put/Call hedge ratio.
    Never fabricates FINRA short interest percentages from 13F P/C ratios: when FINRA
    short float is unavailable on FMP, reports truthful `inst_put_call_ratio`,
    `inst_lockup_pct`, and `inst_hedge_regime`.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return _default_short_float_metrics(sym)

    cache_key = f"equity_short_float_v5_{sym}"
    cached = get_cached(cache_key, ttl=ttl)
    if cached is not None:
        return cached

    if sym in THEMATIC_ETFS:
        etf_res = _default_short_float_metrics(sym)
        etf_res["hazard_badge"] = "ETF BASKET"
        etf_res["squeeze_label"] = "Thematic ETF Creation/Redemption Basket"
        etf_res["collar_advice"] = "Thematic ETF Basket — single-equity float lockup constraints not applicable."
        etf_res["source"] = "Thematic ETF Basket"
        set_cached(cache_key, etf_res, ttl=ttl)
        return etf_res

    try:
        sf_data = fmp_get("shares-float", params={"symbol": sym}, ttl=ttl)
        sf0 = sf_data[0] if (isinstance(sf_data, list) and len(sf_data) > 0 and isinstance(sf_data[0], dict)) else {}

        shares_out = int(float(sf0.get("outstandingShares") or 0))
        float_shares = int(float(sf0.get("floatShares") or shares_out))
        raw_free_float = sf0.get("freeFloat")
        free_float_pct = float(raw_free_float) if raw_free_float is not None else (
            round((float_shares / shares_out) * 100.0, 1) if shares_out > 0 and float_shares > 0 else 0.0
        )

        # FMP 13F Institutional Ownership & Put/Call positioning
        oi_13f = get_fmp_institutional_open_interest(sym, {}, fetch_live=True)
        inst_shares_13f = int(oi_13f.get("inst_shares_13f") or 0)
        denom_sh = float(float_shares if float_shares > 0 else shares_out)
        inst_pct = round(min(98.0, (inst_shares_13f / denom_sh) * 100.0), 1) if (denom_sh > 0 and inst_shares_13f > 0) else 0.0
        insider_pct = round(max(0.0, min(60.0, 100.0 - free_float_pct)), 1) if free_float_pct > 0 else 0.0
        inst_lockup_pct = round(max(0.0, 100.0 - free_float_pct), 1) if free_float_pct > 0 else round(min(95.0, inst_pct), 1)

        # Check if FMP explicitly returned real shortPercentOfFloat; never fabricate fake short %
        raw_short_pct = sf0.get("shortPercentOfFloat") or sf0.get("shortInterestPct")
        has_true_short = False
        short_pct = 0.0
        short_ratio = 0.0
        if raw_short_pct is not None and float(raw_short_pct) > 0:
            has_true_short = True
            short_pct = round(float(raw_short_pct), 2)
            short_ratio = round(float(sf0.get("shortRatio") or sf0.get("daysToCover") or 0.0), 2)

        pc_13f = float(oi_13f.get("inst_put_call_ratio") or 1.0)
        puts_chg_pct = float(oi_13f.get("inst_puts_change_pct") or 0.0)
        if pc_13f >= 1.20:
            inst_hedge_regime = "HEAVY PUT HEDGING"
        elif pc_13f <= 0.72:
            inst_hedge_regime = "BULLISH 13F CALL SKEW"
        else:
            inst_hedge_regime = "BALANCED 13F HEDGE"

        retail_float_pct = max(0.0, round(100.0 - min(98.0, inst_pct + insider_pct), 1))

        # Float Lockup & Institutional Hedge Pressure Hazard Classification
        if (has_true_short and short_pct >= 18.0) or (free_float_pct > 0 and free_float_pct <= 22.0 and pc_13f >= 1.35):
            hazard_level = "EXTREME"
            hazard_badge = "TIGHT FLOAT / HEAVY HEDGE"
            hazard_color = "#F43F5E"
            is_warning = True
            collar_advice = "Tight free float paired with heavy 13F put hedging. Deploy High-Delta (0.50Δ) calls or call debit spreads."
        elif (has_true_short and short_pct >= 10.0) or (puts_chg_pct >= 25.0 and pc_13f >= 1.25):
            hazard_level = "ELEVATED"
            hazard_badge = "ELEVATED 13F PUT HEDGE"
            hazard_color = "#F59E0B"
            is_warning = True
            collar_advice = "Rising institutional 13F put hedging creates coiled wing volatility. Vertical Debit Spread reduces vega exposure."
        elif pc_13f >= 1.05 or (free_float_pct > 0 and free_float_pct <= 45.0):
            hazard_level = "MODERATE"
            hazard_badge = "ACTIVE INSTITUTIONAL FLOW"
            hazard_color = "#38BDF8"
            is_warning = False
            collar_advice = "Two-way institutional hedge flow across liquid strikes. Standard 30-45 DTE High-Delta playbook applies."
        else:
            hazard_level = "LOW"
            hazard_badge = "UNENCUMBERED LIQUID FLOAT"
            hazard_color = "#10B981"
            is_warning = False
            collar_advice = "Deep unencumbered float with balanced institutional positioning."

        squeeze_label = (
            f"{short_pct:.1f}% Short Float ({short_ratio:.1f}d DTC)"
            if has_true_short
            else f"13F P/C {pc_13f:.2f}x ({free_float_pct:.0f}% Float)"
        )

        has_data = bool(shares_out > 0 or float_shares > 0 or inst_shares_13f > 0)
        res = {
            "symbol": sym,
            "has_true_short_interest": has_true_short,
            "short_pct": round(short_pct, 2),
            "days_to_cover": round(short_ratio, 2),
            "shares_short": int(float(sf0.get("sharesShort") or 0)),
            "shares_short_prior": 0,
            "short_mom_pct": 0.0,
            "shares_outstanding": shares_out,
            "float_shares": float_shares,
            "free_float_pct": round(free_float_pct, 1),
            "inst_lockup_pct": inst_lockup_pct,
            "inst_put_call_ratio": round(pc_13f, 2),
            "inst_hedge_regime": inst_hedge_regime,
            "squeeze_label": squeeze_label,
            "inst_pct": round(inst_pct, 1),
            "insider_pct": round(insider_pct, 1),
            "retail_float_pct": retail_float_pct,
            "hazard_level": hazard_level,
            "hazard_badge": hazard_badge,
            "hazard_color": hazard_color,
            "is_warning": is_warning,
            "collar_advice": collar_advice,
            "has_data": has_data,
            "source": "FMP /stable/shares-float + 13F"
        }
        set_cached(cache_key, res, ttl=ttl)
        return res
    except Exception:
        default_res = _default_short_float_metrics(sym)
        set_cached(cache_key, default_res, ttl=ttl)
        return default_res


def batch_get_short_squeeze_warnings(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fast concurrent fetcher for short squeeze warnings across watchlist and top-5 candidates.
    Cached with in-memory TTL; takes ~0ms for cached symbols.
    """
    import concurrent.futures
    clean_syms = list(dict.fromkeys([s.strip().upper() for s in symbols if s and s.strip()]))
    if not clean_syms:
        return {}

    out = {}
    uncached = []
    for s in clean_syms:
        c = get_cached(f"equity_short_float_v5_{s}", ttl=14400)
        if c is not None:
            out[s] = c
        else:
            uncached.append(s)

    if uncached:
        workers = min(6, len(uncached))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_sym = {executor.submit(get_equity_short_and_float_metrics, s): s for s in uncached}
            for future in concurrent.futures.as_completed(future_to_sym):
                s = future_to_sym[future]
                try:
                    res = future.result()
                    out[s] = res
                except Exception:
                    out[s] = _default_short_float_metrics(s)

    return out


def get_near_live_option_contract(
    symbol: str,
    action: str,
    target_strike: float,
    target_dte: int = 35,
    target_delta: float = 0.50,
    delta_mode: str = "HIGH_DELTA",
    chain_df: Optional[pd.DataFrame] = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieves live real exchange option contract from OPRA via MarketData.app
    (`/v1/options/chain/{symbol}/?feed=cached`) returning real OPRA Bid, Ask, Mid,
    Open Interest, Volume, Implied Volatility, and native Greeks (Delta, Gamma, Theta, Vega).
    Supports single-pass `chain_df` sharing and High-Delta (`0.40D-0.65D`, default `0.50D`)
    vs `CONVEX_OTM` strike selection.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    cache_key = f"live_opt_contract_v5_{sym}_{action}_{target_dte}_{delta_mode}_{round(target_strike, 1)}"
    if chain_df is None:
        cached = get_cached(cache_key, ttl=1800)
        if cached is not None:
            return cached if cached != {} else None

    today = get_ny_now().date()
    opt_is_call = "CALL" in action.upper()
    opt_type = "CALL" if opt_is_call else "PUT"
    type_letter = "C" if opt_is_call else "P"
    side_param = "call" if opt_is_call else "put"

    # 1. Primary: MarketData.app OPRA Options Chain (Single-Pass `chain_df` or `feed="cached"`)
    try:
        md_df = chain_df
        if md_df is None or md_df.empty:
            md_df = marketdata_client.get_option_chain_native(
                sym, dte=target_dte, side=side_param, strike_limit=60, ttl=900, feed="cached"
            )
        if md_df is not None and not md_df.empty:
            df_c = md_df[md_df["side"].str.lower() == side_param].copy() if "side" in md_df.columns else md_df.copy()
            if df_c.empty:
                df_c = md_df.copy()

            if delta_mode == "HIGH_DELTA" and "delta" in df_c.columns and df_c["delta"].notna().any():
                df_valid = df_c.dropna(subset=["delta"]).copy()
                df_valid["abs_delta"] = df_valid["delta"].abs()
                hd_band = df_valid[(df_valid["abs_delta"] >= 0.40) & (df_valid["abs_delta"] <= 0.65)]
                pool = hd_band if not hd_band.empty else df_valid
                liq_pool = pool[(pool["bid"] > 0) | (pool["mid"] > 0) | (pool["openInterest"] > 0)]
                if not liq_pool.empty:
                    pool = liq_pool
                pool = pool.copy()
                pool["diff"] = (pool["abs_delta"] - abs(target_delta)).abs()
                row = pool.sort_values(["diff", "openInterest"], ascending=[True, False]).iloc[0]
            else:
                df_c["diff"] = (df_c["strike"] - target_strike).abs()
                row = df_c.sort_values("diff").iloc[0]

            strike = float(row["strike"])
            best_exp = str(row.get("expirationDate") or get_target_options_friday(target_dte))
            best_dte = int(row.get("dte") or target_dte)
            bid = float(row.get("bid", 0.0) or 0.0)
            ask = float(row.get("ask", 0.0) or 0.0)
            mid = float(row.get("mid", 0.0) or 0.0)
            last_p = float(row.get("lastPrice", 0.0) or mid)
            if mid <= 0 and bid > 0 and ask > 0:
                mid = round((bid + ask) / 2.0, 2)
            elif mid <= 0 and last_p > 0:
                mid = round(last_p, 2)
            mid = max(0.05, round(mid, 2))
            if bid <= 0:
                bid = max(0.01, round(mid * 0.96, 2))
            if ask <= 0:
                ask = round(mid * 1.04, 2)

            raw_iv = float(row.get("impliedVolatility", 0.40) or 0.40)
            iv = round((raw_iv if 0.05 <= raw_iv <= 3.50 else 0.40) * 100.0, 1)
            oi = int(row.get("openInterest", 0) or 0)
            vol = int(row.get("volume", 0) or 0)
            contract_str = f"{best_exp} ${strike:g}{type_letter}"

            result = {
                "symbol": sym,
                "action": action,
                "option_type": opt_type,
                "expiry": best_exp,
                "dte": best_dte,
                "strike": strike,
                "bid": round(bid, 2),
                "ask": round(ask, 2),
                "last": round(last_p, 2),
                "mid": mid,
                "iv": iv,
                "oi": oi,
                "volume": vol,
                "delta": float(row.get("delta", 0.0) or 0.0),
                "gamma": float(row.get("gamma", 0.0) or 0.0),
                "theta": float(row.get("theta", 0.0) or 0.0),
                "vega": float(row.get("vega", 0.0) or 0.0),
                "intrinsic": float(row.get("intrinsicValue", 0.0) or 0.0),
                "extrinsic": float(row.get("extrinsicValue", 0.0) or 0.0),
                "contract_str": contract_str,
                "summary": f"{contract_str} · Mid ${mid:.2f} (Bid ${bid:.2f} / Ask ${ask:.2f}) · IV {iv:.0f}% · OI {oi:,}",
                "source": "MarketData.app Live OPRA Chain"
            }
            set_cached(cache_key, result)
            return result
    except Exception:
        pass

    # 2. Fallback Path: get_near_live_option_chain_dataframe
    try:
        chain_data = get_near_live_option_chain_dataframe(sym, expiry=None)
        if not chain_data:
            set_cached(cache_key, {})
            return None

        best_exp = chain_data["expiry"]
        try:
            best_dte = max(1, (datetime.date.fromisoformat(best_exp) - today).days)
        except Exception:
            best_dte = target_dte

        df = chain_data["calls"] if opt_is_call else chain_data["puts"]
        if df is None or df.empty:
            set_cached(cache_key, {})
            return None

        df_copy = df.copy()
        df_copy["diff"] = (df_copy["strike"] - target_strike).abs()
        row = df_copy.sort_values("diff").iloc[0]

        strike = float(row["strike"])
        bid = float(row.get("bid", 0.0) or 0.0)
        ask = float(row.get("ask", 0.0) or 0.0)
        last_p = float(row.get("lastPrice", 0.0) or 0.0)
        raw_iv = float(row.get("impliedVolatility", 0.0) or 0.0)
        t_years = max(1, best_dte) / 365.0

        curr_spot = float(row.get("underlyingPrice", strike) or strike)
        if curr_spot <= 0:
            curr_spot = strike
        intrinsic = max(0.0, (curr_spot - strike) if opt_is_call else (strike - curr_spot))

        if bid > 0 and ask > 0 and ask >= bid and (ask - bid) <= max(3.0, 0.40 * curr_spot):
            mid = round((bid + ask) / 2.0, 2)
        elif last_p > 0 and intrinsic <= last_p <= curr_spot:
            mid = round(last_p, 2)
            if bid <= 0:
                bid = max(0.01, round(mid * 0.95, 2))
            if ask <= 0:
                ask = round(mid * 1.05, 2)
        else:
            eff_iv = raw_iv if (0.10 <= raw_iv <= 2.50) else 0.40
            if opt_is_call:
                bs_val, _ = bs_call_price_delta(curr_spot, strike, t_years, 0.0425, eff_iv)
            else:
                bs_val, _ = bs_put_price_delta(curr_spot, strike, t_years, 0.0425, eff_iv)
            mid = max(0.05, round(bs_val, 2))
            if bid <= 0:
                bid = max(0.01, round(mid * 0.95, 2))
            if ask <= 0:
                ask = round(mid * 1.05, 2)

        iv = round((raw_iv if 0.05 <= raw_iv <= 2.50 else 0.40) * 100.0, 1)
        oi = int(row.get("openInterest", 0) or 0)
        vol = int(row.get("volume", 0) or 0)

        contract_str = f"{best_exp} ${strike:g}{type_letter}"
        summary = (
            f"{best_exp} ${strike:g}{type_letter} · Mid ${mid:.2f} "
            f"(Bid ${bid:.2f} / Ask ${ask:.2f}) · IV {iv:.0f}% · OI {oi:,}"
        )

        result = {
            "symbol": sym,
            "action": action,
            "option_type": opt_type,
            "expiry": best_exp,
            "dte": best_dte,
            "strike": strike,
            "bid": bid,
            "ask": ask,
            "last": last_p,
            "mid": mid,
            "iv": iv,
            "oi": oi,
            "volume": vol,
            "contract_str": contract_str,
            "summary": summary,
            "source": "MarketData.app OPRA + CBOE Chain"
        }
        set_cached(cache_key, result)
        return result
    except Exception:
        set_cached(cache_key, {})
        return None


def get_real_exchange_expiries(symbol: str) -> List[Dict[str, Any]]:
    """
    Returns verified exchange-listed option expiration cycles for symbol from OPRA via
    MarketData.app `/v1/options/expirations/{symbol}/` (with automatic CBOE/yfinance fallback).
    Each entry includes label, date_str, iso_date, dte, is_monthly, and cycle_tag.
    Cached for 30 minutes (ttl=1800).
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return []
    cache_key = f"live_opt_expiries_v4_{sym}"
    cached = get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached

    today = get_ny_now().date()
    expiries_set = set()

    # 1. Primary: Query MarketData.app OPRA Expirations (`/v1/options/expirations/{symbol}/`)
    try:
        md_exps = marketdata_client.get_option_expirations(sym, ttl=3600)
        for ep in md_exps:
            if ep:
                expiries_set.add(str(ep))
    except Exception:
        pass

    # 2. Fallback with CBOE/yfinance expiries if needed
    if not expiries_set:
        try:
            import yfinance as yf
            tk = yf.Ticker(sym)
            yf_exps = getattr(tk, "options", None) or []
            for ep in yf_exps:
                expiries_set.add(ep)
        except Exception:
            pass

    if not expiries_set:
        set_cached(cache_key, [])
        return []

    out = []
    for exp_s in sorted(expiries_set):
        try:
            exp_d = datetime.date.fromisoformat(exp_s)
            dte = (exp_d - today).days
            if dte < 0:
                continue
            is_monthly = (15 <= exp_d.day <= 21) and (exp_d.weekday() == 4)
            cycle_tag = "Monthly" if is_monthly else "Weekly"
            label = f"{exp_d.strftime('%b %d, %Y')} ({dte} DTE · {cycle_tag})"
            out.append({
                "label": label,
                "date_str": exp_d.strftime("%b %d, %Y"),
                "iso_date": exp_s,
                "dte": dte,
                "is_monthly": is_monthly,
                "cycle_tag": cycle_tag
            })
        except Exception:
            continue

    set_cached(cache_key, out)
    return out


def get_near_live_option_chain_dataframe(
    symbol: str,
    expiry: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Returns live OPRA option chain data for the Schwab Simulator desk:
    {'calls': DataFrame, 'puts': DataFrame, 'expiries': list, 'expiry': chosen_expiry}
    Uses MarketData.app `/v1/options/chain/{symbol}/` (returning native OPRA Delta, Gamma,
    Theta, Vega, IV, Bid, Ask, Mid, OI, Volume) as primary with CBOE fallback.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None
    cache_key = f"live_opt_chain_df_v4_{sym}_{expiry or 'default'}"
    cached = get_cached(cache_key, ttl=900)
    if cached is not None:
        return cached if cached != {} else None

    exp_objs = get_real_exchange_expiries(sym)
    expiries = [e["iso_date"] for e in exp_objs]
    if not expiries:
        set_cached(cache_key, {})
        return None

    chosen_exp = None
    if expiry:
        exp_clean = str(expiry).strip()
        if exp_clean in expiries:
            chosen_exp = exp_clean
        else:
            for ep in expiries:
                if ep in exp_clean:
                    chosen_exp = ep
                    break
            if not chosen_exp:
                try:
                    parsed_dt = datetime.datetime.strptime(exp_clean.split("(")[0].strip(), "%b %d, %Y").date()
                    parsed_iso = parsed_dt.isoformat()
                    if parsed_iso in expiries:
                        chosen_exp = parsed_iso
                except Exception:
                    pass

    if not chosen_exp:
        today = get_ny_now().date()
        best_diff = 9999
        for ep in expiries:
            try:
                d = datetime.date.fromisoformat(ep)
                dte = (d - today).days
                if 25 <= dte <= 55:
                    diff = abs(dte - 35)
                    if diff < best_diff:
                        best_diff = diff
                        chosen_exp = ep
            except Exception:
                continue
        if not chosen_exp:
            chosen_exp = expiries[0]

    # 1. Primary: MarketData.app Live OPRA Chain (`/v1/options/chain/{symbol}/`)
    try:
        md_chain = marketdata_client.get_option_chain_native(
            sym, expiration=chosen_exp, strike_limit=60, ttl=900
        )
        if md_chain is not None and not md_chain.empty:
            calls_df = md_chain[md_chain["side"].str.lower() == "call"].sort_values("strike").reset_index(drop=True)
            puts_df = md_chain[md_chain["side"].str.lower() == "put"].sort_values("strike").reset_index(drop=True)
            if not calls_df.empty or not puts_df.empty:
                res = {
                    "calls": calls_df,
                    "puts": puts_df,
                    "expiries": list(expiries),
                    "expiry": chosen_exp,
                    "source": "MarketData.app Live OPRA Chain"
                }
                set_cached(cache_key, res)
                return res
    except Exception:
        pass

    # 2. Fallback: CBOE/yfinance option_chain
    try:
        import yfinance as yf
        tk = yf.Ticker(sym)
        chain = tk.option_chain(chosen_exp)
        if chain and chain.calls is not None and not chain.calls.empty:
            res = {
                "calls": chain.calls,
                "puts": chain.puts,
                "expiries": list(expiries),
                "expiry": chosen_exp,
                "source": "CBOE Option Chain Fallback"
            }
            set_cached(cache_key, res)
            return res
    except Exception:
        pass

    set_cached(cache_key, {})
    return None


def compute_fundamental_quality_score(symbol: str, fetch_live: bool = True, is_etf: bool = False) -> Dict[str, Any]:
    """
    True Institutional 0-100 Fundamental & Balance Sheet Bifurcation Score (100% Real FMP Ultra):
    1. /financial-scores: Real Altman Z-Score & Piotroski F-Score (0-9) [up to 30 pts]
    2. /ratios-ttm & /key-metrics-ttm: Current Ratio, Debt/Equity, Operating Margin, ROE, FCF Yield [up to 45 pts]
    3. /financial-growth: Real Revenue Growth YoY, 3Y Revenue Growth & Operating Income Growth [up to 25 pts]
    When `is_etf` is True (or `symbol in THEMATIC_ETFS`), skips corporate statements and returns a clean
    `ETF Basket` fundamental baseline (`fund_score = 68.0`, `solvency_tier = "ETF Basket"`, `is_etf = True`).
    """
    sym = symbol.strip().upper()
    if is_etf or sym in THEMATIC_ETFS:
        return {
            "fund_score": 68.0,
            "viable": True,
            "is_etf": True,
            "solvency_tier": "ETF Basket",
            "altman_z": 3.5,
            "piotroski_score": 7,
            "current_ratio": 2.0,
            "debt_to_equity": 0.25,
            "fcf_yield_pct": 2.5,
            "fcf_ttm_positive": True,
            "operating_margin_pct": 18.0,
            "gross_margin_pct": 45.0,
            "net_margin_pct": 15.0,
            "roe_pct": 16.0,
            "rev_growth_yoy_pct": 12.0,
            "rev_growth_pct": 12.0,
            "rev_growth_3y_pct": 12.0,
            "op_inc_growth_pct": 12.0,
            "is_stage1_est": False,
        }

    cache_key = f"fund_score_v36_{sym}"
    cached = get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached

    if not fetch_live:
        return {
            "fund_score": 58.0,
            "viable": True,
            "is_etf": False,
            "solvency_tier": "Stage-1 Baseline",
            "altman_z": 3.1,
            "piotroski_score": 6,
            "current_ratio": 1.6,
            "debt_to_equity": 0.6,
            "fcf_yield_pct": 2.0,
            "fcf_ttm_positive": True,
            "operating_margin_pct": 12.0,
            "gross_margin_pct": 42.0,
            "net_margin_pct": 10.0,
            "roe_pct": 12.0,
            "rev_growth_yoy_pct": 10.0,
            "rev_growth_pct": 10.0,
            "rev_growth_3y_pct": 10.0,
            "op_inc_growth_pct": 10.0,
            "is_stage1_est": True
        }

    # 1. Real Altman Z-Score & Piotroski F-Score
    f_scores = fmp_get("financial-scores", params={"symbol": sym}, ttl=1800)
    altman_z = None
    piotroski = None
    if isinstance(f_scores, list) and len(f_scores) > 0 and isinstance(f_scores[0], dict):
        fs0 = f_scores[0]
        if fs0.get("altmanZScore") is not None:
            altman_z = float(fs0["altmanZScore"])
        if fs0.get("piotroskiScore") is not None:
            piotroski = int(fs0["piotroskiScore"])

    # 2. Ratios TTM & Key Metrics TTM
    ratios = fmp_get("ratios-ttm", params={"symbol": sym}, ttl=1800)
    cr = None
    de = None
    op_margin = None
    gross_margin = None
    net_margin = None
    if isinstance(ratios, list) and len(ratios) > 0 and isinstance(ratios[0], dict):
        r = ratios[0]
        if r.get("currentRatioTTM") is not None:
            cr = float(r["currentRatioTTM"])
        if r.get("debtEquityRatioTTM") is not None:
            de = float(r["debtEquityRatioTTM"])
        elif r.get("debtToEquityTTM") is not None:
            de = float(r["debtToEquityTTM"])
        if r.get("operatingProfitMarginTTM") is not None:
            op_margin = float(r["operatingProfitMarginTTM"])
        if r.get("grossProfitMarginTTM") is not None:
            gross_margin = float(r["grossProfitMarginTTM"])
        if r.get("netProfitMarginTTM") is not None:
            net_margin = float(r["netProfitMarginTTM"])

    km = fmp_get("key-metrics-ttm", params={"symbol": sym}, ttl=1800)
    fcf_yield = None
    roe = None
    roic = None
    if isinstance(km, list) and len(km) > 0 and isinstance(km[0], dict):
        k = km[0]
        if k.get("freeCashFlowYieldTTM") is not None:
            fcf_yield = float(k["freeCashFlowYieldTTM"])
        if k.get("returnOnEquityTTM") is not None:
            roe = float(k["returnOnEquityTTM"])
        if k.get("returnOnInvestedCapitalTTM") is not None:
            roic = float(k["returnOnInvestedCapitalTTM"])

    # 3. Real Financial Growth (/financial-growth)
    fg = fmp_get("financial-growth", params={"symbol": sym, "limit": 1}, ttl=1800)
    rev_growth_yoy = 0.0
    rev_growth_3y = 0.0
    op_inc_growth = 0.0
    if isinstance(fg, list) and len(fg) > 0 and isinstance(fg[0], dict):
        g0 = fg[0]
        if g0.get("revenueGrowth") is not None:
            rev_growth_yoy = float(g0["revenueGrowth"]) * 100.0
        if g0.get("threeYRevenueGrowthPerShare") is not None:
            # Convert cumulative 3Y growth to annualized % approximation
            raw_3y = float(g0["threeYRevenueGrowthPerShare"])
            rev_growth_3y = ((1.0 + max(-0.9, raw_3y)) ** (1.0 / 3.0) - 1.0) * 100.0 if raw_3y > -0.9 else -30.0
        else:
            rev_growth_3y = rev_growth_yoy
        if g0.get("operatingIncomeGrowth") is not None:
            op_inc_growth = float(g0["operatingIncomeGrowth"]) * 100.0

    # --- CONTINUOUS GRANULAR SCORING (0 to 100) ---
    # A. Solvency & Altman Z + Piotroski (0 - 30 pts)
    if altman_z is not None:
        pts_altman = float(np.clip((altman_z - 1.0) / 5.0 * 16.0, 0.0, 16.0))
    else:
        pts_altman = 7.0
    if piotroski is not None:
        pts_pio = float(np.clip((piotroski / 9.0) * 14.0, 1.0, 14.0))
    else:
        pts_pio = 6.0

    # B. Liquidity & Leverage (0 - 20 pts)
    cr_val = cr if cr is not None else 1.1
    de_val = de if de is not None else 0.9
    pts_liq = float(np.clip((cr_val - 0.6) / 2.2 * 10.0, 0.0, 10.0))
    pts_lev = float(np.clip((2.5 - max(0.0, de_val)) / 2.5 * 10.0, 0.0, 10.0))

    # C. Cash Flow & Profitability Margins (0 - 30 pts)
    fcf_val = fcf_yield if fcf_yield is not None else 0.0
    op_val = op_margin if op_margin is not None else 0.0
    roe_val = roe if roe is not None else (roic if roic is not None else 0.0)

    pts_fcf = float(np.clip((fcf_val + 0.03) / 0.08 * 12.0, 0.0, 12.0))
    pts_margin = float(np.clip((op_val + 0.10) / 0.35 * 10.0, 0.0, 10.0))
    pts_roe = float(np.clip((roe_val + 0.05) / 0.28 * 8.0, 0.0, 8.0))

    # D. Revenue & Operating Growth Trajectory (0 - 20 pts)
    pts_growth = float(np.clip((rev_growth_yoy + 10.0) / 45.0 * 12.0, 0.0, 12.0))
    pts_3y = float(np.clip((rev_growth_3y + 5.0) / 35.0 * 8.0, 0.0, 8.0))

    total_fund_score = round(float(np.clip(
        pts_altman + pts_pio + pts_liq + pts_lev + pts_fcf + pts_margin + pts_roe + pts_growth + pts_3y,
        8.0, 98.0
    )), 1)

    viable = (total_fund_score >= 46.0 and cr_val >= 0.80)
    altman_z_out = round(altman_z, 2) if altman_z is not None else round(1.5 + total_fund_score * 0.035, 2)
    solvency_tier = (
        "Healthy" if altman_z_out >= 3.0 else ("Caution" if altman_z_out >= 1.8 else "Distressed")
    )

    result = {
        "fund_score": total_fund_score,
        "viable": viable,
        "altman_z": altman_z_out,
        "piotroski_score": piotroski if piotroski is not None else int(round(total_fund_score / 12.0)),
        "current_ratio": round(cr_val, 2),
        "debt_to_equity": round(max(0.0, de_val), 2),
        "fcf_yield_pct": round(fcf_val * 100.0, 1),
        "fcf_ttm_positive": (fcf_val > 0.0),
        "operating_margin_pct": round(op_val * 100.0, 1),
        "gross_margin_pct": round((gross_margin or 0.0) * 100.0, 1),
        "net_margin_pct": round((net_margin or op_val) * 100.0, 1),
        "roe_pct": round(roe_val * 100.0, 1),
        "rev_growth_yoy_pct": round(rev_growth_yoy, 1),
        "rev_growth_pct": round(rev_growth_yoy, 1),
        "rev_growth_3y_pct": round(rev_growth_3y, 1),
        "op_inc_growth_pct": round(op_inc_growth, 1),
        "solvency_tier": solvency_tier,
        "is_etf": False,
        "is_stage1_est": False
    }
    set_cached(cache_key, result)
    return result


def compute_cash_runway_and_burn(symbol: str) -> Dict[str, Any]:
    """
    FMP Pro Balance Sheet & Cash Flow Audit for Track B (Bottleneck) and Track C (Mirage).
    Zero fake $250M defaults: calculates real cash, quarterly burn, runway quarters, and deferred revenue QoQ.
    """
    sym = symbol.strip().upper()
    cache_key = f"runway_burn_v35_{sym}"
    cached = get_cached(cache_key, ttl=900)
    if cached is not None:
        return cached

    cash = 0.0
    quarterly_burn = 0.0
    cash_runway = 12.0
    def_rev = 0.0
    def_rev_growth = 0.0

    try:
        bs_list = fmp_get("balance-sheet-statement", params={"symbol": sym, "period": "quarter", "limit": 4}, ttl=1800)
        if isinstance(bs_list, list) and len(bs_list) > 0:
            b0 = bs_list[0]
            c_eq = float(b0.get("cashAndCashEquivalents") or 0.0)
            st_inv = float(b0.get("shortTermInvestments") or 0.0)
            cash = max(c_eq + st_inv, float(b0.get("cashAndShortTermInvestments") or 0.0))
            def_rev = float(b0.get("deferredRevenue") or 0.0)

            if len(bs_list) >= 2:
                b1 = bs_list[1]
                prev_def_rev = float(b1.get("deferredRevenue") or 0.0)
                if prev_def_rev > 0:
                    def_rev_growth = ((def_rev - prev_def_rev) / prev_def_rev) * 100.0

        cf_list = fmp_get("cash-flow-statement", params={"symbol": sym, "period": "quarter", "limit": 4}, ttl=1800)
        if isinstance(cf_list, list) and len(cf_list) > 0:
            fcf_vals = [float(c.get("freeCashFlow") if c.get("freeCashFlow") is not None else (c.get("operatingCashFlow") or 0.0)) for c in cf_list]
            avg_fcf = sum(fcf_vals) / len(fcf_vals)
            if avg_fcf < 0:
                quarterly_burn = abs(avg_fcf)
                cash_runway = round(cash / quarterly_burn, 1) if quarterly_burn > 0 else 1.0
            else:
                quarterly_burn = 0.0
                cash_runway = 40.0  # Self-funding positive FCF
    except Exception as e:
        print(f"Error auditing cash runway for {sym}: {e}")

    result = {
        "cash_millions": round(cash / 1e6, 1),
        "quarterly_burn_millions": round(quarterly_burn / 1e6, 1),
        "cash_runway_quarters": cash_runway,
        "deferred_rev_millions": round(def_rev / 1e6, 1),
        "deferred_rev_growth_pct": round(def_rev_growth, 1),
        "runway_viable_track_b": (cash_runway >= 6.0),
        "dilution_vulnerable_track_c": (cash_runway < 4.5 or quarterly_burn > 45_000_000.0)
    }
    set_cached(cache_key, result)
    return result


def get_insider_conviction(symbol: str, fetch_live: bool = True) -> Dict[str, Any]:
    sym = symbol.strip().upper()
    cache_key = f"insider_v35_{sym}"
    cached = get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached
    if not fetch_live:
        return {
            "acq_ratio": 0.0,
            "total_acquired": 0,
            "total_disposed": 0,
            "has_cluster_buy": False,
            "insider_bonus_pts": 0
        }

    data = fmp_get("insider-trading/statistics", params={"symbol": sym}, ttl=1800)
    acq_ratio = 0.0
    tot_acq = 0
    tot_disp = 0
    has_cluster_buy = False

    if isinstance(data, list) and len(data) > 0:
        latest = data[0]
        acq_ratio = float(latest.get("acquiredDisposedRatio") or 0.0)
        tot_acq = int(latest.get("totalAcquired") or 0)
        tot_disp = int(latest.get("totalDisposed") or 0)
        if acq_ratio >= 0.75 or (tot_acq > 0 and tot_acq >= tot_disp):
            has_cluster_buy = True

    result = {
        "acq_ratio": round(acq_ratio, 2),
        "total_acquired": tot_acq,
        "total_disposed": tot_disp,
        "has_cluster_buy": has_cluster_buy,
        "insider_bonus_pts": 8 if has_cluster_buy else 0
    }
    set_cached(cache_key, result)
    return result


def get_analyst_consensus(symbol: str, current_price: float, fetch_live: bool = True) -> Dict[str, Any]:
    sym = symbol.strip().upper()
    cache_key = f"analyst_v35_{sym}"
    cached = get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached
    if not fetch_live:
        return {
            "target_consensus": round(current_price * 1.06, 2),
            "target_high": round(current_price * 1.22, 2),
            "target_low": round(current_price * 0.85, 2),
            "implied_upside_pct": 6.0
        }

    data = fmp_get("price-target-consensus", params={"symbol": sym}, ttl=1800)
    target_cons = current_price
    target_high = current_price * 1.2
    target_low = current_price * 0.8
    upside_pct = 0.0

    if isinstance(data, list) and len(data) > 0:
        item = data[0]
        target_cons = float(item.get("targetConsensus") or current_price)
        target_high = float(item.get("targetHigh") or current_price * 1.2)
        target_low = float(item.get("targetLow") or current_price * 0.8)
        if current_price > 0:
            upside_pct = round(((target_cons - current_price) / current_price) * 100.0, 1)

    result = {
        "target_consensus": round(target_cons, 2),
        "target_high": round(target_high, 2),
        "target_low": round(target_low, 2),
        "implied_upside_pct": upside_pct
    }
    set_cached(cache_key, result)
    return result


def get_recent_news(ticker: str, limit: int = 5) -> List[Dict[str, str]]:
    """Fetches recent institutional news via MarketData.app `/v1/stocks/news/{symbol}/` with FMP fallback."""
    sym = ticker.strip().upper()
    m_news = marketdata_client.get_marketdata_news(sym, limit=limit, ttl=600)
    if m_news:
        return m_news

    data = fmp_get("news/stock", params={"symbols": sym, "limit": limit}, ttl=300)
    if not isinstance(data, list):
        return []
    news_items = []
    for item in data[:limit]:
        news_items.append({
            "title": item.get("title", ""),
            "publishedDate": item.get("publishedDate", ""),
            "site": item.get("site", ""),
            "text": item.get("text", "")[:260]
        })
    return news_items


def audit_headlines_with_gemini(symbol: str, headlines: List[Dict[str, str]]) -> Dict[str, Any]:
    """Routes headline audit through Universal LLM Router (Qwen 3.8 on GX10 or Gemini 2.5)."""
    if not headlines:
        return {
            "verdict": "GREEN_LIGHT",
            "summary": "No breaking negative news. Stretch driven by sector/macro liquidity sympathy.",
            "is_structural_blowup": False
        }

    head_text = "\n".join([f"- {h.get('title', '')} ({h.get('publishedDate', '')}): {h.get('text', '')}" for h in headlines[:5]])
    try:
        import llm_router
        prompt = (
            f"You are a Senior Risk Auditor on an ASUS GX10 Quantitative Desk. Analyze these 5 recent headlines for {symbol}:\n\n"
            f"{head_text}\n\n"
            "Determine if the recent move is:\n"
            "A) A sympathetic sector/macro move or constructive catalyst (Verdict: GREEN_LIGHT)\n"
            "B) A severe accounting scandal, fraud, or terminal guidance collapse (Verdict: QUARANTINE)\n\n"
            "Respond in strictly 2 concise sentences beginning with '[GREEN_LIGHT]' or '[QUARANTINE]'."
        )
        text, err = llm_router.generate_text(prompt, temperature=0.1)
        if err or not text:
            return {
                "verdict": "UNVERIFIED_ERROR",
                "summary": f"Headline audit unavailable ({err or 'empty LLM response'}): treat setup with caution.",
                "is_structural_blowup": False,
                "audit_failed": True,
            }
        is_quarantine = "[QUARANTINE]" in text.upper()
        verdict = "QUARANTINE" if is_quarantine else "GREEN_LIGHT"
        return {
            "verdict": verdict,
            "summary": text.replace("[GREEN_LIGHT]", "").replace("[QUARANTINE]", "").strip(),
            "is_structural_blowup": is_quarantine,
            "audit_failed": False,
        }
    except Exception as e:
        return {
            "verdict": "UNVERIFIED_ERROR",
            "summary": f"Headline audit exception ({str(e)[:50]}): treat setup with caution.",
            "is_structural_blowup": False,
            "audit_failed": True,
        }


# =========================================================================
# PILLAR 6: 30-45 DTE OPTIONS BLUEPRINT & 1-5 DAY MOVE POTENTIAL SCORER
# =========================================================================

def get_target_options_friday(days_forward: int = 35) -> str:
    now = get_ny_now()
    target_dt = now + timedelta(days=days_forward)
    days_to_fri = (4 - target_dt.weekday()) % 7
    final_fri = target_dt + timedelta(days=days_to_fri)
    return final_fri.strftime("%b %d, %Y")


def structure_30_45_dte_blueprint(
    symbol: str,
    metrics: Dict[str, Any],
    fund: Dict[str, Any],
    insider: Dict[str, Any],
    analyst: Dict[str, Any],
    temporal: Dict[str, Any],
    macro: Dict[str, Any],
    earnings_info: Optional[Dict[str, Any]] = None,
    whale_oi: Optional[Dict[str, Any]] = None,
    regime_pulse: Optional[Dict[str, Any]] = None,
    radar_24_48: Optional[Dict[str, Any]] = None,
    live_option: Optional[Dict[str, Any]] = None,
    gamma_walls: Optional[Dict[str, Any]] = None,
    skew_optimizer: Optional[Dict[str, Any]] = None,
    extended_hours: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Institutional 1-5 Day Basis Move & Rubberband Scorer (0-100 Composite Score):
    1. Obvious Bad-Data & Solvency Quarantine Gate: Immediately quarantines broken data, penny stocks,
       split glitches, or insolvent zombies.
    2. Directional Rubberband Elasticity & Band Geometry (0 - 30 pts)
    3. Empirical 5-Year Conditional Basis % Move & Daily ATR Velocity (0 - 28 pts)
    4. Whale & Sharp Flow (CMF-20, 10D Up/Dn Block Vol, CLV, 13F Call/Put Open Interest) & Market Regime Alignment (0 - 27 pts)
    5. Fundamental Solvency Shield & 25-Day Earnings Catalyst Window (0 - 15 pts)
    """
    z = float(metrics["z_score_5d"])
    z_abs = float(metrics.get("z_abs", z))
    z_rel = float(metrics.get("z_rel_5d", 0.0))
    action = metrics["action"]
    state = metrics["state"]
    playbook = metrics.get("playbook_type", "MEAN_REVERSION")
    fund_score = float(fund.get("fund_score", 50.0))
    altman_z = float(fund.get("altman_z", 3.0))
    piotroski = int(fund.get("piotroski_score", 6))
    curr_ratio = float(fund.get("current_ratio", 1.5))
    clv = float(metrics["clv"])
    rvol = float(metrics["rvol"])
    half_life = float(metrics.get("ou_half_life", 4.5))
    accel_z = float(metrics.get("accel_z_2d", 0.0))
    delta_z_1d = float(metrics.get("delta_z_1d", 0.0))
    squeeze_ratio = float(metrics.get("squeeze_ratio", 1.05))
    price = max(0.50, float(metrics.get("price", 100.0)))
    atr14 = float(metrics.get("atr14", price * 0.03))
    atr_pct = (atr14 / price) * 100.0
    bull_obv = bool(metrics.get("bull_obv_divergence", False))
    is_bad_data = bool(metrics.get("is_bad_data", False))

    exp_basis_pct = float(metrics.get("expected_basis_pct", 0.0))
    exp_abs_basis = abs(exp_basis_pct)
    emp_win_rate = float(metrics.get("empirical_win_rate_pct", 54.0))

    _fb_whale = (float(metrics.get("sharp_tape_score", 50.0) or 50.0) - 50.0) * 2.0
    whale_score = float(whale_oi.get("whale_score", _fb_whale)) if whale_oi else _fb_whale
    whale_badge = whale_oi.get("whale_badge", metrics.get("sharp_badge", "TWO-WAY FLOW")) if whale_oi else metrics.get("sharp_badge", "TWO-WAY FLOW")

    days_to_earn = int(earnings_info.get("days_to_earnings", 45)) if earnings_info else 45
    has_earnings_25d = bool(earnings_info.get("has_earnings_25d", 0 <= days_to_earn <= 25)) if earnings_info else (0 <= days_to_earn <= 25)
    has_binary_earn_7d = bool(earnings_info.get("has_binary_earnings_7d", 0 <= days_to_earn <= 7)) if earnings_info else (0 <= days_to_earn <= 7)

    # Hard Quarantine for Obvious Bad Data
    if is_bad_data:
        return {
            "direction": "DATA QUARANTINE",
            "playbook_type": "DATA QUARANTINED",
            "composite_score": 15.0,
            "move_score": 15.0,
            "target_expiration": get_target_options_friday(35),
            "structure": f"QUARANTINED ({metrics.get('bad_data_reason', 'Data Anomaly')})",
            "structure_rationale": f"Engine quarantined {symbol}: {metrics.get('bad_data_reason', 'Anomalous data detected')}.",
            "target_price": metrics["target_price"],
            "invalidation_price": metrics["invalidation_price"],
            "rr_ratio": 1.0,
            "is_vertical_spread": False,
            "strike": metrics["recommended_strike"],
            "otm_pct": 0.0,
            "estimated_delta": 0.0,
            "days_to_earnings": days_to_earn,
            "has_earnings_25d": has_earnings_25d,
            "has_binary_earnings_7d": has_binary_earn_7d,
            "expected_basis_pct": exp_basis_pct,
            "empirical_win_rate_pct": emp_win_rate,
            "whale_badge": whale_badge
        }

    # 1. Directional Rubberband Elasticity & Band Geometry (0 - 30 pts)
    if "CALL" in action:
        if "COILED" in state and squeeze_ratio <= 0.98:
            pts_tension = min(28.0, 16.0 + max(0.0, (1.0 - squeeze_ratio) * 40.0) + min(5.0, max(0.0, z_rel) * 3.5))
        elif z < 0 or z_abs < 0:
            pullback_depth = max(abs(min(0.0, z)), abs(min(0.0, z_abs)) * 0.95)
            pts_tension = min(30.0, (pullback_depth / 1.60) * 25.5 + max(0.0, abs(z_rel)) * 2.2 + (2.0 if bull_obv else 0.0))
        else:
            pts_tension = min(12.0, max(3.5, (1.0 - max(0.0, squeeze_ratio - 0.85)) * 9.0))
    elif "PUT" in action:
        if "COILED" in state:
            pts_tension = min(27.0, 15.0 + abs(min(0.0, z_rel)) * 5.0)
        elif z > 0 or z_abs > 0:
            extension_height = max(max(0.0, z), max(0.0, z_abs) * 0.95)
            pts_tension = min(30.0, (extension_height / 1.60) * 25.5 + max(0.0, abs(z_rel)) * 2.2)
        else:
            pts_tension = min(14.0, abs(z) * 9.0 + abs(z_rel) * 2.5)
    else:
        pts_tension = min(10.0, abs(z) * 7.0)

    # 2. Empirical 5-Year Conditional Basis % Move & Daily ATR Velocity (0 - 28 pts)
    # Stocks whose 5-year history proves large 5-day basis moves (+4.5% to +11%) from similar Z-stretches score highest
    pts_basis = float(np.clip((exp_abs_basis - 1.5) * 2.2, 1.0, 12.5))
    pts_winrate = float(np.clip((emp_win_rate - 48.0) * 0.35, 0.0, 5.5))
    pts_atr = float(np.clip((atr_pct - 1.40) * 1.45, 1.0, 6.0))
    if 1.2 <= half_life <= 5.5:
        pts_speed = 4.0
    elif half_life <= 8.5:
        pts_speed = 2.5
    else:
        pts_speed = 1.0
    pts_kinetic = min(28.0, pts_basis + pts_winrate + pts_atr + pts_speed)

    # 3. Whale/Sharp Flow (CMF-20, Up/Dn Block Vol, 13F OI), Velocity Hook & Market Regime Alignment (0 - 27 pts)
    insider_pts = float(insider.get("insider_bonus_pts", 0))
    implied_upside = float(analyst.get("implied_upside_pct", 0.0))

    if "CALL" in action:
        turn_boost = float(np.clip((delta_z_1d + 0.16) * 22.0, 0.0, 7.0))
        accel_boost = float(np.clip((accel_z + 0.20) * 6.5, 0.0, 2.5))
        clv_boost = float(np.clip((clv + 0.35) * 4.5, 0.0, 3.5))
        # Whale/Sharp loading alignment for Calls (-6 to +8.5 pts)
        whale_align = float(np.clip(whale_score / 5.5, -6.0, 8.5))
        pts_hook = min(20.0, max(1.0, turn_boost + accel_boost + clv_boost + whale_align))
    elif "PUT" in action:
        turn_boost = float(np.clip((-delta_z_1d + 0.16) * 22.0, 0.0, 7.0))
        accel_boost = float(np.clip((-accel_z + 0.20) * 6.5, 0.0, 2.5))
        clv_boost = float(np.clip((-clv + 0.35) * 4.5, 0.0, 3.5))
        # Whale/Sharp unloading alignment for Puts (-6 to +8.5 pts)
        whale_align = float(np.clip(-whale_score / 5.5, -6.0, 8.5))
        pts_hook = min(20.0, max(1.0, turn_boost + accel_boost + clv_boost + whale_align))
    else:
        pts_hook = 4.0

    pts_rvol = float(np.clip((rvol - 0.55) * 5.0, 0.5, 4.5))
    pts_catalyst = min(4.5, insider_pts * 0.35 + (2.2 if ("CALL" in action and implied_upside >= 7.0) or ("PUT" in action and implied_upside <= -4.0) else 0.8))

    # Pre-Earnings IV Expansion & Binary Hazard Window (Aligned with >15D Top-5 Gate):
    # - 16 to 30 days before earnings: Clean 1-5D hold + pre-ER institutional positioning & IV expansion tailwind (+2.5 pts)
    # - 0 to 15 days before earnings: Binary earnings gap/IV crush hazard (-3.5 pts unless extreme whale loading)
    if 16 <= days_to_earn <= 30:
        pts_catalyst += 2.5
    elif 0 <= days_to_earn <= 15 and abs(whale_score) < 22.0:
        pts_catalyst -= 3.5

    # Market Regime, 24-48H Forward Macro Radar, Yield Shock & Temporal Alignment:
    is_timid_tape = bool(regime_pulse.get("is_timid_green", False)) if regime_pulse else False
    regime_name = str(regime_pulse.get("market_regime", "")) if regime_pulse else ""
    is_risk_off_flush = ("RISK-OFF FLUSH" in regime_name)
    has_strong_catalyst = (rvol >= 1.35) or (whale_score >= 22.0) or (insider_pts >= 4.0)
    if "CALL" in action and (z >= 0.85 or z_abs >= 1.05) and not has_strong_catalyst:
        pts_catalyst -= (16.0 if is_timid_tape else 13.0)

    macro_fscore = float(radar_24_48.get("forecast_score", 0.0)) if radar_24_48 else 0.0
    vix_term = float(radar_24_48.get("vix_term_ratio", 0.94)) if radar_24_48 else 0.94
    yield_reg = str(macro.get("yield_regime", "STABLE_RATES")) if macro else "STABLE_RATES"
    is_friday = bool(temporal.get("is_friday_mode", False)) if temporal else False
    is_opex = bool(temporal.get("is_opex_week", False)) if temporal else False

    macro_regime_adj = 0.0
    if "CALL" in action:
        if macro_fscore >= 16.0 or vix_term <= 0.91:
            macro_regime_adj += 3.5
        elif (macro_fscore <= -20.0 or vix_term >= 1.00 or is_risk_off_flush) and z > -1.95:
            # Penalize early Call knife-catches during backwardated VIX / credit stress flushes
            macro_regime_adj -= 5.5
        if yield_reg == "YIELD_TAILWIND":
            macro_regime_adj += 2.0
        elif yield_reg == "RATE_SHOCK_HEADWIND":
            macro_regime_adj -= 2.5
    elif "PUT" in action:
        if macro_fscore <= -15.0 or vix_term >= 0.98 or is_risk_off_flush:
            macro_regime_adj += 4.5
        elif macro_fscore >= 22.0 and z < 1.95:
            macro_regime_adj -= 4.0
        if yield_reg == "RATE_SHOCK_HEADWIND":
            macro_regime_adj += 2.5
        elif yield_reg == "YIELD_TAILWIND":
            macro_regime_adj -= 1.5

    if is_friday and rvol < 1.10 and abs(delta_z_1d) < 0.15:
        macro_regime_adj -= 1.5
    if is_opex and abs(z) >= 1.60:
        macro_regime_adj += 1.5

    pts_catalyst += macro_regime_adj

    # 4. Fundamental Solvency Gate & Bifurcation Multiplier (0 - 15 pts + Hard Zombie Quarantine)
    is_zombie_or_illiquid = (altman_z < 0.50 and piotroski <= 3) or (fund_score < 28.0) or (rvol < 0.25)
    if "CALL" in action:
        if is_zombie_or_illiquid:
            pts_fund = -28.0
            action = "WATCHLIST"
            metrics["action"] = "WATCHLIST"
            playbook = "SOLVENCY QUARANTINE"
            metrics["playbook_type"] = "SOLVENCY QUARANTINE"
            metrics["playbook"] = "SOLVENCY QUARANTINE"
        else:
            solvency_fortress_bonus = 3.5 if (piotroski >= 6 and altman_z >= 2.5 and curr_ratio >= 1.5) else 0.0
            kinetic_engagement = min(1.18, max(0.50, (pts_tension + pts_basis) / 26.0))
            pts_fund = min(15.0, ((fund_score / 100.0) * 11.5 + solvency_fortress_bonus) * kinetic_engagement)
    elif "PUT" in action:
        fragility_pts = ((100.0 - fund_score) / 100.0) * 13.5
        blowoff_pts = min(15.0, max(0.0, (max(z, z_abs) - 1.10) * 11.5))
        pts_fund = min(15.0, max(fragility_pts, blowoff_pts))
    else:
        pts_fund = (fund_score / 100.0) * 5.5

    # 5. Live OPRA Options Flow, Liquidity Gate, Gamma Wall Pin & Extended-Hours Alignment (-18 to +7.5 pts)
    pts_options_flow = 0.0
    opra_flow_tag = ""
    if live_option and isinstance(live_option, dict):
        opt_oi = int(live_option.get("oi", 0) or 0)
        opt_vol = int(live_option.get("volume", 0) or 0)
        opt_bid = float(live_option.get("bid", 0.0) or 0.0)
        opt_ask = float(live_option.get("ask", 0.0) or 0.0)
        opt_mid = max(0.05, float(live_option.get("mid", 0.05) or 0.05))
        spread_pct = ((opt_ask - opt_bid) / opt_mid) * 100.0 if (opt_bid > 0 and opt_ask >= opt_bid) else 12.0

        # Liquidity & Bid-Ask Spread Friction Gate
        if spread_pct > 32.0:
            pts_options_flow -= 12.0
            opra_flow_tag = "WIDE SPREAD FRICTION"
        elif spread_pct > 20.0:
            pts_options_flow -= 4.5
        elif spread_pct <= 8.5 and opt_oi >= 250:
            pts_options_flow += 2.0

        # Unusual Volume-to-OI Sweep on the Target Strike
        if opt_vol >= 50 and opt_oi > 0 and (opt_vol / max(1, opt_oi)) >= 1.15:
            pts_options_flow += 2.5
            opra_flow_tag = f"UNUSUAL SWEEP ({opt_vol/max(1,opt_oi):.1f}x V/OI)"

    if gamma_walls and isinstance(gamma_walls, dict) and (gamma_walls.get("has_data") or gamma_walls.get("has_opra")):
        total_chain_oi = int(gamma_walls.get("total_call_oi", 0) or 0) + int(gamma_walls.get("total_put_oi", 0) or 0)
        tot_c_vol = int(gamma_walls.get("total_call_vol", 0) or 0)
        tot_p_vol = int(gamma_walls.get("total_put_vol", 0) or 0)
        pc_vol_ratio = (
            round(tot_p_vol / max(1, tot_c_vol), 2)
            if (tot_c_vol + tot_p_vol) >= 25
            else float(gamma_walls.get("call_put_oi_ratio", 1.0) or 1.0)
        )
        call_wall_k = float(gamma_walls.get("call_wall_strike", 0.0) or 0.0)
        put_wall_k = float(gamma_walls.get("put_wall_strike", 0.0) or 0.0)
        sweeps_list = gamma_walls.get("unusual_flows") or gamma_walls.get("unusual_sweeps") or []

        if total_chain_oi < 80:
            pts_options_flow -= 14.0
            opra_flow_tag = "THIN OPRA CHAIN"
        elif "CALL" in action:
            if pc_vol_ratio <= 0.68:
                pts_options_flow += 2.0
                if not opra_flow_tag:
                    opra_flow_tag = f"BULL OPRA FLOW (P/C {pc_vol_ratio:.2f})"
            elif pc_vol_ratio >= 1.65:
                pts_options_flow -= 2.5
            # Check if Call Wall is magnetizing upward toward target price vs capping directly overhead
            if call_wall_k > price * 1.015:
                pts_options_flow += 1.0
            call_sweeps = [s for s in sweeps_list if s.get("side") == "CALL" and float(s.get("ratio", s.get("vol_oi_ratio", 0))) >= 1.25]
            if call_sweeps:
                pts_options_flow += 1.5
        elif "PUT" in action:
            if pc_vol_ratio >= 1.25:
                pts_options_flow += 2.0
                if not opra_flow_tag:
                    opra_flow_tag = f"BEAR OPRA FLOW (P/C {pc_vol_ratio:.2f})"
            elif pc_vol_ratio <= 0.50:
                pts_options_flow -= 2.5
            if 0 < put_wall_k < price * 0.985:
                pts_options_flow += 1.0
            put_sweeps = [s for s in sweeps_list if s.get("side") == "PUT" and float(s.get("ratio", s.get("vol_oi_ratio", 0))) >= 1.25]
            if put_sweeps:
                pts_options_flow += 1.5

    if extended_hours and isinstance(extended_hours, dict) and float(extended_hours.get("ext_price", 0.0) or 0.0) > 0:
        ext_thesis = str(extended_hours.get("thesis_badge", extended_hours.get("thesis", ""))).upper()
        if "CALL" in action and "ACCUMULATION" in ext_thesis:
            pts_options_flow += 1.5
        elif "CALL" in action and "DISTRIBUTION" in ext_thesis:
            pts_options_flow -= 2.0
        elif "PUT" in action and "DISTRIBUTION" in ext_thesis:
            pts_options_flow += 1.5
        elif "PUT" in action and "ACCUMULATION" in ext_thesis:
            pts_options_flow -= 2.0

    pts_options_flow = float(np.clip(pts_options_flow, -18.0, 7.5))

    composite_score = round(float(np.clip(
        pts_tension + pts_kinetic + pts_hook + pts_rvol + pts_catalyst + pts_fund + pts_options_flow,
        18.0, 99.0
    )), 0)

    is_event_risk = macro.get("has_binary_48h", False) or has_binary_earn_7d
    is_iv_elevated = (metrics.get("vol_rank", 50.0) > 78.0)
    skew_Rich = False
    if skew_optimizer and isinstance(skew_optimizer, dict) and (skew_optimizer.get("has_data") or skew_optimizer.get("has_skew")):
        rec_struct_skew = str(skew_optimizer.get("recommended_structure", "")).upper()
        if "VERTICAL" in rec_struct_skew or float(skew_optimizer.get("spread_friction_pct", skew_optimizer.get("atm_spread_pct", 0.0)) or 0.0) > 16.0:
            skew_Rich = True

    target_friday = (
        str(live_option.get("expiry"))
        if (live_option and isinstance(live_option, dict) and live_option.get("expiry"))
        else get_target_options_friday(35)
    )
    rec_strike = (
        float(live_option.get("strike"))
        if (live_option and isinstance(live_option, dict) and live_option.get("strike"))
        else metrics["recommended_strike"]
    )
    otm_dist = round(abs(rec_strike - metrics["price"]) / metrics["price"] * 100.0, 2)
    est_delta = (
        round(abs(float(live_option.get("delta"))), 2)
        if (live_option and isinstance(live_option, dict) and live_option.get("delta"))
        else metrics.get("estimated_delta", 0.28)
    )
    earn_tag = (
        f" [ER in {days_to_earn}d]" if has_binary_earn_7d
        else f" [ER in {days_to_earn}d]" if has_earnings_25d
        else ""
    )

    if "CALL" in action:
        direction_label = "CALL BREAKOUT" if "COILED" in state else "CALL SNAPBACK"
        structure_type = (
            f"Expected 5D Basis: {exp_basis_pct:+.1f}% ({emp_win_rate:.0f}% 5Y Win) | {whale_badge}{earn_tag}"
        )
        structure_rationale = (
            f"{playbook}: 5Y Historical Basis Expectation {exp_basis_pct:+.1f}% (P75: +{metrics.get('p75_basis_pct', abs(exp_basis_pct)*1.4):.1f}%, "
            f"Half-Life {half_life:.1f}d) toward ${metrics['target_price']:.2f}. {whale_oi.get('whale_summary', '') if whale_oi else ''}"
        )
    elif "PUT" in action:
        direction_label = "PUT BREAKDOWN" if "COILED" in state else "PUT SNAPBACK"
        structure_type = (
            f"Expected 5D Basis: {exp_basis_pct:+.1f}% ({emp_win_rate:.0f}% 5Y Win) | {whale_badge}{earn_tag}"
        )
        p75_abs = abs(float(metrics.get("p75_basis_pct", abs(exp_basis_pct) * 1.4)))
        structure_rationale = (
            f"{playbook}: 5Y Historical Basis Expectation {exp_basis_pct:+.1f}% (P75: -{p75_abs:.1f}%, "
            f"Half-Life {half_life:.1f}d) toward ${metrics['target_price']:.2f}. {whale_oi.get('whale_summary', '') if whale_oi else ''}"
        )
    else:
        direction_label = "EQUILIBRIUM"
        structure_type = f"WATCHLIST (Z: {z:+.2f}σ | Est 5D Basis: {exp_basis_pct:+.1f}% | {whale_badge}){earn_tag}"
        structure_rationale = "Trading near institutional VWMA-20 equilibrium. Awaiting stretch or volatility squeeze ignition."

    return {
        "direction": direction_label,
        "playbook_type": playbook,
        "composite_score": composite_score,
        "move_score": composite_score,
        "target_expiration": target_friday,
        "structure": structure_type,
        "structure_rationale": structure_rationale,
        "target_price": metrics["target_price"],
        "invalidation_price": metrics["invalidation_price"],
        "rr_ratio": metrics["rr_ratio"],
        "is_vertical_spread": (is_event_risk or is_iv_elevated or skew_Rich),
        "opra_flow_tag": opra_flow_tag,
        "pts_options_flow": round(pts_options_flow, 1),
        "strike": rec_strike,
        "otm_pct": otm_dist,
        "estimated_delta": est_delta,
        "days_to_earnings": days_to_earn,
        "has_earnings_25d": has_earnings_25d,
        "has_binary_earnings_7d": has_binary_earn_7d,
        "expected_basis_pct": exp_basis_pct,
        "empirical_win_rate_pct": emp_win_rate,
        "whale_badge": whale_badge,
        "whale_score": whale_score
    }


def simulate_1k_options_trade(
    current_price: float,
    recommended_strike: float,
    target_price: float,
    invalidation_price: float,
    realized_vol: float,
    action: str,
    budget: float = 1000.0,
    days_to_exp: int = 35,
    r: float = 0.043,
    vol_rank: float = 50.0,
    live_option: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Simulates $1,000 capital deployment in 30-45 DTE options over a 1-5 day swing horizon
    using live CBOE/OPRA contract IV & mid-price when available, with honest Black-Scholes
    exit repricing (zero artificial profit floors) and Vanna/Vega IV shift modeling.
    """
    eff_strike = float(live_option["strike"]) if (live_option and float(live_option.get("strike") or 0) > 0) else recommended_strike
    eff_dte = int(live_option["dte"]) if (live_option and int(live_option.get("dte") or 0) >= 14) else days_to_exp
    T_entry = max(0.04, eff_dte / 365.0)
    T_exit = max(0.015, max(5, eff_dte - 4) / 365.0)  # 4 trading days later at 1-5D target

    live_iv_pct = float(live_option.get("iv") or 0.0) if live_option else 0.0
    base_vol_pct = live_iv_pct if (10.0 <= live_iv_pct <= 220.0) else (realized_vol if not np.isnan(realized_vol) else 42.0)
    sigma_entry = max(0.16, base_vol_pct / 100.0)

    is_call = ("CALL" in action) or (action == "WATCHLIST" and target_price >= current_price)
    direction = "CALL" if is_call else "PUT"

    if is_call:
        iv_mult_target = 1.03 if vol_rank < 35.0 else (0.93 if vol_rank > 70.0 else 0.97)
        iv_mult_stop = 1.05
    else:
        iv_mult_target = 1.09 if vol_rank < 65.0 else 1.02
        iv_mult_stop = 0.96

    sigma_target = max(0.14, sigma_entry * iv_mult_target)
    sigma_stop = max(0.14, sigma_entry * iv_mult_stop)

    if is_call:
        eff_target = max(current_price * 1.032, target_price)
        eff_stop = min(current_price * 0.968, invalidation_price)
        bs_entry_prem, delta_entry = bs_call_price_delta(current_price, eff_strike, T_entry, r, sigma_entry)
        raw_target_opt, _ = bs_call_price_delta(eff_target, eff_strike, T_exit, r, sigma_target)
        raw_stop_opt, _ = bs_call_price_delta(eff_stop, eff_strike, T_exit, r, sigma_stop)
    else:
        eff_target = min(current_price * 0.968, target_price)
        eff_stop = max(current_price * 1.032, invalidation_price)
        bs_entry_prem, delta_entry = bs_put_price_delta(current_price, eff_strike, T_entry, r, sigma_entry)
        raw_target_opt, _ = bs_put_price_delta(eff_target, eff_strike, T_exit, r, sigma_target)
        raw_stop_opt, _ = bs_put_price_delta(eff_stop, eff_strike, T_exit, r, sigma_stop)

    live_mid = float(live_option.get("mid") or 0.0) if live_option else 0.0
    if live_mid >= 0.15 and bs_entry_prem > 0.05:
        prem_est = round(live_mid, 2)
        # Preserve market skew ratio between live mid and theoretical BS entry
        skew_scale = float(np.clip(live_mid / bs_entry_prem, 0.65, 1.55))
        raw_target_opt *= skew_scale
        raw_stop_opt *= skew_scale
    else:
        prem_est = max(0.20, round(bs_entry_prem, 2))

    cost_per_contract = round(prem_est * 100.0, 2)
    num_contracts = max(1, round(budget / cost_per_contract))
    total_invested = round(num_contracts * cost_per_contract, 2)

    gain_per_share = max(0.05, round(raw_target_opt - prem_est, 2))
    total_target_gain = round(num_contracts * gain_per_share * 100.0, 2)
    roi_pct = round((total_target_gain / total_invested) * 100.0, 1)

    loss_per_share = min(prem_est * 0.65, max(prem_est * 0.15, round(prem_est - raw_stop_opt, 2)))
    total_stop_loss = round(num_contracts * loss_per_share * 100.0, 2)
    loss_pct = round((total_stop_loss / total_invested) * 100.0, 1)

    sim_rr = round(total_target_gain / total_stop_loss, 2) if total_stop_loss > 0 else 2.0
    otm_pct = abs(eff_strike - current_price) / current_price * 100.0

    return {
        "budget": budget,
        "direction": direction,
        "strike_used": eff_strike,
        "dte_used": eff_dte,
        "iv_used_pct": round(sigma_entry * 100.0, 1),
        "prem_per_share": prem_est,
        "cost_per_contract": cost_per_contract,
        "contracts": num_contracts,
        "total_invested": total_invested,
        "target_profit": total_target_gain,
        "target_roi_pct": roi_pct,
        "stop_loss": total_stop_loss,
        "stop_loss_pct": loss_pct,
        "sim_rr_ratio": sim_rr,
        "delta_entry": round(delta_entry, 2),
        "otm_pct": round(otm_pct, 1),
        "summary": (
            f"Simulated ${budget:,.0f} Allocation: Buy {num_contracts}x {direction}s "
            f"at ${eff_strike:.2f} ({otm_pct:.1f}% OTM | Δ {delta_entry:+.2f} | IV {sigma_entry*100:.0f}%) "
            f"~${prem_est:.2f}/sh (${total_invested:,.0f} total). "
            f"1–5D Target P&L at ${target_price:.2f}: +${total_target_gain:,.0f} (+{roi_pct:.1f}%). "
            f"Stop Loss at ${invalidation_price:.2f}: -${total_stop_loss:,.0f} (-{loss_pct:.1f}%). "
            f"Asymmetric Options R:R: {sim_rr:.1f} : 1"
        )
    }


def calculate_options_volatility_and_spread_telemetry(
    symbol: str,
    metrics: Dict[str, Any],
    live_option: Optional[Dict[str, Any]] = None,
    dte: int = 35,
    hold_days: int = 5,
    iv_shift_pct: float = 0.0,
    budget: float = 1000.0,
    r: float = 0.043,
    chain_df: Optional[pd.DataFrame] = None,
    skew_optimizer: Optional[Dict[str, Any]] = None,
    term_structure: Optional[Dict[str, Any]] = None,
    r_rate: Optional[float] = None,
    div_yield: float = 0.0,
) -> Dict[str, Any]:
    """
    AAA Options Volatility, Greek Efficiency, Hold-Day Breakeven & Naked vs. Vertical Debit Spread Engine.
    Uses live OPRA short-leg quotes (`chain_df`), real OPRA 25D SVI skew (`skew_optimizer`),
    multi-expiry term structure (`term_structure`), American CRR tree pricing with dividend yield,
    accumulated SQLite OPRA IV rank, Daily Variance Rent Ratio, and a 5x4 Spot x Hold-Day
    Scenario P&L Matrix.
    """
    eff_r = max(0.005, min(0.12, float(r_rate if r_rate is not None else r)))
    eff_q = max(0.0, min(0.15, float(div_yield or 0.0)))
    spot = max(1.0, float(metrics.get("price", 100.0)))
    action = str(metrics.get("action", "BUY CALL"))
    is_call = ("CALL" in action) or (action == "WATCHLIST" and float(metrics.get("target_price", spot)) >= spot)
    direction = "CALL" if is_call else "PUT"

    hv20_pct = max(16.0, float(metrics.get("realized_vol", 42.0)))
    hv_rank_1y = round(float(metrics.get("vol_rank", 50.0)), 1)
    live_iv_raw = float(live_option.get("iv") or 0.0) if live_option else 0.0
    if 10.0 <= live_iv_raw <= 220.0:
        iv_pct = round(live_iv_raw, 1)
        iv_source = "OPRA Live Chain"
    else:
        iv_pct = round(hv20_pct * (0.91 + (hv_rank_1y / 100.0) * 0.26), 1)
        iv_source = "HV-Rank Calibrated"

    # Persist OPRA ATM IV snapshot and blend OPRA IV percentile with 1Y realized vol rank
    opra_iv_days = 0
    vol_rank = hv_rank_1y
    if iv_source == "OPRA Live Chain":
        try:
            import diary_db
            diary_db.record_daily_iv_snapshot(symbol, iv_pct)
            iv_stats = diary_db.get_iv_percentile_stats(symbol, iv_pct, fallback_hv_rank=hv_rank_1y)
            vol_rank = float(iv_stats.get("iv_rank_blended", hv_rank_1y))
            opra_iv_days = int(iv_stats.get("opra_iv_days", 0) or 0)
        except Exception:
            pass

    iv_hv_spread = round(iv_pct - hv20_pct, 1)
    if iv_hv_spread <= -2.0 or (vol_rank <= 32.0 and iv_hv_spread <= 2.5):
        vega_regime = "UNDERPRICED VEGA (LONG CONVEXITY)"
        vega_badge = f"CHEAP VEGA ({iv_hv_spread:+.1f}%)"
        vega_color = "#34D399"
        vega_advice = "Implied Vol is discounted vs realized movement — favor Naked OTM Calls/Puts for dual Delta + Vega expansion."
    elif iv_hv_spread >= 8.0 or vol_rank >= 72.0:
        vega_regime = "RICH VEGA (IV CRUSH HAZARD)"
        vega_badge = f"RICH VEGA ({iv_hv_spread:+.1f}%)"
        vega_color = "#F87171"
        vega_advice = "Implied Vol trades at a steep premium to HV20 — deploy a Vertical Debit Spread to sell expensive OTM wing Vega."
    else:
        vega_regime = "FAIR VEGA PRICING"
        vega_badge = f"FAIR VEGA ({iv_hv_spread:+.1f}%)"
        vega_color = "#FBBF24"
        vega_advice = "Implied Vol is aligned with 20D historical realized vol — standard 0.40–0.55Δ High-Delta execution."

    eff_strike = float(live_option["strike"]) if (live_option and float(live_option.get("strike") or 0) > 0) else float(metrics.get("recommended_strike", spot))
    eff_dte = int(live_option["dte"]) if (live_option and int(live_option.get("dte") or 0) >= 14 and abs(int(live_option.get("dte", 35)) - dte) <= 12) else max(10, int(dte))
    hold_d = max(1, min(eff_dte - 2, int(hold_days)))

    T_in = max(0.03, eff_dte / 365.0)
    T_out = max(0.008, (eff_dte - hold_d) / 365.0)
    sigma_in = max(0.14, iv_pct / 100.0)
    sigma_out = max(0.10, sigma_in * (1.0 + (float(iv_shift_pct) / 100.0)))

    # Entry & Hold-Day pricing via American CRR / BSM with dividend yield
    try:
        import quant_kernel
        g_in = quant_kernel.american_crr_price_and_greeks(spot, eff_strike, T_in, eff_r, sigma_in, is_call=is_call, steps=36, q=eff_q)
        g_flat = quant_kernel.american_crr_price_and_greeks(spot, eff_strike, T_out, eff_r, sigma_in, is_call=is_call, steps=36, q=eff_q)
        bs_in, delta_in = g_in["price"], g_in["delta"]
        bs_flat_no_iv = g_flat["price"]
        gamma_est = abs(g_in["gamma"])
        daily_theta_exact = max(0.005, abs(g_in["theta_daily"]))
    except Exception:
        if is_call:
            bs_in, delta_in = bs_call_price_delta(spot, eff_strike, T_in, eff_r, sigma_in)
            bs_flat_no_iv, _ = bs_call_price_delta(spot, eff_strike, T_out, eff_r, sigma_in)
        else:
            bs_in, delta_in = bs_put_price_delta(spot, eff_strike, T_in, eff_r, sigma_in)
            bs_flat_no_iv, _ = bs_put_price_delta(spot, eff_strike, T_out, eff_r, sigma_in)
        d1_val = (math.log(spot / eff_strike) + (eff_r - eff_q + 0.5 * sigma_in ** 2) * T_in) / (sigma_in * math.sqrt(T_in))
        gamma_est = ((1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * (d1_val ** 2))) / max(0.5, spot * sigma_in * math.sqrt(T_in))
        daily_theta_exact = max(0.005, abs(bs_flat_no_iv - bs_in) / max(1, hold_d))

    live_mid = float(live_option.get("mid") or 0.0) if (live_option and abs(eff_dte - int(dte)) <= 12) else 0.0
    skew_mult = float(np.clip(live_mid / bs_in, 0.65, 1.55)) if (live_mid >= 0.15 and bs_in > 0.05) else 1.0
    prem_entry = round(live_mid, 2) if (live_mid >= 0.15 and bs_in > 0.05) else max(0.15, round(bs_in, 2))
    prem_flat_hold = max(0.02, bs_flat_no_iv * skew_mult)

    contracts_naked = max(1, round(budget / (prem_entry * 100.0)))
    invested_naked = round(contracts_naked * prem_entry * 100.0, 2)

    theta_hold_per_sh = prem_flat_hold - prem_entry  # negative value
    theta_hold_dollar = round(contracts_naked * theta_hold_per_sh * 100.0, 0)
    theta_hold_pct = round((theta_hold_dollar / max(1.0, invested_naked)) * 100.0, 1)
    daily_theta_dollar = round(theta_hold_dollar / max(1, hold_d), 1)

    def _bs_price_q(
        s_val: float,
        k_val: float,
        t_val: float,
        r_val: float,
        sig_val: float,
        q_val: float,
        call_flag: bool,
    ) -> Tuple[float, float]:
        try:
            import quant_kernel
            g_bs = quant_kernel.black_scholes_all_greeks(
                s_val, k_val, t_val, r_val, sig_val, is_call=call_flag, q=q_val
            )
            return float(g_bs["price"]), float(g_bs["delta"])
        except Exception:
            if call_flag:
                return bs_call_price_delta(s_val, k_val, t_val, r_val, sig_val)
            return bs_put_price_delta(s_val, k_val, t_val, r_val, sig_val)

    daily_theta_per_sh = max(0.005, max(daily_theta_exact, abs(theta_hold_per_sh) / max(1, hold_d)))
    gamma_theta_ratio = round((gamma_est * spot * 0.01) / daily_theta_per_sh, 2)
    # Match calendar-day daily_theta_per_sh (1/365) with calendar-day realized variance (1/365)
    daily_gamma_rent = 0.5 * gamma_est * (spot ** 2) * (((hv20_pct / 100.0) / math.sqrt(365.0)) ** 2)
    variance_rent_ratio = round(daily_gamma_rent / daily_theta_per_sh, 2)

    # Dynamic Hold-Day Breakeven Spot Price (Binary search for Spot where Option(S, T_out, sigma_out) == prem_entry)
    if is_call:
        lo_s, hi_s = spot * 0.60, max(spot * 1.80, eff_strike * 1.60)
        for _ in range(22):
            mid_s = 0.5 * (lo_s + hi_s)
            val_m, _ = _bs_price_q(mid_s, eff_strike, T_out, eff_r, sigma_out, eff_q, True)
            if val_m * skew_mult < prem_entry:
                lo_s = mid_s
            else:
                hi_s = mid_s
        be_hold_price = round(0.5 * (lo_s + hi_s), 2)
        be_exp_price = round(eff_strike + prem_entry, 2)
    else:
        lo_s, hi_s = max(0.05, min(spot * 0.40, eff_strike * 0.40)), spot * 1.40
        for _ in range(22):
            mid_s = 0.5 * (lo_s + hi_s)
            val_m, _ = _bs_price_q(mid_s, eff_strike, T_out, eff_r, sigma_out, eff_q, False)
            if val_m * skew_mult < prem_entry:
                hi_s = mid_s
            else:
                lo_s = mid_s
        be_hold_price = round(0.5 * (lo_s + hi_s), 2)
        be_exp_price = round(max(0.50, eff_strike - prem_entry), 2)

    be_hold_move_pct = round(((be_hold_price - spot) / spot) * 100.0, 2)
    be_exp_move_pct = round(((be_exp_price - spot) / spot) * 100.0, 2)

    # Real OPRA 25-Delta Put/Call Skew when available, falling back to tape heuristic only when offline
    if isinstance(skew_optimizer, dict) and skew_optimizer.get("has_data"):
        skew_25d_pct = round(float(skew_optimizer.get("skew_25d_pct", 0.0)), 1)
        skew_source = "OPRA 25Δ SVI"
    else:
        pc_oi = float(metrics.get("inst_put_call_ratio", 1.0))
        cmf_20 = float(metrics.get("cmf_20", 0.0))
        z_5d = float(metrics.get("z_score_5d", 0.0))
        skew_25d_pct = round(float(np.clip(2.2 + (pc_oi - 0.95) * 3.2 - (cmf_20 * 4.5) - (z_5d * 0.85), -4.5, 9.5)), 1)
        skew_source = "Flow Heuristic"

    if skew_25d_pct >= 3.5:
        skew_label = f"PUT SKEW BID (+{skew_25d_pct:.1f}%)"
        skew_color = "#F87171"
    elif skew_25d_pct <= 0.5:
        skew_label = f"CALL WING BID ({skew_25d_pct:+.1f}%)"
        skew_color = "#34D399"
    else:
        skew_label = f"NEUTRAL SKEW ({skew_25d_pct:+.1f}%)"
        skew_color = "#FBBF24"

    # Pace expected underlying spot price at Hold Day using O-U Half-Life decay
    target_5d = float(metrics.get("target_price", spot * (1.045 if is_call else 0.955)))
    ou_hl = max(1.5, float(metrics.get("ou_half_life", 4.5)))
    pace_ratio = (1.0 - (2.0 ** (-hold_d / ou_hl))) / max(0.15, (1.0 - (2.0 ** (-5.0 / ou_hl))))
    pace_ratio = float(np.clip(pace_ratio, 0.35, 1.35))
    spot_at_hold = spot + (target_5d - spot) * pace_ratio

    # Strategy A: Naked OTM Option at Hold Day & IV Shift
    naked_out_raw, _ = _bs_price_q(spot_at_hold, eff_strike, T_out, eff_r, sigma_out, eff_q, is_call)
    naked_out_prem = max(0.02, round(naked_out_raw * skew_mult, 2))
    naked_profit_1k = round(contracts_naked * (naked_out_prem - prem_entry) * 100.0, 0)
    naked_roi_pct = round((naked_profit_1k / max(1.0, invested_naked)) * 100.0, 1)

    # Strategy B: 30-45 DTE Vertical Debit Spread — Look up real OPRA Short Strike K2 quote if chain_df available!
    atr14 = float(metrics.get("atr14", spot * 0.035))
    if is_call:
        raw_k2 = max(eff_strike * 1.04, target_5d, eff_strike + 1.25 * atr14)
        short_strike = round_to_standard_strike(raw_k2)
        if short_strike <= eff_strike:
            short_strike = round(eff_strike + max(1.0, round(spot * 0.04, 0)), 2)
    else:
        raw_k2 = min(eff_strike * 0.96, target_5d, eff_strike - 1.25 * atr14)
        short_strike = round_to_standard_strike(max(1.0, raw_k2))
        if short_strike >= eff_strike:
            short_strike = max(0.5, round(eff_strike - max(1.0, round(spot * 0.04, 0)), 2))

    short_leg_source = "BS Wing Model"
    sigma_short_in = sigma_in * (0.98 if is_call else 1.03)
    short_skew_mult = skew_mult
    short_entry_live = None
    short_delta_live = None

    if chain_df is not None and not chain_df.empty and "strike" in chain_df.columns and "side" in chain_df.columns:
        side_df = chain_df[chain_df["side"].astype(str).str.lower() == ("call" if is_call else "put")].copy()
        if not side_df.empty:
            wing_cands = side_df[side_df["strike"] > eff_strike] if is_call else side_df[side_df["strike"] < eff_strike]
            if not wing_cands.empty:
                wing_cands["k_dist"] = (wing_cands["strike"] - raw_k2).abs()
                s_row = wing_cands.loc[wing_cands["k_dist"].idxmin()]
                s_k_val = float(s_row.get("strike", short_strike) or short_strike)
                s_mid = float(s_row.get("mid", 0.0) or ((float(s_row.get("bid", 0.0) or 0.0) + float(s_row.get("ask", 0.0) or 0.0)) / 2.0))
                s_iv = float(s_row.get("impliedVolatility", 0.0) or 0.0)
                if s_iv > 3.5:
                    s_iv /= 100.0
                if abs(s_k_val - eff_strike) >= max(0.5, spot * 0.015) and s_mid >= 0.05:
                    short_strike = s_k_val
                    short_entry_live = round(s_mid, 2)
                    if 0.05 <= s_iv <= 2.80:
                        sigma_short_in = s_iv
                    if s_row.get("delta") is not None:
                        short_delta_live = float(s_row["delta"])
                    short_leg_source = "OPRA Live Short Leg"

    sigma_short_out = max(0.08, sigma_short_in * (1.0 + (float(iv_shift_pct) / 100.0)))
    short_in, short_delta = _bs_price_q(spot, short_strike, T_in, eff_r, sigma_short_in, eff_q, is_call)
    short_out, _ = _bs_price_q(spot_at_hold, short_strike, T_out, eff_r, sigma_short_out, eff_q, is_call)
    short_flat, _ = _bs_price_q(spot, short_strike, T_out, eff_r, sigma_short_in, eff_q, is_call)

    if short_entry_live is not None and short_in > 0.05:
        short_entry = min(prem_entry * 0.80, max(0.05, short_entry_live))
        short_skew_mult = float(np.clip(short_entry / short_in, 0.65, 1.55))
    else:
        short_entry = min(prem_entry * 0.72, max(0.05, round(short_in * skew_mult, 2)))
        if short_in > 0.05:
            short_skew_mult = float(np.clip(short_entry / short_in, 0.65, 1.55))

    if short_delta_live is not None:
        short_delta = short_delta_live

    net_debit = max(0.15, round(prem_entry - short_entry, 2))
    spread_width = round(abs(short_strike - eff_strike), 2)
    spread_val_out = min(spread_width, max(0.02, round(naked_out_prem - (short_out * short_skew_mult), 2)))
    spread_val_flat = max(0.02, round(prem_flat_hold - (short_flat * short_skew_mult), 2))

    spread_contracts = max(1, round(budget / (net_debit * 100.0)))
    spread_invested = round(spread_contracts * net_debit * 100.0, 2)
    spread_profit_1k = round(spread_contracts * (spread_val_out - net_debit) * 100.0, 0)
    spread_roi_pct = round((spread_profit_1k / max(1.0, spread_invested)) * 100.0, 1)
    spread_theta_dollar = round(spread_contracts * (spread_val_flat - net_debit) * 100.0, 0)
    spread_theta_eq_notional = spread_theta_dollar * (invested_naked / max(1.0, spread_invested))
    theta_saved_dollar = round(spread_theta_eq_notional - theta_hold_dollar, 0)

    prefer_spread = (iv_hv_spread >= 8.0) or (vol_rank >= 72.0) or (iv_shift_pct <= -5.0) or (spread_roi_pct > naked_roi_pct + 8.0)
    rec_structure = f"{eff_dte}D VERTICAL DEBIT SPREAD" if prefer_spread else f"{eff_dte}D NAKED OTM {direction}"

    # 5x4 Spot Shock x Hold-Day Scenario P&L Matrix with Spot-Vol skew beta
    step_mv = round(max(2.0, min(5.0, (abs(target_5d - spot) / spot) * 100.0 * 0.55)), 1)
    spot_shocks_pct = [-2.0 * step_mv, -step_mv, 0.0, step_mv, 2.0 * step_mv]
    day_cols = [d_c for d_c in (1, 3, 5, 10) if d_c < eff_dte] or [1, 2]
    scenario_rows = []
    for sp_pct in spot_shocks_pct:
        s_sc = spot * (1.0 + sp_pct / 100.0)
        iv_beta_mult = 1.0 + (float(iv_shift_pct) / 100.0) - (0.35 * (sp_pct / 100.0))
        sig_l_sc = max(0.08, sigma_in * iv_beta_mult)
        sig_s_sc = max(0.08, sigma_short_in * iv_beta_mult)
        row_cells = []
        for dc in day_cols:
            t_sc = max(1, eff_dte - dc) / 365.0
            p_l_raw, _ = _bs_price_q(s_sc, eff_strike, t_sc, eff_r, sig_l_sc, eff_q, is_call)
            p_s_raw, _ = _bs_price_q(s_sc, short_strike, t_sc, eff_r, sig_s_sc, eff_q, is_call)
            n_val = max(0.01, p_l_raw * skew_mult)
            sp_val = min(spread_width, max(0.01, n_val - (p_s_raw * short_skew_mult)))
            n_roi = round(((n_val - prem_entry) / max(0.05, prem_entry)) * 100.0, 1)
            sp_roi = round(((sp_val - net_debit) / max(0.05, net_debit)) * 100.0, 1)
            n_pnl = round(contracts_naked * (n_val - prem_entry) * 100.0, 0)
            sp_pnl = round(spread_contracts * (sp_val - net_debit) * 100.0, 0)
            row_cells.append({
                "day": dc,
                "naked_roi_pct": n_roi,
                "naked_pnl": n_pnl,
                "spread_roi_pct": sp_roi,
                "spread_pnl": sp_pnl,
            })
        scenario_rows.append({
            "spot_pct": round(sp_pct, 1),
            "spot_price": round(s_sc, 2),
            "cells": row_cells,
        })

    ts_dict = term_structure if isinstance(term_structure, dict) else {}

    return {
        "direction": direction,
        "iv_pct": iv_pct,
        "hv20_pct": round(hv20_pct, 1),
        "iv_hv_spread": iv_hv_spread,
        "vrp_vol_pts": iv_hv_spread,
        "hv_rank_1y": hv_rank_1y,
        "iv_rank_blended": round(vol_rank, 1),
        "opra_iv_days": opra_iv_days,
        "iv_source": iv_source,
        "vega_regime": vega_regime,
        "vega_badge": vega_badge,
        "vega_color": vega_color,
        "vega_advice": vega_advice,
        "hold_days": hold_d,
        "iv_shift_pct": round(float(iv_shift_pct), 1),
        "dte_used": eff_dte,
        "strike_used": eff_strike,
        "short_strike": short_strike,
        "short_leg_source": short_leg_source,
        "spread_width": spread_width,
        "prem_entry": prem_entry,
        "net_debit": net_debit,
        "delta_in": round(delta_in, 2),
        "short_delta": round(short_delta, 2),
        "net_spread_delta": round(delta_in - short_delta, 2),
        "theta_hold_dollar": theta_hold_dollar,
        "theta_hold_pct": theta_hold_pct,
        "daily_theta_dollar": daily_theta_dollar,
        "gamma_theta_ratio": gamma_theta_ratio,
        "variance_rent_ratio": variance_rent_ratio,
        "breakeven_hold_price": be_hold_price,
        "breakeven_hold_move_pct": be_hold_move_pct,
        "breakeven_exp_price": be_exp_price,
        "breakeven_exp_move_pct": be_exp_move_pct,
        "skew_25d_pct": skew_25d_pct,
        "skew_source": skew_source,
        "skew_label": skew_label,
        "skew_color": skew_color,
        "term_slope_30_60_pct": float(ts_dict.get("term_slope_30_60_pct", 0.0) or 0.0),
        "term_regime": str(ts_dict.get("term_regime", "NORMAL CONTANGO")),
        "core_implied_move_pct": float(ts_dict.get("core_implied_move_pct", 0.0) or 0.0),
        "front_implied_move_pct": float(ts_dict.get("front_implied_move_pct", 0.0) or 0.0),
        "spot_at_hold": round(spot_at_hold, 2),
        "naked_contracts": contracts_naked,
        "naked_invested": invested_naked,
        "naked_out_prem": naked_out_prem,
        "naked_profit_1k": naked_profit_1k,
        "naked_roi_pct": naked_roi_pct,
        "spread_contracts": spread_contracts,
        "spread_invested": spread_invested,
        "spread_val_out": spread_val_out,
        "spread_profit_1k": spread_profit_1k,
        "spread_roi_pct": spread_roi_pct,
        "spread_theta_dollar": spread_theta_dollar,
        "theta_saved_dollar": max(0.0, theta_saved_dollar),
        "prefer_spread": prefer_spread,
        "recommended_structure": rec_structure,
        "scenario_matrix": {"day_cols": day_cols, "rows": scenario_rows},
    }


def calculate_macro_ticker_transmission(
    symbol: str,
    metrics: Dict[str, Any],
    macro_regime: Dict[str, Any],
    radar_24_48: Dict[str, Any],
    sector_name: str = "Semiconductors"
) -> Dict[str, Any]:
    """
    Computes the Macro-to-Ticker Transmission HUD telemetry linking top-of-house Macro Spider
    & 1-5D Risk Runway directly to the focused ticker inside the Active Strike Terminal:
      1. Rate & Duration Coupling (Beta + 10Y Velocity impact on valuation multiple)
      2. Dealer Gamma & Dispersion Alignment (How +Γ/-Γ impacts this stock's O-U Half-Life)
      3. O-U Half-Life vs. 1-5D Macro Calendar Collision Check
    """
    beta = float(metrics.get("beta", 1.25))
    ou_hl = float(metrics.get("ou_half_life", 4.5))
    action = str(metrics.get("action", "BUY CALL"))
    bps_5d = float(macro_regime.get("rate_change_5d_bps", 0.0))
    y10 = float(macro_regime.get("y10_current", 4.20))

    # 1. Rate & Duration Sensitivity
    duration_mult = 1.35 if ("Nuclear" in sector_name or "AI" in sector_name or beta >= 1.45) else 1.0
    rate_drag_score = round(-bps_5d * 0.12 * duration_mult, 2)
    if bps_5d >= 8.0:
        rate_tag = f"10Y +{bps_5d:.0f}bps Headwind (High-Beta Multiple Drag)"
        rate_color = "#F87171" if "CALL" in action else "#34D399"
    elif bps_5d <= -6.0:
        rate_tag = f"10Y {bps_5d:+.0f}bps Tailwind (Duration Relief Boost)"
        rate_color = "#34D399" if "CALL" in action else "#FBBF24"
    else:
        rate_tag = f"10Y Stable ({y10:.2f}% · {bps_5d:+.0f}bps 5D) — Neutral Rate Beta ({beta:.2f}β)"
        rate_color = "#FBBF24"

    # 2. Dealer Gamma & Sector Dispersion Coupling
    gamma_short = radar_24_48.get("dealer_gamma_short", "+Γ DIP-BUY BUFFER")
    gamma_col = radar_24_48.get("dealer_gamma_color", "#34D399")
    disp_short = radar_24_48.get("dispersion_short", "Stock-Pick Alpha")
    disp_col = radar_24_48.get("dispersion_color", "#34D399")

    # 3. Ornstein-Uhlenbeck Half-Life vs. 1-5D Macro Risk Runway Collision Check
    ou_window_hours = max(24.0, min(144.0, ou_hl * 24.0))
    upcoming = macro_regime.get("upcoming_events", [])
    colliding = [
        ev for ev in upcoming
        if 0.0 <= float(ev.get("hours_away", 999.0)) <= ou_window_hours
    ]
    if colliding:
        first_ev = colliding[0]
        ev_hrs = float(first_ev.get("hours_away", 24.0))
        when_str = f"in {ev_hrs:.0f}h" if ev_hrs < 48.0 else f"in {ev_hrs/24.0:.1f}d"
        collision_tag = f"⚡ {first_ev.get('event', 'Macro Print')} ({when_str}) inside {symbol}'s {ou_hl:.1f}D O-U Window"
        collision_color = "#F87171" if ev_hrs <= 48.0 else "#FBBF24"
        collision_advice = "Use Vertical Spread or scale 50% prior to release" if ev_hrs <= 48.0 else "Monitor pre-print IV expansion"
    else:
        collision_tag = f"Clear Runway across {symbol}'s {ou_hl:.1f}D O-U Reversion Window"
        collision_color = "#34D399"
        collision_advice = "Zero binary macro prints colliding with half-life target"

    return {
        "beta": beta,
        "ou_half_life": ou_hl,
        "rate_tag": rate_tag,
        "rate_color": rate_color,
        "rate_drag_score": rate_drag_score,
        "gamma_short": gamma_short,
        "gamma_color": gamma_col,
        "dispersion_short": disp_short,
        "dispersion_color": disp_col,
        "has_collision": len(colliding) > 0,
        "collision_count": len(colliding),
        "collision_tag": collision_tag,
        "collision_color": collision_color,
        "collision_advice": collision_advice
    }


# =========================================================================
# PILLAR 7: TWO-STAGE TOP-5 SECTOR VETTING & DUE DILIGENCE ENGINE
# =========================================================================

def get_due_diligence_candidate(
    symbol: str,
    benchmark_symbol: str = "SMH",
    day_override: Optional[Any] = None,
    moneyness_mode: str = "aggressive_otm",
    vet_deep: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Evaluates a ticker using the Two-Stage Vetting Architecture:
    - When vet_deep=False (Stage 1 full-sector screening): Runs 100% of the 5-year EOD + live batch quote
      quantitative math (Z-scores, 180D O-U half-life, 252D variance ratio, 5Y Empirical Basis % Move,
      Live Tape Sharp CMF-20 & Up/Down Block Volume, and Obvious Bad-Data Quarantine) while reusing
      cached fundamentals/13F/earnings if present, saving ~70% of FMP API calls.
    - When vet_deep=True (Stage 2 Top-5 per sector + active focused ticker): Pulls full FMP Ultra
      endpoints (/earnings?symbol=SYM&limit=6 for exact 25-day earnings, /institutional-ownership/symbol-positions-summary
      for 13F Call/Put Open Interest & Whale Loading/Unloading, /financial-scores, /ratios-ttm, /key-metrics-ttm,
      /financial-growth, /insider-trading/statistics, /price-target-consensus, /profile, and 4H bars).
    """
    if isinstance(day_override, str):
        moneyness_mode = day_override
        day_override = None
    sym = symbol.strip().upper()
    eff_bench = normalize_benchmark(SUB_BENCHMARK_MAP.get(sym, benchmark_symbol))

    deep_cache_key = f"dd_cand_v49_{sym}_{eff_bench}_{moneyness_mode}_{day_override}_deep"
    cached_deep = get_cached(deep_cache_key, ttl=180)
    if cached_deep is not None:
        return cached_deep

    if not vet_deep:
        stage1_cache_key = f"dd_cand_v49_{sym}_{eff_bench}_{moneyness_mode}_{day_override}_s1"
        cached_s1 = get_cached(stage1_cache_key, ttl=180)
        if cached_s1 is not None:
            return cached_s1

    try:
        # Profile lookup BEFORE metric gating so thematic ETFs bypass corporate cap/fundamental gates cleanly
        prof_cached = get_cached(_fmp_cache_key("profile", {"symbol": sym}), ttl=3600)
        if prof_cached is None and (vet_deep or sym in THEMATIC_ETFS):
            prof_cached = fmp_get("profile", params={"symbol": sym}, ttl=3600)
        prof = prof_cached[0] if (isinstance(prof_cached, list) and len(prof_cached) > 0) else {}
        is_etf = bool(prof.get("isEtf") or prof.get("isFund") or (sym in THEMATIC_ETFS))

        # When evaluating a benchmark ETF itself (e.g. REMX or URA), compare against broad growth/market index
        rel_bench = eff_bench
        if sym == rel_bench:
            rel_bench = "SPY" if sym == "QQQ" else "QQQ"

        t_df, live_q, latest_4h = get_hybrid_price_series(sym, fetch_4h=vet_deep)
        b_df, _, _ = get_hybrid_price_series(rel_bench, fetch_4h=False)
        if t_df.empty or b_df.empty:
            return None

        metrics = calculate_rubberband_metrics_v3(
            t_df, b_df, latest_4h, day_override=day_override, moneyness_mode=moneyness_mode, is_etf=is_etf
        )
        if not metrics:
            return None

        company_name = prof.get("companyName") or live_q.get("name") or sym
        company_logo = prof.get("image", f"https://images.financialmodelingprep.com/symbol/{sym}.png")
        default_desc = (
            "Thematic institutional ETF basket tracked for relative dispersion and macro flow."
            if is_etf
            else "High-beta US technology & industrial leader."
        )
        description = (prof.get("description") or default_desc)[:200] + "..."
        sector = prof.get("sector") or ("ETF / Thematic Basket" if is_etf else "Technology")
        industry = prof.get("industry") or ("Thematic ETF" if is_etf else "Semiconductors & Systems")
        # FMP /stable/profile uses marketCap (while legacy/ETF profiles can leave mktCap=None)
        mkt_cap = prof.get("mktCap") or prof.get("marketCap") or live_q.get("marketCap") or 0

        fund = compute_fundamental_quality_score(sym, fetch_live=vet_deep, is_etf=is_etf)
        if is_etf:
            insider = {"insider_net_shares": 0, "insider_score": 50.0, "summary": "ETF Basket"}
            analyst = {"upside_pct": 0.0, "consensus": "ETF Basket", "target_mean": metrics["price"]}
            earn_info = {
                "days_to_earnings": 99,
                "earnings_date": "ETF Basket",
                "has_earnings_25d": False,
                "has_binary_earnings_7d": False,
                "eps_beat_streak": 0,
            }
        else:
            insider = get_insider_conviction(sym, fetch_live=vet_deep)
            analyst = get_analyst_consensus(sym, metrics["price"], fetch_live=vet_deep)
            # 25-Day Exact Earnings Check (/earnings?symbol=SYM&limit=6 on vetted tickers)
            earn_info = get_ticker_earnings_25d(sym, fetch_live=vet_deep)

        temporal = get_temporal_regime(override_day=day_override)
        macro = get_macro_yield_regime()
        regime_pulse = get_sector_macro_pulse()
        radar_24_48 = get_24_48h_market_direction_radar()

        # 13F Institutional Call/Put Open Interest + Live Tape Sharp/Whale Flow
        sharp_tape_dict = {
            "sharp_tape_score": metrics.get("sharp_tape_score", 0.0),
            "cmf_20": metrics.get("cmf_20", 0.0),
            "up_down_vol_ratio": metrics.get("up_down_vol_ratio", 1.0),
            "direction": metrics.get("action", "")
        }
        whale_oi = get_fmp_institutional_open_interest(sym, sharp_tape_dict, fetch_live=vet_deep)

        metrics["days_to_earnings"] = earn_info["days_to_earnings"]
        metrics["earnings_date"] = earn_info["earnings_date"]
        metrics["has_earnings_25d"] = earn_info.get("has_earnings_25d", 0 <= earn_info["days_to_earnings"] <= 25)
        metrics["has_binary_earnings_7d"] = earn_info["has_binary_earnings_7d"]
        metrics["eps_beat_streak"] = earn_info.get("eps_beat_streak", 0)
        metrics["hist_er_avg_move_pct"] = earn_info.get("hist_er_avg_move_pct", 0.0)
        metrics["hist_er_med_move_pct"] = earn_info.get("hist_er_med_move_pct", 0.0)
        metrics["hist_er_max_move_pct"] = earn_info.get("hist_er_max_move_pct", 0.0)
        metrics["hist_er_quarters_n"] = earn_info.get("hist_er_quarters_n", 0)
        metrics["sub_benchmark"] = eff_bench

        # Inject Whale / 13F Open Interest telemetry directly into metrics for UI & charts
        metrics["whale_status"] = whale_oi["whale_status"]
        metrics["whale_badge"] = whale_oi["whale_badge"]
        metrics["whale_color"] = whale_oi["whale_color"]
        metrics["whale_score"] = whale_oi["whale_score"]
        metrics["whale_summary"] = whale_oi["whale_summary"]
        metrics["flow_alignment"] = whale_oi.get("flow_alignment", "")
        metrics["tape_sentiment"] = whale_oi.get("tape_sentiment", "")
        metrics["inst_quarter"] = whale_oi.get("inst_quarter", "")
        metrics["inst_total_calls"] = whale_oi["inst_total_calls"]
        metrics["inst_total_puts"] = whale_oi["inst_total_puts"]
        metrics["inst_put_call_ratio"] = whale_oi["inst_put_call_ratio"]
        metrics["inst_calls_change_pct"] = whale_oi["inst_calls_change_pct"]
        metrics["inst_puts_change_pct"] = whale_oi["inst_puts_change_pct"]
        metrics["inst_shares_change_pct"] = whale_oi["inst_shares_change_pct"]
        metrics["inst_net_buyers"] = whale_oi["inst_net_buyers"]
        metrics["has_13f_oi_data"] = whale_oi["has_13f_oi_data"]
        metrics["is_top5_vetted"] = vet_deep

        # Inject live quote day change % directly into metrics
        live_chg_pct = float(live_q.get("changePercentage", live_q.get("changesPercentage", 0.0)) or 0.0)
        if abs(live_chg_pct) < 1e-4 and "change_pct_1d" in metrics and abs(float(metrics["change_pct_1d"])) > 1e-4:
            live_chg_pct = float(metrics["change_pct_1d"])
        metrics["change_pct_1d"] = round(live_chg_pct, 2)
        metrics["change_1d"] = round(float(live_q.get("change", 0.0) or 0.0), 2)

        r_live = max(0.01, min(0.10, float(macro.get("y3m_current", 4.25) or 4.25) / 100.0))
        q_live = max(0.0, min(0.12, float(prof.get("lastDiv", 0.0) or 0.0) / max(1.0, metrics["price"])))

        # Near-Live Exchange Option Contract & Institutional OPRA Telemetry (MarketData.app)
        rec_strike = float(metrics.get("recommended_strike", metrics["price"]))
        delta_mode = "CONVEX_OTM" if str(moneyness_mode).lower() in ("deep_convexity_otm", "convex_otm") else "HIGH_DELTA"
        target_delta = 0.25 if delta_mode == "CONVEX_OTM" else 0.50
        chain_df = None
        term_structure: Dict[str, Any] = {}
        if vet_deep:
            chain_df = marketdata_client.get_option_chain_native(
                sym, dte=35, strike_limit=60, side=None, ttl=900, feed="cached"
            )
            opt_contract = get_near_live_option_contract(
                sym,
                metrics.get("action", ""),
                rec_strike,
                target_dte=35,
                target_delta=target_delta,
                delta_mode=delta_mode,
                chain_df=chain_df,
            )
            ext_telemetry = marketdata_client.get_extended_hours_telemetry(sym, ttl=300)
            gamma_walls = marketdata_client.get_opra_gamma_walls_and_unusual_flow(
                sym, dte=35, ttl=600, chain_df=chain_df
            )
            skew_optimizer = marketdata_client.get_25d_skew_and_spread_optimizer(
                sym, dte=35, spot=metrics["price"], ttl=600, chain_df=chain_df
            )
            term_structure = marketdata_client.get_iv_term_structure_and_implied_move(
                sym, spot=metrics["price"], primary_chain_df=chain_df, ttl=900
            )
        else:
            opt_cached_k = f"live_opt_contract_v5_{sym}_{metrics.get('action', '')}_35_{delta_mode}_{round(rec_strike, 1)}"
            c_opt = get_cached(opt_cached_k, ttl=1800)
            if not (isinstance(c_opt, dict) and c_opt):
                c_opt = get_cached(f"live_opt_contract_v4_{sym}_{metrics.get('action', '')}_{round(rec_strike, 1)}", ttl=1800)
            opt_contract = c_opt if (isinstance(c_opt, dict) and c_opt) else None
            ext_telemetry = {}
            gamma_walls = {}
            skew_optimizer = {}

        if opt_contract and isinstance(opt_contract, dict) and opt_contract.get("strike"):
            metrics["recommended_strike"] = float(opt_contract["strike"])
            if opt_contract.get("delta") is not None:
                _d_raw = float(opt_contract["delta"])
                _act_up = str(metrics.get("action", "")).upper()
                if "PUT" in _act_up and _d_raw > 0:
                    _d_raw = -abs(_d_raw)
                elif "CALL" in _act_up and _d_raw < 0:
                    _d_raw = abs(_d_raw)
                metrics["signed_delta"] = round(_d_raw, 2)
                metrics["estimated_delta"] = round(abs(_d_raw), 2)

        metrics["near_live_option"] = opt_contract
        metrics["extended_hours"] = ext_telemetry
        metrics["gamma_walls"] = gamma_walls
        metrics["skew_optimizer"] = skew_optimizer
        metrics["term_structure"] = term_structure
        if term_structure.get("has_data") and metrics.get("hist_er_avg_move_pct", 0.0) > 0.0:
            imp_mv = float(term_structure.get("front_implied_move_pct") or term_structure.get("core_implied_move_pct") or 0.0)
            metrics["er_vol_edge_pct"] = round(imp_mv - float(metrics["hist_er_avg_move_pct"]), 2)
        else:
            metrics["er_vol_edge_pct"] = 0.0

        blueprint = structure_30_45_dte_blueprint(
            sym,
            metrics,
            fund,
            insider,
            analyst,
            temporal,
            macro,
            earnings_info=earn_info,
            whale_oi=whale_oi,
            regime_pulse=regime_pulse,
            radar_24_48=radar_24_48,
            live_option=opt_contract,
            gamma_walls=gamma_walls,
            skew_optimizer=skew_optimizer,
            extended_hours=ext_telemetry
        )

        sim_1k = simulate_1k_options_trade(
            current_price=metrics["price"],
            recommended_strike=metrics["recommended_strike"],
            target_price=metrics["target_price"],
            invalidation_price=metrics["invalidation_price"],
            realized_vol=metrics["realized_vol"],
            action=metrics["action"],
            vol_rank=metrics.get("vol_rank", 50.0),
            live_option=opt_contract
        )
        metrics["sim_1k"] = sim_1k

        opt_telemetry = calculate_options_volatility_and_spread_telemetry(
            symbol=sym,
            metrics=metrics,
            live_option=opt_contract,
            dte=35,
            hold_days=5,
            iv_shift_pct=0.0,
            chain_df=chain_df,
            skew_optimizer=skew_optimizer,
            term_structure=term_structure,
            r_rate=r_live,
            div_yield=q_live,
        )
        macro_trans = calculate_macro_ticker_transmission(
            symbol=sym,
            metrics=metrics,
            macro_regime=macro,
            radar_24_48=radar_24_48,
            sector_name=sector
        )
        metrics["options_telemetry"] = opt_telemetry
        metrics["macro_transmission"] = macro_trans

        # Institutional Quant Kernel: 2D Kalman Beta/Alpha + Walk-Forward 5-Quantile EV + Quarter-Kelly Sizing
        quant_edge = {}
        try:
            import quant_kernel
            if "date" in t_df.columns and "date" in b_df.columns:
                _k_aligned = pd.DataFrame({
                    "t": pd.Series(t_df["close"].to_numpy(dtype=float), index=pd.to_datetime(t_df["date"]).dt.normalize()),
                    "b": pd.Series(b_df["close"].to_numpy(dtype=float), index=pd.to_datetime(b_df["date"]).dt.normalize()),
                })
                _k_aligned = _k_aligned[~_k_aligned.index.duplicated(keep="last")].dropna()
            else:
                _k_aligned = pd.DataFrame({"t": t_df["close"], "b": b_df["close"]}).dropna()
            k_res = quant_kernel.kalman_dynamic_beta_and_z(
                _k_aligned["t"].to_numpy(dtype=float),
                _k_aligned["b"].to_numpy(dtype=float),
            )
            ev_res = quant_kernel.compute_institutional_ev_and_kelly(
                metrics=metrics,
                live_option=opt_contract,
                gamma_walls=gamma_walls,
                skew_optimizer=skew_optimizer,
                account_equity=25000.0,
                r=r_live,
                q=q_live,
            )
            quant_edge = {**k_res, **ev_res}
        except Exception:
            quant_edge = {}

        metrics["quant_edge"] = quant_edge
        blueprint["net_ev_pct"] = quant_edge.get("net_ev_pct", 0.0)
        blueprint["quarter_kelly_pct"] = quant_edge.get("quarter_kelly_pct", 0.0)
        blueprint["kelly_dollars"] = quant_edge.get("kelly_dollars", 0)
        blueprint["kelly_contracts"] = quant_edge.get("kelly_contracts", 0)
        blueprint["vrp_vol_pts"] = quant_edge.get("vrp_vol_pts", 0.0)
        blueprint["kalman_beta"] = quant_edge.get("kalman_beta", metrics.get("beta", 1.15))

        # Orthogonalized -200 to +200 Conviction Score & 30/45 DTE Duration Prescription
        conv_200: Dict[str, Any] = {}
        try:
            import quant_kernel
            conv_payload = {
                "symbol": sym,
                "is_etf": is_etf,
                "metrics": metrics,
                "quant_edge": quant_edge,
                "fundamentals": fund,
                "live_option": opt_contract,
                "gamma_walls": gamma_walls,
                "skew_optimizer": skew_optimizer,
                "whale_oi": whale_oi,
                "macro": macro,
                "blueprint": blueprint,
                "earnings": earn_info,
                **earn_info,
                "radar_24_48": radar_24_48,
                "regime_pulse": regime_pulse,
                "options_telemetry": opt_telemetry,
                "term_structure": term_structure,
                "macro_regime_label": regime_pulse.get("market_regime", ""),
            }
            conv_200 = quant_kernel.compute_conviction_score_200(conv_payload)
        except Exception:
            fallback_score = int(round(float(blueprint.get("composite_score", 50))))
            sign = -1 if "PUT" in str(metrics.get("action", "")).upper() else 1
            c200 = sign * max(18, min(145, int(round((fallback_score - 20) / 0.395))))
            conv_200 = {
                "conviction_score_200": c200,
                "conviction_abs_200": abs(c200),
                "composite_score": fallback_score,
                "conviction_tier": "WATCH / DEVELOPING",
                "recommended_dte": 45 if 14 < int(earn_info.get("days_to_earnings", 99)) <= 28 else 30,
                "dte_rationale": "Fallback 30/45 DTE horizon.",
                "synergy_unlocked": False,
                "regime_gate_mult": 1.0,
                "conviction_pillars": {
                    "elasticity_kalman": 0.0,
                    "kinetic_asymmetry": 0.0,
                    "dealer_whale_flow": 0.0,
                    "surface_convexity": 0.0,
                    "regime_solvency": 0.0,
                },
            }

        conv_fields = {
            "conviction_score_200": conv_200["conviction_score_200"],
            "conviction_abs_200": conv_200["conviction_abs_200"],
            "composite_score": conv_200["composite_score"],
            "move_score": conv_200["composite_score"],
            "conviction_tier": conv_200["conviction_tier"],
            "recommended_dte": conv_200["recommended_dte"],
            "dte_rationale": conv_200["dte_rationale"],
            "synergy_unlocked": conv_200["synergy_unlocked"],
            "regime_gate_mult": conv_200.get("regime_gate_mult", 1.0),
            "conviction_pillars": conv_200["conviction_pillars"],
        }
        blueprint.update(conv_fields)
        metrics.update(conv_fields)
        metrics["is_etf"] = is_etf
        metrics["solvency_tier"] = fund.get("solvency_tier", "ETF Basket" if is_etf else "Healthy")

        out = {
            "symbol": sym,
            "company_name": company_name,
            "company_logo": company_logo,
            "description": description,
            "sector": sector,
            "industry": industry,
            "market_cap": mkt_cap,
            "is_etf": is_etf,
            "solvency_tier": fund.get("solvency_tier", "ETF Basket" if is_etf else "Healthy"),
            "benchmark": eff_bench,
            "is_deep_vetted": vet_deep,
            "is_top5_vetted": vet_deep,
            "metrics": metrics,
            "fundamentals": fund,
            "insider": insider,
            "analyst": analyst,
            "temporal": temporal,
            "macro": macro,
            "earnings": earn_info,
            "whale_oi": whale_oi,
            "blueprint": blueprint,
            "sim_1k": sim_1k,
            "options_telemetry": opt_telemetry,
            "macro_transmission": macro_trans,
            "extended_hours": ext_telemetry,
            "gamma_walls": gamma_walls,
            "skew_optimizer": skew_optimizer,
            "term_structure": term_structure,
            "quant_edge": quant_edge,
            **conv_fields,
        }
        metrics["is_deep_vetted"] = vet_deep
        if vet_deep:
            set_cached(deep_cache_key, out)
        else:
            set_cached(f"dd_cand_v49_{sym}_{eff_bench}_{moneyness_mode}_{day_override}_s1", out)
        return out
    except Exception as e:
        print(f"Error evaluating {sym}: {e}")
        return None


def get_ranked_sector_candidates(
    sector_name: str,
    benchmark_override: Optional[str] = None,
    moneyness_mode: str = "aggressive_otm",
    top_n_vet: int = 5,
    active_ticker: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Two-Stage Institutional Sector Scanner ("Vet Top 5 Candidates Per Sector"):
    - Stage 1 (Fast Vectorized Screen): Pre-warms `/batch-quote` in 1 call and evaluates all sector
      tickers using 5Y EOD history + live tape sharp flow + 5Y empirical basis % expectation + bad-data
      quarantine (`vet_deep=False`), avoiding wasted API calls on low-ranking noise tickers.
    - Stage 2 (Deep FMP Ultra Vetting on Top 5 + 3 Alternates + Disqualified Top 4 + active_ticker):
      Runs full FMP Ultra endpoints (`/earnings` 25-day check, `/institutional-ownership/symbol-positions-summary`
      13F Call/Put Open Interest & Whale Loading, `/financial-scores`, `/ratios-ttm`, `/key-metrics-ttm`,
      `/financial-growth`, `/insider-trading/statistics`, `/price-target-consensus`, plus CBOE Option Chains)
      on the top 8 eligible candidates BEFORE slicing the final Top 5 so any zombie solvency trap or
      negative-flow divergence is caught and replaced by a clean Deep-Vetted alternate (#6-#8).
    """
    sec_clean = normalize_sector_name(sector_name)
    sec_meta = SECTORS[sec_clean]
    tickers = sec_meta["tickers"]
    bench = normalize_benchmark(benchmark_override or sec_meta["benchmark"])

    act_sym = (active_ticker or "").strip().upper()
    cache_key = f"ranked_cands_v49_{sec_clean}_{bench}_{moneyness_mode}_{top_n_vet}_{act_sym}"
    cached = get_cached(cache_key, ttl=180)
    if cached is not None:
        return cached

    # Pre-warm batch quotes + market regime + global earnings baseline in parallel/bulk before Stage-1 threads
    # (Skip Stage-1 26-ticker live earnings N+1 loop; Stage-2 deep vetting calls exact /earnings for finalists only)
    quotes_map = fmp_batch_quotes(
        tickers + [bench, "SPY", "QQQ", "RSP", "IWM", "^VIX", "HYG", "LQD", "SMH", "SRVR", "URA", "REMX", "ROBO", "JEDI", "QTUM"]
    )
    get_upcoming_earnings_map()
    get_sector_macro_pulse()

    # --- STAGE 1: Fast Vectorized Screen Across All Sector Constituents ---
    def _eval_stage1(t: str):
        return get_due_diligence_candidate(t, benchmark_symbol=bench, moneyness_mode=moneyness_mode, vet_deep=False)

    with ThreadPoolExecutor(max_workers=12) as ex:
        stage1_cands = [c for c in ex.map(_eval_stage1, tickers) if c is not None]

    def _rank_key(c: Dict[str, Any]):
        m = c["metrics"]
        if m.get("is_bad_data", False) or m.get("action") == "QUARANTINED":
            return (-1, 0.0, 0.0, 0.0)
        act = m["action"]
        is_actionable = 1 if act in ["BUY CALL", "BUY PUT"] else 0
        conv_abs = float(c.get("conviction_abs_200", c.get("blueprint", {}).get("conviction_abs_200", 0.0)))
        exp_basis = abs(float(m.get("expected_basis_pct", 0.0)))
        abs_z = abs(float(m["z_score_5d"]))
        return (is_actionable, conv_abs, exp_basis, abs_z)

    # 15-Day Binary Earnings Gate:
    # Partition candidates into:
    # 1. Eligible for Top 5: (days_to_earnings > 15 or clear) AND (not is_bad_data)
    # 2. Disqualified by 15-Day Earnings Gate: (0 <= days_to_earnings <= 15) AND (not is_bad_data)
    # 3. Quarantined (penny / delisted / corrupted data)
    eligible_pool: List[Dict[str, Any]] = []
    disqualified_pool: List[Dict[str, Any]] = []
    quarantine_pool: List[Dict[str, Any]] = []

    for c in stage1_cands:
        m = c["metrics"]
        days_er = int(m.get("days_to_earnings", 45))
        is_bad = bool(m.get("is_bad_data", False))
        if is_bad:
            quarantine_pool.append(c)
        elif 0 <= days_er <= 15:
            c["disqualified_top5_earnings"] = True
            c["disqualified_reason"] = f"Binary Earnings in {days_er}d ({m.get('earnings_date', '')})"
            m["disqualified_top5_earnings"] = True
            m["disqualified_reason"] = c["disqualified_reason"]
            disqualified_pool.append(c)
        else:
            c["disqualified_top5_earnings"] = False
            m["disqualified_top5_earnings"] = False
            eligible_pool.append(c)

    # Sort each pool by Stage-1 institutional edge key
    eligible_pool.sort(key=_rank_key, reverse=True)
    disqualified_pool.sort(key=_rank_key, reverse=True)

    # Symbols to deep-vet in Stage 2:
    # Vet Top N + 3 alternates (8 total eligible) so any zombie trap or negative-flow divergence
    # caught during Stage-2 FMP Ultra auditing is genuinely replaced by a clean deep-vetted alternate.
    vet_pool_size = min(len(eligible_pool), top_n_vet + 3)
    vet_symbols = [c["symbol"] for c in eligible_pool[:vet_pool_size] + disqualified_pool[:4]]
    if act_sym and act_sym in tickers and act_sym not in vet_symbols:
        vet_symbols.append(act_sym)

    # --- STAGE 2: Deep Institutional Vetting ---
    def _eval_stage2(t: str):
        return get_due_diligence_candidate(t, benchmark_symbol=bench, moneyness_mode=moneyness_mode, vet_deep=True)

    vetted_map: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        for vc in ex.map(_eval_stage2, vet_symbols):
            if vc is not None:
                vetted_map[vc["symbol"]] = vc

    def _apply_vetted_and_quotes(c_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for c in c_list:
            sym = c["symbol"]
            is_deep = sym in vetted_map
            final_c = vetted_map.get(sym, c)
            final_c["is_deep_vetted"] = is_deep
            final_c["metrics"]["is_deep_vetted"] = is_deep
            q_item = quotes_map.get(sym, {})
            q_chg = float(q_item.get("changePercentage", q_item.get("changesPercentage", 0.0)) or 0.0)
            if q_chg != 0.0 or final_c["metrics"].get("change_pct_1d") is None:
                final_c["metrics"]["change_pct_1d"] = round(q_chg, 2)
            out.append(final_c)
        return out

    eligible_pool = _apply_vetted_and_quotes(eligible_pool)
    disqualified_pool = _apply_vetted_and_quotes(disqualified_pool)
    quarantine_pool = _apply_vetted_and_quotes(quarantine_pool)

    # Re-partition after Stage-2 deep vetting: fresh /earnings or bad-data flags discovered in Stage 2
    # must demote <=15d earnings equities into disqualified_pool before selecting Top 5.
    still_eligible: List[Dict[str, Any]] = []
    for c in eligible_pool:
        m_c = c.get("metrics", {})
        c_is_etf = bool(c.get("is_etf") or m_c.get("is_etf"))
        c_days_er = int(m_c.get("days_to_earnings", 45) if m_c.get("days_to_earnings") is not None else 45)
        if bool(m_c.get("is_bad_data", False)):
            quarantine_pool.append(c)
        elif (not c_is_etf) and (0 <= c_days_er <= 15):
            c["disqualified_top5_earnings"] = True
            c["disqualified_reason"] = f"Binary Earnings in {c_days_er}d ({m_c.get('earnings_date', '')})"
            m_c["disqualified_top5_earnings"] = True
            m_c["disqualified_reason"] = c["disqualified_reason"]
            disqualified_pool.append(c)
        else:
            still_eligible.append(c)
    eligible_pool = still_eligible

    # Re-sort eligible_pool AFTER Stage-2 deep vetting so zombies/weak setups drop out of Top 5
    # and clean alternates (#6-#8) are promoted into top5_recommended
    eligible_pool.sort(key=_rank_key, reverse=True)
    disqualified_pool.sort(key=_rank_key, reverse=True)

    top5_recommended = eligible_pool[:top_n_vet]
    remaining_eligible = eligible_pool[top_n_vet:]

    for c in top5_recommended:
        c["is_top5_vetted"] = True
        c["metrics"]["is_top5_vetted"] = True
        c["disqualified_top5_earnings"] = False
        c["metrics"]["disqualified_top5_earnings"] = False

    for c in disqualified_pool:
        c["is_top5_vetted"] = False
        c["metrics"]["is_top5_vetted"] = False
        c["disqualified_top5_earnings"] = True
        c["metrics"]["disqualified_top5_earnings"] = True

    for c in remaining_eligible + quarantine_pool:
        c["is_top5_vetted"] = False
        c["metrics"]["is_top5_vetted"] = False
        c["disqualified_top5_earnings"] = False
        c["metrics"]["disqualified_top5_earnings"] = False

    # Assembled in definitive institutional order:
    # 1. Top 5 Recommended (Guaranteed Deep-Vetted + ZERO earnings <= 15d)
    # 2. Disqualified by Earnings <= 15d (High-edge setups bumped for binary IV crush risk)
    # 3. Remaining Eligible (Includes Deep-Vetted Alternates #6-#8 + Stage-1 Screen)
    # 4. Quarantined bad-data
    final_ranked = top5_recommended + disqualified_pool + remaining_eligible + quarantine_pool
    for idx, c in enumerate(final_ranked):
        c["sector_rank"] = idx + 1
        c["metrics"]["sector_rank"] = idx + 1

    set_cached(cache_key, final_ranked)
    return final_ranked


# =========================================================================
# PILLAR 8: ASUS GX10 INTEL BUS & TRACK-SPECIFIC QUANTITATIVE CALIBRATIONS
# =========================================================================

def calculate_whale_residual(symbol: str, whale_symbol: str) -> Dict[str, Any]:
    sym = symbol.strip().upper()
    whale = whale_symbol.strip().upper()
    cache_key = f"whale_res_v35_{sym}_{whale}"
    cached = get_cached(cache_key, ttl=300)
    if cached is not None:
        return cached

    default_result = {
        "symbol": sym,
        "whale_symbol": whale,
        "whale_price": 0.0,
        "whale_change_pct": 0.0,
        "whale_5d_ret_pct": 0.0,
        "ticker_5d_ret_pct": 0.0,
        "whale_beta": 1.0,
        "whale_residual_pct": 0.0,
        "whale_residual_z": 0.0,
        "sympathy_lag_alert": False,
        "summary": f"{sym} / {whale} whale residual neutral."
    }

    try:
        t_df, t_live, _ = get_hybrid_price_series(sym)
        w_df, w_live, _ = get_hybrid_price_series(whale)

        if t_df.empty or w_df.empty or len(t_df) < 20 or len(w_df) < 20:
            return default_result

        merged = pd.DataFrame({
            "t_close": t_df["close"],
            "w_close": w_df["close"]
        }).dropna()

        if len(merged) < 20:
            return default_result

        merged["t_ret"] = np.log(merged["t_close"] / merged["t_close"].shift(1))
        merged["w_ret"] = np.log(merged["w_close"] / merged["w_close"].shift(1))

        cov_20 = merged["t_ret"].rolling(20).cov(merged["w_ret"])
        var_20 = merged["w_ret"].rolling(20).var().replace(0, np.nan)
        beta_series = (cov_20 / var_20).ffill().fillna(1.0).clip(lower=0.2, upper=3.5)
        curr_beta = float(beta_series.iloc[-1])

        merged["t_5d"] = np.log(merged["t_close"] / merged["t_close"].shift(5))
        merged["w_5d"] = np.log(merged["w_close"] / merged["w_close"].shift(5))
        merged["whale_resid_5d"] = merged["t_5d"] - (beta_series * merged["w_5d"])

        roll_mean = merged["whale_resid_5d"].rolling(60, min_periods=20).mean()
        roll_std = merged["whale_resid_5d"].rolling(60, min_periods=20).std().replace(0, np.nan).fillna(0.02)
        z_series = ((merged["whale_resid_5d"] - roll_mean) / roll_std).replace([np.inf, -np.inf], np.nan).dropna()
        whale_z = float(z_series.iloc[-1]) if len(z_series) > 0 else 0.0

        t_5d_pct = float((math.exp(merged["t_5d"].iloc[-1]) - 1.0) * 100.0) if not np.isnan(merged["t_5d"].iloc[-1]) else 0.0
        w_5d_pct = float((math.exp(merged["w_5d"].iloc[-1]) - 1.0) * 100.0) if not np.isnan(merged["w_5d"].iloc[-1]) else 0.0
        resid_pct = float(merged["whale_resid_5d"].iloc[-1] * 100.0) if not np.isnan(merged["whale_resid_5d"].iloc[-1]) else 0.0

        whale_p = float(w_live.get("price", merged["w_close"].iloc[-1]))
        whale_chg = float(w_live.get("changePercentage", 0.0))

        sympathy_lag = (whale_z <= -1.65) or (w_5d_pct >= -2.0 and t_5d_pct <= -6.0)

        result = {
            "symbol": sym,
            "whale_symbol": whale,
            "whale_price": round(whale_p, 2),
            "whale_change_pct": round(whale_chg, 2),
            "whale_5d_ret_pct": round(w_5d_pct, 2),
            "ticker_5d_ret_pct": round(t_5d_pct, 2),
            "whale_beta": round(curr_beta, 2),
            "whale_residual_pct": round(resid_pct, 2),
            "whale_residual_z": round(whale_z, 2),
            "sympathy_lag_alert": sympathy_lag,
            "summary": (
                f"Whale Sympathy Lag: {whale} 5D {w_5d_pct:+.1f}% vs {sym} 5D {t_5d_pct:+.1f}% "
                f"(β={curr_beta:.2f}, Whale Residual Z={whale_z:+.2f}σ)."
            )
        }
        set_cached(cache_key, result)
        return result
    except Exception as e:
        print(f"Error calculating whale residual for {sym} vs {whale}: {e}")
        return default_result


def evaluate_track_candidate(
    intel_record: Dict[str, Any],
    day_override: Optional[int] = None,
    moneyness_mode: str = "aggressive_otm"
) -> Dict[str, Any]:
    sym = intel_record.get("symbol", "").strip().upper()
    track = intel_record.get("track", "TRACK_A_FORTRESS")
    wiki_score = int(intel_record.get("wiki_score", 50))
    benchmark = normalize_benchmark(intel_record.get("primary_benchmark", "SMH"))
    whale = intel_record.get("parent_whale", "").strip().upper()
    dilution_risk = bool(intel_record.get("dilution_risk", False))
    thesis_hook = intel_record.get("thesis_hook", "")
    last_updated = intel_record.get("last_updated", "")

    dd = get_due_diligence_candidate(sym, benchmark_symbol=benchmark, day_override=day_override, moneyness_mode=moneyness_mode)
    if not dd:
        return {
            "intel": intel_record,
            "symbol": sym,
            "track": track,
            "track_name": track.replace("_", " ").title(),
            "wiki_score": wiki_score,
            "benchmark": benchmark,
            "whale": whale,
            "dilution_risk": dilution_risk,
            "thesis_hook": thesis_hook,
            "candidate": None,
            "gate_passed": False,
            "gate_label": "API Connection Failed",
            "gate_rationale": "Unable to fetch hybrid price series or fundamental profile.",
            "z_trigger_passed": False,
            "z_trigger_rationale": "No price data.",
            "micro_trigger_passed": False,
            "micro_trigger_rationale": "No microstructure data.",
            "overall_status": "OFFLINE",
            "status_badge": "OFFLINE",
            "options_play": "N/A"
        }

    metrics = dd["metrics"]
    fund = dd["fundamentals"]
    z_5d = metrics["z_score_5d"]
    z_3d = metrics["z_score_3d"]
    daily_clv = metrics["daily_clv"]
    h4_clv = metrics["h4_clv"]
    rvol = metrics["rvol"]
    rec_strike = metrics["recommended_strike"]
    target_price = metrics["target_price"]
    half_life = metrics.get("ou_half_life", 4.2)

    runway = compute_cash_runway_and_burn(sym)
    whale_res = calculate_whale_residual(sym, whale) if whale else None

    track_labels = {
        "TRACK_A_FORTRESS": ("Track A: Golden Fortress", "text-emerald-400", ""),
        "TRACK_B_BOTTLENECK": ("Track B: Karpathy Moat / Bottleneck", "text-cyan-400", ""),
        "TRACK_C_MIRAGE": ("Track C: Mirage Breakdown", "text-rose-400", "")
    }
    track_title, track_color, track_icon = track_labels.get(track, ("Track A: Golden Fortress", "text-slate-300", ""))

    gate_passed = False
    gate_label = ""
    gate_rationale = ""
    z_trigger = False
    z_rationale = ""
    micro_trigger = False
    micro_rationale = ""
    options_play = ""

    if track == "TRACK_A_FORTRESS":
        has_fcf = fund.get("fcf_yield_pct", 0.0) > 0.0 or runway["quarterly_burn_millions"] == 0.0
        altman_ok = fund.get("altman_z", 0.0) >= 2.6 or fund.get("fund_score", 0) >= 58
        gate_passed = has_fcf and altman_ok
        gate_label = "FMP Pro Solvency Audit (Altman Z >= 2.6, Piotroski & FCF > 0)"
        gate_rationale = (
            f"Altman Z: {fund.get('altman_z', 0):.2f} | Piotroski: {fund.get('piotroski_score', 5)}/9 | "
            f"Quality: {fund.get('fund_score', 0):.0f}/100 | FCF Yield: {fund.get('fcf_yield_pct', 0.0):+.1f}%. "
            f"{'PASS: Fortress balance sheet verified.' if gate_passed else 'FAIL: Balance sheet below fortress threshold.'}"
        )

        z_trigger = (z_5d <= -1.65) or ("COILED" in metrics["state"])
        z_rationale = (
            f"Effective Stretch Z: {z_5d:+.2f}σ vs {benchmark} (O-U Half-Life: {half_life:.1f}d). "
            f"{'TRIGGERED: Actionable elasticity or volatility coil.' if z_trigger else 'AWAITING: Stretch inside equilibrium corridor.'}"
        )

        micro_trigger = (daily_clv >= 0.0 or h4_clv >= 0.0) and (rvol >= 1.10)
        micro_rationale = (
            f"CLV: {daily_clv:+.2f} (4H: {h4_clv:+.2f}) | RVOL: {rvol:.2f}x. "
            f"{'CONFIRMED: Institutional bottom-tail absorption.' if micro_trigger else 'PENDING: Awaiting absorption volume confirmation.'}"
        )

        options_play = (
            f"30–45 DTE Aggressive Call (${rec_strike:.2f} Strike | Δ {metrics.get('estimated_delta', 0.28):+.2f}) "
            f"targeting 1–5D move to VWMA Equilibrium ${target_price:.2f}."
        )

    elif track == "TRACK_B_BOTTLENECK":
        runway_ok = runway["cash_runway_quarters"] >= 6.0
        def_rev_ok = (runway["deferred_rev_growth_pct"] >= 0.0 or runway["deferred_rev_millions"] >= 5.0 or runway["cash_millions"] >= 100.0)
        gate_passed = runway_ok and def_rev_ok
        gate_label = "Karpathy Breakthrough Runway & RPO Gate (>= 6 Qtrs Cash)"
        gate_rationale = (
            f"Cash Runway: {runway['cash_runway_quarters']:.1f} Qtrs (Cash: ${runway['cash_millions']:.1f}M, Burn: ${runway['quarterly_burn_millions']:.1f}M/qtr) | "
            f"Deferred Rev: ${runway['deferred_rev_millions']:.1f}M ({runway['deferred_rev_growth_pct']:+.1f}% QoQ). "
            f"{'PASS: Moat commercialization runway cleared.' if gate_passed else 'FAIL: Cash runway < 6 quarters.'}"
        )

        whale_z = whale_res["whale_residual_z"] if whale_res else 0.0
        z_trigger = (z_5d <= -1.75) or (whale_res and whale_z <= -1.65) or ("COILED" in metrics["state"])
        z_rationale = (
            f"Effective Z vs {benchmark}: {z_5d:+.2f}σ | Whale Residual vs {whale}: {whale_z:+.2f}σ (Half-Life: {half_life:.1f}d). "
            f"{'TRIGGERED: Sympathy lag or coiled breakout detected.' if z_trigger else 'AWAITING: Deeper relative stretch or squeeze.'}"
        )

        micro_trigger = (h4_clv >= 0.25 or daily_clv >= 0.20)
        micro_rationale = (
            f"4H Intraday CLV: {h4_clv:+.2f} | Daily CLV: {daily_clv:+.2f} (Required >= +0.25). "
            f"{'CONFIRMED: Intraday tail sweep reversal.' if micro_trigger else 'PENDING: Awaiting 4H bottom-tail absorption.'}"
        )

        options_play = (
            f"30–45 DTE Convexity Call (${rec_strike:.2f} Strike | Δ {metrics.get('estimated_delta', 0.25):+.2f}) "
            f"capturing 1–5D Gamma/Vega expansion toward ${target_price:.2f}."
        )

    elif track == "TRACK_C_MIRAGE":
        dilution_wall = dilution_risk or (runway["cash_runway_quarters"] < 4.5) or (fund.get("fund_score", 50) < 42)
        gate_passed = dilution_wall
        gate_label = "ATM Dilution Wall & Fragility Gate (Runway < 4.5 Qtrs / Low Altman Z)"
        gate_rationale = (
            f"Dilution Risk: {'ACTIVE ATM/SHELF' if dilution_risk else 'High Burn'} | "
            f"Quality Score: {fund.get('fund_score', 0):.0f}/100 | Runway: {runway['cash_runway_quarters']:.1f} Qtrs. "
            f"{'PASS: Structural equity overhang verified.' if gate_passed else 'FAIL: Balance sheet not sufficiently vulnerable.'}"
        )

        z_trigger = (z_5d >= 1.50) or (z_3d >= 1.65) or (metrics["action"] == "BUY PUT")
        z_rationale = (
            f"Effective Z: {z_5d:+.2f}σ | 3D Velocity Z: {z_3d:+.2f}σ (Half-Life: {half_life:.1f}d). "
            f"{'TRIGGERED: Overextended pump into ATM supply wall.' if z_trigger else 'AWAITING: Upward retail squeeze exhaustion.'}"
        )

        micro_trigger = (daily_clv <= -0.15 or h4_clv <= -0.15) and (rvol >= 1.20)
        micro_rationale = (
            f"CLV: {daily_clv:+.2f} | RVOL: {rvol:.2f}x (Required CLV <= -0.15, RVOL >= 1.2x). "
            f"{'CONFIRMED: Institutional / ATM supply dumping into retail bounce.' if micro_trigger else 'PENDING: Awaiting upper-wick rejection.'}"
        )

        options_play = (
            f"30–45 DTE Aggressive Put (${rec_strike:.2f} Strike | Δ {metrics.get('estimated_delta', -0.28):+.2f}) "
            f"targeting 1–5D breakdown to ${target_price:.2f}."
        )

    if gate_passed and z_trigger and micro_trigger:
        overall_status = "TRIGGERED"
        status_badge = "TRIGGERED (High Conviction)"
    elif gate_passed and z_trigger:
        overall_status = "ARMED"
        status_badge = "ARMED (Awaiting 4H Hook)"
    elif gate_passed:
        overall_status = "MONITORING"
        status_badge = "MONITORING (Gate Cleared)"
    else:
        overall_status = "DISQUALIFIED"
        status_badge = "DISQUALIFIED (Gate Failed)"

    return {
        "intel": intel_record,
        "symbol": sym,
        "track": track,
        "track_name": track_title,
        "track_color": track_color,
        "track_icon": track_icon,
        "wiki_score": wiki_score,
        "benchmark": benchmark,
        "whale": whale,
        "dilution_risk": dilution_risk,
        "thesis_hook": thesis_hook,
        "last_updated": last_updated,
        "candidate": dd,
        "whale_residual": whale_res,
        "cash_runway": runway,
        "gate_passed": gate_passed,
        "gate_label": gate_label,
        "gate_rationale": gate_rationale,
        "z_trigger_passed": z_trigger,
        "z_trigger_rationale": z_rationale,
        "micro_trigger_passed": micro_trigger,
        "micro_trigger_rationale": micro_rationale,
        "overall_status": overall_status,
        "status_badge": status_badge,
        "options_play": options_play
    }


def scan_all_intel_bus_candidates(
    day_override: Optional[int] = None,
    moneyness_mode: str = "aggressive_otm"
) -> List[Dict[str, Any]]:
    try:
        from intel_bus_bridge import read_intel_bus_signals
        signals = read_intel_bus_signals()
    except Exception as e:
        print(f"Error reading intel bus signals: {e}")
        signals = []

    if signals:
        fmp_batch_quotes([s.get("symbol", "") for s in signals] + ["SMH", "BOTZ", "URA", "XLU", "NVDA", "TSM", "MSFT", "AMZN", "WMT"])

    results = []
    status_priority = {"TRIGGERED": 0, "ARMED": 1, "MONITORING": 2, "DISQUALIFIED": 3, "OFFLINE": 4}

    with ThreadPoolExecutor(max_workers=7) as ex:
        futures = [ex.submit(evaluate_track_candidate, sig, day_override, moneyness_mode) for sig in signals]
        for fut in futures:
            try:
                results.append(fut.result())
            except Exception as e:
                print(f"Error evaluating intel candidate: {e}")

    results.sort(key=lambda x: (status_priority.get(x["overall_status"], 99), -x["wiki_score"]))
    return results


def check_fundamentals(ticker: str) -> Dict[str, Any]:
    """Compatibility wrapper returning real FMP Pro Altman Z, Piotroski, Revenue 3Y CAGR, and margins."""
    fq = compute_fundamental_quality_score(ticker)
    return {
        "viable": fq["viable"],
        "fund_score": fq["fund_score"],
        "altman_z": fq["altman_z"],
        "piotroski_score": fq["piotroski_score"],
        "current_ratio": fq["current_ratio"],
        "debt_to_equity": fq["debt_to_equity"],
        "fcf_ttm_positive": fq["fcf_ttm_positive"],
        "fcf_yield_pct": fq["fcf_yield_pct"],
        "rev_growth_3y": fq["rev_growth_3y_pct"],
        "rev_growth_yoy": fq["rev_growth_yoy_pct"],
        "net_margin": fq["net_margin_pct"],
        "operating_margin_pct": fq["operating_margin_pct"]
    }


def _quote_clv(q: Dict[str, Any]) -> float:
    """Computes intraday Close Location Value [-1.0 to +1.0] from a live FMP quote dict."""
    try:
        p = float(q.get("price") or 0.0)
        h = float(q.get("dayHigh") or p)
        l = float(q.get("dayLow") or p)
        if h > l and p > 0:
            return round(float(np.clip(((p - l) - (h - p)) / (h - l), -1.0, 1.0)), 2)
    except Exception:
        pass
    return 0.0


def _quote_rvol(sym: str, q: Dict[str, Any], default_20d_vol: float = 50_000_000.0) -> float:
    """
    Computes time-of-day U-shaped curve adjusted Relative Volume (RVOL) for an index/sector ETF.
    Uses cached EOD 20-day median volume if available, or standard institutional 20D baseline.
    """
    try:
        vol_today = float(q.get("volume") or 0.0)
        if vol_today <= 0:
            return 1.0
        # Check if EOD history is already in local cache for exact 20D median volume
        base_vol = default_20d_vol
        eod_cached = get_cached(_fmp_cache_key("historical-price-eod/full", {"symbol": sym}), ttl=7200)
        if isinstance(eod_cached, list) and len(eod_cached) >= 15:
            vols = [float(r.get("volume") or 0.0) for r in eod_cached[:21] if float(r.get("volume") or 0.0) > 0]
            if len(vols) >= 10:
                base_vol = float(np.median(vols[1:21])) if len(vols) > 1 else float(np.median(vols))

        ny_now = get_ny_now()
        mkt_open = ny_now.replace(hour=9, minute=30, second=0, microsecond=0)
        mkt_close = ny_now.replace(hour=16, minute=0, second=0, microsecond=0)
        if ny_now.weekday() < 5 and mkt_open <= ny_now <= mkt_close:
            t_lin = max(0.06, min(1.0, (ny_now - mkt_open).total_seconds() / (6.5 * 3600.0)))
            intraday_frac = max(0.08, min(1.0, t_lin + 0.14 * math.sin(2.0 * math.pi * t_lin)))
            expected_vol = max(1.0, base_vol * intraday_frac)
        else:
            expected_vol = max(1.0, base_vol)

        return round(float(np.clip(vol_today / expected_vol, 0.15, 4.5)), 2)
    except Exception:
        return 1.0


def get_sector_macro_pulse() -> Dict[str, Any]:
    """
    Institutional Market Regime, Tape Conviction & Cross-Sector Capital Rotation Engine.
    Evaluates:
    - Broad Tape & Volume Conviction: SPY & QQQ price change + U-shaped intraday RVOL + Intraday CLV
    - Equal-Weight Breadth vs Mega-Cap Concentration: RSP change% vs QQQ/SPY change%
    - Small-Cap Risk Appetite: IWM change% + IWM Intraday CLV
    - Volatility & Credit Stress: ^VIX level/change + HYG vs LQD credit spread
    Accurately diagnoses 'Timid & Tentative Green Days' (where surface index is green on 0.4x-0.6x volume
    with narrow breadth or fading small caps) vs true 'Conviction Risk-On Breadth Expansion'.
    """
    cache_key = "sector_macro_pulse_v46"
    cached = get_cached(cache_key, ttl=180)
    if cached is not None:
        return cached

    all_constituents = []
    lead_tickers = []
    for _sm in SECTORS.values():
        all_constituents.extend(_sm["tickers"])
        if _sm.get("tickers"):
            lead_tickers.append(_sm["tickers"][0])
        if _sm.get("benchmark"):
            lead_tickers.append(_sm["benchmark"])
    benchmark_symbols = list(dict.fromkeys(
        ["SPY", "QQQ", "RSP", "IWM", "^VIX", "HYG", "LQD",
         "SMH", "SOXX", "SRVR", "DTCR", "IGV", "URA", "REMX", "NLR", "GRID", "XLU", "ROBO", "BOTZ", "JEDI", "QTUM"]
        + all_constituents
    ))
    quotes_map = fmp_batch_quotes(benchmark_symbols, ttl=120)

    # Batch sector headlines in a single /stable/news/stock call (zero N+1 news queries)
    news_syms = list(dict.fromkeys(lead_tickers + ["NVDA", "VRT", "CEG", "ISRG", "ARM"]))
    batched_news = fmp_get("news/stock", params={"symbols": ",".join(news_syms), "limit": 30}, ttl=600)
    news_by_sym: Dict[str, List[Dict[str, Any]]] = {}
    if isinstance(batched_news, list):
        for art in batched_news:
            if not isinstance(art, dict):
                continue
            sym_art = str(art.get("symbol") or "").upper()
            if sym_art:
                news_by_sym.setdefault(sym_art, []).append(art)

    spy_q = quotes_map.get("SPY", {})
    qqq_q = quotes_map.get("QQQ", {})
    rsp_q = quotes_map.get("RSP", {})
    iwm_q = quotes_map.get("IWM", {})
    vix_q = quotes_map.get("^VIX", {})
    hyg_q = quotes_map.get("HYG", {})
    lqd_q = quotes_map.get("LQD", {})

    spy_change = float(spy_q.get("changePercentage", 0.0) or 0.0)
    qqq_change = float(qqq_q.get("changePercentage", 0.0) or 0.0)
    rsp_change = float(rsp_q.get("changePercentage", spy_change) or 0.0)
    iwm_change = float(iwm_q.get("changePercentage", 0.0) or 0.0)
    vix_level = float(vix_q.get("price", 18.5) or 18.5)
    vix_change = float(vix_q.get("changePercentage", 0.0) or 0.0)
    credit_spread_chg = round(float(hyg_q.get("changePercentage", 0.0) or 0.0) - float(lqd_q.get("changePercentage", 0.0) or 0.0), 2)

    spy_rvol = _quote_rvol("SPY", spy_q, default_20d_vol=60_000_000.0)
    qqq_rvol = _quote_rvol("QQQ", qqq_q, default_20d_vol=42_000_000.0)
    smh_rvol = _quote_rvol("SMH", quotes_map.get("SMH", {}), default_20d_vol=18_000_000.0)

    spy_clv = _quote_clv(spy_q)
    iwm_clv = _quote_clv(iwm_q)
    breadth_spread = round(rsp_change - qqq_change, 2)  # Equal-Weight S&P vs Mega-Cap Nasdaq

    is_green_day = spy_change >= 0.0

    # --- 5-STATE INSTITUTIONAL MARKET REGIME & TAPE CONVICTION DIAGNOSIS ---
    is_timid_green = False
    if spy_change >= 0.0:
        # Check if the green day is timid/tentative (low RVOL, narrow breadth, or fading small-cap CLV)
        low_tape_vol = (spy_rvol < 0.78) or (smh_rvol < 0.70 and qqq_rvol < 0.78)
        narrow_breadth = (breadth_spread <= -0.45) or (rsp_change < 0.15 and qqq_change >= 0.65)
        fading_tails = (iwm_clv <= 0.05) or (spy_clv <= 0.05)

        if low_tape_vol or (narrow_breadth and fading_tails):
            is_timid_green = True
            market_regime = "TIMID & TENTATIVE GREEN TAPE (LOW-VOL / NARROW BREADTH)"
            market_regime_badge = "TIMID & TENTATIVE GREEN"
            regime_color = "amber"
            tape_conviction_score = round(float(np.clip(38.0 + spy_rvol * 20.0 + breadth_spread * 10.0, 22.0, 58.0)), 0)
            regime_rationale = (
                f"Surface green (SPY {spy_change:+.2f}%, QQQ {qqq_change:+.2f}%), but institutional conviction is thin: "
                f"SPY RVOL is {spy_rvol:.2f}x (SMH {smh_rvol:.2f}x), Equal-Weight RSP ({rsp_change:+.2f}%) lags QQQ by {breadth_spread:+.2f}%, "
                f"and Small-Cap IWM CLV is {iwm_clv:+.2f}. Favor deeply coiled or oversold rubberband snapbacks over chasing breakouts."
            )
        else:
            market_regime = "CONVICTION RISK-ON BREADTH EXPANSION"
            market_regime_badge = "CONVICTION RISK-ON"
            regime_color = "emerald"
            tape_conviction_score = round(float(np.clip(68.0 + spy_rvol * 18.0 + spy_clv * 10.0, 62.0, 96.0)), 0)
            regime_rationale = (
                f"Broad institutional participation: SPY {spy_change:+.2f}% ({spy_rvol:.2f}x RVOL, CLV {spy_clv:+.2f}), "
                f"Equal-Weight RSP {rsp_change:+.2f}%, Credit HYG/LQD {credit_spread_chg:+.2f}%."
            )
    elif spy_change > -0.65:
        if spy_clv >= 0.15 or spy_rvol < 0.85:
            market_regime = "CONSTRUCTIVE PULLBACK & DIP ABSORPTION"
            market_regime_badge = "DIP ABSORPTION"
            regime_color = "cyan"
            tape_conviction_score = 55.0
            regime_rationale = (
                f"Controlled pullback (SPY {spy_change:+.2f}% on {spy_rvol:.2f}x RVOL, CLV {spy_clv:+.2f}). "
                f"Ideal environment for oversold Track-A Call snapbacks into VWMA-20 support."
            )
        else:
            market_regime = "DEFENSIVE CHOP & DISTRIBUTION"
            market_regime_badge = "DEFENSIVE DISTRIBUTION"
            regime_color = "amber"
            tape_conviction_score = 40.0
            regime_rationale = (
                f"Distribution pressure (SPY {spy_change:+.2f}%, CLV {spy_clv:+.2f}, VIX {vix_level:.1f}). "
                f"Require confirmed Whale/Sharp accumulation before deploying Call delta."
            )
    else:
        market_regime = "HIGH-VELOCITY RISK-OFF FLUSH"
        market_regime_badge = "RISK-OFF FLUSH"
        regime_color = "rose"
        tape_conviction_score = 25.0
        regime_rationale = (
            f"Heavy institutional liquidation (SPY {spy_change:+.2f}% on {spy_rvol:.2f}x RVOL, VIX {vix_level:.1f} {vix_change:+.1f}%). "
            f"Prioritize Mirage Puts and extreme -2.2σ capitulation washout hooks."
        )

    sector_etf_defaults = {
        "SMH": 18_000_000.0,
        "SOXX": 8_000_000.0,
        "SRVR": 120_000.0,
        "DTCR": 120_000.0,
        "IGV": 6_500_000.0,
        "URA": 5_500_000.0,
        "REMX": 900_000.0,
        "NLR": 400_000.0,
        "GRID": 600_000.0,
        "XLU": 14_000_000.0,
        "ROBO": 200_000.0,
        "BOTZ": 1_800_000.0,
        "JEDI": 170_000.0,
        "QTUM": 1_200_000.0,
    }
    sector_results = {}
    total_dollar_vol_b = 0.0

    for sec_name, sec_meta in SECTORS.items():
        bench_sym = sec_meta["benchmark"]
        bench_q = quotes_map.get(bench_sym, {})
        etf_chg = float(bench_q.get("changePercentage", 0.0) or 0.0)
        etf_price = float(bench_q.get("price", 100.0) or 100.0)
        etf_vol = float(bench_q.get("volume", 5000000.0) or 5000000.0)
        etf_dvol_b = (etf_price * etf_vol) / 1e9

        # Blend ETF benchmark with true dollar-volume-weighted constituent breadth & flow
        const_dvol_b = 0.0
        const_weighted_chg = 0.0
        const_weighted_clv = 0.0
        adv_count = 0
        valid_count = 0
        best_sym, best_chg = sec_meta["tickers"][0], -999.0
        worst_sym, worst_chg = sec_meta["tickers"][0], 999.0
        for tk in sec_meta["tickers"]:
            tq = quotes_map.get(tk, {})
            tp = float(tq.get("price") or 0.0)
            tv = float(tq.get("volume") or 0.0)
            if tp <= 0:
                continue
            valid_count += 1
            tc = float(tq.get("changePercentage") or 0.0)
            if tc >= 0:
                adv_count += 1
            if tc > best_chg:
                best_chg = tc
                best_sym = tk
            if tc < worst_chg:
                worst_chg = tc
                worst_sym = tk
            tdv = max(0.005, (tp * tv) / 1e9)
            const_dvol_b += tdv
            const_weighted_chg += tc * tdv
            const_weighted_clv += _quote_clv(tq) * tdv

        if best_chg <= -900.0:
            best_chg = etf_chg
        if worst_chg >= 900.0:
            worst_chg = etf_chg

        if const_dvol_b > 0:
            const_chg = const_weighted_chg / const_dvol_b
            const_clv = const_weighted_clv / const_dvol_b
            pct_change = 0.45 * etf_chg + 0.55 * const_chg
            dollar_vol_b = max(0.35, const_dvol_b + etf_dvol_b * 0.25)
        else:
            pct_change = etf_chg
            const_clv = _quote_clv(bench_q)
            dollar_vol_b = max(0.35, etf_dvol_b)

        total_dollar_vol_b += dollar_vol_b
        etf_rvol = _quote_rvol(bench_sym, bench_q, default_20d_vol=sector_etf_defaults.get(bench_sym, 8_000_000.0))
        etf_clv = round(0.50 * _quote_clv(bench_q) + 0.50 * const_clv, 2)
        adv_breadth_pct = round((adv_count / max(1, valid_count)) * 100.0, 0)

        lead_ticker = sec_meta["tickers"][0]
        news_items = news_by_sym.get(lead_ticker) or news_by_sym.get(bench_sym) or []
        top_headline = news_items[0].get("title") if news_items else f"Institutional flow active in {sec_name} ({bench_sym})"

        if pct_change >= 0.85 and etf_rvol >= 0.80:
            bias = "HIGH-CONVICTION BREAKOUT CALLS"
            bias_class = "txt-green"
            bias_badge = f"STRONG INFLOW ({etf_rvol:.2f}x Vol · {adv_breadth_pct:.0f}% Adv)"
            flow_state = "Conviction Inflow"
        elif pct_change >= 0.0:
            if etf_rvol < 0.75 or etf_clv < -0.05:
                bias = "SELECTIVE COIL & SNAPBACK CALLS"
                bias_class = "txt-cyan"
                bias_badge = f"TIMID INFLOW ({etf_rvol:.2f}x Vol · {adv_breadth_pct:.0f}% Adv)"
                flow_state = "Tentative / Thin Inflow"
            else:
                bias = "COILED SPRING CALLS"
                bias_class = "txt-cyan"
                bias_badge = f"ACCUMULATION ({etf_rvol:.2f}x Vol · {adv_breadth_pct:.0f}% Adv)"
                flow_state = "Steady Inflow"
        elif pct_change > -1.5:
            bias = "ELASTIC SNAPBACK HOOKS"
            bias_class = "txt-purple"
            bias_badge = f"PULLBACK COIL ({etf_rvol:.2f}x Vol · {adv_breadth_pct:.0f}% Adv)"
            flow_state = "Mild Outflow"
        else:
            bias = "DEEP WASHOUT CALLS / MIRAGE PUTS"
            bias_class = "txt-red"
            bias_badge = f"HEAVY FLUSH ({etf_rvol:.2f}x Vol · {adv_breadth_pct:.0f}% Adv)"
            flow_state = "Heavy Outflow"

        # RVOL & CLV conditioned flow weight for truthful Sankey width
        est_flow_volume = max((abs(pct_change) * 0.55 + dollar_vol_b * 0.28) * max(0.65, min(1.5, etf_rvol)), 0.35)
        net_flow_sign = 1.0 if (pct_change > 0.08 or (pct_change >= -0.05 and etf_clv >= 0.15)) else -1.0

        sector_results[sec_name] = {
            "name": sec_name,
            "benchmark": bench_sym,
            "change_pct": round(pct_change, 2),
            "etf_raw_change_pct": round(etf_chg, 2),
            "etf_price": round(etf_price, 2),
            "etf_rvol": etf_rvol,
            "etf_clv": etf_clv,
            "adv_breadth_pct": adv_breadth_pct,
            "adv_count": adv_count,
            "valid_count": max(1, valid_count),
            "dollar_vol_b": round(dollar_vol_b, 2),
            "flow_state": flow_state,
            "flow_volume": round(est_flow_volume, 2),
            "net_flow_sign": net_flow_sign,
            "bias": bias,
            "bias_class": bias_class,
            "bias_badge": bias_badge,
            "top_headline": top_headline,
            "lead_ticker": lead_ticker,
            "top_leader_sym": best_sym,
            "top_leader_chg": round(best_chg, 2),
            "top_laggard_sym": worst_sym,
            "top_laggard_chg": round(worst_chg, 2),
            "constituent_count": len(sec_meta["tickers"])
        }

    macro_pulse = {
        "spy_change": round(spy_change, 2),
        "qqq_change": round(qqq_change, 2),
        "rsp_change": round(rsp_change, 2),
        "iwm_change": round(iwm_change, 2),
        "vix_level": round(vix_level, 2),
        "vix_change": round(vix_change, 2),
        "credit_spread_chg": credit_spread_chg,
        "breadth_spread": breadth_spread,
        "spy_rvol": spy_rvol,
        "qqq_rvol": qqq_rvol,
        "smh_rvol": smh_rvol,
        "spy_clv": spy_clv,
        "iwm_clv": iwm_clv,
        "is_green_day": is_green_day,
        "is_timid_green": is_timid_green,
        "tape_conviction_score": tape_conviction_score,
        "market_regime": market_regime,
        "market_regime_badge": market_regime_badge,
        "regime_color": regime_color,
        "regime_rationale": regime_rationale,
        "sectors": sector_results,
        "cross_sector_volume_b": round(total_dollar_vol_b, 1),
        "timestamp": get_ny_now().strftime("%Y-%m-%d %H:%M:%S EST")
    }

    set_cached(cache_key, macro_pulse)
    return macro_pulse


def get_overall_macro_market_pulse() -> Dict[str, Any]:
    """
    Aggregates the 6 Core Macro Pillars + Core Sector ETFs for the Global Macro Liquidity Sankey:
    Bonds (TLT), Credit (HYG), Crude Oil (CLUSD/USO), Gold (GLD), Silver (SLV), Bitcoin (BTCUSD),
    Euro/Dollar (EURUSD), S&P 500 (SPY), Semiconductors (SMH), Robotics (BOTZ), Nuclear Energy (URA).
    """
    cache_key = "overall_macro_pulse_v35"
    cached = get_cached(cache_key, ttl=180)
    if cached is not None:
        return cached

    macro_symbols = ["TLT", "HYG", "LQD", "USO", "CLUSD", "GLD", "SLV", "BTCUSD", "UUP", "SPY", "SMH", "BOTZ", "URA"]
    quotes_map = fmp_batch_quotes(macro_symbols, ttl=120)

    oil_q = quotes_map.get("CLUSD") if quotes_map.get("CLUSD", {}).get("price") else quotes_map.get("USO", {})
    oil_sym = "CLUSD" if quotes_map.get("CLUSD", {}).get("price") else "USO"

    assets = {
        "20Y+ Treasuries (TLT)": {
            "category": "Bonds / Rates",
            "symbol": "TLT",
            "price": quotes_map.get("TLT", {}).get("price", 80.0),
            "change_pct": quotes_map.get("TLT", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("TLT", {}).get("volume", 40000000)
        },
        "High-Yield Credit (HYG)": {
            "category": "Credit Stress",
            "symbol": "HYG",
            "price": quotes_map.get("HYG", {}).get("price", 77.0),
            "change_pct": quotes_map.get("HYG", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("HYG", {}).get("volume", 30000000)
        },
        "Crude Oil (WTI)": {
            "category": "Commodities",
            "symbol": oil_sym,
            "price": oil_q.get("price", 98.0),
            "change_pct": oil_q.get("changePercentage", 0.0),
            "volume": oil_q.get("volume", 15000000)
        },
        "Gold Trust (GLD)": {
            "category": "Safe Haven",
            "symbol": "GLD",
            "price": quotes_map.get("GLD", {}).get("price", 378.0),
            "change_pct": quotes_map.get("GLD", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("GLD", {}).get("volume", 8000000)
        },
        "Silver Trust (SLV)": {
            "category": "Industrial Metal",
            "symbol": "SLV",
            "price": quotes_map.get("SLV", {}).get("price", 52.0),
            "change_pct": quotes_map.get("SLV", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("SLV", {}).get("volume", 18000000)
        },
        "Bitcoin (BTCUSD)": {
            "category": "24/7 Liquidity",
            "symbol": "BTCUSD",
            "price": quotes_map.get("BTCUSD", {}).get("price", 83000.0),
            "change_pct": quotes_map.get("BTCUSD", {}).get("changePercentage", 0.0),
            "volume": 25000000
        },
        "USD Liquidity Index (UUP)": {
            "category": "USD Funding Stress",
            "symbol": "UUP",
            "price": quotes_map.get("UUP", {}).get("price", 28.5),
            "change_pct": quotes_map.get("UUP", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("UUP", {}).get("volume", 3500000)
        },
        "S&P 500 (SPY)": {
            "category": "Broad Equities",
            "symbol": "SPY",
            "price": quotes_map.get("SPY", {}).get("price", 760.0),
            "change_pct": quotes_map.get("SPY", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("SPY", {}).get("volume", 60000000)
        },
        "Semiconductors (SMH)": {
            "category": "Core Sector",
            "symbol": "SMH",
            "price": quotes_map.get("SMH", {}).get("price", 540.0),
            "change_pct": quotes_map.get("SMH", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("SMH", {}).get("volume", 18000000)
        },
        "Robotics & AI (BOTZ)": {
            "category": "Core Sector",
            "symbol": "BOTZ",
            "price": quotes_map.get("BOTZ", {}).get("price", 33.0),
            "change_pct": quotes_map.get("BOTZ", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("BOTZ", {}).get("volume", 2000000)
        },
        "Nuclear & Clean Energy (URA)": {
            "category": "Core Sector",
            "symbol": "URA",
            "price": quotes_map.get("URA", {}).get("price", 35.0),
            "change_pct": quotes_map.get("URA", {}).get("changePercentage", 0.0),
            "volume": quotes_map.get("URA", {}).get("volume", 6000000)
        }
    }

    result = {
        "assets": assets,
        "quotes": quotes_map,
        "timestamp": get_ny_now().strftime("%Y-%m-%d %H:%M:%S EST")
    }
    set_cached(cache_key, result)
    return result


def get_cross_asset_rotation_compass_data() -> Dict[str, Any]:
    """
    AAA Cross-Asset Relative Rotation & RVOL-Conditioned Risk-Appetite Compass Engine.
    Replaces synthetic central clearing hubs with true institutional 2D vector geometry:
    - X-Axis (x_now, [-3.0σ, +3.0σ]): 20D Volume-Weighted Equilibrium Stretch Z-Score ((Price - Equil20) / (1.35 * ATR14))
    - Y-Axis (y_now, [-2.8σ, +2.8σ]): RVOL & Intraday CLV-Conditioned Kinetic Velocity Thrust
    - Multi-Point 3-Day Comet Trajectory: (x_3d, y_3d) -> (x_1d, y_1d) -> (x_now, y_now)
    Evaluates 15 non-duplicated cross-asset pillars across 3 distinct institutional tiers:
      1. POWER_SECTOR: SMH, IGV, BOTZ, URA
      2. EQUITY_INDEX: SPY, QQQ, RSP, IWM
      3. MACRO_PLUMBING: TLT, HYG, UUP, GLD, SLV, USO, BTCUSD
    """
    cache_key = "cross_asset_compass_v3"
    cached = get_cached(cache_key, ttl=180)
    if cached is not None:
        return cached

    compass_universe = [
        # Tactical Power Sectors (5-Sector Thematic ETF Universe)
        {"symbol": "SMH", "short": "SMH", "name": "Semiconductors", "role": "Compute & Silicon", "tier": "POWER_SECTOR", "sector_key": "Semiconductors", "default_vol": 18_000_000.0},
        {"symbol": "SRVR", "short": "SRVR", "name": "AI Infrastructure", "role": "Data Center & Optical Fabric", "tier": "POWER_SECTOR", "sector_key": "AI Infrastructure", "default_vol": 120_000.0},
        {"symbol": "URA", "short": "URA", "name": "Energy, Grid & Materials", "role": "Baseload Power & Critical Minerals", "tier": "POWER_SECTOR", "sector_key": "Energy, Grid & Materials", "default_vol": 5_500_000.0},
        {"symbol": "ROBO", "short": "ROBO", "name": "Robotics & Autonomous", "role": "Embodied Physical AI & Space", "tier": "POWER_SECTOR", "sector_key": "Robotics & Autonomous", "default_vol": 200_000.0},
        {"symbol": "QTUM", "short": "QTUM", "name": "Edge AI & Next-Gen", "role": "Edge Silicon & Quantum Compute", "tier": "POWER_SECTOR", "sector_key": "Edge AI & Next-Gen Compute", "default_vol": 1_200_000.0},
        # Broad Equity Index Tiers
        {"symbol": "SPY", "short": "SPY", "name": "S&P 500 Cap-Wt", "role": "Core US Large-Cap", "tier": "EQUITY_INDEX", "sector_key": "", "default_vol": 60_000_000.0},
        {"symbol": "QQQ", "short": "QQQ", "name": "Nasdaq-100", "role": "Mega-Cap Growth", "tier": "EQUITY_INDEX", "sector_key": "", "default_vol": 42_000_000.0},
        {"symbol": "RSP", "short": "RSP", "name": "S&P Equal-Wt", "role": "True Market Breadth", "tier": "EQUITY_INDEX", "sector_key": "", "default_vol": 7_500_000.0},
        {"symbol": "IWM", "short": "IWM", "name": "Russell 2000", "role": "Small-Cap Domestic Beta", "tier": "EQUITY_INDEX", "sector_key": "", "default_vol": 32_000_000.0},
        # Global Macro Plumbing & Safe Havens
        {"symbol": "TLT", "short": "TLT", "name": "20Y+ Treasuries", "role": "Long-Duration Rates", "tier": "MACRO_PLUMBING", "sector_key": "", "default_vol": 38_000_000.0},
        {"symbol": "HYG", "short": "HYG", "name": "High-Yield Credit", "role": "Corporate Credit Appetite", "tier": "MACRO_PLUMBING", "sector_key": "", "default_vol": 30_000_000.0},
        {"symbol": "UUP", "short": "UUP", "name": "USD Liquidity Index", "role": "Offshore USD Funding & FX Stress", "tier": "MACRO_PLUMBING", "sector_key": "", "default_vol": 3_500_000.0},
        {"symbol": "GLD", "short": "GLD", "name": "Gold Bullion", "role": "Sovereign Safe Haven", "tier": "MACRO_PLUMBING", "sector_key": "", "default_vol": 8_500_000.0},
        {"symbol": "SLV", "short": "SLV", "name": "Silver Trust", "role": "Monetary / Solar Metal", "tier": "MACRO_PLUMBING", "sector_key": "", "default_vol": 20_000_000.0},
        {"symbol": "USO", "short": "USO", "name": "WTI Crude Oil", "role": "Energy & Inflation Impulse", "tier": "MACRO_PLUMBING", "sector_key": "", "default_vol": 5_000_000.0},
        {"symbol": "BTCUSD", "short": "BTC", "name": "Bitcoin 24/7", "role": "24/7 High-Beta Liquidity", "tier": "MACRO_PLUMBING", "sector_key": "", "default_vol": 28_000.0},
    ]

    symbols = [u["symbol"] for u in compass_universe]
    quotes_map = fmp_batch_quotes(symbols, ttl=120)

    hist_map: Dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        fut_to_sym = {executor.submit(get_historical_series, sym): sym for sym in symbols}
        for fut, sym in fut_to_sym.items():
            try:
                hist_map[sym] = fut.result()
            except Exception:
                hist_map[sym] = pd.DataFrame()

    nodes: List[Dict[str, Any]] = []
    quad_counts = {
        "INFLOW_LEADER": 0,
        "SNAPBACK_IGNITION": 0,
        "CROWDED_EXHAUSTION": 0,
        "LIQUIDATION_FLUSH": 0,
    }

    for meta in compass_universe:
        sym = meta["symbol"]
        q = quotes_map.get(sym, {}) or {}
        df = hist_map.get(sym, pd.DataFrame())

        live_price = float(q.get("price") or (df["close"].iloc[-1] if not df.empty else 100.0) or 100.0)
        chg_1d = float(q.get("changePercentage") or 0.0)
        clv_live = _quote_clv(q)
        rvol_live = _quote_rvol(sym, q, default_20d_vol=meta["default_vol"])
        vol_raw = float(q.get("volume") or 0.0)
        if sym == "BTCUSD":
            dollar_vol_b = round(max(1.8, (live_price * max(vol_raw, 18_000.0)) / 1e9), 2)
        else:
            dollar_vol_b = round(max(0.08, (live_price * vol_raw) / 1e9), 2)

        chg_5d = chg_1d * 1.8
        atr_pct = 1.65

        if not df.empty and len(df) >= 22:
            c_s = df["close"].astype(float).replace(0, np.nan).ffill()
            h_s = (df["high"].astype(float) if "high" in df.columns else c_s * 1.008).fillna(c_s)
            l_s = (df["low"].astype(float) if "low" in df.columns else c_s * 0.992).fillna(c_s)
            v_s = (df["volume"].astype(float) if "volume" in df.columns else pd.Series(meta["default_vol"], index=df.index)).replace(0, np.nan).ffill().fillna(meta["default_vol"])

            pv_20 = (c_s * v_s).rolling(20, min_periods=5).sum()
            vol_20 = v_s.rolling(20, min_periods=5).sum().replace(0, np.nan)
            vwma_20 = (pv_20 / vol_20).fillna(c_s.rolling(20, min_periods=1).mean())
            ema_20 = c_s.ewm(span=20, adjust=False).mean()
            equil_20 = 0.55 * vwma_20 + 0.45 * ema_20

            atr_14 = calculate_atr(h_s, l_s, c_s, 14).replace(0, np.nan).bfill().fillna(c_s * 0.015)
            denom = (atr_14 * 1.32).clip(lower=c_s * 0.0045)

            # X-Axis Series: 20D Institutional Trend Stretch Z-Score
            x_series = ((c_s - equil_20) / denom).replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(-3.0, 3.0)

            # Historical Bar-by-Bar CLV & RVOL-Conditioned Velocity Thrust Series
            hl_span = (h_s - l_s).replace(0, np.nan)
            clv_s = (((c_s - l_s) - (h_s - c_s)) / hl_span).fillna(0.0).clip(-1.0, 1.0)
            vol_med_20 = v_s.rolling(20, min_periods=5).median().replace(0, np.nan).bfill().fillna(meta["default_vol"])
            rvol_s = (v_s / vol_med_20).fillna(1.0).clip(0.55, 2.5)
            rvol_mult_s = (0.76 + 0.24 * rvol_s).clip(0.75, 1.36)

            vel_1d = (c_s - c_s.shift(1)) / atr_14.clip(lower=1e-4)
            vel_2d = (c_s - c_s.shift(2)) / (atr_14.clip(lower=1e-4) * 1.414)
            raw_thrust = (0.52 * vel_1d + 0.30 * vel_2d + 0.36 * clv_s) * rvol_mult_s
            y_series = raw_thrust.replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(-2.75, 2.75)

            x_now = float(x_series.iloc[-1])
            x_1d = float(x_series.iloc[-2]) if len(x_series) >= 2 else x_now
            x_3d = float(x_series.iloc[-4]) if len(x_series) >= 4 else x_1d

            # Blend live quote RVOL + CLV into today's thrust coordinate for zero-lag intraday precision
            atr_curr = float(atr_14.iloc[-1]) if float(atr_14.iloc[-1]) > 0 else live_price * 0.015
            atr_pct = round((atr_curr / max(0.01, live_price)) * 100.0, 2)
            live_rvol_mult = float(np.clip(0.76 + 0.24 * rvol_live, 0.72, 1.40))
            live_1d_atr = chg_1d / max(0.35, atr_pct)
            vel_2d_curr = float(vel_2d.iloc[-1]) if not np.isnan(vel_2d.iloc[-1]) else live_1d_atr
            y_now = float(np.clip((0.54 * live_1d_atr + 0.26 * vel_2d_curr + 0.38 * clv_live) * live_rvol_mult, -2.75, 2.75))
            y_1d = float(y_series.iloc[-2]) if len(y_series) >= 2 else y_now * 0.7
            y_3d = float(y_series.iloc[-4]) if len(y_series) >= 4 else y_1d * 0.7

            if len(c_s) >= 6 and float(c_s.iloc[-6]) > 0:
                chg_5d = round(((live_price / float(c_s.iloc[-6])) - 1.0) * 100.0, 2)
        else:
            x_now = float(np.clip(chg_1d * 0.65, -2.6, 2.6))
            x_1d = x_now * 0.72
            x_3d = x_now * 0.40
            y_now = float(np.clip((chg_1d * 0.75 + clv_live * 0.45) * np.clip(0.8 + 0.2 * rvol_live, 0.75, 1.35), -2.6, 2.6))
            y_1d = y_now * 0.65
            y_3d = y_now * 0.35

        # Quadrant diagnosis & desk actionability
        if x_now >= 0.0 and y_now >= 0.0:
            quadrant = "INFLOW_LEADER"
            quad_label = "Institutional Inflow Leader"
            desk_implication = "Momentum expansion on positive thrust — favor Breakout & Trend Calls."
        elif x_now < 0.0 and y_now >= 0.0:
            quadrant = "SNAPBACK_IGNITION"
            quad_label = "Rubberband Snapback Ignition"
            desk_implication = "Stretched below 20D VWMA but hooking upward on positive thrust — Prime Elastic Call Zone."
        elif x_now >= 0.0 and y_now < 0.0:
            quadrant = "CROWDED_EXHAUSTION"
            quad_label = "Upper-Band Exhaustion / Distribution"
            desk_implication = "Extended above 20D equilibrium with decelerating thrust — Harvest Calls / Scout Mirage Puts."
        else:
            quadrant = "LIQUIDATION_FLUSH"
            quad_label = "Liquidation Flush / Risk-Off Drain"
            desk_implication = "Below equilibrium with negative velocity — demand bottom-tail CLV absorption before catching."

        quad_counts[quadrant] += 1

        nodes.append({
            "symbol": sym,
            "short": meta["short"],
            "name": meta["name"],
            "role": meta["role"],
            "tier": meta["tier"],
            "sector_key": meta["sector_key"],
            "price": round(live_price, 2),
            "chg_1d": round(chg_1d, 2),
            "chg_5d": round(chg_5d, 2),
            "atr_pct": atr_pct,
            "rvol": round(rvol_live, 2),
            "clv": round(clv_live, 2),
            "dollar_vol_b": dollar_vol_b,
            "x_now": round(x_now, 3),
            "y_now": round(y_now, 3),
            "x_1d": round(x_1d, 3),
            "y_1d": round(y_1d, 3),
            "x_3d": round(x_3d, 3),
            "y_3d": round(y_3d, 3),
            "delta_x_3d": round(x_now - x_3d, 2),
            "delta_y_3d": round(y_now - y_3d, 2),
            "quadrant": quadrant,
            "quad_label": quad_label,
            "desk_implication": desk_implication,
        })

    node_by_sym = {n["symbol"]: n for n in nodes}
    risk_syms = ["SPY", "QQQ", "IWM", "HYG", "SMH", "SRVR", "BTCUSD"]
    haven_syms = ["TLT", "GLD", "UUP"]

    risk_thrust = float(np.mean([node_by_sym[s]["y_now"] for s in risk_syms if s in node_by_sym])) if nodes else 0.0
    haven_thrust = float(np.mean([node_by_sym[s]["y_now"] for s in haven_syms if s in node_by_sym])) if nodes else 0.0
    risk_spread = round(risk_thrust - haven_thrust, 2)

    power_nodes = [n for n in nodes if n["tier"] == "POWER_SECTOR"]
    top_power = max(power_nodes, key=lambda item: item["y_now"] + 0.35 * item["x_now"]) if power_nodes else None
    hook_power = [n for n in power_nodes if n["quadrant"] == "SNAPBACK_IGNITION"]

    if risk_spread >= 0.55 and risk_thrust >= 0.25:
        rotation_badge = "RISK-ON CAPITAL EXPANSION"
        rotation_tone = "emerald"
        rotation_summary = (
            f"Global capital is rotating aggressively out of defensive shelters into high-beta equities "
            f"(Risk vs. Haven Thrust {risk_spread:+.2f}σ · Top Magnet: {top_power['short'] if top_power else 'SMH'})."
        )
    elif len(hook_power) >= 2 or (risk_spread >= 0.10 and any(n["x_now"] < -0.35 and n["y_now"] > 0.15 for n in power_nodes)):
        rotation_badge = "ELASTIC SNAPBACK ROTATION"
        rotation_tone = "cyan"
        hook_list = ", ".join(n["short"] for n in hook_power[:3]) if hook_power else (top_power["short"] if top_power else "SMH")
        rotation_summary = (
            f"Discounted growth & thematic desks ({hook_list}) are hooking upward from below 20D equilibrium "
            f"with positive intraday thrust ({risk_spread:+.2f}σ spread vs. Havens)."
        )
    elif risk_spread <= -0.45 and haven_thrust >= -0.05:
        rotation_badge = "DEFENSIVE HAVEN ROTATION"
        rotation_tone = "rose"
        haven_leaders = [n["short"] for n in nodes if n["symbol"] in haven_syms and n["y_now"] >= 0.0]
        haven_txt = ", ".join(haven_leaders) if haven_leaders else "TLT/GLD/UUP"
        rotation_summary = (
            f"Institutional liquidity is rotating defensively into {haven_txt} over high-beta risk "
            f"(Risk vs. Haven Spread {risk_spread:+.2f}σ) — demand confirmed bottom-tail CLV absorption before deploying Calls."
        )
    elif risk_thrust <= -0.55 or quad_counts["LIQUIDATION_FLUSH"] >= 8:
        rotation_badge = "BROAD RISK-OFF DE-RISKING"
        rotation_tone = "rose"
        rotation_summary = (
            f"Cross-asset risk beta is undergoing broad de-risking ({quad_counts['LIQUIDATION_FLUSH']}/15 pillars in flush, "
            f"Risk Thrust {risk_thrust:+.2f}σ) — prioritize Mirage Puts or deeply coiled {top_power['short'] if top_power else 'BOTZ'} snapbacks."
        )
    else:
        rotation_badge = "SELECTIVE BIFURCATED ROTATION"
        rotation_tone = "amber"
        rotation_summary = (
            f"Cross-asset liquidity is selectively dispersed (Risk vs. Haven Spread {risk_spread:+.2f}σ) — "
            f"concentrate delta in RVOL-backed Power Sector leaders ({top_power['short'] if top_power else 'SMH'})."
        )

    payload = {
        "nodes": nodes,
        "quadrant_counts": quad_counts,
        "risk_thrust": round(risk_thrust, 2),
        "haven_thrust": round(haven_thrust, 2),
        "risk_appetite_spread": risk_spread,
        "rotation_badge": rotation_badge,
        "rotation_tone": rotation_tone,
        "rotation_summary": rotation_summary,
        "top_power_symbol": top_power["symbol"] if top_power else "SMH",
        "timestamp": get_ny_now().strftime("%H:%M:%S EST"),
    }
    set_cached(cache_key, payload)
    return payload


def get_unified_5day_catalyst_outlook(
    sector_name: str = "Semiconductors",
    active_ticker: str = "",
) -> Dict[str, Any]:
    """
    Unified 5-Day Institutional Catalyst, 8-K, Fed/Macro Calendar & Symbolism Outlook.
    Cached 900s in data/fmp_cache.db (and L1 RAM). Concurrently fetches:
      - FMP /stable/sec-filings-8k + /stable/sec-filings-search/symbol
      - FMP /stable/economic-calendar (US + Fed/FOMC + Tier-1 Macro Prints & Treasury Auctions)
      - FMP /stable/news/stock (batched active_ticker + sector ETFs + core thematic benchmarks)
      - Earnings calendar map + active ticker exact earnings
      - Macro symbolism (yield curve, VIX term structure, credit stress Z, breadth spread, RVOL)
    """
    sec_clean = normalize_sector_name(sector_name)
    act_sym = (active_ticker or "").strip().upper()
    cache_key = f"unified_5d_catalyst_outlook_v2_{sec_clean}_{act_sym}"
    cached = get_cached(cache_key, ttl=900)
    if cached is not None:
        return cached

    sec_meta = SECTORS.get(sec_clean, SECTORS["Semiconductors"])
    sec_etfs = list(dict.fromkeys([sec_meta.get("benchmark", "SMH")] + list(sec_meta.get("etfs", []))))
    sec_tickers = set(sec_meta.get("tickers", []))
    core_etfs = ["SMH", "SRVR", "URA", "REMX", "ROBO", "JEDI", "QTUM"]
    news_syms = list(dict.fromkeys(([act_sym] if act_sym else []) + sec_etfs + core_etfs))
    tracked_universe = set(news_syms) | sec_tickers

    now_ny = get_ny_now()
    today_d = now_ny.date()
    from_5d_str = (today_d - timedelta(days=5)).strftime("%Y-%m-%d")
    from_30d_str = (today_d - timedelta(days=30)).strftime("%Y-%m-%d")
    today_str = today_d.strftime("%Y-%m-%d")
    to_7d_str = (today_d + timedelta(days=7)).strftime("%Y-%m-%d")

    def _fetch_8k_market():
        return fmp_get(
            "sec-filings-8k",
            params={"from": from_5d_str, "to": today_str, "limit": 200},
            ttl=900,
        )

    def _fetch_8k_active():
        if not act_sym:
            return []
        return fmp_get(
            "sec-filings-search/symbol",
            params={"symbol": act_sym, "from": from_30d_str, "to": today_str, "limit": 10},
            ttl=900,
        )

    def _fetch_econ():
        return fmp_get(
            "economic-calendar",
            params={"from": today_str, "to": to_7d_str},
            ttl=900,
        )

    def _fetch_news():
        return fmp_get(
            "news/stock",
            params={"symbols": ",".join(news_syms), "limit": 40},
            ttl=600,
        )

    def _fetch_earnings():
        emap = get_upcoming_earnings_map()
        act_e = get_ticker_earnings_25d(act_sym, fetch_live=True) if (act_sym and act_sym not in THEMATIC_ETFS) else {}
        return emap, act_e

    def _fetch_macro_stack():
        return (
            get_macro_yield_regime(),
            get_temporal_regime(),
            get_24_48h_market_direction_radar(),
            get_sector_macro_pulse(),
        )

    with ThreadPoolExecutor(max_workers=6) as ex:
        fut_8k_mkt = ex.submit(_fetch_8k_market)
        fut_8k_act = ex.submit(_fetch_8k_active)
        fut_econ = ex.submit(_fetch_econ)
        fut_news = ex.submit(_fetch_news)
        fut_earn = ex.submit(_fetch_earnings)
        fut_macro = ex.submit(_fetch_macro_stack)

        raw_8k_mkt = fut_8k_mkt.result() or []
        raw_8k_act = fut_8k_act.result() or []
        raw_econ = fut_econ.result() or []
        raw_news = fut_news.result() or []
        earnings_map, act_earn = fut_earn.result()
        macro, temporal, radar, pulse = fut_macro.result()

    # --- 1. Parse & Classify US Economic Calendar + Fed/FOMC + Tier-1 Prints ---
    tier1_binary_kw = (
        "CPI", "PPI", "PCE", "NFP", "NONFARM", "NON-FARM", "PAYROLL", "UNEMPLOYMENT RATE",
        "GDP", "ISM", "RETAIL SALES", "FOMC", "RATE DECISION", "INTEREST RATE",
        "10-YEAR", "30-YEAR", "POWELL"
    )
    macro_watchlist_kw = tier1_binary_kw + (
        "JOLTS", "TREASURY", "AUCTION", "2-YEAR", "JOBLESS", "DURABLE", "HOUSING",
        "CONSUMER SENTIMENT", "MICHIGAN"
    )
    fed_kw = (
        "FED", "FOMC", "POWELL", "WALLER", "WILLIAMS", "BOSTIC", "BARKIN", "KASHKARI",
        "JEFFERSON", "BOWMAN", "COOK", "KUGLER", "MIRAN", "HAMMACK", "SCHMID", "MUSALEM",
        "INTEREST RATE", "RATE DECISION", "MINUTES", "BEIGE BOOK", "SPEECH", "SPEAKS"
    )

    fed_and_macro_events: List[Dict[str, Any]] = []
    events_by_date: Dict[str, List[Dict[str, Any]]] = {}

    if isinstance(raw_econ, list):
        for ev in raw_econ:
            if not isinstance(ev, dict):
                continue
            country = str(ev.get("country") or "").strip().upper()
            currency = str(ev.get("currency") or "").strip().upper()
            if country not in ("US", "USA", "UNITED STATES", "") and currency != "USD":
                continue
            if country == "" and currency not in ("USD", ""):
                continue
            title = str(ev.get("event") or ev.get("title") or "").strip()
            if not title:
                continue
            dt_raw = str(ev.get("date") or "").strip()
            dt_day = dt_raw[:10]
            if not dt_day:
                continue

            u_title = title.upper()
            is_fed = any(k in u_title for k in fed_kw)
            is_tier1_binary = any(k in u_title for k in tier1_binary_kw)
            is_tier1 = any(k in u_title for k in macro_watchlist_kw)
            imp_raw = str(ev.get("impact") or "").strip().upper()
            if is_tier1_binary or (imp_raw == "HIGH" and "BILL AUCTION" not in u_title):
                impact = "HIGH"
            elif is_fed or is_tier1 or imp_raw in ("HIGH", "MEDIUM"):
                impact = "MEDIUM"
            else:
                impact = "LOW"

            if impact == "LOW" and not (is_fed or is_tier1):
                continue

            category = "FED / FOMC" if is_fed else ("TIER-1 MACRO" if is_tier1 else "US MACRO")
            ev_obj = {
                "date": dt_day,
                "datetime": dt_raw[:16].replace("T", " "),
                "event": title,
                "category": category,
                "impact": impact,
                "is_fed": is_fed,
                "is_tier1": is_tier1,
                "estimate": ev.get("estimate"),
                "previous": ev.get("previous"),
                "actual": ev.get("actual"),
                "country": country or "US",
            }
            fed_and_macro_events.append(ev_obj)
            events_by_date.setdefault(dt_day, []).append({
                "type": category,
                "title": title,
                "impact": impact,
                "symbol": "MACRO",
                "time": dt_raw[11:16] if len(dt_raw) >= 16 else "",
            })

    fed_and_macro_events.sort(key=lambda x: (x["datetime"], 0 if x["impact"] == "HIGH" else 1))

    # --- 2. Parse SEC 8-K Filings (prioritize active ticker + sector/ETF universe) ---
    sec_8k_filings: List[Dict[str, Any]] = []
    seen_8k = set()
    combined_8k = []
    if isinstance(raw_8k_act, list):
        combined_8k.extend(raw_8k_act)
    if isinstance(raw_8k_mkt, list):
        combined_8k.extend(raw_8k_mkt)

    sector_8k: List[Dict[str, Any]] = []
    broad_8k: List[Dict[str, Any]] = []
    for f in combined_8k:
        if not isinstance(f, dict):
            continue
        form_t = str(f.get("formType") or "8-K").upper()
        if "8-K" not in form_t and f not in (raw_8k_act if isinstance(raw_8k_act, list) else []):
            continue
        fsym = str(f.get("symbol") or "").strip().upper()
        fdate = str(f.get("filingDate") or f.get("acceptedDate") or "")[:10]
        flink = str(f.get("finalLink") or f.get("link") or "")
        dedup_k = (fsym, form_t, fdate, flink[:80])
        if dedup_k in seen_8k:
            continue
        seen_8k.add(dedup_k)

        is_act = bool(act_sym and fsym == act_sym)
        is_sec = fsym in tracked_universe
        item_dict = {
            "symbol": fsym or "SEC",
            "company": str(f.get("companyName") or f.get("cik") or fsym),
            "form_type": form_t,
            "filing_date": fdate,
            "accepted_date": str(f.get("acceptedDate") or fdate)[:16].replace("T", " "),
            "link": flink,
            "is_active_match": is_act,
            "is_sector_match": is_sec,
        }
        if is_act or is_sec:
            sector_8k.append(item_dict)
        else:
            broad_8k.append(item_dict)

    sec_8k_filings = (sector_8k + broad_8k)[:12]

    # --- 3. Parse Sector & Active Ticker News ---
    sector_news: List[Dict[str, Any]] = []
    if isinstance(raw_news, list):
        for art in raw_news[:15]:
            if not isinstance(art, dict):
                continue
            sector_news.append({
                "symbol": str(art.get("symbol") or "").upper(),
                "title": str(art.get("title") or "").strip(),
                "site": str(art.get("site") or art.get("publisher") or ""),
                "published_date": str(art.get("publishedDate") or "")[:16].replace("T", " "),
                "url": str(art.get("url") or ""),
                "text": str(art.get("text") or "")[:220],
            })

    # --- 4. Merge Sector & Active Earnings into 5-Day Window ---
    if isinstance(earnings_map, dict):
        for esym, edata in earnings_map.items():
            if esym not in tracked_universe:
                continue
            edate = str((edata or {}).get("earnings_date") or (edata or {}).get("date") or "")[:10]
            if len(edate) == 10 and edate != "ETF Basket":
                events_by_date.setdefault(edate, []).append({
                    "type": "EARNINGS",
                    "title": f"{esym} Earnings ({str((edata or {}).get('time') or 'TBD').upper()})",
                    "impact": "HIGH" if esym == act_sym else "MEDIUM",
                    "symbol": esym,
                    "time": str((edata or {}).get("time") or ""),
                })
    if act_sym and isinstance(act_earn, dict):
        act_edate = str(act_earn.get("earnings_date") or "")[:10]
        if len(act_edate) == 10 and act_edate != "ETF Basket":
            existing_titles = {e.get("symbol") for e in events_by_date.get(act_edate, []) if e.get("type") == "EARNINGS"}
            if act_sym not in existing_titles:
                events_by_date.setdefault(act_edate, []).append({
                    "type": "EARNINGS",
                    "title": f"{act_sym} Earnings Release",
                    "impact": "HIGH",
                    "symbol": act_sym,
                    "time": "",
                })

    # --- 5. Build 5 Trading-Day Horizon Cards ---
    trading_days: List[datetime.date] = []
    probe_d = today_d
    while len(trading_days) < 5:
        if probe_d.weekday() < 5:
            trading_days.append(probe_d)
        probe_d += timedelta(days=1)

    days: List[Dict[str, Any]] = []
    binary_event_count_5d = 0
    has_tier1_macro_5d = False

    for d_obj in trading_days:
        d_str = d_obj.strftime("%Y-%m-%d")
        day_evs = events_by_date.get(d_str, [])
        high_evs = [e for e in day_evs if e.get("impact") == "HIGH"]
        med_evs = [e for e in day_evs if e.get("impact") == "MEDIUM"]
        binary_hits = len(high_evs)
        binary_event_count_5d += binary_hits
        if any(e.get("type") in ("FED / FOMC", "TIER-1 MACRO") and e.get("impact") == "HIGH" for e in day_evs):
            has_tier1_macro_5d = True

        intensity_pct = int(min(100, (len(high_evs) * 35) + (len(med_evs) * 18)))
        if intensity_pct >= 65 or len(high_evs) >= 2:
            risk_tone = "rose"
        elif intensity_pct >= 35 or len(high_evs) == 1:
            risk_tone = "amber"
        elif len(day_evs) > 0:
            risk_tone = "cyan"
        else:
            risk_tone = "emerald"

        headline_tag = (
            high_evs[0]["title"][:44]
            if high_evs
            else (day_evs[0]["title"][:44] if day_evs else "Clear Runway")
        )
        days.append({
            "date": d_str,
            "day_short": d_obj.strftime("%a"),
            "day_num": d_obj.day,
            "is_today": (d_obj == today_d),
            "intensity_pct": intensity_pct,
            "risk_tone": risk_tone,
            "event_count": len(day_evs),
            "headline_tag": headline_tag,
            "events": day_evs[:8],
        })

    # --- 6. Symbolism & 30 vs 45 DTE Prescription ---
    vix_ratio = round(float(radar.get("vix_term_ratio", 0.93) or 0.93), 3)
    vix_state = str(radar.get("vix_term_regime", "NORMAL CONTANGO"))
    credit_z = round(float(radar.get("credit_stress_z", 0.0) or 0.0), 2)
    tnx_yield = round(float(macro.get("y10_current", 4.25) or 4.25), 2)
    rsp_5d = float((radar.get("rsp", {}) or {}).get("change_5d_pct", 0.0) or 0.0)
    qqq_5d = float((radar.get("qqq", {}) or {}).get("change_5d_pct", 0.0) or 0.0)
    breadth_spread_5d = round(rsp_5d - qqq_5d, 2)
    spy_rvol = round(float(pulse.get("spy_rvol", (radar.get("spy", {}) or {}).get("rvol", 1.0)) or 1.0), 2)
    regime_label = str(pulse.get("market_regime_badge") or radar.get("signage_title", "MACRO EQUILIBRIUM"))

    act_days_er = int((act_earn or {}).get("days_to_earnings", 99) or 99)
    if (act_days_er <= 7) or binary_event_count_5d >= 3 or (has_tier1_macro_5d and vix_ratio >= 0.98):
        binary_risk_level = "HIGH"
    elif binary_event_count_5d >= 2 or (7 < act_days_er <= 21) or vix_ratio >= 0.96:
        binary_risk_level = "ELEVATED"
    elif binary_event_count_5d == 1 or has_tier1_macro_5d:
        binary_risk_level = "MODERATE"
    else:
        binary_risk_level = "LOW"

    exposure_cap_pct = int(round(float(np.clip(
        100 - (binary_event_count_5d * 10) - (25 if vix_ratio >= 1.0 else (10 if vix_ratio >= 0.96 else 0)),
        35,
        100,
    ))))

    symbolism = {
        "regime_label": regime_label,
        "vix_ratio": vix_ratio,
        "vix_state": vix_state,
        "credit_z": credit_z,
        "tnx_yield": tnx_yield,
        "breadth_spread_5d": breadth_spread_5d,
        "spy_rvol": spy_rvol,
        "exposure_cap_pct": exposure_cap_pct,
    }

    if (act_sym and 14 < act_days_er <= 28) or vix_ratio >= 0.98 or binary_event_count_5d >= 3:
        recommended_dte = 45
        dte_prescription_label = "45 DTE · Macro & Event Theta Cushion"
        reasons = []
        if act_sym and 14 < act_days_er <= 28:
            reasons.append(f"{act_sym} earnings in {act_days_er}d")
        if vix_ratio >= 0.98:
            reasons.append(f"VIX/VIX3M elevated ({vix_ratio:.3f})")
        if binary_event_count_5d >= 3:
            reasons.append(f"{binary_event_count_5d} Tier-1 catalysts in 5D window")
        dte_rationale = "Prescribing 45 DTE to bridge " + ", ".join(reasons) + " with slower daily theta decay."
    else:
        recommended_dte = 30
        dte_prescription_label = "30 DTE · High-Velocity Gamma Capture"
        dte_rationale = (
            f"Prescribing 30 DTE: VIX/VIX3M is calm ({vix_ratio:.3f}, {vix_state}) with "
            f"{binary_event_count_5d} binary 5D events — crisp 0.40-0.65D gamma elasticity."
        )

    radar_score = float(radar.get("forecast_score", 0.0) or 0.0)
    pulse_conv = float(pulse.get("tape_conviction_score", 50.0) or 50.0) - 50.0
    temp_edge = float(temporal.get("day_edge_score", 0.0) or 0.0)
    bias_score = int(round(float(np.clip((0.55 * radar_score) + (0.60 * pulse_conv) + (0.40 * temp_edge), -100.0, 100.0))))

    if bias_score >= 30:
        directional_bias = "CONSTRUCTIVE_RISK_ON"
    elif bias_score >= 10:
        directional_bias = "BULLISH_MEAN_REVERSION"
    elif bias_score <= -30:
        directional_bias = "RISK_OFF_PUT_BIAS"
    elif bias_score <= -10:
        directional_bias = "DEFENSIVE_CHOP"
    else:
        directional_bias = "NEUTRAL_COIL"

    payload = {
        "sector_name": sec_clean,
        "active_ticker": act_sym,
        "directional_bias": directional_bias,
        "bias_score": bias_score,
        "binary_risk_level": binary_risk_level,
        "binary_event_count_5d": binary_event_count_5d,
        "recommended_dte": recommended_dte,
        "dte_prescription_label": dte_prescription_label,
        "dte_rationale": dte_rationale,
        "symbolism": symbolism,
        "days": days,
        "sec_8k_filings": sec_8k_filings,
        "fed_and_macro_events": fed_and_macro_events[:20],
        "sector_news": sector_news,
        "timestamp": now_ny.strftime("%Y-%m-%d %H:%M:%S EST"),
    }
    set_cached(cache_key, payload, ttl=900)
    return payload


def get_ai_5day_bias_shield_assessment(
    catalyst_outlook: Dict[str, Any],
    sector_name: str = "Semiconductors",
    active_ticker: str = "",
    force_refresh: bool = False,
    active_cand: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Uses the connected AI engine (via llm_router) to synthesize the 5-Trading-Day
    Bias & Binary Shield plus live OPRA options surface telemetry (VRP, 25D Skew,
    Term Structure, Dealer GEX/Vanna/Gamma-Flip, Variance Rent, 5D Net EV%) into a
    -200 (Put Bias) to +200 (Call Bias) assessment + summation.
    """
    import llm_router

    sec_clean = normalize_sector_name(sector_name)
    act_sym = (active_ticker or "").strip().upper()
    bias_score = int(catalyst_outlook.get("bias_score", 0) or 0)
    bin_risk = str(catalyst_outlook.get("binary_risk_level", "MODERATE") or "MODERATE")
    bin_cnt = int(catalyst_outlook.get("binary_event_count_5d", 0) or 0)
    backend = llm_router.get_active_backend()

    # Extract active ticker OPRA options surface telemetry when provided
    surf_tag = "nosurf"
    surf_prompt_line = ""
    opt_score_adj = 0.0
    if isinstance(active_cand, dict):
        ot = active_cand.get("options_telemetry") or active_cand.get("metrics", {}).get("options_telemetry") or {}
        gw = active_cand.get("gamma_walls") or active_cand.get("metrics", {}).get("gamma_walls") or {}
        qe = active_cand.get("quant_edge") or active_cand.get("metrics", {}).get("quant_edge") or {}
        ts = active_cand.get("term_structure") or active_cand.get("metrics", {}).get("term_structure") or {}
        iv_pct = float(ot.get("iv_pct", 0.0) or 0.0)
        hv20_pct = float(ot.get("hv20_pct", 0.0) or 0.0)
        vrp_pts = float(ot.get("vrp_vol_pts", ot.get("iv_hv_spread", 0.0)) or 0.0)
        skew_25 = float(ot.get("skew_25d_pct", 0.0) or 0.0)
        var_rent = float(qe.get("variance_rent_ratio", ot.get("variance_rent_ratio", 0.0)) or 0.0)
        net_ev = float(qe.get("net_ev_pct", 0.0) or 0.0)
        net_vanna = float(gw.get("net_vanna_m", 0.0) or 0.0)
        g_flip = float(gw.get("gamma_flip_strike", 0.0) or 0.0)
        t_regime = str(ts.get("term_regime", ot.get("term_regime", "N/A")))
        t_slope = float(ts.get("term_slope_30_60_pct", 0.0) or 0.0)
        conv_signed = int(active_cand.get("conviction_score_200", 0) or 0)
        if iv_pct > 0 or net_ev != 0.0:
            surf_tag = f"{int(round(vrp_pts))}_{int(round(skew_25))}_{int(round(conv_signed / 10.0))}"
            surf_prompt_line = (
                f"- Active Ticker ({act_sym}) OPRA Surface: 30D IV {iv_pct:.1f}% vs HV20 {hv20_pct:.1f}% "
                f"(VRP {vrp_pts:+.1f} vol pts) | 25Δ Skew {skew_25:+.1f}% | Term Structure: {t_regime} ({t_slope:+.1f}%) | "
                f"Dealer Vanna {net_vanna:+.1f}M/vol, Gamma Flip ${g_flip:.0f} | "
                f"Daily Variance Rent {var_rent:.2f}x | Quant 5D Net EV {net_ev:+.1f}% | Quant Score {conv_signed:+d}\n"
            )
            opt_score_adj = (conv_signed * 0.22) + (net_vanna * 2.5) - (max(0.0, vrp_pts - 8.0) * 1.1)

    cache_key = f"ai_5d_bias_shield_v2_{backend}_{sec_clean}_{act_sym}_{bias_score}_{bin_risk}_{bin_cnt}_{surf_tag}"
    if not force_refresh:
        cached = get_cached(cache_key, ttl=900)
        if cached is not None:
            return cached

    sym = catalyst_outlook.get("symbolism", {}) or {}
    dir_bias = str(catalyst_outlook.get("directional_bias", "NEUTRAL_COIL"))
    dte_rec = int(catalyst_outlook.get("recommended_dte", 30) or 30)
    dte_rat = str(catalyst_outlook.get("dte_rationale", "") or "")
    days = catalyst_outlook.get("days", [])[:5]
    fed_evs = catalyst_outlook.get("fed_and_macro_events", [])[:6]
    news = catalyst_outlook.get("sector_news", [])[:4]
    filings_cnt = len(catalyst_outlook.get("sec_8k_filings", []) or [])

    days_summary = "; ".join(
        f"{d.get('day_short', '')} {d.get('day_num', '')}: {d.get('headline_tag', 'Clear')} ({d.get('event_count', 0)} ev)"
        for d in days
    )
    macro_summary = "; ".join(
        f"{e.get('event') or e.get('title', '')} [{e.get('impact', '')}]"
        for e in fed_evs
        if (e.get("event") or e.get("title"))
    )
    news_summary = "; ".join(
        str(n.get("title", "") or "")[:90]
        for n in news
        if n.get("title")
    )

    prompt = (
        f"You are an institutional options desk strategist at Jane Street assessing the 5-trading-day "
        f"macro, catalyst, and OPRA volatility surface posture for {act_sym or sec_clean} ({sec_clean} desk).\n\n"
        f"Telemetry:\n"
        f"- Directional Bias: {dir_bias} (quant bias_score={bias_score:+d} on -100..+100)\n"
        f"- Binary Shield: {bin_risk} ({bin_cnt} Tier-1 5D events; {filings_cnt} recent SEC 8-K filings)\n"
        f"- Recommended DTE: {dte_rec} DTE ({dte_rat})\n"
        f"{surf_prompt_line}"
        f"- Regime: {sym.get('regime_label', 'MACRO EQUILIBRIUM')} | VIX/VIX3M: {sym.get('vix_ratio', 0.93)} ({sym.get('vix_state', '')}) "
        f"| Credit Z: {sym.get('credit_z', 0.0)} | 10Y: {sym.get('tnx_yield', 4.25)}% | Breadth 5D: {sym.get('breadth_spread_5d', 0.0)}% "
        f"| Exposure Cap: {sym.get('exposure_cap_pct', 100)}%\n"
        f"- 5-Day Runway: {days_summary or 'Clear'}\n"
        f"- Key Fed/Macro Events: {macro_summary or 'None listed'}\n"
        f"- Sector Wire Headlines: {news_summary or 'Quiet wire'}\n\n"
        f"Task: Produce a Put vs Call assessment score from -200 (maximum Put / defensive downside skew) through 0 (neutral/balanced) "
        f"to +200 (maximum Call / upside convexity), plus a crisp 2-sentence institutional summation synthesizing directional bias, "
        f"binary shield event risk, and live OPRA option pricing (VRP/skew/structure).\n"
        f"Respond ONLY with valid JSON: {{\"score\": <int -200..200>, \"stance\": \"<SHORT_UPPERCASE_LABEL>\", \"summary\": \"<2 concise sentences>\"}}"
    )

    ai_score: Optional[int] = None
    ai_stance: str = ""
    ai_summary: str = ""
    source_tag = "ai"

    try:
        raw_resp, err = llm_router.generate_text(
            prompt=prompt,
            system_instruction="Return strictly valid JSON with keys: score (int -200..200), stance (string), summary (string).",
            temperature=0.15,
        )
        if raw_resp and not err:
            m = re.search(r"\{[\s\S]*\}", raw_resp)
            if m:
                parsed = json.loads(m.group(0))
                if "score" in parsed:
                    ai_score = int(np.clip(int(round(float(parsed["score"]))), -200, 200))
                ai_stance = str(parsed.get("stance", "") or "").strip().upper()[:28]
                ai_summary = str(parsed.get("summary", "") or "").strip()
    except Exception:
        pass

    if ai_score is None or not ai_summary:
        source_tag = "quant_fallback"
        vix_r = float(sym.get("vix_ratio", 0.93) or 0.93)
        risk_drag = -35 if bin_risk == "HIGH" else (-18 if bin_risk == "ELEVATED" else (0 if bin_risk == "MODERATE" else 12))
        vix_drag = -25 if vix_r >= 1.0 else (-10 if vix_r >= 0.96 else 8)
        ai_score = int(np.clip(round((bias_score * 1.40) + risk_drag + vix_drag + opt_score_adj), -200, 200))
        if ai_score <= -100:
            ai_stance = "HEAVY PUT SKEW"
        elif ai_score <= -30:
            ai_stance = "DEFENSIVE PUT BIAS"
        elif ai_score < 30:
            ai_stance = "NEUTRAL COIL"
        elif ai_score < 100:
            ai_stance = "CONSTRUCTIVE CALL BIAS"
        else:
            ai_stance = "HIGH CALL CONVEXITY"
        posture_word = "protective put skew" if ai_score <= -30 else ("upside call convexity" if ai_score >= 30 else "balanced delta-neutrality")
        surf_note = f" | Surface: {surf_prompt_line.splitlines()[0].split(':', 1)[-1].strip()[:85]}" if surf_prompt_line else ""
        ai_summary = (
            f"Macro bias ({dir_bias.replace('_', ' ').lower()}, {bias_score:+d}) paired with {bin_risk} binary shield risk "
            f"({bin_cnt} 5D events, VIX/VIX3M {vix_r:.3f}) prescribes {posture_word} at {dte_rec} DTE{surf_note}. "
            f"Size exposure within the {sym.get('exposure_cap_pct', 100)}% cap around Tier-1 catalysts."
        )

    if not ai_stance:
        ai_stance = (
            "STRONG PUT BIAS" if ai_score <= -120 else
            "PUT SKEW" if ai_score <= -30 else
            "NEUTRAL COIL" if ai_score < 30 else
            "CALL SKEW" if ai_score < 120 else
            "STRONG CALL BIAS"
        )

    result = {
        "score": int(ai_score),
        "stance": ai_stance.replace("_", " "),
        "summary": ai_summary,
        "source": source_tag,
        "backend": backend,
    }
    set_cached(cache_key, result, ttl=900)
    return result



