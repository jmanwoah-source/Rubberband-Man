"""
MarketData.app (MarketData.com) Institutional Market & Options Client for Rubberband Man.
Provides zero-jank, disk+memory cached access to:
1. Live OPRA Option Chains with Native Greeks (Delta, Gamma, Theta, Vega), IV, Bid/Ask/Mid, OI & Volume
   (`/v1/options/chain/{symbol}/` & `/v1/options/expirations/{symbol}/`)
2. Level-1 NBBO Bulk Stock Quotes with Bid/Ask Size & Mid (`/v1/stocks/bulkquotes/` & `/v1/stocks/quotes/{symbol}/`)
3. Split-Adjusted Daily, 4-Hour, and Extended-Hours (Pre-Market & After-Hours) Candles
   (`/v1/stocks/candles/{resolution}/{symbol}/?extended=true`)
4. Earnings Calendar & EPS Surprises (`/v1/stocks/earnings/{symbol}/`)
5. Real-Time Ticker News (`/v1/stocks/news/{symbol}/`)
6. US Market Status (`/v1/markets/status/`)

Backed by a 100,000 requests/day quota plus two-tier RAM + SQLite WAL caching (`data/marketdata_cache.db`).
"""

import os
import time
import math
import json
import sqlite3
import datetime
import threading
from datetime import timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

MARKETDATA_BASE_URL = os.getenv("MARKETDATA_BASE_URL", "https://api.marketdata.app/v1").strip().rstrip("/")

_DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(_DB_DIR, exist_ok=True)
_MD_CACHE_DB = os.path.join(_DB_DIR, "marketdata_cache.db")

_MEM_CACHE: Dict[str, Tuple[Any, float]] = {}
_CACHE_LOCK = threading.RLock()
last_http_status: Optional[int] = None

_SESSION = requests.Session()
_ADAPTER = HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=1)
_SESSION.mount("https://", _ADAPTER)
_SESSION.mount("http://", _ADAPTER)


def _init_cache_db() -> None:
    try:
        cutoff = time.time() - (7 * 86400)
        with sqlite3.connect(_MD_CACHE_DB, timeout=10) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute("DELETE FROM api_cache WHERE updated_at < ?", (cutoff,))
    except Exception:
        pass


_init_cache_db()


def get_marketdata_api_key() -> str:
    """Retrieves MarketData.app API token from `.env` (`MARKETDATA_API_KEY`) and ensures trailing base64 padding (`=`)."""
    raw = os.getenv("MARKETDATA_API_KEY", "").strip()
    if not raw:
        return ""
    if len(raw) % 4 != 0:
        raw += "=" * (4 - (len(raw) % 4))
    return raw


def get_last_http_status() -> Optional[int]:
    """Returns the most recent HTTP status code recorded by MarketData.app requests (e.g. 200 live, 203 cached)."""
    return last_http_status


def _get_cached(key: str, ttl: int = 300, allow_stale: bool = False) -> Optional[Any]:
    now = time.time()
    with _CACHE_LOCK:
        if key in _MEM_CACHE:
            val, ts = _MEM_CACHE[key]
            if now - ts < ttl or allow_stale:
                return val

    try:
        with sqlite3.connect(_MD_CACHE_DB, timeout=5) as conn:
            row = conn.execute(
                "SELECT payload, updated_at FROM api_cache WHERE cache_key = ?", (key,)
            ).fetchone()
            if row:
                payload_str, ts = row
                if now - ts < ttl or allow_stale:
                    val = json.loads(payload_str)
                    with _CACHE_LOCK:
                        _MEM_CACHE[key] = (val, ts)
                    return val
    except Exception:
        pass
    return None


def _set_cached(key: str, val: Any) -> None:
    now = time.time()
    with _CACHE_LOCK:
        _MEM_CACHE[key] = (val, now)
    try:
        payload_str = json.dumps(val)
        with sqlite3.connect(_MD_CACHE_DB, timeout=5) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO api_cache (cache_key, payload, updated_at) VALUES (?, ?, ?)",
                (key, payload_str, now),
            )
    except Exception:
        pass


