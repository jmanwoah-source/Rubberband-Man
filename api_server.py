"""
Rubberband Man FastAPI Backend
==============================
Exposes the institutional quant, options pricing, 5Y empirical backtest,
5-day catalyst, SQLite practice diary, and Learn Mode education engines over
a clean JSON API and serves the built React PWA from `web/dist`.
"""
from __future__ import annotations

import datetime
import math
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import diary_db
import edu_annotations
import marketdata_client
import rubberband_engine_v3 as rbe3

THEMATIC_ETFS: List[str] = ["REMX", "SRVR", "ROBO", "JEDI", "SMH", "URA", "QTUM", "IGV"]
ROOT_DIR = Path(__file__).resolve().parent
WEB_DIST_DIR = ROOT_DIR / "web" / "dist"


class _TTLCache:
    """Thread-safe in-memory TTL cache for expensive market/engine calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: Dict[str, tuple[float, Any]] = {}

    def get_or_compute(self, key: str, ttl_seconds: float, fn) -> Any:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry and entry[0] > now:
                return entry[1]
        val = fn()
        with self._lock:
            self._store[key] = (time.monotonic() + ttl_seconds, val)
        return val


_CACHE = _TTLCache()


def _clean_json(obj: Any) -> Any:
    """Recursively convert NumPy/Pandas types and non-finite floats into strict JSON-safe values."""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return [_clean_json(x) for x in obj.tolist()]
    if isinstance(obj, pd.DataFrame):
        return None
    if isinstance(obj, pd.Series):
        return [_clean_json(x) for x in obj.tolist()]
    if isinstance(obj, dict):
        return {
            str(k): _clean_json(v)
            for k, v in obj.items()
            if not isinstance(v, pd.DataFrame)
        }
    if isinstance(obj, (list, tuple, set)):
        return [_clean_json(x) for x in obj]
    return obj


def _normalize_sector(sector_name: str) -> str:
    raw = str(sector_name or "Semiconductors").strip()
    if hasattr(rbe3, "normalize_sector_name"):
        try:
            return rbe3.normalize_sector_name(raw)
        except Exception:
            pass
    sectors = list(getattr(rbe3, "SECTORS", {}).keys())
    return raw if raw in sectors else (sectors[0] if sectors else "Semiconductors")


def _compact_candidate_row(cand: Dict[str, Any]) -> Dict[str, Any]:
    """Return a fast, lightweight summary row for Scanner lists while preserving key signal badges."""
    m = cand.get("metrics") or {}
    bp = cand.get("blueprint") or {}
    qe = cand.get("quant_edge") or m.get("quant_edge") or {}
    tel = cand.get("options_telemetry") or m.get("options_telemetry") or {}
    near = m.get("near_live_option") if isinstance(m.get("near_live_option"), dict) else {}
    return _clean_json({
        "symbol": cand.get("symbol"),
        "company_name": cand.get("company_name"),
        "sector": cand.get("sector"),
        "is_etf": bool(cand.get("is_etf", False)),
        "is_top5_vetted": bool(cand.get("is_top5_vetted", False)),
        "sector_rank": cand.get("sector_rank"),
        "price": m.get("price"),
        "change_pct_1d": m.get("change_pct_1d"),
        "z_score_5d": m.get("z_score_5d"),
        "action": m.get("action") or bp.get("direction") or "MONITOR",
        "conviction_score_200": cand.get("conviction_score_200") if cand.get("conviction_score_200") is not None else bp.get("conviction_score_200", 0),
        "conviction_tier": cand.get("conviction_tier") or bp.get("conviction_tier") or "WATCH",
        "recommended_dte": cand.get("recommended_dte") or bp.get("recommended_dte") or 35,
        "empirical_win_rate_pct": m.get("empirical_win_rate_pct", 55.0),
        "empirical_sample_n": m.get("empirical_sample_n", 40),
        "net_ev_pct": qe.get("net_ev_pct") if qe.get("net_ev_pct") is not None else bp.get("net_ev_pct", 0.0),
        "strike": near.get("strike") or m.get("recommended_strike") or m.get("price"),
        "delta": near.get("delta") or m.get("estimated_delta") or 0.50,
        "mid": near.get("mid") or tel.get("prem_entry"),
        "vrp_vol_pts": tel.get("vrp_vol_pts", 0.0),
        "prefer_spread": bool(tel.get("prefer_spread", False)),
        "days_to_earnings": m.get("days_to_earnings", 45),
        "whale_badge": m.get("whale_badge", "FLOW"),
    })


def _build_chart_series(symbol: str, live_price: Optional[float] = None, bars: int = 95) -> List[Dict[str, Any]]:
    """Compute OHLCV + VWMA-20 equilibrium + ±2σ envelope for Lightweight Charts."""
    sym = str(symbol or "NVDA").strip().upper()
    df = _CACHE.get_or_compute(
        f"hist:{sym}",
        300.0,
        lambda: rbe3.get_historical_series(sym),
    )
    if df is None or not isinstance(df, pd.DataFrame) or df.empty or "close" not in df.columns:
        return []

    work = df.copy()
    if not isinstance(work.index, pd.DatetimeIndex):
        work.index = pd.to_datetime(work.index, errors="coerce")
    work = work[work.index.notna()].sort_index()
    work = work.dropna(subset=["close"])
    if work.empty:
        return []

    if "volume" in work.columns and float(work["volume"].fillna(0).sum()) > 0:
        vol = work["volume"].fillna(0.0).clip(lower=0.0)
        pv = work["close"] * vol
        vwma20 = pv.rolling(20, min_periods=5).sum() / vol.rolling(20, min_periods=5).sum().replace(0.0, np.nan)
        vwma20 = vwma20.fillna(work["close"].rolling(20, min_periods=1).mean())
    else:
        vwma20 = work["close"].rolling(20, min_periods=1).mean()

    ema20 = work["close"].ewm(span=20, adjust=False).mean()
    equil = 0.55 * vwma20 + 0.45 * ema20
    std20 = work["close"].rolling(20, min_periods=5).std().bfill().fillna(work["close"] * 0.03)

    if "high" in work.columns and "low" in work.columns:
        prev_c = work["close"].shift(1).fillna(work["close"])
        tr = pd.concat(
            [
                (work["high"] - work["low"]).abs(),
                (work["high"] - prev_c).abs(),
                (work["low"] - prev_c).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr14 = tr.ewm(alpha=1.0 / 14.0, adjust=False).mean().bfill()
    else:
        atr14 = std20

    unit = np.maximum(std20, 1.35 * atr14)
    work["equil"] = equil
    work["upper2"] = equil + 2.0 * unit
    work["lower2"] = np.maximum(0.5, equil - 2.0 * unit)

    tail = work.tail(max(30, min(250, bars)))
    seen_dates = set()
    rows: List[Dict[str, Any]] = []
    for idx, row in tail.iterrows():
        dt_str = idx.strftime("%Y-%m-%d")
        if dt_str in seen_dates:
            continue
        seen_dates.add(dt_str)
        c_val = float(row["close"])
        o_val = float(row["open"]) if "open" in tail.columns and pd.notna(row["open"]) else c_val
        h_val = float(row["high"]) if "high" in tail.columns and pd.notna(row["high"]) else max(o_val, c_val)
        l_val = float(row["low"]) if "low" in tail.columns and pd.notna(row["low"]) else min(o_val, c_val)
        v_val = float(row["volume"]) if "volume" in tail.columns and pd.notna(row["volume"]) else 0.0
        rows.append({
            "time": dt_str,
            "open": round(o_val, 2),
            "high": round(h_val, 2),
            "low": round(l_val, 2),
            "close": round(c_val, 2),
            "volume": int(max(0, round(v_val))),
            "vwma20": round(float(row["equil"]), 2),
            "upper2": round(float(row["upper2"]), 2),
            "lower2": round(float(row["lower2"]), 2),
        })

    if rows and live_price is not None and math.isfinite(float(live_price)) and float(live_price) > 0:
        lp = round(float(live_price), 2)
        rows[-1]["close"] = lp
        rows[-1]["high"] = max(rows[-1]["high"], lp)
        rows[-1]["low"] = min(rows[-1]["low"], lp)

    return _clean_json(rows)


def _compute_options_telemetry(
    symbol: str,
    cand: Dict[str, Any],
    dte: int = 35,
    hold_days: int = 5,
    iv_shift: float = 0.0,
) -> Dict[str, Any]:
    m = cand.get("metrics") or {}
    near = m.get("near_live_option") if isinstance(m.get("near_live_option"), dict) else None
    try:
        chain_df = _CACHE.get_or_compute(
            f"chain:{symbol}:{dte}",
            300.0,
            lambda: marketdata_client.get_option_chain_native(symbol, dte=dte, strike_limit=36, ttl=300, feed="cached"),
        )
    except Exception:
        chain_df = None
    try:
        telem = rbe3.calculate_options_volatility_and_spread_telemetry(
            symbol=symbol,
            metrics=m,
            live_option=near,
            dte=dte,
            hold_days=hold_days,
            iv_shift_pct=iv_shift,
            chain_df=chain_df,
            skew_optimizer=cand.get("skew_optimizer"),
            term_structure=cand.get("term_structure"),
        )
        return _clean_json(telem)
    except Exception:
        return _clean_json(cand.get("options_telemetry") or m.get("options_telemetry") or {})


def _build_edu_bundle(
    symbol: str,
    sector: str,
    cand: Dict[str, Any],
    macro_pulse: Dict[str, Any],
    catalyst_outlook: Dict[str, Any],
    options_telem: Dict[str, Any],
    ranked_cands: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, str]]:
    m = cand.get("metrics") or {}
    bp = cand.get("blueprint") or {}
    qe = cand.get("quant_edge") or m.get("quant_edge") or {}
    gw = cand.get("gamma_walls") or m.get("gamma_walls") or {}
    near = m.get("near_live_option") if isinstance(m.get("near_live_option"), dict) else {}
    symb = (catalyst_outlook.get("symbolism") if isinstance(catalyst_outlook, dict) else None) or macro_pulse.get("symbolism") or {}

    spot = float(m.get("price") or 100.0)
    mid_v = float(near.get("mid") or options_telem.get("prem_entry") or 2.50)
    strike_v = float(near.get("strike") or options_telem.get("strike_used") or m.get("recommended_strike") or spot)
    s200 = int(cand.get("conviction_score_200") if cand.get("conviction_score_200") is not None else bp.get("conviction_score_200") or 0)
    top_row = ranked_cands[0] if ranked_cands else cand
    top_m = top_row.get("metrics") or {}
    top_qe = top_row.get("quant_edge") or top_m.get("quant_edge") or {}
    top_tel = top_row.get("options_telemetry") or top_m.get("options_telemetry") or {}

    contexts = {
        "mobile_hero": {
            "symbol": symbol,
            "z_score_5d": m.get("z_score_5d", 0.0),
            "ou_half_life": m.get("ou_half_life", 4.5),
            "conviction_score_200": s200,
            "contract_cost": mid_v * 100.0,
            "breakeven": options_telem.get("breakeven_hold_price", strike_v + mid_v),
        },
        "elasticity_micro": {
            "symbol": symbol,
            "z_score_5d": m.get("z_score_5d", 0.0),
            "kalman_beta": qe.get("kalman_beta") or m.get("kalman_beta") or m.get("beta", 1.15),
            "ou_half_life": m.get("ou_half_life", 5.0),
            "hurst": m.get("hurst_exponent") or m.get("hurst") or 0.48,
            "clv": m.get("clv_today", m.get("clv", 0.0)),
            "rvol": m.get("rvol", 1.0),
        },
        "conviction_5pillar": {
            "conviction_score_200": s200,
            "conviction_tier": cand.get("conviction_tier") or bp.get("conviction_tier") or "WATCH",
            "synergy_unlocked": bool(cand.get("synergy_unlocked", bp.get("synergy_unlocked", False))),
            "regime_gate_mult": cand.get("regime_gate_mult", bp.get("regime_gate_mult", 1.0)),
        },
        "trade_anatomy": {
            "symbol": symbol,
            "spot": spot,
            "vwma20": m.get("vwma20", spot),
            "strike": strike_v,
            "breakeven": options_telem.get("breakeven_hold_price", spot),
            "target_price": m.get("target_price", spot * 1.05),
            "stop_price": m.get("invalidation_price", spot * 0.95),
            "call_wall": gw.get("call_wall_strike", 0.0),
            "put_wall": gw.get("put_wall_strike", 0.0),
            "gamma_flip": gw.get("gamma_flip_strike", 0.0),
        },
        "options_surface": {
            "opra_iv": options_telem.get("iv_pct", 35.0),
            "hv20": options_telem.get("hv20_pct", 35.0),
            "net_gex_m": gw.get("net_gex_m", 0.0),
            "gamma_flip_strike": gw.get("gamma_flip_strike", spot),
            "net_vanna_m": gw.get("net_vanna_m", 0.0),
            "variance_rent_ratio": options_telem.get("variance_rent_ratio", 1.0),
            "prefer_spread": options_telem.get("prefer_spread", False),
        },
        "scanner_matrix": {
            "sector": sector,
            "top_symbol": top_row.get("symbol", symbol),
            "net_ev_pct": top_qe.get("net_ev_pct", 0.0),
            "win_rate_pct": top_m.get("empirical_win_rate_pct", 55.0),
            "sample_n": top_m.get("empirical_sample_n", 40),
            "vrp_pts": top_tel.get("vrp_vol_pts", 0.0),
            "prefer_spread": top_tel.get("prefer_spread", False),
        },
        "macro_regime": {
            "vix_ratio": symb.get("vix_ratio", 0.94),
            "credit_z": symb.get("credit_z", 0.0),
            "tnx_yield": symb.get("tnx_yield", 4.25),
            "exposure_cap_pct": symb.get("exposure_cap_pct", 100),
            "regime_label": symb.get("regime_label", macro_pulse.get("market_regime_badge", "MACRO EQUILIBRIUM")),
        },
        "ev_kelly_backtest": {
            "net_ev_pct": qe.get("net_ev_pct", 0.0),
            "bayesian_win_prob_pct": qe.get("bayesian_win_prob_pct", m.get("empirical_win_rate_pct", 55.0)),
            "quarter_kelly_pct": qe.get("quarter_kelly_pct", 0.0),
            "spread_friction_pct": (cand.get("skew_optimizer") or {}).get("spread_friction_pct", 5.0),
            "edge_t_stat": qe.get("edge_t_stat", 0.0),
        },
    }
    out: Dict[str, Dict[str, str]] = {}
    for k, ctx in contexts.items():
        topic = edu_annotations.get_edu_topic(k, ctx)
        if topic:
            out[k] = topic
    return out


class CreateTradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=12)
    action: str = "BUY_TO_OPEN"
    option_type: str = "CALL"
    strike: float = Field(..., gt=0)
    expiration_date: str = Field(..., min_length=8, max_length=20)
    quantity: int = Field(1, ge=1, le=500)
    limit_price: float = Field(..., gt=0)
    stock_price_at_entry: float = Field(..., gt=0)
    strategy: str = "SINGLE_LEG"
    order_type: str = "LIMIT"
    target_stock_price: Optional[float] = None
    stop_stock_price: Optional[float] = None
    conviction_score: float = 50.0
    expected_basis_pct: float = 0.0
    whale_badge: str = "TWO-WAY FLOW"
    catalyst_tag: str = ""
    notes: str = ""
    dte: Optional[int] = 35
    short_strike: Optional[float] = None


class CloseTradeRequest(BaseModel):
    exit_premium: float = Field(..., ge=0.0)
    exit_stock_price: float = Field(..., gt=0.0)
    exit_notes: str = ""


app = FastAPI(title="Rubberband Man API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    diary_db.init_diary_db()


@app.get("/api/health")
def api_health() -> Dict[str, Any]:
    sectors = list(getattr(rbe3, "SECTORS", {}).keys())
    return {
        "ok": True,
        "sectors": sectors,
        "thematic_etfs": THEMATIC_ETFS,
        "pwa_built": WEB_DIST_DIR.exists(),
    }


@app.get("/api/bootstrap")
def api_bootstrap(
    sector: str = Query("Semiconductors"),
    ticker: str = Query(""),
) -> Dict[str, Any]:
    norm_sec = _normalize_sector(sector)
    sectors_list = list(getattr(rbe3, "SECTORS", {}).keys())
    req_tk = str(ticker or "").strip().upper()

    ranked = _CACHE.get_or_compute(
        f"sector_scan:{norm_sec}",
        300.0,
        lambda: rbe3.get_ranked_sector_candidates(norm_sec, top_n_vet=5),
    )

    active_cand = None
    if req_tk:
        active_cand = next((c for c in ranked if str(c.get("symbol", "")).upper() == req_tk), None)
        if active_cand is None:
            bench = getattr(rbe3, "SECTORS", {}).get(norm_sec, {}).get("benchmark", "SMH")
            active_cand = _CACHE.get_or_compute(
                f"cand:{req_tk}:{bench}",
                180.0,
                lambda: rbe3.get_due_diligence_candidate(req_tk, benchmark_symbol=bench, vet_deep=True),
            )
    if active_cand is None and ranked:
        active_cand = ranked[0]

    if active_cand is None:
        raise HTTPException(status_code=404, detail=f"Unable to load candidate data for {req_tk or norm_sec}")

    active_sym = str(active_cand.get("symbol") or req_tk or "NVDA").upper()
    macro_pulse = _CACHE.get_or_compute("macro_pulse", 180.0, rbe3.get_sector_macro_pulse)
    cat_outlook = _CACHE.get_or_compute(
        f"catalyst:{norm_sec}:{active_sym}",
        180.0,
        lambda: rbe3.get_unified_5day_catalyst_outlook(sector_name=norm_sec, active_ticker=active_sym),
    )

    rec_dte = int(active_cand.get("recommended_dte") or (active_cand.get("blueprint") or {}).get("recommended_dte") or 35)
    options_telem = _compute_options_telemetry(active_sym, active_cand, dte=rec_dte, hold_days=5, iv_shift=0.0)
    live_p = (active_cand.get("metrics") or {}).get("price")
    chart_series = _build_chart_series(active_sym, live_price=live_p, bars=95)
    edu_bundle = _build_edu_bundle(active_sym, norm_sec, active_cand, macro_pulse, cat_outlook, options_telem, ranked)

    return _clean_json({
        "sector": norm_sec,
        "sectors": sectors_list,
        "thematic_etfs": THEMATIC_ETFS,
        "macro_pulse": macro_pulse,
        "catalyst_outlook": cat_outlook,
        "ranked_candidates": [_compact_candidate_row(c) for c in ranked[:12]],
        "active_ticker": active_sym,
        "active_candidate": active_cand,
        "chart_series": chart_series,
        "options_telemetry": options_telem,
        "edu_topics": edu_bundle,
    })


@app.get("/api/ticker/{symbol}")
def api_ticker_detail(
    symbol: str,
    sector: str = Query("Semiconductors"),
    dte: int = Query(35, ge=7, le=180),
    hold_days: int = Query(5, ge=1, le=30),
    iv_shift: float = Query(0.0, ge=-40.0, le=60.0),
) -> Dict[str, Any]:
    sym = "".join(ch for ch in str(symbol or "").strip().upper() if ch.isalnum() or ch in (".", "-", "^"))[:12]
    if not sym:
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    norm_sec = _normalize_sector(sector)
    bench = getattr(rbe3, "SECTORS", {}).get(norm_sec, {}).get("benchmark", "SMH")
    cand = _CACHE.get_or_compute(
        f"cand:{sym}:{bench}",
        180.0,
        lambda: rbe3.get_due_diligence_candidate(sym, benchmark_symbol=bench, vet_deep=True),
    )
    if not cand:
        raise HTTPException(status_code=404, detail=f"Ticker {sym} not found")

    macro_pulse = _CACHE.get_or_compute("macro_pulse", 180.0, rbe3.get_sector_macro_pulse)
    cat_outlook = _CACHE.get_or_compute(
        f"catalyst:{norm_sec}:{sym}",
        180.0,
        lambda: rbe3.get_unified_5day_catalyst_outlook(sector_name=norm_sec, active_ticker=sym),
    )
    options_telem = _compute_options_telemetry(sym, cand, dte=dte, hold_days=hold_days, iv_shift=iv_shift)
    live_p = (cand.get("metrics") or {}).get("price")
    chart_series = _build_chart_series(sym, live_price=live_p, bars=95)
    edu_bundle = _build_edu_bundle(sym, norm_sec, cand, macro_pulse, cat_outlook, options_telem, None)

    return _clean_json({
        "symbol": sym,
        "sector": norm_sec,
        "active_candidate": cand,
        "catalyst_outlook": cat_outlook,
        "chart_series": chart_series,
        "options_telemetry": options_telem,
        "edu_topics": edu_bundle,
    })


@app.get("/api/diary")
def api_get_diary() -> Dict[str, Any]:
    diary_db.init_diary_db()
    summary = diary_db.get_diary_portfolio_summary()
    open_trades = diary_db.get_open_trades()
    closed_trades = diary_db.get_closed_trades(limit=50)
    edu_ticket = edu_annotations.get_edu_topic("schwab_ticket", {"symbol": open_trades[0]["symbol"] if open_trades else "NVDA"})
    return _clean_json({
        "summary": summary,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "edu_topic": edu_ticket,
    })


@app.post("/api/diary/trades")
def api_create_trade(payload: CreateTradeRequest) -> Dict[str, Any]:
    diary_db.init_diary_db()
    sym = "".join(ch for ch in payload.symbol.upper().strip() if ch.isalnum() or ch in (".", "-", "^"))[:12]
    if not sym:
        raise HTTPException(status_code=400, detail="Invalid symbol")

    trade = diary_db.create_simulated_trade(
        symbol=sym,
        action=payload.action,
        option_type=payload.option_type,
        strike=payload.strike,
        expiration_date=payload.expiration_date,
        quantity=payload.quantity,
        limit_price=payload.limit_price,
        stock_price_at_entry=payload.stock_price_at_entry,
        strategy=payload.strategy,
        order_type=payload.order_type,
        target_stock_price=payload.target_stock_price,
        stop_stock_price=payload.stop_stock_price,
        conviction_score=payload.conviction_score,
        expected_basis_pct=payload.expected_basis_pct,
        whale_badge=payload.whale_badge,
        catalyst_tag=payload.catalyst_tag,
        notes=payload.notes,
        dte=payload.dte,
        short_strike=payload.short_strike,
    )
    return _clean_json({"ok": True, "trade": trade, "summary": diary_db.get_diary_portfolio_summary()})


@app.post("/api/diary/trades/{trade_id}/close")
def api_close_trade(trade_id: int, payload: CloseTradeRequest) -> Dict[str, Any]:
    diary_db.init_diary_db()
    ok = diary_db.close_simulated_trade(
        trade_id=trade_id,
        exit_premium=payload.exit_premium,
        exit_stock_price=payload.exit_stock_price,
        exit_notes=payload.exit_notes,
    )
    if not ok:
        raise HTTPException(status_code=404, detail=f"Open trade #{trade_id} not found or already closed")
    return _clean_json({"ok": True, "summary": diary_db.get_diary_portfolio_summary()})


@app.get("/api/ledger")
def api_get_ledger(
    date: str = Query(""),
    sector: str = Query("All Sectors"),
) -> Dict[str, Any]:
    diary_db.init_diary_db()
    dates = diary_db.get_all_snapshot_dates()
    sel_date = date if (date and date in dates) else (dates[0] if dates else "")
    if not sel_date:
        return _clean_json({"dates": [], "selected_date": "", "snapshots": [], "stats": {"count": 0, "win_rate_pct": 0.0, "avg_dir_pct": 0.0}, "edu_topic": edu_annotations.get_edu_topic("journal_audit", {})})

    all_rows = diary_db.get_historical_snapshots(snapshot_date=sel_date, sector_name=None)
    if sector and sector != "All Sectors":
        norm_target = _normalize_sector(sector)
        rows = [r for r in all_rows if _normalize_sector(r.get("sector", "")) == norm_target]
    else:
        rows = list(all_rows)

    symbols = sorted({str(r.get("symbol", "")).upper() for r in rows if r.get("symbol")})
    quotes = _CACHE.get_or_compute(
        f"quotes:{','.join(symbols)}",
        60.0,
        lambda: rbe3.fmp_batch_quotes(symbols, ttl=60) if symbols else {},
    )

    wins = 0
    sum_dir = 0.0
    enriched: List[Dict[str, Any]] = []
    for r in rows:
        sym = str(r.get("symbol", "")).upper()
        snap_p = float(r.get("price_at_snapshot") or 0.0)
        q = quotes.get(sym, {}) if isinstance(quotes, dict) else {}
        cur_p = float(q.get("price") or snap_p)
        act = str(r.get("action") or "CALL").upper()
        pct = ((cur_p - snap_p) / max(0.01, snap_p)) * 100.0 if snap_p > 0 else 0.0
        dir_ret = -pct if "PUT" in act else pct
        is_win = dir_ret > 0.0
        if is_win:
            wins += 1
        sum_dir += dir_ret
        enriched.append({
            **r,
            "normalized_sector": _normalize_sector(r.get("sector", "")),
            "current_price": round(cur_p, 2),
            "move_pct": round(pct, 2),
            "directional_pct": round(dir_ret, 2),
            "is_win": is_win,
        })

    cnt = len(enriched)
    win_rt = round((wins / cnt) * 100.0, 1) if cnt else 0.0
    avg_d = round(sum_dir / cnt, 2) if cnt else 0.0
    edu_ledger = edu_annotations.get_edu_topic(
        "journal_audit",
        {"snapshot_date": sel_date, "win_rate_pct": win_rt, "avg_dir_pct": avg_d, "avg_opt_roi_pct": round(avg_d * 4.5, 1), "count": cnt},
    )
    return _clean_json({
        "dates": dates,
        "selected_date": sel_date,
        "sectors": ["All Sectors"] + list(getattr(rbe3, "SECTORS", {}).keys()),
        "snapshots": enriched,
        "stats": {"count": cnt, "wins": wins, "win_rate_pct": win_rt, "avg_dir_pct": avg_d},
        "edu_topic": edu_ledger,
    })


if (WEB_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST_DIR / "assets")), name="assets")


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="API endpoint not found")
    candidate = WEB_DIST_DIR / full_path
    if full_path and candidate.exists() and candidate.is_file():
        return FileResponse(str(candidate))
    index_file = WEB_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Rubberband Man API is running. Build web/dist to serve the React PWA."}