def md_get(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    ttl: int = 300,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Executes an authenticated GET request against MarketData.app REST API (`https://api.marketdata.app/v1`).
    Accepts HTTP 200 (live) and HTTP 203 (cached/non-authoritative live), recording `last_http_status`.
    """
    global last_http_status
    clean_path = path if path.startswith("/") else f"/{path}"
    p = dict(params or {})
    cache_key = f"md_{clean_path}_{json.dumps(p, sort_keys=True)}"

    if use_cache:
        cached = _get_cached(cache_key, ttl=ttl, allow_stale=False)
        if cached is not None:
            if isinstance(cached, dict) and cached.get("http_code"):
                last_http_status = int(cached["http_code"])
            return cached

    token = get_marketdata_api_key()
    if not token:
        stale = _get_cached(cache_key, ttl=ttl, allow_stale=True)
        if stale is not None:
            return stale
        return {"s": "error", "errmsg": "MARKETDATA_API_KEY is missing."}

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{MARKETDATA_BASE_URL}{clean_path}"

    try:
        res = _SESSION.get(url, params=p, headers=headers, timeout=12)
        last_http_status = int(res.status_code)
        if res.status_code in (200, 203):
            data = res.json()
            if isinstance(data, dict) and data.get("s") == "ok":
                data["http_code"] = int(res.status_code)
                if use_cache:
                    _set_cached(cache_key, data)
                return data
            return data if isinstance(data, dict) else {"s": "error", "http_code": int(res.status_code)}
        stale = _get_cached(cache_key, ttl=ttl, allow_stale=True)
        if stale is not None:
            return stale
        return {"s": "error", "http_code": res.status_code, "errmsg": res.text[:200]}
    except Exception as e:
        stale = _get_cached(cache_key, ttl=ttl, allow_stale=True)
        if stale is not None:
            return stale
        return {"s": "error", "errmsg": str(e)}


def get_market_status() -> Dict[str, Any]:
    """Queries `/v1/markets/status/` for authoritative US exchange status."""
    data = md_get("/markets/status/", ttl=300)
    if isinstance(data, dict) and data.get("s") == "ok":
        statuses = data.get("status") or []
        st_str = str(statuses[-1] if statuses else "closed").lower()
        return {
            "market": st_str,
            "is_open": st_str == "open",
            "source": "MarketData.app"
        }
    return {"market": "unknown", "is_open": False, "source": "Fallback"}


def get_bulk_stock_quotes(symbols: List[str], ttl: int = 120) -> Dict[str, Dict[str, Any]]:
    """
    Fetches Level-1 NBBO quotes (`bid`, `bidSize`, `ask`, `askSize`, `mid`, `last`, `change`, `changepct`, `volume`)
    for multiple equities in ONE single call via `/v1/stocks/bulkquotes/`.
    """
    clean_syms = [
        str(s).strip().upper()
        for s in symbols
        if s and str(s).strip() and not str(s).strip().startswith("^")
    ]
    clean_syms = list(dict.fromkeys(clean_syms))
    if not clean_syms:
        return {}

    joined = ",".join(clean_syms[:100])
    data = md_get("/stocks/bulkquotes/", params={"symbols": joined}, ttl=ttl)
    if not isinstance(data, dict) or data.get("s") != "ok":
        return {}

    syms = data.get("symbol") or []
    asks = data.get("ask") or []
    ask_sizes = data.get("askSize") or []
    bids = data.get("bid") or []
    bid_sizes = data.get("bidSize") or []
    mids = data.get("mid") or []
    lasts = data.get("last") or []
    chgs = data.get("change") or []
    chgpcts = data.get("changepct") or []
    vols = data.get("volume") or []
    updateds = data.get("updated") or []

    out: Dict[str, Dict[str, Any]] = {}
    for i, sym in enumerate(syms):
        if not sym:
            continue
        last_px = float(lasts[i]) if i < len(lasts) and lasts[i] is not None else 0.0
        if last_px <= 0:
            continue
        bid_px = float(bids[i]) if i < len(bids) and bids[i] is not None else last_px
        ask_px = float(asks[i]) if i < len(asks) and asks[i] is not None else last_px
        mid_px = float(mids[i]) if i < len(mids) and mids[i] is not None else round((bid_px + ask_px) / 2.0, 4)
        chg_val = float(chgs[i]) if i < len(chgs) and chgs[i] is not None else 0.0
        # MarketData returns changepct as decimal (e.g. 0.0522 = +5.22%)
        raw_pct = float(chgpcts[i]) if i < len(chgpcts) and chgpcts[i] is not None else 0.0
        chg_pct = round(raw_pct * 100.0, 2)
        vol_val = float(vols[i]) if i < len(vols) and vols[i] is not None else 0.0
        ts_val = int(updateds[i]) if i < len(updateds) and updateds[i] is not None else int(time.time())
        b_sz = int(bid_sizes[i]) if i < len(bid_sizes) and bid_sizes[i] is not None else 0
        a_sz = int(ask_sizes[i]) if i < len(ask_sizes) and ask_sizes[i] is not None else 0

        out[str(sym).upper()] = {
            "symbol": str(sym).upper(),
            "price": last_px,
            "bid": bid_px,
            "ask": ask_px,
            "mid": mid_px,
            "bidSize": b_sz,
            "askSize": a_sz,
            "change": round(chg_val, 2),
            "changePercentage": chg_pct,
            "changesPercentage": chg_pct,
            "volume": vol_val,
            "timestamp": ts_val,
            "source": "MarketData.app"
        }
    return out


def get_candles_df(
    symbol: str,
    resolution: str = "D",
    countback: int = 1260,
    extended: bool = False,
    ttl: int = 1800
) -> Optional[pd.DataFrame]:
    """
    Fetches split-adjusted OHLCV candles from `/v1/stocks/candles/{resolution}/{symbol}/`.
    Supports `D` (Daily), `4H` (4-Hour), `1H` (1-Hour), `15` (15-Minute) with `extended=true`
    for Pre-Market (04:00-09:30 ET) and After-Hours (16:00-20:00 ET) institutional flow analysis.
    """
    sym = (symbol or "").strip().upper()
    if not sym or sym.startswith("^"):
        return None

    to_str = datetime.date.today().isoformat()
    params: Dict[str, Any] = {"to": to_str, "countback": countback}
    if extended:
        params["extended"] = "true"

    data = md_get(f"/stocks/candles/{resolution}/{sym}/", params=params, ttl=ttl)
    if not isinstance(data, dict) or data.get("s") != "ok":
        return None

    ts_list = data.get("t") or []
    o_list = data.get("o") or []
    h_list = data.get("h") or []
    l_list = data.get("l") or []
    c_list = data.get("c") or []
    v_list = data.get("v") or []

    n = min(len(ts_list), len(c_list))
    if n < 5:
        return None

    rows = []
    ny_tz = ZoneInfo("America/New_York")
    is_daily = resolution.upper() in ("D", "1D", "DAILY")
    for i in range(n):
        dt_ny = datetime.datetime.fromtimestamp(int(ts_list[i]), tz=ny_tz)
        c_val = float(c_list[i] or 0.0)
        h_val = float(h_list[i] or c_val) if i < len(h_list) else c_val
        l_val = float(l_list[i] or c_val) if i < len(l_list) else c_val
        o_val = float(o_list[i] or c_val) if i < len(o_list) else c_val
        v_val = float(v_list[i] or 0.0) if i < len(v_list) else 0.0
        rows.append({
            "date": pd.Timestamp(year=dt_ny.year, month=dt_ny.month, day=dt_ny.day) if is_daily else pd.Timestamp(dt_ny.replace(tzinfo=None)),
            "timestamp": int(ts_list[i]),
            "hour_ny": dt_ny.hour + dt_ny.minute / 60.0,
            "open": o_val,
            "high": h_val,
            "low": l_val,
            "close": c_val,
            "volume": v_val,
            "vwap": round((h_val + l_val + c_val) / 3.0, 4)
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df


def get_extended_hours_telemetry(symbol: str, ttl: int = 300) -> Dict[str, Any]:
    """
    Analyzes Pre-Market (04:00–09:30 ET) and After-Hours (16:00–20:00 ET) 15-minute candles
    from `/v1/stocks/candles/15/{symbol}/?extended=true` plus Level-1 NBBO bid/ask size imbalance.
    Produces an Early-Morning & After-Hours Directional Thesis.
    """
    sym = (symbol or "").strip().upper()
    default_out = {
        "symbol": sym,
        "ext_session": "REGULAR",
        "ext_price": 0.0,
        "cash_close": 0.0,
        "ext_change_pct": 0.0,
        "ext_volume": 0,
        "ext_vwap": 0.0,
        "nbbo_imbalance_pct": 0.0,
        "thesis_badge": "NEUTRAL EXTENDED TAPE",
        "thesis_color": "#8AB4F8",
        "thesis_summary": "Extended-hours volume tracking inline with cash close equilibrium."
    }
    if not sym or sym.startswith("^"):
        return default_out

    df_15m = get_candles_df(sym, resolution="15", countback=36, extended=True, ttl=ttl)
    q_map = get_bulk_stock_quotes([sym], ttl=ttl)
    q = q_map.get(sym, {})

    bid_sz = float(q.get("bidSize") or 0.0)
    ask_sz = float(q.get("askSize") or 0.0)
    nbbo_imb = round(((bid_sz - ask_sz) / (bid_sz + ask_sz)) * 100.0, 1) if (bid_sz + ask_sz) > 0 else 0.0

    if df_15m is None or df_15m.empty:
        return default_out

    # Partition into Regular Cash Session (9.5 <= hour_ny < 16.0) vs Extended (hour_ny < 9.5 or hour_ny >= 16.0)
    cash_bars = df_15m[(df_15m["hour_ny"] >= 9.5) & (df_15m["hour_ny"] < 16.0)]
    ext_bars = df_15m[(df_15m["hour_ny"] < 9.5) | (df_15m["hour_ny"] >= 16.0)]

    cash_close = float(cash_bars["close"].iloc[-1]) if not cash_bars.empty else float(df_15m["close"].iloc[0])
    last_bar = df_15m.iloc[-1]
    ext_price = float(q.get("price") or last_bar["close"])

    recent_ext = ext_bars.tail(12)
    ext_vol = int(recent_ext["volume"].sum()) if not recent_ext.empty else 0
    if not recent_ext.empty and ext_vol > 0:
        ext_vwap = round(float((recent_ext["vwap"] * recent_ext["volume"]).sum() / max(1.0, float(ext_vol))), 2)
    else:
        ext_vwap = round(ext_price, 2)

    last_hr = float(last_bar["hour_ny"])
    ext_session = "AFTER-HOURS" if last_hr >= 16.0 else ("PRE-MARKET" if last_hr < 9.5 else "CASH-SESSION")
    ext_chg_pct = round(((ext_price - cash_close) / max(0.01, cash_close)) * 100.0, 2)

    if ext_chg_pct >= 0.45 and (ext_price >= ext_vwap or nbbo_imb >= 15.0):
        badge = f"🟢 {ext_session} ACCUMULATION ({ext_chg_pct:+.2f}%)"
        color = "#34D399"
        summary = (
            f"{sym} {ext_session.title()} bid {ext_chg_pct:+.2f}% above cash close (${ext_price:.2f} vs VWAP ${ext_vwap:.2f}, "
            f"Vol {ext_vol:,}, NBBO Size Imbalance {nbbo_imb:+.0f}%)."
        )
    elif ext_chg_pct <= -0.45 and (ext_price <= ext_vwap or nbbo_imb <= -15.0):
        badge = f"🔴 {ext_session} DISTRIBUTION ({ext_chg_pct:+.2f}%)"
        color = "#F87171"
        summary = (
            f"{sym} {ext_session.title()} offered {ext_chg_pct:+.2f}% below cash close (${ext_price:.2f} vs VWAP ${ext_vwap:.2f}, "
            f"Vol {ext_vol:,}, NBBO Size Imbalance {nbbo_imb:+.0f}%)."
        )
    else:
        badge = f"⚖️ {ext_session} EQUILIBRIUM ({ext_chg_pct:+.2f}%)"
        color = "#FBBF24"
        summary = (
            f"{sym} {ext_session.title()} holding near ${ext_price:.2f} ({ext_chg_pct:+.2f}% vs cash close, "
            f"Ext VWAP ${ext_vwap:.2f}, Vol {ext_vol:,})."
        )

    return {
        "symbol": sym,
        "ext_session": ext_session,
        "ext_price": round(ext_price, 2),
        "cash_close": round(cash_close, 2),
        "ext_change_pct": ext_chg_pct,
        "ext_volume": ext_vol,
        "ext_vwap": ext_vwap,
        "nbbo_imbalance_pct": nbbo_imb,
        "thesis_badge": badge,
        "thesis_color": color,
        "thesis_summary": summary
    }


def get_option_expirations(symbol: str, ttl: int = 1800) -> List[str]:
    """
    Fetches verified OPRA option expiration dates (`YYYY-MM-DD`) for `symbol`
    from `/v1/options/expirations/{symbol}/`.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return []
    data = md_get(f"/options/expirations/{sym}/", ttl=ttl)
    if isinstance(data, dict) and data.get("s") == "ok":
        exps = data.get("expirations") or []
        return [str(e) for e in exps if e]
    return []


def get_option_chain_native(
    symbol: str,
    expiration: Optional[str] = None,
    dte: Optional[int] = 35,
    side: Optional[str] = None,
    strike_limit: int = 40,
    ttl: int = 600,
    feed: str = "cached"
) -> Optional[pd.DataFrame]:
    """
    Fetches native OPRA Option Chain from MarketData.app `/v1/options/chain/{symbol}/`
    including authoritative Exchange Greeks (`delta`, `gamma`, `theta`, `vega`),
    Implied Volatility (`iv`), `bid`, `ask`, `mid`, `last`, `openInterest`, `volume`,
    `inTheMoney`, `intrinsicValue`, `extrinsicValue`, and `underlyingPrice`.
    Defaults to `feed="cached"` (HTTP 203 at 1 credit/chain); supports `feed="live"`.
    Returns a standardized DataFrame with columns compatible with both Rubberband Engine
    and Schwab Simulator Desk.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None

    params: Dict[str, Any] = {"strikeLimit": strike_limit}
    if feed in ("cached", "live"):
        params["feed"] = feed
    if expiration:
        params["expiration"] = expiration
    elif dte is not None:
        # Resolve the best 3rd-Friday Monthly expiration in the 21..55 DTE window when possible,
        # so we pull the deepest-liquidity institutional OPRA chain instead of a thin weekly cycle.
        best_exp = None
        try:
            exps = get_option_expirations(sym, ttl=3600)
            today_d = datetime.date.today()
            monthly_cands = []
            all_cands = []
            for e_str in exps:
                try:
                    ed = datetime.date.fromisoformat(e_str[:10])
                    days_out = (ed - today_d).days
                    if 21 <= days_out <= 58:
                        all_cands.append((abs(days_out - dte), e_str))
                        # 3rd Friday of the month falls on day 15..21 (or Thursday day 14..20 if Friday holiday)
                        if ed.weekday() in (3, 4) and 15 <= ed.day <= 21:
                            monthly_cands.append((abs(days_out - dte), e_str))
                except Exception:
                    continue
            if monthly_cands:
                monthly_cands.sort(key=lambda x: x[0])
                best_exp = monthly_cands[0][1]
            elif all_cands:
                all_cands.sort(key=lambda x: x[0])
                best_exp = all_cands[0][1]
        except Exception:
            best_exp = None

        if best_exp:
            params["expiration"] = best_exp
            expiration = best_exp
        else:
            params["dte"] = dte
    if side in ("call", "put"):
        params["side"] = side

    data = md_get(f"/options/chain/{sym}/", params=params, ttl=ttl)
    if not isinstance(data, dict) or data.get("s") != "ok":
        return None

    opt_syms = data.get("optionSymbol") or []
    n = len(opt_syms)
    if n == 0:
        return None

    def _col(k: str, default: Any = None) -> List[Any]:
        arr = data.get(k)
        if isinstance(arr, list) and len(arr) == n:
            return arr
        return [default] * n

    exps = _col("expiration", 0)
    sides = _col("side", "call")
    strikes = _col("strike", 0.0)
    dtes = _col("dte", dte or 35)
    bids = _col("bid", 0.0)
    bid_sizes = _col("bidSize", 0)
    mids = _col("mid", 0.0)
    asks = _col("ask", 0.0)
    ask_sizes = _col("askSize", 0)
    lasts = _col("last", 0.0)
    ois = _col("openInterest", 0)
    vols = _col("volume", 0)
    itms = _col("inTheMoney", False)
    intrinsics = _col("intrinsicValue", 0.0)
    extrinsics = _col("extrinsicValue", 0.0)
    under_pxs = _col("underlyingPrice", 0.0)
    ivs = _col("iv", 0.40)
    deltas = _col("delta", None)
    gammas = _col("gamma", None)
    thetas = _col("theta", None)
    vegas = _col("vega", None)
    updateds = _col("updated", int(time.time()))

    ny_tz = ZoneInfo("America/New_York")
    rows = []
    for i in range(n):
        exp_ts = int(exps[i] or 0)
        if exp_ts > 0:
            exp_iso = datetime.datetime.fromtimestamp(exp_ts, tz=ny_tz).strftime("%Y-%m-%d")
        else:
            exp_iso = expiration or ""

        upd_ts = int(updateds[i] or 0)
        upd_iso = datetime.datetime.fromtimestamp(upd_ts, tz=ny_tz).strftime("%Y-%m-%d") if upd_ts > 0 else ""

        iv_val = float(ivs[i]) if ivs[i] is not None else 0.40
        bid_val = float(bids[i] or 0.0)
        ask_val = float(asks[i] or 0.0)
        mid_val = float(mids[i] or ((bid_val + ask_val) / 2.0 if (bid_val > 0 and ask_val > 0) else 0.0))
        last_val = float(lasts[i] or mid_val)

        rows.append({
            "contractSymbol": str(opt_syms[i]),
            "side": str(sides[i] or "call").lower(),
            "expiration": exp_iso,
            "expirationDate": exp_iso,
            "dte": int(dtes[i] or 35),
            "strike": float(strikes[i] or 0.0),
            "bid": bid_val,
            "bidSize": int(bid_sizes[i] or 0),
            "ask": ask_val,
            "askSize": int(ask_sizes[i] or 0),
            "mid": mid_val,
            "lastPrice": last_val,
            "impliedVolatility": iv_val,
            "openInterest": int(ois[i] or 0),
            "volume": int(vols[i] or 0),
            "inTheMoney": bool(itms[i]),
            "intrinsicValue": float(intrinsics[i] or 0.0),
            "extrinsicValue": float(extrinsics[i] or 0.0),
            "underlyingPrice": float(under_pxs[i] or 0.0),
            "delta": float(deltas[i]) if deltas[i] is not None else None,
            "gamma": float(gammas[i]) if gammas[i] is not None else None,
            "theta": float(thetas[i]) if thetas[i] is not None else None,
            "vega": float(vegas[i]) if vegas[i] is not None else None,
            "lastTradeDate": upd_iso,
        })

    return pd.DataFrame(rows)


def get_marketdata_news(symbol: str, limit: int = 5, ttl: int = 600) -> List[Dict[str, str]]:
    """
    Fetches ticker news from `/v1/stocks/news/{symbol}/`.
    """
    sym = (symbol or "").strip().upper()
    if not sym or "," in sym:
        return []
    data = md_get(f"/stocks/news/{sym}/", ttl=ttl)
    if not isinstance(data, dict) or data.get("s") != "ok":
        return []

    headlines = data.get("headline") or []
    contents = data.get("content") or []
    sources = data.get("source") or []
    pub_dates = data.get("publicationDate") or []
    ny_tz = ZoneInfo("America/New_York")

    out = []
    for i in range(min(limit, len(headlines))):
        ts = int(pub_dates[i]) if i < len(pub_dates) and pub_dates[i] else 0
        dt_str = datetime.datetime.fromtimestamp(ts, tz=ny_tz).strftime("%Y-%m-%d %H:%M") if ts > 0 else ""
        src = str(sources[i]) if i < len(sources) and sources[i] else "MarketData Wire"
        txt = str(contents[i])[:260] if i < len(contents) and contents[i] else ""
        out.append({
            "title": str(headlines[i]),
            "publishedDate": dt_str,
            "site": src[:45],
            "text": txt,
            "url": src if src.startswith("http") else ""
        })
    return out


def get_opra_gamma_walls_and_unusual_flow(
    symbol: str,
    dte: int = 35,
    ttl: int = 600,
    chain_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Computes Real OPRA Gamma Walls (Call Wall resistance & Put Wall floor), Net Dealer Gamma Exposure (GEX),
    and Unusual Options Sweeps (Volume > 1.25x Open Interest) via MarketData.app `/v1/options/chain/{symbol}/`.
    Accepts an optional pre-fetched `chain_df` for single-pass chain sharing.
    """
    sym = (symbol or "").strip().upper()
    default_res = {
        "symbol": sym,
        "call_wall_strike": 0.0,
        "call_wall_oi": 0,
        "put_wall_strike": 0.0,
        "put_wall_oi": 0,
        "net_gex_regime": "NEUTRAL DEALER GAMMA",
        "net_gex_color": "#8AB4F8",
        "total_call_oi": 0,
        "total_put_oi": 0,
        "call_put_oi_ratio": 1.0,
        "total_call_vol": 0,
        "total_put_vol": 0,
        "unusual_flows": [],
        "has_data": False,
        "summary": "No active OPRA chain telemetry."
    }
    if not sym or sym.startswith("^"):
        return default_res

    cache_key = f"opra_gamma_walls_{sym}_{dte}"
    if chain_df is None:
        cached = _get_cached(cache_key, ttl=ttl)
        if cached is not None:
            return cached

    try:
        df = chain_df if (chain_df is not None and not chain_df.empty) else get_option_chain_native(sym, dte=dte, strike_limit=50, ttl=ttl, feed="cached")
        if df is None or df.empty:
            _set_cached(cache_key, default_res)
            return default_res

        calls = df[df["side"].str.lower() == "call"].copy()
        puts = df[df["side"].str.lower() == "put"].copy()

        call_wall_strike = 0.0
        call_wall_oi = 0
        if not calls.empty and "openInterest" in calls.columns:
            max_c_idx = calls["openInterest"].idxmax()
            c_row = calls.loc[max_c_idx]
            call_wall_strike = float(c_row.get("strike", 0.0))
            call_wall_oi = int(c_row.get("openInterest", 0))

        put_wall_strike = 0.0
        put_wall_oi = 0
        if not puts.empty and "openInterest" in puts.columns:
            max_p_idx = puts["openInterest"].idxmax()
            p_row = puts.loc[max_p_idx]
            put_wall_strike = float(p_row.get("strike", 0.0))
            put_wall_oi = int(p_row.get("openInterest", 0))

        tot_call_oi = int(calls["openInterest"].sum()) if not calls.empty else 0
        tot_put_oi = int(puts["openInterest"].sum()) if not puts.empty else 0
        tot_call_vol = int(calls["volume"].sum()) if not calls.empty else 0
        tot_put_vol = int(puts["volume"].sum()) if not puts.empty else 0
        cp_ratio = round(tot_put_oi / max(1, tot_call_oi), 2)

        # Net Dealer Gamma Exposure (GEX) approximation:
        # Calls generate positive dealer gamma (dealers buy dips / sell rallies), Puts generate negative gamma.
        call_gex = 0.0
        if not calls.empty and "gamma" in calls.columns and "openInterest" in calls.columns:
            call_gex = float((calls["gamma"].fillna(0.0) * calls["openInterest"].fillna(0)).sum())

        put_gex = 0.0
        if not puts.empty and "gamma" in puts.columns and "openInterest" in puts.columns:
            put_gex = float((puts["gamma"].fillna(0.0) * puts["openInterest"].fillna(0)).sum())

        net_gex = call_gex - put_gex
        if net_gex > 0.05:
            net_gex_regime = "+Γ LONG DEALER GAMMA (DIP-BUY PIN BUFFER)"
            net_gex_color = "#34D399"
        elif net_gex < -0.05:
            net_gex_regime = "-Γ SHORT DEALER GAMMA (VOL ACCELERANT / SQUEEZE FUEL)"
            net_gex_color = "#F87171"
        else:
            net_gex_regime = "BALANCED DEALER GAMMA"
            net_gex_color = "#FBBF24"

        # Unusual Options Flow Detector:
        # Strikes with Volume >= 200 AND Volume >= 1.25 * Open Interest (fresh aggressive opening sweeps)
        unusual_list = []
        for _, row in df.iterrows():
            vol = int(row.get("volume", 0) or 0)
            oi = int(row.get("openInterest", 0) or 0)
            if vol >= 200 and (vol >= 1.25 * max(1, oi) or (vol >= 1000 and oi < 2000)):
                ratio = round(vol / max(1, oi), 2)
                raw_iv = float(row.get("impliedVolatility", 0.0) or 0.0)
                unusual_list.append({
                    "strike": float(row.get("strike", 0.0)),
                    "side": str(row.get("side", "")).upper(),
                    "volume": vol,
                    "oi": oi,
                    "ratio": ratio,
                    "iv_pct": round(raw_iv * 100.0, 1),
                    "bid": float(row.get("bid", 0.0) or 0.0),
                    "ask": float(row.get("ask", 0.0) or 0.0),
                    "mid": float(row.get("mid", 0.0) or 0.0),
                })

        unusual_list.sort(key=lambda x: (x["volume"], x["ratio"]), reverse=True)
        top_unusual = unusual_list[:6]

        # Second-Order Dealer Exposure (Net GEX $M, Net Vanna $M/vol, Net Charm $M/day)
        vanna_charm = {}
        try:
            import quant_kernel
            spot_ref = float(df["underlyingPrice"].iloc[0] or call_wall_strike or 100.0)
            vanna_charm = quant_kernel.compute_dealer_vanna_charm_profile(df, spot=spot_ref)
        except Exception:
            vanna_charm = {}

        summary = (
            f"OPRA Call Wall ${call_wall_strike:.0f} ({call_wall_oi:,} OI) · "
            f"Put Wall ${put_wall_strike:.0f} ({put_wall_oi:,} OI) · "
            f"P/C OI Ratio {cp_ratio:.2f} · {len(unusual_list)} Unusual Sweeps Detected"
        )

        res = {
            "symbol": sym,
            "call_wall_strike": call_wall_strike,
            "call_wall_oi": call_wall_oi,
            "put_wall_strike": put_wall_strike,
            "put_wall_oi": put_wall_oi,
            "net_gex_regime": net_gex_regime,
            "net_gex_color": net_gex_color,
            "net_gex_m": vanna_charm.get("net_gex_m", 0.0),
            "net_vanna_m": vanna_charm.get("net_vanna_m", 0.0),
            "net_charm_m": vanna_charm.get("net_charm_m", 0.0),
            "gamma_flip_strike": vanna_charm.get("gamma_flip_strike", 0.0),
            "vanna_regime": vanna_charm.get("vanna_regime", "NEUTRAL VANNA"),
            "vanna_color": vanna_charm.get("vanna_color", "#38BDF8"),
            "charm_regime": vanna_charm.get("charm_regime", "NEUTRAL CHARM"),
            "strike_profile": vanna_charm.get("strike_profile", []),
            "total_call_oi": tot_call_oi,
            "total_put_oi": tot_put_oi,
            "call_put_oi_ratio": cp_ratio,
            "total_call_vol": tot_call_vol,
            "total_put_vol": tot_put_vol,
            "unusual_flows": top_unusual,
            "unusual_count": len(unusual_list),
            "has_data": True,
            "summary": summary
        }
        _set_cached(cache_key, res)
        return res
    except Exception as e:
        _set_cached(cache_key, default_res)
        return default_res


def get_25d_skew_and_spread_optimizer(
    symbol: str,
    dte: int = 35,
    spot: float = 0.0,
    ttl: int = 600,
    chain_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Computes exact OPRA 25-Delta Put/Call Volatility Skew and Bid-Ask Spread Friction %
    from MarketData.app `/v1/options/chain/{symbol}/`.
    Automatically determines whether to buy Naked OTM, deploy a Vertical Debit Spread,
    or structure a Zero-Cost Collar.
    Accepts an optional pre-fetched `chain_df` for single-pass chain sharing.
    """
    sym = (symbol or "").strip().upper()
    default_out = {
        "symbol": sym,
        "skew_25d_pct": 0.0,
        "skew_regime": "NEUTRAL SKEW",
        "skew_badge": "SKEW 0.0%",
        "skew_color": "#8AB4F8",
        "call_25d_strike": 0.0,
        "call_25d_iv": 0.0,
        "put_25d_strike": 0.0,
        "put_25d_iv": 0.0,
        "atm_bid": 0.0,
        "atm_ask": 0.0,
        "atm_mid": 0.0,
        "spread_friction_pct": 0.0,
        "friction_warning": False,
        "limit_order_advice": "Standard market order acceptable.",
        "recommended_structure": "30-45 DTE NAKED OPTION",
        "structure_rationale": "Symmetric volatility pricing across strikes.",
        "has_data": False
    }
    if not sym or sym.startswith("^"):
        return default_out

    cache_key = f"opra_25d_skew_{sym}_{dte}"
    if chain_df is None:
        cached = _get_cached(cache_key, ttl=ttl)
        if cached is not None:
            return cached

    try:
        df = chain_df if (chain_df is not None and not chain_df.empty) else get_option_chain_native(sym, dte=dte, strike_limit=50, ttl=ttl, feed="cached")
        if df is None or df.empty or "delta" not in df.columns or "impliedVolatility" not in df.columns:
            _set_cached(cache_key, default_out)
            return default_out

        calls = df[df["side"].str.lower() == "call"].dropna(subset=["delta", "impliedVolatility"])
        puts = df[df["side"].str.lower() == "put"].dropna(subset=["delta", "impliedVolatility"])

        if calls.empty or puts.empty:
            _set_cached(cache_key, default_out)
            return default_out

        # Match Call closest to +0.25 Delta
        c_diffs = (calls["delta"] - 0.25).abs()
        c25_row = calls.loc[c_diffs.idxmin()]
        call_25d_k = float(c25_row.get("strike", 0.0))
        call_25d_iv = round(float(c25_row.get("impliedVolatility", 0.0)) * 100.0, 1)

        # Match Put closest to -0.25 Delta
        p_diffs = (puts["delta"].abs() - 0.25).abs()
        p25_row = puts.loc[p_diffs.idxmin()]
        put_25d_k = float(p25_row.get("strike", 0.0))
        put_25d_iv = round(float(p25_row.get("impliedVolatility", 0.0)) * 100.0, 1)

        skew_25d = round(put_25d_iv - call_25d_iv, 1)

        # ATM contract bid-ask friction
        under_p = spot if spot > 0 else float(df["underlyingPrice"].iloc[0] or 100.0)
        atm_diffs = (calls["strike"] - under_p).abs()
        atm_c = calls.loc[atm_diffs.idxmin()]
        atm_bid = float(atm_c.get("bid", 0.0) or 0.0)
        atm_ask = float(atm_c.get("ask", 0.0) or 0.0)
        atm_mid = float(atm_c.get("mid", 0.0) or ((atm_bid + atm_ask) / 2.0))
        if atm_mid > 0 and atm_ask >= atm_bid:
            friction_pct = round(((atm_ask - atm_bid) / atm_mid) * 100.0, 1)
        else:
            friction_pct = 0.0

        friction_warning = friction_pct >= 8.0
        if friction_warning:
            limit_target = round((atm_bid + atm_mid) / 2.0, 2)
            limit_advice = (
                f"⚠️ WIDE SPREAD FRICTION ({friction_pct:.1f}%): AVOID market orders. "
                f"Work a Limit Order between Bid (${atm_bid:.2f}) and Mid (${atm_mid:.2f}), targeting ${limit_target:.2f}."
            )
        else:
            limit_advice = f"Tight institutional liquidity ({friction_pct:.1f}% spread friction). Work mid-price order at ${atm_mid:.2f}."

        # Strategic Structure Recommendation based on Real Skew:
        if skew_25d >= 4.5:
            skew_regime = "STEEP PUT SKEW (ELEVATED DOWN FLOOR)"
            skew_badge = f"PUT SKEW +{skew_25d:.1f}%"
            skew_color = "#F87171"
            rec_structure = "VERTICAL DEBIT SPREAD OR COLLAR"
            rationale = (
                f"25Δ Put IV ({put_25d_iv:.1f}%) trades {skew_25d:+.1f}% above Call IV ({call_25d_iv:.1f}%). "
                f"Downside protection is expensive. Sell elevated OTM skew to finance a Vertical Debit Spread or Zero-Cost Collar."
            )
        elif skew_25d <= -1.5:
            skew_regime = "CALL WING EXPANSION (BULL SQUEEZE DEMAND)"
            skew_badge = f"CALL SKEW {skew_25d:+.1f}%"
            skew_color = "#34D399"
            rec_structure = "BULL CALL DEBIT SPREAD"
            rationale = (
                f"Call wings trade at a premium ({call_25d_iv:.1f}% vs Put {put_25d_iv:.1f}%). "
                f"Sell the overpriced upper wing strike to finance 60%+ of the ATM Call entry cost."
            )
        else:
            skew_regime = "SYMMETRIC VOLATILITY SKEW"
            skew_badge = f"BALANCED SKEW ({skew_25d:+.1f}%)"
            skew_color = "#FBBF24"
            rec_structure = "30-45 DTE NAKED OTM OPTION"
            rationale = f"Balanced 25Δ skew ({skew_25d:+.1f}%). Standard single-leg 0.30Δ options execution is optimal."

        # Filter liquid OPRA quotes before Gatheral SVI calibration & compute Put-Call Parity Implied Carry
        svi_info: Dict[str, Any] = {}
        implied_carry_pct = 0.0
        implied_borrow_bps = 0.0
        synthetic_fwd = round(under_p, 2)
        t_exp_yrs = max(7.0, float(df["dte"].median() if "dte" in df.columns and not df["dte"].dropna().empty else dte)) / 365.0
        r_ref = 0.0425

        try:
            import quant_kernel

            def _filter_liquid(sub_df: pd.DataFrame) -> pd.DataFrame:
                if sub_df is None or sub_df.empty:
                    return pd.DataFrame()
                tmp = sub_df.copy()
                tmp["bid_f"] = pd.to_numeric(tmp.get("bid", 0.0), errors="coerce").fillna(0.0)
                tmp["ask_f"] = pd.to_numeric(tmp.get("ask", 0.0), errors="coerce").fillna(0.0)
                tmp["mid_f"] = pd.to_numeric(tmp.get("mid", 0.0), errors="coerce").fillna((tmp["bid_f"] + tmp["ask_f"]) / 2.0)
                tmp["iv_f"] = pd.to_numeric(tmp.get("impliedVolatility", 0.0), errors="coerce").fillna(0.0)
                tmp["spr_rel"] = (tmp["ask_f"] - tmp["bid_f"]) / tmp["mid_f"].clip(lower=0.05)
                liq = tmp[
                    (tmp["bid_f"] > 0.0)
                    & (tmp["ask_f"] >= tmp["bid_f"])
                    & (tmp["spr_rel"] <= 0.40)
                    & (tmp["iv_f"].between(0.05, 2.80))
                ]
                return liq if len(liq) >= 2 else tmp[tmp["iv_f"].between(0.05, 2.80)]

            otm_p = _filter_liquid(puts[puts["strike"] <= under_p])
            otm_c = _filter_liquid(calls[calls["strike"] > under_p])
            smile_df = pd.concat([otm_p, otm_c]).sort_values("strike").drop_duplicates("strike")
            if len(smile_df) >= 4:
                spr_col = pd.to_numeric(smile_df.get("spr_rel", 0.10), errors="coerce").fillna(0.10).to_numpy(dtype=float)
                inv_w = 1.0 / np.clip(spr_col, 0.02, 0.50)
                svi_info = quant_kernel.fit_svi_volatility_smile(
                    smile_df["strike"].to_numpy(dtype=float),
                    smile_df["impliedVolatility"].to_numpy(dtype=float),
                    spot=under_p,
                    t_years=t_exp_yrs,
                    r=r_ref,
                    q=0.0,
                    weights=inv_w,
                )

            # Put-Call Parity Implied Carry / Hard-to-Borrow Yield from near-ATM pairs
            c_liq = _filter_liquid(calls)
            p_liq = _filter_liquid(puts)
            if not c_liq.empty and not p_liq.empty and under_p > 1.0:
                merged_cp = pd.merge(
                    c_liq[["strike", "mid_f"]],
                    p_liq[["strike", "mid_f"]],
                    on="strike",
                    suffixes=("_c", "_p"),
                )
                if not merged_cp.empty:
                    merged_cp["dist"] = (merged_cp["strike"] - under_p).abs()
                    near_cp = merged_cp.nsmallest(3, "dist")
                    q_ests = []
                    for _, prow in near_cp.iterrows():
                        k_p = float(prow["strike"])
                        c_mid_p = float(prow["mid_f_c"])
                        p_mid_p = float(prow["mid_f_p"])
                        disc_k = k_p * math.exp(-r_ref * t_exp_yrs)
                        pv_spot_adj = c_mid_p - p_mid_p + disc_k
                        if pv_spot_adj > 0.25 * under_p:
                            q_val = -math.log(pv_spot_adj / under_p) / max(0.01, t_exp_yrs)
                            if -0.25 <= q_val <= 0.35:
                                q_ests.append(q_val)
                    if q_ests:
                        q_med = float(np.median(q_ests))
                        implied_carry_pct = round(q_med * 100.0, 2)
                        implied_borrow_bps = round(max(0.0, q_med) * 10000.0, 0)
                        synthetic_fwd = round(under_p * math.exp((r_ref - q_med) * t_exp_yrs), 2)
        except Exception:
            svi_info = {}

        res = {
            "symbol": sym,
            "skew_25d_pct": skew_25d,
            "skew_regime": skew_regime,
            "skew_badge": skew_badge,
            "skew_color": skew_color,
            "call_25d_strike": call_25d_k,
            "call_25d_iv": call_25d_iv,
            "put_25d_strike": put_25d_k,
            "put_25d_iv": put_25d_iv,
            "atm_bid": atm_bid,
            "atm_ask": atm_ask,
            "atm_mid": atm_mid,
            "spread_friction_pct": friction_pct,
            "friction_warning": friction_warning,
            "limit_order_advice": limit_advice,
            "recommended_structure": rec_structure,
            "structure_rationale": rationale,
            "svi_rho": svi_info.get("svi_rho", -0.20),
            "svi_vol_of_vol": svi_info.get("svi_vol_of_vol", 0.15),
            "svi_params": svi_info.get("svi_params", {}),
            "svi_rmse_vol_pts": svi_info.get("svi_rmse_vol_pts", 0.0),
            "butterfly_arbitrage_free": svi_info.get("butterfly_arbitrage_free", True),
            "cheapest_strike": svi_info.get("cheapest_strike", call_25d_k),
            "cheapest_iv_discount_pct": svi_info.get("cheapest_iv_discount_pct", 0.0),
            "cheapest_call_strike": svi_info.get("cheapest_call_strike", call_25d_k),
            "cheapest_call_edge_vol_pts": svi_info.get("cheapest_call_edge_vol_pts", 0.0),
            "cheapest_put_strike": svi_info.get("cheapest_put_strike", put_25d_k),
            "cheapest_put_edge_vol_pts": svi_info.get("cheapest_put_edge_vol_pts", 0.0),
            "richest_strike": svi_info.get("richest_strike", put_25d_k),
            "richest_iv_premium_pct": svi_info.get("richest_iv_premium_pct", 0.0),
            "implied_carry_yield_pct": implied_carry_pct,
            "implied_borrow_bps": implied_borrow_bps,
            "synthetic_forward_price": synthetic_fwd,
            "has_data": True
        }
        _set_cached(cache_key, res)
        return res
    except Exception as e:
        _set_cached(cache_key, default_out)
        return default_out


def get_iv_term_structure_and_implied_move(
    symbol: str,
    spot: float = 0.0,
    primary_chain_df: Optional[pd.DataFrame] = None,
    ttl: int = 900,
) -> Dict[str, Any]:
    """
    Fetches lightweight ATM OPRA slices across 4 DTE term buckets:
      1. Front Event (7-20 DTE)
      2. Core Swing (24-42 DTE — reuses `primary_chain_df` at zero extra API cost)
      3. Mid Cycle (45-68 DTE)
      4. Back Macro (70-115 DTE)
    Computes Term Structure Slope (30D-60D/Back), Forward Volatility (T1 -> T2),
    ATM Straddle Implied Move %, and Multi-Expiry GEX/Vanna aggregation.
    """
    sym = (symbol or "").strip().upper()
    default_ts = {
        "symbol": sym,
        "has_data": False,
        "term_points": [],
        "front_iv_pct": 0.0,
        "core_iv_pct": 0.0,
        "back_iv_pct": 0.0,
        "term_slope_30_60_pct": 0.0,
        "forward_vol_30_60_pct": 0.0,
        "term_regime": "UNAVAILABLE",
        "front_implied_move_pct": 0.0,
        "core_implied_move_pct": 0.0,
        "multi_expiry_gex_m": 0.0,
        "multi_expiry_vanna_m": 0.0,
        "multi_expiry_gamma_flip": 0.0,
    }
    if not sym or sym.startswith("^"):
        return default_ts

    cache_key = f"opra_term_struct_v1_{sym}"
    cached = _get_cached(cache_key, ttl=ttl)
    if cached is not None:
        return cached

    try:
        under_p = float(spot or 0.0)
        if under_p <= 0 and primary_chain_df is not None and not primary_chain_df.empty:
            under_p = float(primary_chain_df["underlyingPrice"].iloc[0] or 0.0)
        if under_p <= 0:
            return default_ts

        def _extract_atm_metrics(sub_df: Optional[pd.DataFrame], label: str) -> Optional[Dict[str, Any]]:
            if sub_df is None or sub_df.empty or "strike" not in sub_df.columns:
                return None
            c_df = sub_df[sub_df["side"].str.lower() == "call"].copy()
            p_df = sub_df[sub_df["side"].str.lower() == "put"].copy()
            if c_df.empty or p_df.empty:
                return None
            dte_val = int(sub_df["dte"].median() if "dte" in sub_df.columns and not sub_df["dte"].dropna().empty else 35)
            exp_val = str(sub_df["expiration"].iloc[0] or "")[:10]
            # Pick strike closest to spot with both call & put quotes
            common_strikes = sorted(set(c_df["strike"].astype(float)).intersection(set(p_df["strike"].astype(float))))
            if not common_strikes:
                return None
            atm_k = min(common_strikes, key=lambda k: abs(k - under_p))
            c_row = c_df[c_df["strike"] == atm_k].iloc[0]
            p_row = p_df[p_df["strike"] == atm_k].iloc[0]
            c_mid = float(c_row.get("mid", 0.0) or ((float(c_row.get("bid", 0.0) or 0.0) + float(c_row.get("ask", 0.0) or 0.0)) / 2.0))
            p_mid = float(p_row.get("mid", 0.0) or ((float(p_row.get("bid", 0.0) or 0.0) + float(p_row.get("ask", 0.0) or 0.0)) / 2.0))
            straddle_mid = round(max(0.0, c_mid + p_mid), 2)
            c_iv = float(c_row.get("impliedVolatility", 0.0) or 0.0)
            p_iv = float(p_row.get("impliedVolatility", 0.0) or 0.0)
            valid_ivs = [x * (100.0 if x <= 3.5 else 1.0) for x in (c_iv, p_iv) if x > 0.02]
            if not valid_ivs:
                return None
            atm_iv_pct = round(float(np.mean(valid_ivs)), 2)
            # Standard 0.85x ATM Straddle empirical 1-sigma expected move
            implied_mv_pct = round((straddle_mid * 0.85 / under_p) * 100.0, 2) if straddle_mid > 0 else round(atm_iv_pct * math.sqrt(max(1, dte_val) / 252.0), 2)
            straddle_be_pct = round((straddle_mid / under_p) * 100.0, 2) if straddle_mid > 0 else round(implied_mv_pct / 0.85, 2)
            return {
                "label": label,
                "dte": max(1, dte_val),
                "expiration": exp_val,
                "atm_strike": float(atm_k),
                "atm_iv_pct": atm_iv_pct,
                "straddle_mid": straddle_mid,
                "implied_move_pct": implied_mv_pct,
                "straddle_breakeven_pct": straddle_be_pct,
            }

        exps = get_option_expirations(sym, ttl=3600)
        today_d = datetime.date.today()
        primary_exp = ""
        primary_dte = 35
        if primary_chain_df is not None and not primary_chain_df.empty:
            primary_exp = str(primary_chain_df["expiration"].iloc[0] or "")[:10]
            primary_dte = int(primary_chain_df["dte"].median() or 35)

        buckets = [
            ("Front", 14, 7, 22),
            ("Core 35D", 35, 23, 44),
            ("Mid 55D", 55, 45, 70),
            ("Back 90D", 90, 71, 130),
        ]
        chosen: List[Tuple[str, str, int]] = []
        used_exps = set()
        if primary_exp:
            used_exps.add(primary_exp)

        for label, target_dte, lo_d, hi_d in buckets:
            if primary_exp and lo_d <= primary_dte <= hi_d:
                chosen.append((label, primary_exp, primary_dte))
                continue
            cands = []
            for e_str in exps:
                e_iso = str(e_str)[:10]
                if e_iso in used_exps:
                    continue
                try:
                    days_out = (datetime.date.fromisoformat(e_iso) - today_d).days
                    if lo_d <= days_out <= hi_d:
                        cands.append((abs(days_out - target_dte), e_iso, days_out))
                except Exception:
                    continue
            if cands:
                cands.sort(key=lambda x: x[0])
                chosen.append((label, cands[0][1], cands[0][2]))
                used_exps.add(cands[0][1])

        term_points: List[Dict[str, Any]] = []
        front_df = None
        for label, exp_iso, _ in chosen:
            if primary_exp and exp_iso == primary_exp and primary_chain_df is not None and not primary_chain_df.empty:
                df_bucket = primary_chain_df
            else:
                df_bucket = get_option_chain_native(sym, expiration=exp_iso, strike_limit=10, ttl=ttl, feed="cached")
                if label == "Front":
                    front_df = df_bucket
            pt = _extract_atm_metrics(df_bucket, label)
            if pt:
                term_points.append(pt)

        if not term_points and primary_chain_df is not None and not primary_chain_df.empty:
            pt0 = _extract_atm_metrics(primary_chain_df, "Core 35D")
            if pt0:
                term_points.append(pt0)

        if not term_points:
            _set_cached(cache_key, default_ts)
            return default_ts

        term_points.sort(key=lambda x: x["dte"])
        front_pt = term_points[0]
        core_pt = min(term_points, key=lambda x: abs(x["dte"] - 35))
        back_pt = term_points[-1]

        front_iv = float(front_pt["atm_iv_pct"])
        core_iv = float(core_pt["atm_iv_pct"])
        back_iv = float(back_pt["atm_iv_pct"])
        slope_pct = round(core_iv - back_iv, 2) if len(term_points) >= 2 else 0.0

        # Forward annualized volatility implied between core/front and back expirations
        fwd_vol = core_iv
        if len(term_points) >= 2 and back_pt["dte"] > core_pt["dte"]:
            t1 = core_pt["dte"] / 365.0
            t2 = back_pt["dte"] / 365.0
            v1 = (core_iv / 100.0) ** 2
            v2 = (back_iv / 100.0) ** 2
            fwd_var = max(1e-4, (v2 * t2 - v1 * t1) / max(0.01, t2 - t1))
            fwd_vol = round(math.sqrt(fwd_var) * 100.0, 2)
        elif len(term_points) >= 2 and back_pt["dte"] > front_pt["dte"]:
            t1 = front_pt["dte"] / 365.0
            t2 = back_pt["dte"] / 365.0
            v1 = (front_iv / 100.0) ** 2
            v2 = (back_iv / 100.0) ** 2
            fwd_var = max(1e-4, (v2 * t2 - v1 * t1) / max(0.01, t2 - t1))
            fwd_vol = round(math.sqrt(fwd_var) * 100.0, 2)

        if slope_pct > 2.0:
            term_regime = "BACKWARDATION (EVENT VOL PRICED)"
        elif slope_pct < -2.5:
            term_regime = "STEEP CONTANGO (CALM CARRY)"
        else:
            term_regime = "NORMAL CONTANGO"

        # Multi-expiry dealer GEX/Vanna aggregation combining primary + front chain
        multi_gex = 0.0
        multi_vanna = 0.0
        multi_flip = round(under_p, 2)
        try:
            import quant_kernel
            comb_parts = []
            if primary_chain_df is not None and not primary_chain_df.empty:
                comb_parts.append(primary_chain_df)
            if front_df is not None and not front_df.empty:
                comb_parts.append(front_df)
            if comb_parts:
                comb_df = pd.concat(comb_parts, ignore_index=True)
                vc_multi = quant_kernel.compute_dealer_vanna_charm_profile(comb_df, spot=under_p)
                multi_gex = float(vc_multi.get("net_gex_m", 0.0))
                multi_vanna = float(vc_multi.get("net_vanna_m", 0.0))
                multi_flip = float(vc_multi.get("gamma_flip_strike", round(under_p, 2)))
        except Exception:
            pass

        out = {
            "symbol": sym,
            "has_data": True,
            "term_points": term_points,
            "front_iv_pct": front_iv,
            "core_iv_pct": core_iv,
            "back_iv_pct": back_iv,
            "term_slope_30_60_pct": slope_pct,
            "forward_vol_30_60_pct": fwd_vol,
            "term_regime": term_regime,
            "front_implied_move_pct": float(front_pt["implied_move_pct"]),
            "core_implied_move_pct": float(core_pt["implied_move_pct"]),
            "multi_expiry_gex_m": round(multi_gex, 2),
            "multi_expiry_vanna_m": round(multi_vanna, 2),
            "multi_expiry_gamma_flip": multi_flip,
        }
        _set_cached(cache_key, out)
        return out
    except Exception:
        _set_cached(cache_key, default_ts)
        return default_ts
