"""
Rubberband Man v4.0 — Institutional 30-45 DTE High-Delta Options Terminal
Obsidian Frosted-Glass + Rich Hyper-Orange (#FF6B00) Conviction Cockpit
"""

from __future__ import annotations

import base64
import html as _html
import json
import os
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

import daily_tracker_daemon
import diary_db
import diary_views
import edu_annotations as edu
import intel_bus_bridge as ibb
import llm_router
import marketdata_client
import quant_kernel as qk
import rubberband_arbiter as rba
import rubberband_charts as rbc
import rubberband_engine as rbe
import rubberband_engine_v3 as rbe3
import styles
import ui_kit
import ui_navigation

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_APP_DIR, ".env"))


# =========================================================================
# PROCESS-LEVEL BACKGROUND DAEMONS (RUNS ONCE PER SERVER PROCESS)
# =========================================================================
@st.cache_resource(show_spinner=False)
def _start_process_background_services_once() -> bool:
    try:
        daily_tracker_daemon.auto_snapshot_background_worker()
    except Exception:
        pass

    def _digest_task() -> None:
        try:
            rbe3.digest_world_catalysts_with_llm()
        except Exception:
            pass

    threading.Thread(target=_digest_task, daemon=True, name="CatalystsDigestDaemon").start()
    return True


_start_process_background_services_once()

# =========================================================================
# STREAMLIT MEMOIZATION LAYER
# =========================================================================
@st.cache_data(ttl=120, show_spinner=False)
def cached_get_sector_macro_pulse(_v: int = 50):
    return rbe3.get_sector_macro_pulse()


@st.cache_data(ttl=180, show_spinner=False)
def cached_get_cross_asset_compass(_v: int = 4):
    return rbe3.get_cross_asset_rotation_compass_data()


@st.cache_data(ttl=180, show_spinner=False)
def cached_get_ranked_sector_candidates(sector, bench, moneyness_mode, top_n_vet, active_ticker):
    return rbe3.get_ranked_sector_candidates(
        sector,
        benchmark_override=bench,
        moneyness_mode=moneyness_mode,
        top_n_vet=top_n_vet,
        active_ticker=active_ticker,
    )


@st.cache_data(ttl=240, show_spinner=False)
def cached_get_due_diligence_candidate(ticker, bench, moneyness_mode, vet_deep=True, _v: int = 50):
    return rbe3.get_due_diligence_candidate(
        ticker,
        benchmark_symbol=bench,
        moneyness_mode=moneyness_mode,
        vet_deep=vet_deep,
    )


@st.cache_data(ttl=600, show_spinner=False)
def cached_get_near_live_option(
    symbol: str,
    action: str,
    target_strike: float,
    target_dte: int = 35,
    target_delta: float = 0.50,
    delta_mode: str = "HIGH_DELTA",
):
    s_num = round(float(target_strike), 1) if target_strike else 0.0
    return rbe3.get_near_live_option_contract(
        symbol=symbol,
        action=action,
        target_strike=s_num,
        target_dte=int(target_dte),
        target_delta=float(target_delta),
        delta_mode=delta_mode,
    )


@st.cache_data(ttl=300, show_spinner=False)
def cached_get_unified_5day_catalyst_outlook(sector_name: str, active_ticker: str):
    return rbe3.get_unified_5day_catalyst_outlook(sector_name=sector_name, active_ticker=active_ticker)


@st.cache_data(ttl=600, show_spinner=False)
def cached_get_ai_5day_bias_shield_assessment(
    sector_name: str,
    active_ticker: str,
    bias_score: int,
    bin_risk: str,
    bin_cnt: int,
    backend: str,
    _outlook: Dict[str, Any],
    _active_cand: Optional[Dict[str, Any]] = None,
):
    return rbe3.get_ai_5day_bias_shield_assessment(
        catalyst_outlook=_outlook,
        sector_name=sector_name,
        active_ticker=active_ticker,
        active_cand=_active_cand,
    )


@st.cache_data(ttl=180, show_spinner=False)
def cached_get_24_48h_radar(_v: int = 50):
    return rbe3.get_24_48h_market_direction_radar()


@st.cache_data(ttl=240, show_spinner=False)
def cached_get_macro_econ_7pillar_spider(_v: int = 50):
    return rbe3.get_macro_economic_7pillar_spider_data()


@st.cache_data(ttl=600, show_spinner=False)
def cached_get_smart_money_radar():
    import smart_money_radar as smr
    return smr.get_smart_money_stealth_radar()


@st.cache_data(ttl=900, show_spinner=False)
def cached_get_equity_float(symbol: str):
    return rbe3.get_equity_short_and_float_metrics(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def cached_get_historical_series(symbol: str):
    return rbe3.get_historical_series(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def cached_scan_intel_bus(moneyness_mode: str):
    return rbe3.scan_all_intel_bus_candidates(moneyness_mode=moneyness_mode)


# =========================================================================
# PAGE CONFIG & OBSIDIAN FROSTED-GLASS DESIGN SYSTEM
# =========================================================================
_icon_path = os.path.join(_APP_DIR, "spline_pointer.png")
try:
    _page_icon_img = Image.open(_icon_path) if os.path.exists(_icon_path) else None
except Exception:
    _page_icon_img = None

st.set_page_config(
    page_title="Rubberband Man v4.0 | 30-45 DTE High-Delta Options Terminal",
    page_icon=_page_icon_img,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(styles.get_custom_css(), unsafe_allow_html=True)


# =========================================================================
# CORE HELPERS & WATCHLIST PERSISTENCE
# =========================================================================
WATCHLIST_FILE = os.path.join(_APP_DIR, "watchlist.json")
QUICK_THEMATIC_ETFS = ["REMX", "SRVR", "ROBO", "JEDI", "SMH", "URA", "QTUM", "IGV"]


def _safe_http_url(url: Any) -> str:
    s = str(url or "").strip()
    if s.startswith("https://") or s.startswith("http://"):
        return _html.escape(s, quote=True)
    return ""


@st.cache_data(show_spinner=False)
def get_rubberband_logo_b64() -> str:
    for fname in ("rubberband_logo_256.png", "rubberband_logo.png", "rubberband_logo_512.png"):
        fpath = os.path.join(_APP_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
    return ""


def get_spline_pointer_svg(size: int = 48, color: str = "#FF6B00") -> str:
    b64 = get_rubberband_logo_b64()
    if b64:
        return (
            f'<img src="data:image/png;base64,{b64}" alt="Rubberband Man" '
            f'style="width:{size}px;height:{size}px;min-width:{size}px;border-radius:12px;'
            f'vertical-align:middle;object-fit:cover;border:1px solid rgba(255,107,0,0.50);'
            f'box-shadow:0 6px 18px rgba(0,0,0,0.6),0 0 18px rgba(255,107,0,0.32);"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M12.034 12.681a.498.498 0 0 1 .647-.647l9 3.5a.5.5 0 0 1-.033.943l-3.444 1.068a1 1 0 0 0-.66.66l-1.067 3.443a.5.5 0 0 1-.943.033z"/>'
        f'<path d="M5 17A12 12 0 0 1 17 5"/><circle cx="19" cy="5" r="2"/></svg>'
    )


def clean_html(raw: str) -> str:
    return "".join(line.strip() for line in raw.strip().splitlines())


def _conviction_200_badge(score_200: int, opt_type: str = "") -> str:
    if hasattr(ui_kit, "format_conviction_200_badge"):
        return ui_kit.format_conviction_200_badge(score_200, opt_type)
    val = max(-200, min(200, int(round(float(score_200 or 0)))))
    d_lbl = opt_type.upper() if opt_type else ("CALL" if val > 35 else ("PUT" if val < -35 else "NEUTRAL"))
    col = "#FF8533" if abs(val) >= 150 else ("#10B981" if "CALL" in d_lbl else ("#F43F5E" if "PUT" in d_lbl else "#94A3B8"))
    return f'<span class="rm-conviction-pill" style="color:{col};border-color:{col}55;">{val:+d} {d_lbl}</span>'


def _ring_5day_svg(pct: int, label: str, sub: str, is_active: bool = False, tone_hex: str = "#FF6B00") -> str:
    if hasattr(ui_kit, "render_5day_ring_svg"):
        return ui_kit.render_5day_ring_svg(pct, label, sub, is_active=is_active, tone_hex=tone_hex)
    clamped = max(0, min(100, int(pct)))
    circ = 2.0 * 3.14159 * 31.0
    offset = circ * (1.0 - clamped / 100.0)
    return clean_html(f"""
    <div class="rm-day-card{' is-active' if is_active else ''}">
      <svg viewBox="0 0 80 80" width="60" height="60">
        <circle cx="40" cy="40" r="31" fill="rgba(10,12,18,0.65)" stroke="rgba(255,255,255,0.08)" stroke-width="5.5"/>
        <circle cx="40" cy="40" r="31" fill="none" stroke="{tone_hex}" stroke-width="5.5" stroke-linecap="round"
                stroke-dasharray="{circ:.2f}" stroke-dashoffset="{offset:.2f}" transform="rotate(-90 40 40)"/>
        <text x="40" y="44" text-anchor="middle" fill="#E2E8F0" font-family="JetBrains Mono,monospace" font-size="14" font-weight="700">{clamped}%</text>
      </svg>
      <div class="rm-day-label">{_html.escape(label)}</div>
      <div class="rm-day-sub">{_html.escape(sub)}</div>
    </div>
    """)


def _mask_secret_status(env_var: str) -> str:
    val = str(os.getenv(env_var, "") or "").strip()
    if not val:
        return "NOT CONFIGURED"
    if len(val) <= 6:
        return "CONFIGURED (***)"
    return f"CONFIGURED (***{val[-4:]})"


def save_env_keys(
    fmp_key: Optional[str] = None,
    gemini_key: Optional[str] = None,
    marketdata_key: Optional[str] = None,
    llm_backend: Optional[str] = None,
    local_url: Optional[str] = None,
    local_model: Optional[str] = None,
    local_key: Optional[str] = None,
) -> None:
    env_path = os.path.join(_APP_DIR, ".env")
    raw_lines: List[str] = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            raw_lines = f.read().splitlines()

    def _clean_v(s: Optional[str]) -> str:
        return str(s or "").replace("\r", "").replace("\n", "").strip()

    updates: Dict[str, str] = {}
    if _clean_v(fmp_key):
        updates["FMP_API_KEY"] = _clean_v(fmp_key)
    if _clean_v(gemini_key):
        updates["GEMINI_API_KEY"] = _clean_v(gemini_key)
    if _clean_v(marketdata_key):
        updates["MARKETDATA_API_KEY"] = _clean_v(marketdata_key)
    if _clean_v(local_key):
        updates["LOCAL_LLM_API_KEY"] = _clean_v(local_key)
    if llm_backend is not None and _clean_v(llm_backend):
        updates["LLM_BACKEND"] = _clean_v(llm_backend)
    if local_url is not None and _clean_v(local_url):
        updates["LOCAL_LLM_URL"] = _clean_v(local_url)
    if local_model is not None and _clean_v(local_model):
        updates["LOCAL_LLM_MODEL"] = _clean_v(local_model)

    if not updates:
        return

    for k, v in updates.items():
        os.environ[k] = v

    seen: set = set()
    out_lines: List[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                out_lines.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out_lines.append(line)

    for k, v in updates.items():
        if k not in seen:
            out_lines.append(f"{k}={v}")

    tmp_env = f"{env_path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}"
    with open(tmp_env, "w", encoding="utf-8") as f:
        f.write("\n".join(out_lines) + "\n")
    os.replace(tmp_env, env_path)


def load_personal_watchlist() -> List[str]:
    default_list = ["REMX", "SRVR", "ROBO", "JEDI", "NVDA", "OKLO", "VRT", "ANET"]
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    clean = [str(t).strip().upper() for t in data if str(t).strip()]
                    return list(dict.fromkeys(clean))
        except Exception as exc:
            print(f"Error loading watchlist from {WATCHLIST_FILE}: {exc}")
    save_personal_watchlist(default_list)
    return default_list


def save_personal_watchlist(watchlist: List[str]) -> None:
    try:
        clean_list = list(dict.fromkeys([str(t).strip().upper() for t in watchlist if str(t).strip()]))
        temp_file = f"{WATCHLIST_FILE}.tmp.{os.getpid()}.{uuid.uuid4().hex[:6]}"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(clean_list, f, indent=2)
        os.replace(temp_file, WATCHLIST_FILE)
    except Exception as exc:
        print(f"Error saving watchlist to {WATCHLIST_FILE}: {exc}")


SECTOR_PALETTES = {
    "Semiconductors": {
        "name": "Semiconductors",
        "benchmark": "SMH",
        "color": "#FF6B00",
        "accent": "#FF8533",
        "border": "rgba(255, 107, 0, 0.35)",
        "icon": "fa-microchip",
    },
    "AI Infrastructure": {
        "name": "AI Infrastructure",
        "benchmark": "SRVR",
        "color": "#FB923C",
        "accent": "#FDBA74",
        "border": "rgba(251, 146, 60, 0.35)",
        "icon": "fa-server",
    },
    "Energy, Grid & Materials": {
        "name": "Energy, Grid & Materials",
        "benchmark": "URA",
        "color": "#10B981",
        "accent": "#34D399",
        "border": "rgba(16, 185, 129, 0.35)",
        "icon": "fa-atom",
    },
    "Robotics & Autonomous": {
        "name": "Robotics & Autonomous",
        "benchmark": "ROBO",
        "color": "#F59E0B",
        "accent": "#FBBF24",
        "border": "rgba(245, 158, 11, 0.35)",
        "icon": "fa-robot",
    },
    "Edge AI & Next-Gen Compute": {
        "name": "Edge AI & Next-Gen Compute",
        "benchmark": "QTUM",
        "color": "#A78BFA",
        "accent": "#C4B5FD",
        "border": "rgba(167, 139, 250, 0.35)",
        "icon": "fa-bolt",
    },
}


def get_sector_palette(sector_name: str) -> Dict[str, str]:
    norm = rbe3.normalize_sector_name(sector_name)
    if norm in SECTOR_PALETTES:
        return SECTOR_PALETTES[norm]
    return SECTOR_PALETTES["Semiconductors"]


def _resolve_sector_for_symbol(sym: str) -> Optional[str]:
    u = (sym or "").strip().upper()
    if not u:
        return None
    for s_name, s_meta in rbe3.SECTORS.items():
        if u in s_meta.get("tickers", []) or u == s_meta.get("benchmark") or u in s_meta.get("etfs", []):
            return s_name
    detected = rbe3.get_ticker_sector(u)
    norm = rbe3.normalize_sector_name(detected)
    return norm if norm in rbe3.SECTORS else None


def _select_ticker_and_sector(sym: str) -> None:
    target = (sym or "").strip().upper()
    if not target:
        return
    st.session_state.selected_ticker = target
    sec = _resolve_sector_for_symbol(target)
    if sec:
        st.session_state.selected_sector = sec
        st.session_state.benchmark_override = rbe3.SECTORS[sec]["benchmark"]


# =========================================================================
# DETERMINISTIC SESSION STATE INITIALIZATION (NO RANDOMIZATION)
# =========================================================================
ui_navigation.sync_workspace_from_query_params()

_qp_ticker = str(st.query_params.get("ticker", "") or "").strip().upper()
_qp_sector = str(st.query_params.get("sector", "") or "").strip()
_qp_learn = str(st.query_params.get("learn", "") or "").strip().lower()

if "session_bootstrap_done" not in st.session_state:
    st.session_state["session_bootstrap_done"] = True
    _init_sec = rbe3.normalize_sector_name(_qp_sector) if _qp_sector else "Semiconductors"
    if _init_sec not in rbe3.SECTORS:
        _init_sec = "Semiconductors"
    st.session_state.selected_sector = _init_sec
    st.session_state.benchmark_override = rbe3.SECTORS[_init_sec]["benchmark"]
    st.session_state.selected_ticker = _qp_ticker or "NVDA"
    if _qp_ticker:
        _select_ticker_and_sector(_qp_ticker)
    st.session_state["_seen_qp_ticker"] = st.session_state.selected_ticker
    st.session_state["_seen_qp_sector"] = st.session_state.selected_sector
elif _qp_ticker and _qp_ticker != st.session_state.get("_seen_qp_ticker"):
    _select_ticker_and_sector(_qp_ticker)
    st.session_state["_seen_qp_ticker"] = _qp_ticker
elif _qp_sector and _qp_sector != st.session_state.get("_seen_qp_sector"):
    _norm_sec = rbe3.normalize_sector_name(_qp_sector)
    if _norm_sec in rbe3.SECTORS:
        st.session_state.selected_sector = _norm_sec
        st.session_state.benchmark_override = rbe3.SECTORS[_norm_sec]["benchmark"]
    st.session_state["_seen_qp_sector"] = _qp_sector

st.session_state.selected_sector = rbe3.normalize_sector_name(st.session_state.get("selected_sector", "Semiconductors"))
if st.session_state.selected_sector not in rbe3.SECTORS:
    st.session_state.selected_sector = "Semiconductors"

if not st.session_state.get("selected_ticker"):
    st.session_state.selected_ticker = "NVDA"

if not st.session_state.get("benchmark_override"):
    st.session_state.benchmark_override = rbe3.SECTORS[st.session_state.selected_sector]["benchmark"]
st.session_state.benchmark_override = rbe3.normalize_benchmark(st.session_state.benchmark_override)

if "learn_mode" not in st.session_state:
    st.session_state["learn_mode"] = _qp_learn not in ("0", "false", "off", "no")
if "dte_posture" not in st.session_state:
    st.session_state.dte_posture = "Auto 30/45D"
if "delta_profile" not in st.session_state:
    st.session_state.delta_profile = "High-Delta 0.40-0.65D"
if "moneyness_mode" not in st.session_state:
    st.session_state.moneyness_mode = "moderate_otm"
if "personal_watchlist" not in st.session_state:
    st.session_state.personal_watchlist = load_personal_watchlist()
if "upstream_tickers_input" not in st.session_state:
    st.session_state.upstream_tickers_input = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent_session" not in st.session_state:
    import gemini_agent
    st.session_state.agent_session = gemini_agent.FinancialAgentSession()
if "active_app_view" not in st.session_state:
    st.session_state.active_app_view = ui_navigation.VIEW_TERMINAL
if "llm_backend" not in st.session_state:
    st.session_state["llm_backend"] = llm_router.get_active_backend()

local_cfg = llm_router.get_local_config()
if "input_local_url" not in st.session_state:
    st.session_state["input_local_url"] = local_cfg["url"]
if "input_local_model" not in st.session_state:
    st.session_state["input_local_model"] = local_cfg["model"]

# Ensure density mode reads ?view=mobile query param early
_density_mode = ui_navigation.get_current_density_mode()

# Derive Delta mode from Delta Profile
_is_convex_otm = st.session_state.get("delta_profile") == "Convex OTM 0.28-0.42D"
st.session_state.moneyness_mode = "deep_convexity_otm" if _is_convex_otm else "moderate_otm"
_delta_mode = "CONVEX_OTM" if _is_convex_otm else "HIGH_DELTA"
_target_delta = 0.34 if _is_convex_otm else 0.50

# Pre-compute Core Cockpit Feeds ONLY when rendering Terminal Cockpit (skip heavy scans on Schwab / Journal)
_early_app_view = st.session_state.get("pending_workspace_view") or st.session_state.get("active_app_view", ui_navigation.VIEW_TERMINAL)
if _early_app_view == ui_navigation.VIEW_TERMINAL:
    macro_pulse = cached_get_sector_macro_pulse()
    catalyst_outlook = cached_get_unified_5day_catalyst_outlook(
        st.session_state.selected_sector,
        st.session_state.selected_ticker,
    )
    symbolism = catalyst_outlook.get("symbolism", {})
    ranked_sector_candidates = cached_get_ranked_sector_candidates(
        st.session_state.selected_sector,
        st.session_state.benchmark_override,
        st.session_state.moneyness_mode,
        5,
        st.session_state.selected_ticker,
    )
    ranked_by_conv = sorted(
        ranked_sector_candidates or [],
        key=lambda c: (
            -1 if c.get("metrics", {}).get("is_bad_data", False) else 1,
            int(c.get("conviction_abs_200", abs(int(c.get("conviction_score_200", 0))))),
            float(c.get("blueprint", {}).get("composite_score", 0.0)),
        ),
        reverse=True,
    )
else:
    macro_pulse = {}
    catalyst_outlook = {}
    symbolism = {}
    ranked_sector_candidates = []
    ranked_by_conv = []

# Keep URL query params synchronized cleanly with active ticker/sector/learn state
if str(st.query_params.get("ticker", "") or "").upper() != st.session_state.selected_ticker:
    st.query_params["ticker"] = st.session_state.selected_ticker
    st.session_state["_seen_qp_ticker"] = st.session_state.selected_ticker
if str(st.query_params.get("sector", "") or "") != st.session_state.selected_sector:
    st.query_params["sector"] = st.session_state.selected_sector
    st.session_state["_seen_qp_sector"] = st.session_state.selected_sector
if not bool(st.session_state.get("learn_mode", True)):
    if st.query_params.get("learn") != "0":
        st.query_params["learn"] = "0"
elif "learn" in st.query_params:
    del st.query_params["learn"]


# =========================================================================
# SIDEBAR OVERHAUL: BRAND, NAV, 5 DESKS, ETF CHIPS, DTE/DELTA, TOP HITS, WATCHLIST
# =========================================================================
with st.sidebar:
    reg_badge_sb = symbolism.get("regime_label") or macro_pulse.get("market_regime_badge") or (
        "MACRO EQUILIBRIUM" if _early_app_view == ui_navigation.VIEW_TERMINAL else "WORKSPACE STANDBY"
    )
    exp_cap_sb = int(symbolism.get("exposure_cap_pct", 100) or 100)
    spy_chg_sb = float(macro_pulse.get("spy_change", 0.0) or 0.0)
    cap_col_sb = "#10B981" if exp_cap_sb >= 80 else ("#F43F5E" if exp_cap_sb <= 55 else "#FF8533")
    sb_reg_sub = (
        f"VIX {float(symbolism.get('vix_ratio', 0.94)):.2f}x &bull; 10Y {float(symbolism.get('tnx_yield', 4.25)):.2f}% &bull; Credit {float(symbolism.get('credit_z', 0.0)):+.2f}&sigma;"
        if _early_app_view == ui_navigation.VIEW_TERMINAL
        else "Terminal sector scans paused while in desk view"
    )

    st.markdown(
        clean_html(f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;padding:4px 0;">
          <span>{get_spline_pointer_svg(48, '#FF6B00')}</span>
          <div>
            <div style="font-size:1.15rem;font-weight:900;color:#F8FAFC;letter-spacing:-0.02em;line-height:1.1;">Rubberband Man</div>
            <div style="margin-top:3px;display:flex;align-items:center;gap:6px;">
              <span style="background:rgba(255,107,0,0.16);color:#FF8533;font-size:0.62rem;font-weight:800;padding:1px 7px;border-radius:9999px;border:1px solid rgba(255,107,0,0.38);">v4.0 TERMINAL</span>
              <span style="font-family:'JetBrains Mono',monospace;font-size:0.64rem;color:{cap_col_sb};font-weight:800;">CAP {exp_cap_sb}%</span>
            </div>
          </div>
        </div>
        <div style="background:rgba(13,16,23,0.72);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:7px 10px;margin-bottom:10px;font-size:0.72rem;">
          <div style="font-weight:800;color:#E2E8F0;display:flex;justify-content:space-between;align-items:center;">
            <span>{_html.escape(str(reg_badge_sb))}</span>
            <span style="font-family:'JetBrains Mono',monospace;color:{'#10B981' if spy_chg_sb >= 0 else '#F43F5E'};">SPY {spy_chg_sb:+.2f}%</span>
          </div>
          <div style="color:#94A3B8;font-size:0.66rem;margin-top:2px;font-family:'JetBrains Mono',monospace;">
            {sb_reg_sub}
          </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    # Workspace Navigation Links (synced with ui_navigation)
    view_options = [
        ui_navigation.VIEW_TERMINAL,
        ui_navigation.VIEW_SCHWAB,
        ui_navigation.VIEW_JOURNAL,
    ]
    view_labels = {
        ui_navigation.VIEW_TERMINAL: "⚡ Terminal Cockpit",
        ui_navigation.VIEW_SCHWAB: "📓 Schwab Simulator",
        ui_navigation.VIEW_JOURNAL: "📊 Ticker Journal",
    }
    pending_view = st.session_state.pop("pending_workspace_view", None)
    if pending_view and pending_view in view_options:
        st.session_state["radio_app_workspace_view"] = pending_view
        st.session_state["active_app_view"] = pending_view
    elif st.session_state.get("active_app_view") in view_options and st.session_state.get("active_app_view") != st.session_state.get("radio_app_workspace_view"):
        st.session_state["radio_app_workspace_view"] = st.session_state["active_app_view"]
    elif st.session_state.get("radio_app_workspace_view") not in view_options:
        st.session_state["radio_app_workspace_view"] = st.session_state.get("active_app_view", view_options[0])

    def _on_ws_change() -> None:
        picked_ws = st.session_state.radio_app_workspace_view
        st.session_state.active_app_view = picked_ws
        slug = ui_navigation.VIEW_SLUGS.get(picked_ws, "terminal")
        if slug == "terminal":
            if "page" in st.query_params:
                del st.query_params["page"]
        else:
            st.query_params["page"] = slug

    selected_nav_view = st.radio(
        "Workspace",
        options=view_options,
        format_func=lambda v: view_labels.get(v, v),
        key="radio_app_workspace_view",
        on_change=_on_ws_change,
        label_visibility="collapsed",
    )
    st.session_state.active_app_view = selected_nav_view
    ui_navigation.render_sidebar_density_control()

    # Global Educational Learn Mode Toggle (Beginner -> Intermediate -> Desk Pro)
    st.session_state["sb_learn_mode"] = bool(st.session_state.get("learn_mode", True))

    def _on_learn_mode_toggle() -> None:
        val = bool(st.session_state.get("sb_learn_mode", True))
        st.session_state["learn_mode"] = val
        if not val:
            st.query_params["learn"] = "0"
        elif "learn" in st.query_params:
            del st.query_params["learn"]

    st.toggle(
        "🎓 Learn Mode (Show Guides)",
        key="sb_learn_mode",
        on_change=_on_learn_mode_toggle,
        help="Show collapsible Beginner → Intermediate → Desk Pro guides for Options, Macro & Microstructure.",
    )

    # Sector Selector across all 5 expanded desks
    st.markdown("<div class='rm-sb-section-label'>5-Desk Institutional Universe</div>", unsafe_allow_html=True)
    sector_list = list(rbe3.SECTORS.keys())
    if st.session_state.get("sb_sector_select") not in sector_list or st.session_state.get("sb_sector_select") != st.session_state.selected_sector:
        st.session_state["sb_sector_select"] = st.session_state.selected_sector

    def _on_sb_sector_change() -> None:
        picked = st.session_state.get("sb_sector_select", "Semiconductors")
        if picked in rbe3.SECTORS and picked != st.session_state.selected_sector:
            st.session_state.selected_sector = picked
            st.session_state.benchmark_override = rbe3.SECTORS[picked]["benchmark"]
            sec_tickers_new = rbe3.SECTORS[picked].get("tickers", [])
            if st.session_state.selected_ticker not in sec_tickers_new and sec_tickers_new:
                st.session_state.selected_ticker = sec_tickers_new[0]

    st.selectbox(
        "Sector Desk",
        options=sector_list,
        key="sb_sector_select",
        on_change=_on_sb_sector_change,
        label_visibility="collapsed",
    )

    # 1-Click Thematic ETF Quick-Filter Pill Rail (Compact Zero-Clutter Switcher)
    st.markdown("<div class='rm-sb-section-label'>Thematic ETF Quick-Filter</div>", unsafe_allow_html=True)

    def _on_sb_etf_pick() -> None:
        picked = st.session_state.get("sb_etf_pills")
        cur_t = st.session_state.get("selected_ticker")
        if picked and picked != cur_t:
            _select_ticker_and_sector(picked)
            st.session_state["_sb_etf_synced_tk"] = picked
        elif picked is None and cur_t in QUICK_THEMATIC_ETFS:
            st.session_state["sb_etf_pills"] = cur_t

    _sb_cur_tk = st.session_state.get("selected_ticker")
    if st.session_state.get("_sb_etf_synced_tk") != _sb_cur_tk:
        st.session_state["sb_etf_pills"] = _sb_cur_tk if _sb_cur_tk in QUICK_THEMATIC_ETFS else None
        st.session_state["_sb_etf_synced_tk"] = _sb_cur_tk

    st.pills(
        "Thematic ETFs",
        options=QUICK_THEMATIC_ETFS,
        selection_mode="single",
        key="sb_etf_pills",
        on_change=_on_sb_etf_pick,
        label_visibility="collapsed",
    )

    # DTE Posture & Delta Profile
    st.markdown("<div class='rm-sb-section-label'>DTE Posture & Delta Profile</div>", unsafe_allow_html=True)
    dte_opts = ["Auto 30/45D", "30 DTE", "45 DTE"]
    st.session_state.setdefault("sb_seg_dte_posture", st.session_state.get("dte_posture", "Auto 30/45D"))
    dte_choice = st.segmented_control(
        "DTE Posture",
        options=dte_opts,
        key="sb_seg_dte_posture",
        label_visibility="collapsed",
    )
    if dte_choice and dte_choice != st.session_state.dte_posture:
        st.session_state.dte_posture = dte_choice
        st.rerun()

    delta_opts = ["High-Delta 0.40-0.65D", "Convex OTM 0.28-0.42D"]
    st.session_state.setdefault("sb_radio_delta_profile", st.session_state.get("delta_profile", delta_opts[0]))
    delta_choice = st.radio(
        "Delta Profile",
        options=delta_opts,
        key="sb_radio_delta_profile",
        label_visibility="collapsed",
    )
    if delta_choice != st.session_state.delta_profile:
        st.session_state.delta_profile = delta_choice
        st.session_state.moneyness_mode = "deep_convexity_otm" if "Convex" in delta_choice else "moderate_otm"
        st.rerun()

    # Ranked Sector Top Hits (Signed -200..+200 Conviction)
    st.markdown(f"<div class='rm-sb-section-label'>Top Hits · {_html.escape(st.session_state.selected_sector)}</div>", unsafe_allow_html=True)
    if ranked_by_conv:
        for idx_hit, c_hit in enumerate(ranked_by_conv[:8], start=1):
            h_sym = c_hit["symbol"]
            h_m = c_hit.get("metrics", {})
            h_bp = c_hit.get("blueprint", {})
            h_qe = c_hit.get("quant_edge") or h_m.get("quant_edge") or {}
            h_score = int(c_hit.get("conviction_score_200", h_bp.get("conviction_score_200", 0)))
            h_dir = "CALL" if h_score > 35 else ("PUT" if h_score < -35 else "WAIT")
            h_px = float(h_m.get("price", 0.0) or 0.0)
            h_dte = int(c_hit.get("recommended_dte", h_bp.get("recommended_dte", 35)) or 35)
            h_ev = float(h_qe.get("net_ev_pct", 0.0) or 0.0)
            h_er = int(h_m.get("days_to_earnings", 45) or 45)
            is_h_act = h_sym == st.session_state.selected_ticker
            er_warn = " ⚠️ER" if (0 <= h_er <= 14 and not c_hit.get("is_etf")) else ""
            hit_lbl = f"#{idx_hit} {h_sym}{er_warn} · {h_score:+d} {h_dir} · ${h_px:.1f}"
            hit_help = (
                f"**{h_sym}** ({c_hit.get('conviction_tier', 'SIGNAL')})\n\n"
                f"• Conviction: **{h_score:+d} / ±200** ({h_dir})\n"
                f"• Prescribed DTE: **{h_dte}D** · 5D Net EV: **{h_ev:+.1f}%**\n"
                f"• Earnings Runway: **{h_er}d**"
            )
            if st.button(
                hit_lbl,
                key=f"sb_top_hit_{h_sym}",
                type="primary" if is_h_act else "secondary",
                width="stretch",
                help=hit_help,
            ):
                st.session_state.selected_ticker = h_sym
                st.rerun()

    # Personal Watchlist (watchlist.json preserved)
    st.markdown("<div class='rm-sb-section-label'>Personal Watchlist</div>", unsafe_allow_html=True)
    wl_c1, wl_c2 = st.columns([2.5, 1.0], gap="small")
    with wl_c1:
        new_w_sym = st.text_input(
            "Add Ticker",
            placeholder="Add ticker (e.g. MP, VRT)",
            key="input_add_watchlist",
            label_visibility="collapsed",
        ).strip().upper()
    with wl_c2:
        if st.button("Add", key="btn_add_watchlist", width="stretch") and new_w_sym:
            if new_w_sym not in st.session_state.personal_watchlist:
                st.session_state.personal_watchlist.append(new_w_sym)
                save_personal_watchlist(st.session_state.personal_watchlist)
                st.rerun()

    if st.session_state.personal_watchlist:
        wl_quotes = rbe3.fmp_batch_quotes(list(st.session_state.personal_watchlist))
        for w_sym in list(st.session_state.personal_watchlist):
            q_item = wl_quotes.get(w_sym, {})
            w_px = float(q_item.get("price", 0.0) or 0.0)
            w_chg = float(q_item.get("changePercentage", q_item.get("changesPercentage", 0.0)) or 0.0)
            is_w_act = w_sym == st.session_state.selected_ticker
            wc1, wc2 = st.columns([3.8, 0.9], gap="small")
            with wc1:
                if st.button(
                    f"{w_sym} · ${w_px:.1f} ({w_chg:+.1f}%)",
                    key=f"sb_wl_btn_{w_sym}",
                    type="primary" if is_w_act else "secondary",
                    width="stretch",
                ):
                    _select_ticker_and_sector(w_sym)
                    st.rerun()
            with wc2:
                if st.button("×", key=f"sb_wl_del_{w_sym}", width="stretch", help=f"Remove {w_sym}"):
                    st.session_state.personal_watchlist.remove(w_sym)
                    save_personal_watchlist(st.session_state.personal_watchlist)
                    st.rerun()

    # Compact System, AI & Bus Config Modal (masked secret status — never pre-populates raw keys in HTML)
    @st.dialog("⚙️ System, AI & GX10 Bus Config", width="large")
    def _render_settings_dialog() -> None:
        tab_ai, tab_bus = st.tabs(["🧠 AI Compute & Keys", "📡 GX10 Discovery Bus"])
        with tab_ai:
            st.caption(
                f"Stored credentials — Gemini: `{_mask_secret_status('GEMINI_API_KEY')}` · "
                f"FMP: `{_mask_secret_status('FMP_API_KEY')}` · "
                f"MarketData: `{_mask_secret_status('MARKETDATA_API_KEY')}` · "
                f"Local LLM Key: `{_mask_secret_status('LOCAL_LLM_API_KEY')}`"
            )
            st.session_state.setdefault(
                "dlg_radio_llm_backend",
                "Cloud: Google Gemini" if st.session_state.get("llm_backend", "gemini") == "gemini" else "Local: ASUS GX10 (Qwen 3.8)",
            )
            b_choice = st.radio(
                "Compute Engine",
                options=["Cloud: Google Gemini", "Local: ASUS GX10 (Qwen 3.8)"],
                key="dlg_radio_llm_backend",
            )
            sel_b = "gemini" if "Gemini" in b_choice else "local"
            l_url = st.session_state.get("input_local_url", local_cfg["url"])
            l_mod = st.session_state.get("input_local_model", local_cfg["model"])
            g_in, l_key = "", ""
            if sel_b == "local":
                l_url = st.text_input(
                    "Endpoint URL",
                    value=l_url,
                    key="dlg_local_url_in",
                ).strip()
                l_mod = st.text_input(
                    "Model Identifier",
                    value=l_mod,
                    key="dlg_local_model_in",
                ).strip()
                l_key = st.text_input(
                    "Update Local API Key (optional)",
                    value="",
                    placeholder="Leave blank to keep stored key",
                    type="password",
                    key="dlg_local_key_in",
                ).strip()
            else:
                g_in = st.text_input(
                    "Update Gemini API Key (optional)",
                    value="",
                    placeholder="Leave blank to keep stored key",
                    type="password",
                    key="dlg_gemini_key_in",
                ).strip()
            fmp_in = st.text_input(
                "Update FMP Pro API Key (optional)",
                value="",
                placeholder="Leave blank to keep stored key",
                type="password",
                key="dlg_fmp_key_in",
            ).strip()
            md_in = st.text_input(
                "Update MarketData.app API Key (optional)",
                value="",
                placeholder="Leave blank to keep stored key",
                type="password",
                key="dlg_marketdata_key_in",
            ).strip()
            if st.button("Save Configuration", type="primary", width="stretch", key="dlg_save_keys"):
                st.session_state["llm_backend"] = sel_b
                st.session_state["input_local_url"] = l_url
                st.session_state["input_local_model"] = l_mod
                os.environ["LLM_BACKEND"] = sel_b
                save_env_keys(
                    fmp_key=fmp_in or None,
                    gemini_key=g_in or None,
                    marketdata_key=md_in or None,
                    llm_backend=sel_b,
                    local_url=l_url,
                    local_model=l_mod,
                    local_key=l_key or None,
                )
                st.rerun()
        with tab_bus:
            try:
                bus_sigs = ibb.read_intel_bus_signals()
                bus_dir = ibb.resolve_intel_bus_dir()
            except Exception:
                bus_sigs, bus_dir = [], "Offline"
            st.caption(f"GX10 WAL Bridge: `{bus_dir}` ({len(bus_sigs)} signals)")
            feed_in = st.text_area("Custom Ticker Filter (CSV)", value=st.session_state.upstream_tickers_input, height=70, key="dlg_bus_csv")
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if st.button("Apply CSV", width="stretch", key="dlg_bus_apply"):
                    st.session_state.upstream_tickers_input = feed_in
                    st.rerun()
            with bc2:
                if st.button("Load GX10", width="stretch", key="dlg_bus_load"):
                    st.session_state.upstream_tickers_input = ", ".join([s["symbol"] for s in bus_sigs])
                    st.rerun()
            with bc3:
                if st.button("Clear", width="stretch", key="dlg_bus_clear"):
                    st.session_state.upstream_tickers_input = ""
                    st.rerun()

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    if st.button("⚙️ System, AI & Bus Config", key="btn_open_settings", width="stretch"):
        _render_settings_dialog()


# =========================================================================
# WORKSPACE ROUTING (SCHWAB SIMULATOR | TICKER JOURNAL | TERMINAL COCKPIT)
# =========================================================================
current_view = st.session_state.get("active_app_view", ui_navigation.VIEW_TERMINAL)
if current_view == ui_navigation.VIEW_SCHWAB:
    diary_views.render_schwab_practice_diary_page()
    st.stop()
elif current_view == ui_navigation.VIEW_JOURNAL:
    diary_views.render_daily_recommendation_ledger_page()
    st.stop()

# Ensure Terminal feeds are hydrated if sidebar switched back to Terminal mid-rerun
if not ranked_by_conv and not macro_pulse:
    macro_pulse = cached_get_sector_macro_pulse()
    catalyst_outlook = cached_get_unified_5day_catalyst_outlook(
        st.session_state.selected_sector,
        st.session_state.selected_ticker,
    )
    symbolism = catalyst_outlook.get("symbolism", {})
    ranked_sector_candidates = cached_get_ranked_sector_candidates(
        st.session_state.selected_sector,
        st.session_state.benchmark_override,
        st.session_state.moneyness_mode,
        5,
        st.session_state.selected_ticker,
    )
    ranked_by_conv = sorted(
        ranked_sector_candidates or [],
        key=lambda c: (
            -1 if c.get("metrics", {}).get("is_bad_data", False) else 1,
            int(c.get("conviction_abs_200", abs(int(c.get("conviction_score_200", 0))))),
            float(c.get("blueprint", {}).get("composite_score", 0.0)),
        ),
        reverse=True,
    )

active_ticker = st.session_state.selected_ticker
benchmark_symbol = st.session_state.benchmark_override
active_backend = st.session_state.get("llm_backend", "gemini")
active_model_name = (
    (st.session_state.get("input_local_model") or "Qwen 3.8 (GX10)")
    if active_backend == "local"
    else "Gemini Hydrogen"
)

# Unified Top Floating Glass Navigation Pill Dock
ui_navigation.render_top_navigation_strip(ui_navigation.VIEW_TERMINAL)

# Fetch Active Candidate & Macro Feeds
active_cand = cached_get_due_diligence_candidate(
    active_ticker,
    benchmark_symbol,
    st.session_state.moneyness_mode,
    vet_deep=True,
)
macro_regime = rbe3.get_macro_yield_regime()
radar_24_48 = cached_get_24_48h_radar()

# Mobile Companion Mode (?view=mobile or density toggle)
if _density_mode == "mobile":
    import mobile_scanner_view
    sm_radar = cached_get_smart_money_radar()
    mobile_scanner_view.render_mobile_scanner_page(
        active_cand=active_cand,
        active_ticker=active_ticker,
        benchmark_symbol=benchmark_symbol,
        ranked_sector_candidates=ranked_by_conv,
        macro_pulse=macro_pulse,
        radar_24_48=radar_24_48,
        sm_radar=sm_radar,
        cur_spal=get_sector_palette(st.session_state.selected_sector),
        cached_get_near_live_option=cached_get_near_live_option,
        catalyst_outlook=catalyst_outlook,
    )
    ui_navigation.render_mobile_bottom_dock(ui_navigation.VIEW_TERMINAL)
    st.stop()

if not active_cand:
    st.error(f"Unable to retrieve market series for `{active_ticker}`. Verify FMP/MarketData API keys or select another ticker.")
    st.stop()

# Resolve Effective 30 vs 45 DTE Posture
outlook_dte = int(catalyst_outlook.get("recommended_dte", 30) or 30)
cand_dte = int(active_cand.get("recommended_dte", outlook_dte) or outlook_dte)
if st.session_state.dte_posture == "30 DTE":
    effective_dte = 30
    dte_mode_tag = "LOCKED 30D"
elif st.session_state.dte_posture == "45 DTE":
    effective_dte = 45
    dte_mode_tag = "LOCKED 45D"
else:
    effective_dte = 45 if (cand_dte == 45 or outlook_dte == 45) else 30
    dte_mode_tag = f"AUTO {effective_dte}D"


# =========================================================================
# (A) MACRO REGIME & MARKET SYMBOLISM HUD STRIP (SINGLE CLEAN BAR)
# =========================================================================
reg_label = str(symbolism.get("regime_label") or macro_pulse.get("market_regime_badge", "MACRO EQUILIBRIUM"))
vix_ratio = float(symbolism.get("vix_ratio", radar_24_48.get("vix_term_ratio", 0.94)) or 0.94)
vix_state = str(symbolism.get("vix_state", "CONTANGO"))
credit_z = float(symbolism.get("credit_z", radar_24_48.get("credit_stress_z", 0.0)) or 0.0)
tnx_yield = float(symbolism.get("tnx_yield", macro_regime.get("y10_current", 4.25)) or 4.25)
tnx_5d_bps = float(macro_regime.get("rate_change_5d_bps", 0.0) or 0.0)
spy_ret = float(macro_pulse.get("spy_change", 0.0) or 0.0)
qqq_ret = float(macro_pulse.get("qqq_change", 0.0) or 0.0)
spy_rvol = float(symbolism.get("spy_rvol", macro_pulse.get("spy_rvol", 1.0)) or 1.0)
breadth_5d = float(symbolism.get("breadth_spread_5d", macro_pulse.get("breadth_spread", 0.0)) or 0.0)
exp_cap_pct = int(symbolism.get("exposure_cap_pct", 75) or 75)

vix_col = "#10B981" if vix_ratio < 0.95 else ("#F43F5E" if vix_ratio >= 1.0 else "#FB923C")
cred_col = "#10B981" if credit_z >= 0.25 else ("#F43F5E" if credit_z <= -0.45 else "#FB923C")
tnx_col = "#F43F5E" if tnx_5d_bps >= 8 else ("#10B981" if tnx_5d_bps <= -5 else "#E2E8F0")
cap_col = "#10B981" if exp_cap_pct >= 80 else ("#F43F5E" if exp_cap_pct <= 55 else "#FF8533")
spy_col = "#10B981" if spy_ret >= 0.1 else ("#F43F5E" if spy_ret <= -0.1 else "#E2E8F0")
qqq_col = "#10B981" if qqq_ret >= 0.1 else ("#F43F5E" if qqq_ret <= -0.1 else "#E2E8F0")
brd_col = "#10B981" if breadth_5d >= 0.2 else ("#F43F5E" if breadth_5d <= -0.2 else "#FB923C")

st.markdown(
    clean_html(f"""
    <div class="rm-symbolism-bar">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.74rem;font-weight:800;color:#FF8533;background:rgba(255,107,0,0.14);border:1px solid rgba(255,107,0,0.42);padding:4px 11px;border-radius:9999px;letter-spacing:0.04em;">
          {_html.escape(reg_label)}
        </span>
        <span class="hud-pill">VIX Term: <b style="color:{vix_col};font-family:'JetBrains Mono',monospace;">{vix_ratio:.3f}x</b> <span style="color:#94A3B8;">({_html.escape(vix_state)})</span></span>
        <span class="hud-pill">Credit Z (HYG/LQD): <b style="color:{cred_col};font-family:'JetBrains Mono',monospace;">{credit_z:+.2f}&sigma;</b></span>
        <span class="hud-pill">10Y (^TNX): <b style="color:{tnx_col};font-family:'JetBrains Mono',monospace;">{tnx_yield:.2f}%</b> <span style="color:#94A3B8;">({tnx_5d_bps:+.0f}bps)</span></span>
        <span class="hud-pill">Tape: <b style="color:{spy_col};">SPY {spy_ret:+.2f}%</b> / <b style="color:{qqq_col};">QQQ {qqq_ret:+.2f}%</b> &bull; RVOL <b style="color:#E2E8F0;">{spy_rvol:.2f}x</b> &bull; Breadth 5D <b style="color:{brd_col};">{breadth_5d:+.2f}%</b></span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span class="hud-pill" style="border-color:{cap_col}55;">Exposure Cap: <b style="color:{cap_col};font-family:'JetBrains Mono',monospace;">{exp_cap_pct}%</b></span>
        <span class="rm-dte-pill">{effective_dte} DTE &middot; {_html.escape(dte_mode_tag)}</span>
      </div>
    </div>
    """),
    unsafe_allow_html=True,
)
edu.render_edu_drawer(
    "macro_regime",
    live_ctx={
        "vix_ratio": vix_ratio,
        "credit_z": credit_z,
        "tnx_yield": tnx_yield,
        "exposure_cap_pct": exp_cap_pct,
        "regime_label": reg_label,
    },
)


# =========================================================================
# (B) UNIFIED 5-DAY CATALYST & MACRO OUTLOOK BENTO
# =========================================================================
bias_label = str(catalyst_outlook.get("directional_bias", "NEUTRAL_COIL")).replace("_", " ")
bias_score = int(catalyst_outlook.get("bias_score", 0) or 0)
bin_risk = str(catalyst_outlook.get("binary_risk_level", "MODERATE"))
bin_cnt = int(catalyst_outlook.get("binary_event_count_5d", 0) or 0)
dte_presc_lbl = str(catalyst_outlook.get("dte_prescription_label", f"{effective_dte} DTE Posture"))
dte_rat = str(catalyst_outlook.get("dte_rationale", active_cand.get("dte_rationale", "")))

bias_col = "#10B981" if bias_score >= 15 else ("#F43F5E" if bias_score <= -15 else "#FB923C")
risk_col = "#F43F5E" if bin_risk == "HIGH" else ("#FF8533" if bin_risk == "ELEVATED" else ("#FB923C" if bin_risk == "MODERATE" else "#10B981"))

ai_shield_assess = cached_get_ai_5day_bias_shield_assessment(
    sector_name=st.session_state.selected_sector,
    active_ticker=active_ticker,
    bias_score=bias_score,
    bin_risk=bin_risk,
    bin_cnt=bin_cnt,
    backend=active_backend,
    _outlook=catalyst_outlook,
    _active_cand=active_cand,
)
ai_m_score = max(-200, min(200, int(ai_shield_assess.get("score", 0) or 0)))
ai_m_stance = str(ai_shield_assess.get("stance", "NEUTRAL COIL"))
ai_m_summary = str(ai_shield_assess.get("summary", ""))
ai_m_source = str(ai_shield_assess.get("source", "ai"))
ai_engine_tag = f"{active_model_name}" if ai_m_source == "ai" else f"{active_model_name} (Quant Sync)"

if ai_m_score <= -120:
    liq_c1, liq_c2, liq_c3, liq_glow, liq_txt = "#E11D48", "#F43F5E", "#FB7185", "rgba(244, 63, 94, 0.80)", "#FB7185"
elif ai_m_score <= -25:
    liq_c1, liq_c2, liq_c3, liq_glow, liq_txt = "#EA580C", "#F43F5E", "#FB923C", "rgba(249, 115, 22, 0.72)", "#FB923C"
elif ai_m_score < 25:
    liq_c1, liq_c2, liq_c3, liq_glow, liq_txt = "#0284C7", "#38BDF8", "#7DD3FC", "rgba(56, 189, 248, 0.74)", "#38BDF8"
elif ai_m_score < 120:
    liq_c1, liq_c2, liq_c3, liq_glow, liq_txt = "#059669", "#10B981", "#34D399", "rgba(16, 185, 129, 0.74)", "#34D399"
else:
    liq_c1, liq_c2, liq_c3, liq_glow, liq_txt = "#059669", "#10B981", "#2DD4BF", "rgba(45, 212, 191, 0.84)", "#2DD4BF"

liq_fill_pct = max(2.5, abs(ai_m_score) / 200.0 * 50.0)
liq_left_pct = (50.0 - liq_fill_pct) if ai_m_score < 0 else (48.75 if abs(ai_m_score) < 10 else 50.0)
if abs(ai_m_score) < 10:
    liq_fill_pct = 2.5
meniscus_side = "left: 0px;" if ai_m_score < 0 else "right: 0px;"
meter_dir_word = "PUT" if ai_m_score <= -25 else ("CALL" if ai_m_score >= 25 else "NEUTRAL")

st.markdown(
    clean_html(f"""
    <div class="rm-glass-panel" style="padding:14px 18px !important;margin-bottom:12px !important;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <span style="font-size:0.86rem;font-weight:800;color:#F8FAFC;letter-spacing:-0.01em;">
            <i class="fa-solid fa-calendar-days" style="color:#FF6B00;margin-right:6px;"></i>5-Trading-Day Catalyst &amp; Macro Outlook
          </span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;font-weight:800;color:{bias_col};background:rgba(255,255,255,0.04);border:1px solid {bias_col}55;padding:3px 10px;border-radius:9999px;">
            BIAS: {_html.escape(bias_label)} ({bias_score:+d})
          </span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;font-weight:800;color:{risk_col};background:rgba(255,255,255,0.04);border:1px solid {risk_col}55;padding:3px 10px;border-radius:9999px;">
            BINARY SHIELD: {_html.escape(bin_risk)} ({bin_cnt} 5D Events)
          </span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="rm-dte-pill">{_html.escape(dte_presc_lbl)}</span>
        </div>
      </div>
      <div style="font-size:0.78rem;color:#CBD5E1;line-height:1.45;border-left:2px solid #FF6B00;padding-left:10px;">
        <b style="color:#FF8533;">Duration Prescription:</b> {_html.escape(dte_rat)}
      </div>
      <div class="rm-ai-meter-box" style="--rm-liq-c1:{liq_c1};--rm-liq-c2:{liq_c2};--rm-liq-c3:{liq_c3};--rm-liq-glow:{liq_glow};">
        <div class="rm-ai-meter-hdr">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <span style="font-size:0.76rem;font-weight:800;color:#F8FAFC;letter-spacing:0.03em;text-transform:uppercase;">
              <i class="fa-solid fa-brain" style="color:{liq_txt};margin-right:6px;text-shadow:0 0 10px {liq_glow};"></i>AI Bias &amp; Binary Shield Summation
            </span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;font-weight:700;color:#94A3B8;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.10);padding:2px 8px;border-radius:9999px;">
              {_html.escape(ai_engine_tag)}
            </span>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;font-weight:800;color:{liq_txt};background:rgba(255,255,255,0.04);border:1px solid {liq_txt}55;padding:2px 9px;border-radius:9999px;text-shadow:0 0 10px {liq_glow};">
              {_html.escape(ai_m_stance)}
            </span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.96rem;font-weight:800;color:{liq_txt};text-shadow:0 0 14px {liq_glow};">
              {ai_m_score:+d} {meter_dir_word}
            </span>
          </div>
        </div>
        <div class="rm-ai-meter-summary">{_html.escape(ai_m_summary)}</div>
        <div class="rm-liquid-scale-row">
          <span style="color:#FB7185;">-200 PUT</span>
          <span style="color:#94A3B8;">0 EQUILIBRIUM</span>
          <span style="color:#34D399;">+200 CALL</span>
        </div>
        <div class="rm-liquid-tube">
          <div class="rm-liquid-center-tick"></div>
          <div class="rm-liquid-fill" style="left:{liq_left_pct:.2f}%;width:{liq_fill_pct:.2f}%;">
            <div class="rm-liquid-wave"></div>
            <div class="rm-liquid-bubbles"></div>
            <div class="rm-liquid-meniscus" style="{meniscus_side}"></div>
          </div>
        </div>
      </div>
    </div>
    """),
    unsafe_allow_html=True,
)

# 5-Trading-Day Circular Progress Ring Strip
days_list = catalyst_outlook.get("days", [])[:5]
if days_list:
    tone_hex_map = {
        "rose": "#F43F5E",
        "amber": "#FF6B00",
        "orange": "#FF6B00",
        "cyan": "#FB923C",
        "emerald": "#10B981",
    }
    rings_html = '<div class="rm-5d-strip">'
    for d_item in days_list:
        d_pct = int(d_item.get("intensity_pct", 0) or 0)
        d_lbl = f"{d_item.get('day_short', '')} {d_item.get('day_num', '')}"
        d_cnt = int(d_item.get("event_count", 0) or 0)
        d_tag = str(d_item.get("headline_tag", "Clear Runway") or "Clear Runway")
        d_sub = f"{d_cnt} ev · {d_tag}" if d_cnt > 0 else d_tag
        d_tone = tone_hex_map.get(str(d_item.get("risk_tone", "")).lower(), "#FF6B00")
        rings_html += _ring_5day_svg(
            pct=d_pct,
            label=d_lbl,
            sub=d_sub,
            is_active=bool(d_item.get("is_today", False)),
            tone_hex=d_tone,
        )
    rings_html += "</div>"
    st.markdown(clean_html(rings_html), unsafe_allow_html=True)

edu.render_edu_drawer(
    "catalysts_5d",
    live_ctx={
        "binary_event_count_5d": bin_cnt,
        "recommended_dte": int(catalyst_outlook.get("recommended_dte", effective_dte) or effective_dte),
        "binary_risk_level": bin_risk,
        "ai_bias_score": ai_m_score,
    },
)

# 3-Column Frosted Synthesis Grid: SEC 8-K | Fed & Macro Calendar | Sector FMP News Wire (Collapsible)
filings_raw = catalyst_outlook.get("sec_8k_filings", []) or []
wl_set = set(st.session_state.get("personal_watchlist", []))
sec_set = set(rbe3.SECTORS.get(st.session_state.selected_sector, {}).get("tickers", []))
filings_filt = [
    f for f in filings_raw
    if f.get("is_active_match") or f.get("is_sector_match") or f.get("symbol") in wl_set or f.get("symbol") in sec_set
]
if not filings_filt:
    filings_filt = filings_raw[:6]
fed_evs = catalyst_outlook.get("fed_and_macro_events", []) or []
sec_news = catalyst_outlook.get("sector_news", []) or []

_next_fed_lbl = _html.escape(str(fed_evs[0].get("event", "No macro shock") if fed_evs else "No imminent FOMC shock"))[:54]
_top_news_lbl = _html.escape(str(sec_news[0].get("title", "No breaking wire") if sec_news else "No breaking sector headlines"))[:62]
st.markdown(
    clean_html(f"""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;padding:7px 14px;margin-bottom:6px;background:rgba(15,18,26,0.58);border:1px solid rgba(255,255,255,0.07);border-radius:10px;font-size:0.74rem;color:#CBD5E1;">
      <span><b style="color:#FF8533;">LIVE WIRE:</b> SEC 8-K (<b>{len(filings_filt)}</b>) &bull; Fed/Macro (<b>{len(fed_evs)}</b>: {_next_fed_lbl}) &bull; Sector Headlines (<b>{len(sec_news)}</b>: {_top_news_lbl})</span>
      <span style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;color:#94A3B8;">Expand below for full 3-column tape</span>
    </div>
    """),
    unsafe_allow_html=True,
)

with st.expander("📡 Live Institutional Wire: SEC 8-K Filings • Fed & Treasury Tape • Sector Headlines", expanded=False):
    col_8k, col_fed, col_news = st.columns(3, gap="medium")

    with col_8k:
        rows_8k_html = ""
        for f in filings_filt[:6]:
            fsym = _html.escape(str(f.get("symbol", "SEC")))
            fform = _html.escape(str(f.get("form_type", "8-K")))
            fdate = _html.escape(str(f.get("accepted_date") or f.get("filing_date", "")))
            flink_safe = _safe_http_url(f.get("link")) or "#"
            is_hit = f.get("is_active_match") or fsym == active_ticker
            badge_c = "#FF8533" if is_hit else "#CBD5E1"
            rows_8k_html += (
                f'<div style="padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.75rem;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
                f'<span style="font-family:JetBrains Mono,monospace;font-weight:800;color:{badge_c};">{fsym} &middot; {fform}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.68rem;color:#94A3B8;">{fdate}</span>'
                f'</div>'
                f'<div style="margin-top:2px;"><a href="{flink_safe}" target="_blank" rel="noopener noreferrer" style="color:#E2E8F0;text-decoration:none;font-size:0.73rem;">Open SEC EDGAR Filing &nearr;</a></div>'
                f'</div>'
            )
        if not rows_8k_html:
            rows_8k_html = '<div style="font-size:0.76rem;color:#94A3B8;padding:8px 0;">No recent SEC 8-K filings in tracked universe.</div>'

        st.markdown(
            clean_html(f"""
            <div class="rm-catalyst-col">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08);">
                <span style="font-size:0.76rem;font-weight:800;color:#FF8533;text-transform:uppercase;letter-spacing:0.05em;">
                  <i class="fa-solid fa-file-lines" style="margin-right:5px;"></i>SEC 8-K Material Filings
                </span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.66rem;color:#94A3B8;">{len(filings_filt)} Hits</span>
              </div>
              {rows_8k_html}
            </div>
            """),
            unsafe_allow_html=True,
        )

    with col_fed:
        rows_fed_html = ""
        for ev in fed_evs[:6]:
            ev_title = _html.escape(str(ev.get("event", "")))
            ev_dt = _html.escape(str(ev.get("datetime") or ev.get("date", "")))
            ev_cat = str(ev.get("category", "US MACRO"))
            ev_imp = str(ev.get("impact", "MEDIUM"))
            is_fed_ev = bool(ev.get("is_fed", False))
            tag_col = "#FF6B00" if is_fed_ev else ("#F43F5E" if ev_imp == "HIGH" else "#FB923C")
            est_v = ev.get("estimate")
            prev_v = ev.get("previous")
            act_v = ev.get("actual")
            nums = []
            if act_v is not None:
                nums.append(f"Act {act_v}")
            if est_v is not None:
                nums.append(f"Est {est_v}")
            if prev_v is not None:
                nums.append(f"Prev {prev_v}")
            num_str = " | ".join(nums) if nums else ev_cat
            rows_fed_html += (
                f'<div style="padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.75rem;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.66rem;font-weight:800;color:{tag_col};">{_html.escape(ev_cat)}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.66rem;color:#94A3B8;">{ev_dt}</span>'
                f'</div>'
                f'<div style="color:#E2E8F0;font-weight:700;margin-top:2px;line-height:1.3;">{ev_title}</div>'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:0.67rem;color:#94A3B8;margin-top:1px;">{_html.escape(str(num_str))}</div>'
                f'</div>'
            )
        if not rows_fed_html:
            rows_fed_html = '<div style="font-size:0.76rem;color:#94A3B8;padding:8px 0;">No high-impact US macro or Fed events scheduled.</div>'

        st.markdown(
            clean_html(f"""
            <div class="rm-catalyst-col">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08);">
                <span style="font-size:0.76rem;font-weight:800;color:#FF8533;text-transform:uppercase;letter-spacing:0.05em;">
                  <i class="fa-solid fa-landmark" style="margin-right:5px;"></i>Fed / FOMC &amp; US Macro
                </span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.66rem;color:#94A3B8;">{len(fed_evs)} Events</span>
              </div>
              {rows_fed_html}
            </div>
            """),
            unsafe_allow_html=True,
        )

    with col_news:
        rows_news_html = ""
        for n in sec_news[:6]:
            nsym = _html.escape(str(n.get("symbol", "")))
            ntitle = _html.escape(str(n.get("title", "")))
            nsite = _html.escape(str(n.get("site", "MarketWire")))
            ndate = _html.escape(str(n.get("published_date", ""))[:16])
            nurl_safe = _safe_http_url(n.get("url")) or "#"
            rows_news_html += (
                f'<div style="padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.75rem;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.66rem;font-weight:800;color:#FF8533;">{nsym} &middot; {nsite}</span>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.66rem;color:#94A3B8;">{ndate}</span>'
                f'</div>'
                f'<div style="margin-top:2px;line-height:1.32;"><a href="{nurl_safe}" target="_blank" rel="noopener noreferrer" style="color:#E2E8F0;text-decoration:none;font-weight:600;">{ntitle}</a></div>'
                f'</div>'
            )
        if not rows_news_html:
            rows_news_html = '<div style="font-size:0.76rem;color:#94A3B8;padding:8px 0;">No sector catalyst wire headlines cached.</div>'

        st.markdown(
            clean_html(f"""
            <div class="rm-catalyst-col">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08);">
                <span style="font-size:0.76rem;font-weight:800;color:#FF8533;text-transform:uppercase;letter-spacing:0.05em;">
                  <i class="fa-solid fa-bolt" style="margin-right:5px;"></i>Sector FMP Catalyst Wire
                </span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.66rem;color:#94A3B8;">{len(sec_news)} Stories</span>
              </div>
              {rows_news_html}
            </div>
            """),
            unsafe_allow_html=True,
        )


# =========================================================================
# (C) HIGH-DELTA 30-45 DTE SCANNER MATRIX & ACTIVE SETUP EXECUTION COCKPIT
# =========================================================================
st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
ui_kit.section_header(
    title=f"High-Delta 30-45 DTE Scanner Matrix · {st.session_state.selected_sector}",
    icon="fa-crosshairs",
    subtitle=f"Ranked by |Conviction Score| (-200..+200) · Delta Profile: {st.session_state.delta_profile} · Benchmark: {benchmark_symbol}",
    meta_html=f"<span class='rm-dte-pill'>Active Posture: {effective_dte} DTE</span>",
    icon_color="#FF6B00",
)

if ranked_by_conv:
    _top_sc = ranked_by_conv[0]
    _top_sc_m = _top_sc.get("metrics") or {}
    _top_sc_qe = _top_sc.get("quant_edge") or _top_sc_m.get("quant_edge") or {}
    _top_sc_tel = _top_sc.get("options_telemetry") or _top_sc_m.get("options_telemetry") or {}
    edu.render_edu_drawer(
        "scanner_matrix",
        live_ctx={
            "sector": st.session_state.selected_sector,
            "top_symbol": _top_sc.get("symbol", active_ticker),
            "net_ev_pct": _top_sc_qe.get("net_ev_pct", 0.0),
            "win_rate_pct": _top_sc_m.get("empirical_win_rate_pct", 55.0),
            "sample_n": _top_sc_m.get("empirical_sample_n", 40),
            "vrp_pts": _top_sc_tel.get("vrp_vol_pts", 0.0),
            "prefer_spread": _top_sc_tel.get("prefer_spread", False),
        },
        compact=True,
        align="right",
    )
    for r_idx, cand in enumerate(ranked_by_conv[:8], start=1):
        c_sym = cand["symbol"]
        c_m = cand.get("metrics", {})
        c_bp = cand.get("blueprint", {})
        c_qe = cand.get("quant_edge") or c_m.get("quant_edge") or {}
        c_skew = cand.get("skew_optimizer") or c_m.get("skew_optimizer") or {}
        c_telem = cand.get("options_telemetry") or c_m.get("options_telemetry") or {}
        c_score = int(cand.get("conviction_score_200", c_bp.get("conviction_score_200", 0)))
        c_tier = str(cand.get("conviction_tier", c_bp.get("conviction_tier", "WATCH / DEVELOPING")))
        c_dir = "CALL" if c_score > 35 else ("PUT" if c_score < -35 else ("CALL" if "CALL" in str(c_bp.get("direction", "")) else "PUT"))
        c_dte = int(cand.get("recommended_dte", c_bp.get("recommended_dte", effective_dte)) or effective_dte)
        c_near = c_m.get("near_live_option") if isinstance(c_m.get("near_live_option"), dict) else {}
        c_strike = float(c_near.get("strike") or c_m.get("recommended_strike") or c_m.get("price", 0.0))
        c_delta = float(c_near.get("delta") or c_m.get("estimated_delta") or 0.50)
        c_mid = float(c_near.get("mid") or 0.0)
        c_spr = float(c_skew.get("spread_friction_pct") or c_qe.get("spread_friction_pct") or 0.0)
        c_ev = float(c_qe.get("net_ev_pct", 0.0) or 0.0)
        c_is_etf = bool(cand.get("is_etf") or c_sym in rbe3.THEMATIC_ETFS)
        is_sel_row = c_sym == active_ticker

        c_vrp = float(c_telem.get("vrp_vol_pts", (float(c_telem.get("iv_pct", 0.0) or 0.0) - float(c_m.get("hv_20d", 0.0) or 0.0))))
        c_win = float(c_m.get("empirical_win_rate_pct", 55.0) or 55.0)
        c_neff = int(c_m.get("empirical_sample_n_eff", c_m.get("empirical_sample_n", 30)) or 30)
        c_pref_sp = bool(c_telem.get("prefer_spread", False))
        c_struct_lbl = "SPREAD" if c_pref_sp else "NAKED"
        c_struct_col = "#FF8533" if c_pref_sp else "#38BDF8"
        c_er_days = c_m.get("days_to_earnings", cand.get("earnings", {}).get("days_to_earnings", 45))
        if c_is_etf:
            c_er_lbl, c_er_col = "ETF", "#94A3B8"
        elif c_er_days is not None and 0 <= int(c_er_days) <= 7:
            c_er_lbl, c_er_col = f"ER {int(c_er_days)}d", "#F43F5E"
        elif c_er_days is not None and 0 <= int(c_er_days) <= 25:
            c_er_lbl, c_er_col = f"ER {int(c_er_days)}d", "#FB923C"
        else:
            c_er_lbl, c_er_col = "ER Clear", "#10B981"
        c_vrp_col = "#10B981" if c_vrp <= -2.0 else ("#F43F5E" if c_vrp >= 8.0 else "#CBD5E1")

        ev_col = "#10B981" if c_ev >= 10.0 else ("#F43F5E" if c_ev < 0 else "#FB923C")
        etf_tag = '<span style="font-size:0.60rem;font-weight:800;color:#FF8533;background:rgba(255,107,0,0.14);border:1px solid rgba(255,107,0,0.35);padding:1px 6px;border-radius:9999px;">ETF</span>' if c_is_etf else ""
        contract_txt = (
            f"{c_dte}D ${c_strike:g}{'C' if c_dir=='CALL' else 'P'} &bull; &Delta; {abs(c_delta):.2f}"
            + (f" &bull; Mid ${c_mid:.2f}" if c_mid > 0 else "")
            + (f" &bull; Sprd {c_spr:.1f}%" if c_spr > 0 else "")
        )
        pills_html = (
            f'<span style="font-family:JetBrains Mono,monospace;font-size:0.64rem;font-weight:700;color:{c_vrp_col};background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);padding:2px 7px;border-radius:9999px;">VRP {c_vrp:+.1f}v</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:0.64rem;font-weight:700;color:#E2E8F0;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);padding:2px 7px;border-radius:9999px;">Hit {c_win:.0f}% (n={c_neff})</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:0.64rem;font-weight:800;color:{c_struct_col};background:rgba(255,255,255,0.04);border:1px solid {c_struct_col}55;padding:2px 7px;border-radius:9999px;">{c_struct_lbl}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:0.64rem;font-weight:700;color:{c_er_col};background:rgba(255,255,255,0.04);border:1px solid {c_er_col}44;padding:2px 7px;border-radius:9999px;">{_html.escape(c_er_lbl)}</span>'
        )

        sc_row_col, sc_btn_col = st.columns([5.8, 1.0], gap="small", vertical_alignment="center")
        with sc_row_col:
            st.markdown(
                clean_html(f"""
                <div class="rm-scanner-row{' is-active' if is_sel_row else ''}">
                  <div style="display:flex;align-items:center;gap:10px;min-width:170px;">
                    <span style="font-family:'JetBrains Mono',monospace;font-size:0.74rem;font-weight:800;color:#FF8533;">#{r_idx}</span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:0.94rem;font-weight:800;color:#F8FAFC;">{_html.escape(c_sym)}</span>
                    {etf_tag}
                    <span style="font-size:0.68rem;color:#94A3B8;font-weight:700;">{_html.escape(c_tier)}</span>
                  </div>
                  <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                    {_conviction_200_badge(c_score, c_dir)}
                    <span style="font-family:'JetBrains Mono',monospace;font-size:0.76rem;color:#E2E8F0;">{contract_txt}</span>
                    {pills_html}
                  </div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:0.80rem;font-weight:800;color:{ev_col};white-space:nowrap;">
                    5D EV {c_ev:+.1f}%
                  </div>
                </div>
                """),
                unsafe_allow_html=True,
            )
        with sc_btn_col:
            if st.button(
                "Active" if is_sel_row else "Select",
                key=f"scan_row_sel_{c_sym}",
                type="primary" if is_sel_row else "secondary",
                width="stretch",
            ):
                st.session_state.selected_ticker = c_sym
                st.rerun()

# =========================================================================
# ACTIVE SETUP EXECUTION DESK (selected_ticker)
# =========================================================================
metrics = active_cand["metrics"]
fundamentals = active_cand["fundamentals"]
insider = active_cand["insider"]
analyst = active_cand["analyst"]
blueprint = active_cand["blueprint"]
company_name = active_cand["company_name"]
company_logo = active_cand["company_logo"]
is_etf_active = bool(active_cand.get("is_etf") or fundamentals.get("solvency_tier") == "ETF Basket")

curr_price = float(metrics.get("price", 0.0) or 0.0)
chg_1d = float(metrics.get("change_pct_1d", 0.0) or 0.0)
z_val = float(metrics.get("z_score_5d", 0.0) or 0.0)
z_abs = float(metrics.get("z_abs", z_val) or z_val)
z_rel = float(metrics.get("z_rel_5d", z_val) or z_val)
vwma20_val = float(metrics.get("vwma20", metrics.get("sma20", curr_price)) or curr_price)
ou_hl = float(metrics.get("ou_half_life", 5.0) or 5.0)
hurst_val = float(metrics.get("hurst", 0.45) or 0.45)
playbook_name = str(metrics.get("playbook", "EQUILIBRIUM WATCH"))
action = str(metrics.get("action", "WAIT"))
target_strike = float(metrics.get("recommended_strike", curr_price) or curr_price)
tgt_p = float(metrics.get("target_price", vwma20_val) or vwma20_val)
inv_p = float(metrics.get("invalidation_price", metrics.get("lower_b", curr_price * 0.94)) or curr_price * 0.94)
rr = float(metrics.get("rr_ratio", 1.0) or 1.0)
days_to_er = metrics.get("days_to_earnings", active_cand.get("earnings", {}).get("days_to_earnings", 45))
er_date_str = metrics.get("earnings_date", active_cand.get("earnings", {}).get("earnings_date", "Clear (>25d)"))
has_er_25d = bool(metrics.get("has_earnings_25d", 0 <= int(days_to_er or 45) <= 25))
exp_basis_pct = float(metrics.get("expected_basis_pct", 0.0) or 0.0)
exp_up_basis = float(metrics.get("expected_up_basis_pct", 3.5) or 3.5)
exp_dn_basis = float(metrics.get("expected_down_basis_pct", -3.5) or -3.5)
p75_basis = float(metrics.get("p75_basis_pct", abs(exp_basis_pct) * 1.35) or 0.0)
emp_win_pct = float(metrics.get("empirical_win_rate_pct", 55.0) or 55.0)
emp_n = int(metrics.get("empirical_sample_n", metrics.get("empirical_sample_size", 40)) or 40)
whale_badge = str(metrics.get("whale_badge", "TWO-WAY FLOW"))
whale_score = float(metrics.get("whale_score", 0.0) or 0.0)
cmf_20 = float(metrics.get("cmf_20", 0.0) or 0.0)
ud_vol_ratio = float(metrics.get("up_down_vol_ratio", 1.0) or 1.0)

score_200 = int(active_cand.get("conviction_score_200", blueprint.get("conviction_score_200", 0)) or 0)
conv_tier = str(active_cand.get("conviction_tier", blueprint.get("conviction_tier", "WATCH / DEVELOPING")))
synergy_unlocked = bool(active_cand.get("synergy_unlocked", blueprint.get("synergy_unlocked", False)))
regime_gate_mult = float(active_cand.get("regime_gate_mult", 1.0) or 1.0)
pillars = active_cand.get("conviction_pillars") or {}
dte_rationale_active = str(active_cand.get("dte_rationale", dte_rat))

opt_dir = "CALL" if score_200 > 35 else ("PUT" if score_200 < -35 else ("PUT" if "PUT" in action else "CALL"))
opt_action_cmd = f"BUY {opt_dir}"

# Resolve live option contract aligned to active DTE Posture & Delta Profile
near_opt = metrics.get("near_live_option")
if (
    not isinstance(near_opt, dict)
    or abs(int(near_opt.get("dte", effective_dte)) - effective_dte) > 10
    or _is_convex_otm
):
    fetched_opt = cached_get_near_live_option(
        active_ticker,
        opt_action_cmd,
        target_strike,
        target_dte=effective_dte,
        target_delta=_target_delta,
        delta_mode=_delta_mode,
    )
    if fetched_opt:
        near_opt = fetched_opt

base_opt_telem = (
    active_cand.get("options_telemetry")
    or metrics.get("options_telemetry")
    or rbe3.calculate_options_volatility_and_spread_telemetry(
        active_ticker, metrics, live_option=near_opt, dte=effective_dte, hold_days=5, iv_shift_pct=0.0
    )
)
gw_info = active_cand.get("gamma_walls") or metrics.get("gamma_walls") or {}
skew_opt = active_cand.get("skew_optimizer") or metrics.get("skew_optimizer") or {}
quant_edge = active_cand.get("quant_edge") or metrics.get("quant_edge") or {}

# Ticker Search / Jump Bar
st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
with st.form("lookup_ticker_hero_form", clear_on_submit=True, border=False, enter_to_submit=True):
    col_srch_in, col_srch_btn = st.columns([5.0, 1.0], gap="small")
    with col_srch_in:
        searched_ticker = st.text_input(
            "Jump to Ticker",
            placeholder="Jump to any U.S. equity or thematic ETF (e.g. NVDA, REMX, SRVR, ROBO, JEDI, OKLO, MP)...",
            key="search_hero_ticker_input",
            label_visibility="collapsed",
        ).strip().upper()
    with col_srch_btn:
        btn_search = st.form_submit_button("ENTER ↵", type="primary", width="stretch")

if btn_search and searched_ticker:
    _select_ticker_and_sector(searched_ticker)
    st.rerun()

# Clean Single Telemetry Strip
er_txt = (
    "ETF Basket (No ER)" if is_etf_active
    else (f"ER in {days_to_er}d ({er_date_str})" if (has_er_25d and days_to_er is not None and days_to_er >= 0) else f"ER Clear ({days_to_er}d)")
)
er_col = "#94A3B8" if is_etf_active else ("#F43F5E" if (days_to_er is not None and 0 <= days_to_er <= 7) else ("#FB923C" if has_er_25d else "#10B981"))

st.markdown(
    clean_html(f"""
    <div class="ticker-telemetry-bar">
      <div class="telem-group">
        <div class="ticker-identity-item">
          <img src="{_safe_http_url(company_logo)}" class="ticker-logo-avatar" alt="{_html.escape(active_ticker)}" onerror="this.style.display='none'"/>
          <div class="telem-item">
            <span class="telem-val-hero">{_html.escape(active_ticker)}</span>
            <span class="telem-sub" style="color:#FF8533;max-width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{_html.escape(company_name)}</span>
          </div>
        </div>
        <div class="telem-sep"></div>
        <div class="telem-item">
          <span class="telem-label">SPOT &amp; EARNINGS</span>
          <span class="telem-val-hero">${curr_price:.2f} <span style="font-size:0.9rem;color:{'#10B981' if chg_1d >= 0 else '#F43F5E'};">({chg_1d:+.2f}%)</span></span>
          <span class="telem-sub" style="color:{er_col};font-weight:700;">{_html.escape(er_txt)}</span>
        </div>
        <div class="telem-sep"></div>
        <div class="telem-item">
          <span class="telem-label">DUAL Z (ABS / REL)</span>
          <span class="telem-val" style="color:{'#10B981' if z_val <= -1.5 else ('#F43F5E' if z_val >= 1.5 else '#FB923C')};">{z_val:+.2f}&sigma;</span>
          <span class="telem-sub">Abs {z_abs:+.2f}&sigma; | Rel {z_rel:+.2f}&sigma;</span>
        </div>
        <div class="telem-sep"></div>
        <div class="telem-item">
          <span class="telem-label">5Y BASIS &amp; HIT RATE</span>
          <span class="telem-val" style="color:{'#10B981' if exp_basis_pct >= 0 else '#F43F5E'};">{exp_basis_pct:+.2f}%</span>
          <span class="telem-sub">{emp_win_pct:.0f}% Win (n={emp_n}) &rarr; ${tgt_p:.2f}</span>
        </div>
        <div class="telem-sep"></div>
        <div class="telem-item">
          <span class="telem-label">O-U &tau;&frac12; &amp; HURST</span>
          <span class="telem-val" style="color:{'#10B981' if ou_hl <= 4.5 else ('#F43F5E' if ou_hl > 7.5 else '#FB923C')};">{ou_hl:.1f}d</span>
          <span class="telem-sub">Hurst {hurst_val:.2f} &bull; {_html.escape(playbook_name)}</span>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        {_conviction_200_badge(score_200, opt_dir)}
        <span class="rm-dte-pill">{effective_dte} DTE</span>
      </div>
    </div>
    """),
    unsafe_allow_html=True,
)
edu.render_edu_drawer(
    "elasticity_micro",
    live_ctx={
        "symbol": active_ticker,
        "z_score_5d": z_val,
        "kalman_beta": (quant_edge.get("kalman_beta") if isinstance(quant_edge, dict) else None) or metrics.get("kalman_beta") or metrics.get("beta", 1.15),
        "ou_half_life": ou_hl,
        "hurst": hurst_val,
        "clv": metrics.get("clv_today", metrics.get("clv", 0.0)),
        "rvol": metrics.get("rvol", 1.0),
    },
)

# 5-Pillar Orthogonal Conviction Breakdown + Synergy Gate Badge
pillar_specs = [
    ("Elasticity / Kalman", "elasticity_kalman", 65.0),
    ("Kinetic Asymmetry", "kinetic_asymmetry", 45.0),
    ("Dealer / Whale Flow", "dealer_whale_flow", 40.0),
    ("Surface Convexity", "surface_convexity", 30.0),
    ("Regime / Solvency", "regime_solvency", 20.0),
]
syn_col = "#FF8533" if synergy_unlocked else "#94A3B8"
syn_txt = "SYNERGY GATE UNLOCKED (±200)" if synergy_unlocked else "SYNERGY LOCKED (SOFT-CAPPED ±145)"

pillar_cards_html = ""
for p_title, p_key, p_max in pillar_specs:
    p_val = float(pillars.get(p_key, 0.0) or 0.0)
    p_pct = min(100.0, abs(p_val) / p_max * 100.0)
    p_col = "#10B981" if p_val >= 4.0 else ("#F43F5E" if p_val <= -4.0 else "#64748B")
    pillar_cards_html += (
        f'<div style="background:rgba(13,16,23,0.68);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:9px 11px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">'
        f'<span style="font-size:0.68rem;font-weight:700;color:#94A3B8;text-transform:uppercase;">{p_title}</span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:0.78rem;font-weight:800;color:{p_col};">{p_val:+.1f}</span>'
        f'</div>'
        f'<div style="height:4px;background:rgba(255,255,255,0.06);border-radius:9999px;overflow:hidden;">'
        f'<div style="width:{max(4.0, p_pct):.1f}%;height:100%;background:{p_col};border-radius:9999px;"></div>'
        f'</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.62rem;color:#64748B;margin-top:3px;">Range &plusmn;{int(p_max)}</div>'
        f'</div>'
    )

st.markdown(
    clean_html(f"""
    <div class="rm-glass-panel" style="padding:12px 16px !important;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-size:0.78rem;font-weight:800;color:#E2E8F0;text-transform:uppercase;letter-spacing:0.04em;">
            5-Pillar Orthogonal Conviction Breakdown
          </span>
          <span style="font-family:'JetBrains Mono',monospace;font-size:0.68rem;font-weight:800;color:{syn_col};background:rgba(255,107,0,0.10);border:1px solid {syn_col}55;padding:2px 9px;border-radius:9999px;">
            {syn_txt}
          </span>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#CBD5E1;">
          Tier: <b style="color:#FF8533;">{_html.escape(conv_tier)}</b> &bull; Regime Gate: <b>{regime_gate_mult:.2f}x</b>
        </span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;">
        {pillar_cards_html}
      </div>
    </div>
    """),
    unsafe_allow_html=True,
)
edu.render_edu_drawer(
    "conviction_5pillar",
    live_ctx={
        "conviction_score_200": score_200,
        "conviction_tier": conv_tier,
        "synergy_unlocked": synergy_unlocked,
        "regime_gate_mult": regime_gate_mult,
    },
)

# Chart Row (Gauge + 35-Day Rubberband Envelope) & 30-45 DTE High-Delta Trade Ticket
col_viz, col_ticket = st.columns([1.85, 1.05], gap="medium")

with col_viz:
    v_sub1, v_sub2 = st.columns([0.92, 1.68], gap="small")
    with v_sub1:
        gauge_fig = rbc.create_rubberband_gauge(
            z_val,
            active_ticker,
            action,
            ou_half_life=ou_hl,
            hurst=hurst_val,
            playbook=playbook_name,
            conviction_score_200=score_200,
        )
        st.plotly_chart(gauge_fig, width="stretch", config={"displayModeBar": False, "responsive": True})
    with v_sub2:
        t_series = cached_get_historical_series(active_ticker)
        env_fig = rbc.create_rubberband_envelope_visual(active_ticker, metrics, t_series)
        st.plotly_chart(env_fig, width="stretch", config={"displayModeBar": False, "responsive": True})

with col_ticket:
    t_opt = near_opt if isinstance(near_opt, dict) and near_opt.get("strike") else {}
    t_strike = float(t_opt.get("strike") or target_strike)
    t_dte = int(t_opt.get("dte") or effective_dte)
    t_exp = str(t_opt.get("expiry") or "Standard Cycle")
    t_mid = float(t_opt.get("mid") or base_opt_telem.get("prem_entry", 2.50) or 2.50)
    t_bid = float(t_opt.get("bid") or 0.0)
    t_ask = float(t_opt.get("ask") or 0.0)
    t_delta = float(t_opt.get("delta") or metrics.get("estimated_delta", 0.50) or 0.50)
    t_iv = float(t_opt.get("iv") or base_opt_telem.get("iv_pct", 42.0) or 42.0)
    t_spr = ((t_ask - t_bid) / t_mid * 100.0) if (t_mid > 0 and t_ask >= t_bid > 0) else float(skew_opt.get("spread_friction_pct", 3.2) or 3.2)

    q_kelly_dlr = int(quant_edge.get("kelly_dollars", 500) or 500)
    q_kelly_cnt = int(quant_edge.get("kelly_contracts", 1) or 1)
    q_kelly_pct = float(quant_edge.get("quarter_kelly_pct", 2.0) or 2.0)
    net_ev_pct = float(quant_edge.get("net_ev_pct", exp_basis_pct * 3.0) or 0.0)
    rec_struct = str(skew_opt.get("recommended_structure") or base_opt_telem.get("recommended_structure", f"{t_dte}D HIGH-DELTA"))

    dir_hex = "#10B981" if opt_dir == "CALL" else "#F43F5E"
    st.markdown(
        clean_html(f"""
        <div class="rm-glass-panel" style="border-color:rgba(255,107,0,0.42) !important;margin-bottom:10px !important;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.08);">
            <span style="font-size:0.78rem;font-weight:800;color:#FF8533;text-transform:uppercase;letter-spacing:0.05em;">
              30-45 DTE High-Delta Trade Ticket
            </span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:0.70rem;font-weight:800;color:{dir_hex};">
              {opt_dir} &bull; &Delta; {abs(t_delta):.2f}
            </span>
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:800;color:#F8FAFC;margin-bottom:4px;">
            {active_ticker} ${t_strike:g}{opt_dir[0]} &middot; {t_dte} DTE
          </div>
          <div style="font-size:0.71rem;color:#94A3B8;margin-bottom:10px;font-family:'JetBrains Mono',monospace;">
            Exp {t_exp} &bull; {rec_struct}
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.76rem;margin-bottom:10px;">
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:9px;padding:7px 9px;">
              <div style="font-size:0.63rem;color:#94A3B8;text-transform:uppercase;">Entry Mid (Limit)</div>
              <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#F8FAFC;font-size:0.92rem;">${t_mid:.2f}</div>
              <div style="font-size:0.64rem;color:#94A3B8;">Sprd {t_spr:.1f}% &bull; IV {t_iv:.0f}%</div>
            </div>
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:9px;padding:7px 9px;">
              <div style="font-size:0.63rem;color:#94A3B8;text-transform:uppercase;">5D Net EV / R:R</div>
              <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:{'#10B981' if net_ev_pct >= 10 else '#FB923C'};font-size:0.92rem;">{net_ev_pct:+.1f}%</div>
              <div style="font-size:0.64rem;color:#94A3B8;">R:R {rr:.1f}:1</div>
            </div>
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:9px;padding:7px 9px;">
              <div style="font-size:0.63rem;color:#94A3B8;text-transform:uppercase;">+1&sigma; Stock Target</div>
              <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#10B981;font-size:0.92rem;">${tgt_p:.2f}</div>
              <div style="font-size:0.64rem;color:#94A3B8;">VWMA-20: ${vwma20_val:.2f}</div>
            </div>
            <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:9px;padding:7px 9px;">
              <div style="font-size:0.63rem;color:#94A3B8;text-transform:uppercase;">Structure Stop</div>
              <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#F43F5E;font-size:0.92rem;">${inv_p:.2f}</div>
              <div style="font-size:0.64rem;color:#94A3B8;">Hard Invalidation</div>
            </div>
          </div>
          <div style="background:rgba(255,107,0,0.08);border:1px solid rgba(255,107,0,0.28);border-radius:9px;padding:7px 10px;font-size:0.72rem;color:#E2E8F0;display:flex;justify-content:space-between;align-items:center;">
            <span>0.25x Kelly: <b>${q_kelly_dlr:,}</b> ({q_kelly_cnt}x / {q_kelly_pct:.1f}%)</span>
            <span style="font-family:'JetBrains Mono',monospace;color:{cap_col};font-weight:800;">Gate {exp_cap_pct}%</span>
          </div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    if st.button(
        "⚡ Arm Order in Schwab Simulator",
        key=f"btn_arm_schwab_cockpit_{active_ticker}",
        type="primary",
        width="stretch",
    ):
        _use_sp = bool(base_opt_telem.get("prefer_spread", False))
        _short_k_arm = float(base_opt_telem.get("short_strike", 0.0) or 0.0) if _use_sp else None
        _net_deb_arm = float(base_opt_telem.get("net_debit", t_mid) or t_mid)
        prefill_payload = {
            "symbol": active_ticker,
            "action": "BUY_TO_OPEN",
            "option_type": opt_dir,
            "strategy": "VERTICAL_DEBIT_SPREAD" if (_use_sp and _short_k_arm) else "SINGLE_LEG",
            "strike": t_strike,
            "short_strike": _short_k_arm,
            "net_debit": _net_deb_arm,
            "limit_price": _net_deb_arm if (_use_sp and _short_k_arm) else t_mid,
            "spread_roi_pct": float(base_opt_telem.get("spread_roi_pct", 0.0) or 0.0),
            "expiration_date": t_exp,
            "dte": t_dte,
            "recommended_dte": effective_dte,
            "dte_rationale": dte_rationale_active,
            "spot_price": curr_price,
            "target_price": tgt_p,
            "stop_price": inv_p,
            "iv": t_iv,
            "conviction_score": score_200,
            "conviction_score_200": score_200,
            "conviction_tier": conv_tier,
            "expected_basis_pct": exp_basis_pct,
            "whale_badge": whale_badge,
            "catalyst_tag": er_txt,
            "is_near_live_option": bool(t_opt),
            "near_live_option": t_opt or None,
            "notes": (
                f"Rubberband v4.0: {playbook_name} | Conviction {score_200:+d}/±200 ({conv_tier}) | "
                f"{effective_dte}D {'Vertical Spread $' + f'{t_strike:g}/' + f'{_short_k_arm:g}' if (_use_sp and _short_k_arm) else f'High-Delta (Δ {t_delta:+.2f})'} | "
                f"Target ${tgt_p:.2f} | Stop ${inv_p:.2f}"
            ),
        }
        st.session_state["schwab_prefill"] = prefill_payload
        st.session_state["schwab_prefill_needs_sync"] = True
        st.session_state.pop("schwab_active_leg", None)
        diary_views.render_schwab_order_dialog(prefill_payload, active_cand)

    edu.render_edu_drawer(
        "trade_ticket",
        live_ctx={
            "symbol": active_ticker,
            "delta": t_delta,
            "mid_price": t_mid,
            "target_price": tgt_p,
            "stop_price": inv_p,
            "quarter_kelly_pct": q_kelly_pct,
            "spread_pct": t_spr,
        },
        compact=True,
        align="right",
    )


# =========================================================================
# SECONDARY WORKSPACE: 4-TAB INSTITUTIONAL DRAWERS BELOW MAIN COCKPIT
# =========================================================================
st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
tab_surface, tab_fund, tab_macro, tab_audit = st.tabs([
    "📐 Options Surface & Convexity",
    "🛡️ Deep Fundamentals & Float",
    "🌐 Macro & 13F Whales",
    "📊 Backtest Logs, AI Arbiter & PM Audit",
])

# -------------------------------------------------------------------------
# TAB 1: OPTIONS SURFACE & CONVEXITY
# -------------------------------------------------------------------------
with tab_surface:
    @st.fragment
    def _render_tab_surface_fragment():
        cw_k = float(gw_info.get("call_wall_strike", 0.0) or 0.0)
        cw_oi = int(gw_info.get("call_wall_oi", 0) or 0)
        pw_k = float(gw_info.get("put_wall_strike", 0.0) or 0.0)
        pw_oi = int(gw_info.get("put_wall_oi", 0) or 0)
        g_flip_k = float(gw_info.get("gamma_flip_strike", 0.0) or 0.0)
        gex_reg = str(gw_info.get("net_gex_regime", "NEUTRAL DEALER GAMMA"))
        vanna_reg = str(gw_info.get("vanna_regime", "BALANCED VANNA"))
        charm_reg = str(gw_info.get("charm_regime", "NEUTRAL CHARM"))
        sk_badge = str(skew_opt.get("skew_badge", base_opt_telem.get("skew_label", "NEUTRAL SKEW")))
        svi_cheap_k = float(skew_opt.get("cheapest_strike", target_strike) or target_strike)
        imp_borrow_bps = float(skew_opt.get("implied_borrow_bps", 0.0) or 0.0)
        lim_adv = str(skew_opt.get("limit_order_advice", "Work mid-price limit order."))

        st.markdown(
            clean_html(f"""
            <div class="rm-glass-panel">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
                <span style="font-size:0.84rem;font-weight:800;color:#FF8533;">OPRA Dealer GEX / Vanna / Charm Pin Corridor &amp; 25D SVI Skew</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:#CBD5E1;">{_html.escape(gex_reg)}</span>
              </div>
              <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;font-size:0.76rem;">
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">Gamma Pin &amp; Flip</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#F8FAFC;margin-top:2px;">P ${pw_k:g} &harr; C ${cw_k:g}</div>
                  <div style="font-size:0.66rem;color:#94A3B8;">Flip ${g_flip_k:g} &bull; Put {pw_oi:,} | Call {cw_oi:,}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">2nd-Order Greeks</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#10B981;margin-top:2px;">{_html.escape(vanna_reg)}</div>
                  <div style="font-size:0.66rem;color:#94A3B8;">{_html.escape(charm_reg)}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">25&Delta; Skew &amp; SVI Value</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#FF8533;margin-top:2px;">{_html.escape(sk_badge)}</div>
                  <div style="font-size:0.66rem;color:#94A3B8;">SVI Cheap ${svi_cheap_k:g} &bull; Borrow {imp_borrow_bps:+.0f}bps</div>
                </div>
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">Variance Risk Prem</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#E2E8F0;margin-top:2px;">{_html.escape(str(base_opt_telem.get('vega_badge', 'FAIR VEGA')))} ({base_opt_telem.get('vrp_vol_pts', 0.0):+.1f}v)</div>
                  <div style="font-size:0.66rem;color:#94A3B8;">IV {base_opt_telem.get('iv_pct', 42.0):.1f}% vs HV20 {base_opt_telem.get('hv20_pct', 42.0):.1f}%</div>
                </div>
              </div>
              <div style="margin-top:8px;font-size:0.74rem;color:#CBD5E1;"><b>Execution Note:</b> {_html.escape(lim_adv)}</div>
            </div>
            """),
            unsafe_allow_html=True,
        )

        sc_c1, sc_c2, sc_c3 = st.columns([1.2, 1.4, 1.4], gap="small")
        with sc_c1:
            dte_opts_surf = ["30 DTE (Tactical)", "35 DTE (Core)", "45 DTE (Macro Shield)", "60 DTE", "90 DTE"]
            dte_def_idx = 2 if effective_dte == 45 else 0
            dot_dte_choice = st.selectbox("Expiration Horizon", options=dte_opts_surf, index=dte_def_idx, key=f"dot_dte_sel_{active_ticker}")
            dot_dte_val = int(dot_dte_choice.split()[0])
        with sc_c2:
            hold_choice = st.selectbox(
                "Hold Horizon Scrubber",
                options=["Day 1 (Flash)", f"Day 3 (τ½={ou_hl:.1f}d)", "Day 5 (Standard O-U)", "Day 10 (Swing)"],
                index=2,
                key=f"dot_hold_sel_{active_ticker}",
            )
            hold_days_val = 1 if "Day 1 " in hold_choice else (3 if "Day 3" in hold_choice else (10 if "Day 10" in hold_choice else 5))
        with sc_c3:
            iv_shock_choice = st.selectbox(
                "Volatility Stress Test",
                options=["-15% IV Crush", "-7.5% Vol Cool-Off", "Flat IV (0%)", "+10% Vol Spike", "+20% Vol Shock"],
                index=2,
                key=f"dot_iv_sel_{active_ticker}",
            )
            iv_shift_val = -15.0 if "-15%" in iv_shock_choice else (-7.5 if "-7.5%" in iv_shock_choice else (10.0 if "+10%" in iv_shock_choice else (20.0 if "+20%" in iv_shock_choice else 0.0)))

        try:
            surf_chain_df = marketdata_client.get_option_chain_native(
                active_ticker, dte=dot_dte_val, strike_limit=44, ttl=600, feed="cached"
            )
        except Exception:
            surf_chain_df = None

        scrub_telem = rbe3.calculate_options_volatility_and_spread_telemetry(
            symbol=active_ticker,
            metrics=metrics,
            live_option=near_opt,
            dte=dot_dte_val,
            hold_days=hold_days_val,
            iv_shift_pct=iv_shift_val,
            chain_df=surf_chain_df,
            skew_optimizer=skew_opt,
            term_structure=active_cand.get("term_structure"),
        )

        pref_sp = bool(scrub_telem.get("prefer_spread", False))
        st.markdown(
            clean_html(f"""
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:8px 0 8px 0;">
              <div class="rm-glass-panel" style="margin-bottom:0 !important;border-color:{'rgba(16,185,129,0.45)' if not pref_sp else 'rgba(255,255,255,0.08)'} !important;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                  <b style="color:#F8FAFC;font-size:0.80rem;">Strategy A: Naked {_html.escape(str(scrub_telem['direction']))} (${scrub_telem['strike_used']:.2f})</b>
                  <span style="font-family:'JetBrains Mono',monospace;font-size:0.66rem;color:{'#10B981' if not pref_sp else '#94A3B8'};">{'OPTIMAL' if not pref_sp else 'UNHEDGED VEGA'}</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.0rem;font-weight:800;color:{'#10B981' if scrub_telem['naked_roi_pct'] >= 10 else '#FB923C'};">
                  {scrub_telem['naked_profit_1k']:+,.0f}$ ({scrub_telem['naked_roi_pct']:+.1f}% ROI)
                </div>
                <div style="font-size:0.70rem;color:#94A3B8;margin-top:2px;">
                  {scrub_telem['naked_contracts']}x @ ${scrub_telem['prem_entry']:.2f} (&Delta; {scrub_telem['delta_in']:+.2f}) &bull; Day-{hold_days_val} BE ${scrub_telem['breakeven_hold_price']:.2f}
                </div>
              </div>
              <div class="rm-glass-panel" style="margin-bottom:0 !important;border-color:{'rgba(255,107,0,0.48)' if pref_sp else 'rgba(255,255,255,0.08)'} !important;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                  <b style="color:#F8FAFC;font-size:0.80rem;">Strategy B: Vertical Debit Spread (${scrub_telem['strike_used']:.2f} / ${scrub_telem['short_strike']:.2f})</b>
                  <span style="font-family:'JetBrains Mono',monospace;font-size:0.66rem;color:{'#FF8533' if pref_sp else '#94A3B8'};">{'RECOMMENDED' if pref_sp else 'DEFINED RISK'}</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1.0rem;font-weight:800;color:{'#10B981' if scrub_telem['spread_roi_pct'] >= 10 else '#FB923C'};">
                  {scrub_telem['spread_profit_1k']:+,.0f}$ ({scrub_telem['spread_roi_pct']:+.1f}% ROI)
                </div>
                <div style="font-size:0.70rem;color:#94A3B8;margin-top:2px;">
                  {scrub_telem['spread_contracts']}x @ ${scrub_telem['net_debit']:.2f} Debit (Net &Delta; {scrub_telem['net_spread_delta']:+.2f}) &bull; Saves ${scrub_telem['theta_saved_dollar']:.0f} Theta ({_html.escape(str(scrub_telem.get('short_leg_source', 'BS')))})
                </div>
              </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
        edu.render_edu_drawer(
            "options_surface",
            live_ctx={
                "opra_iv": scrub_telem.get("iv_pct", 35.0),
                "hv20": scrub_telem.get("hv20_pct", 35.0),
                "net_gex_m": gw_info.get("net_gex_m", 0.0),
                "gamma_flip_strike": g_flip_k,
                "net_vanna_m": gw_info.get("net_vanna_m", 0.0),
                "variance_rent_ratio": scrub_telem.get("variance_rent_ratio", 1.0),
                "prefer_spread": pref_sp,
            },
        )

        _arm_label = (
            f"⚡ Arm Recommended Vertical Spread (${scrub_telem['strike_used']:.2f}/${scrub_telem['short_strike']:.2f} {scrub_telem['direction']} @ ${scrub_telem['net_debit']:.2f})"
            if pref_sp
            else f"⚡ Arm Recommended Naked {scrub_telem['direction']} (${scrub_telem['strike_used']:.2f} @ ${scrub_telem['prem_entry']:.2f})"
        )
        if st.button(_arm_label, key=f"btn_arm_surface_rec_{active_ticker}_{dot_dte_val}", type="primary", width="stretch"):
            _k1_s = f"{scrub_telem['strike_used']:.2f}"
            _k2_s = f"{scrub_telem['short_strike']:.2f}"
            _roi_s = scrub_telem["spread_roi_pct"] if pref_sp else scrub_telem["naked_roi_pct"]
            _struct_note = f"Vertical Spread ${_k1_s}/${_k2_s}" if pref_sp else f"Single Leg ${_k1_s}"
            _surf_prefill = {
                "symbol": active_ticker,
                "action": "BUY_TO_OPEN",
                "option_type": scrub_telem["direction"],
                "strategy": "VERTICAL_DEBIT_SPREAD" if pref_sp else "SINGLE_LEG",
                "strike": float(scrub_telem["strike_used"]),
                "short_strike": float(scrub_telem["short_strike"]) if pref_sp else None,
                "net_debit": float(scrub_telem["net_debit"]),
                "limit_price": float(scrub_telem["net_debit"]) if pref_sp else float(scrub_telem["prem_entry"]),
                "expiration_date": t_exp,
                "dte": dot_dte_val,
                "recommended_dte": effective_dte,
                "dte_rationale": dte_rationale_active,
                "spot_price": curr_price,
                "target_price": tgt_p,
                "stop_price": inv_p,
                "iv": float(scrub_telem.get("iv_pct", t_iv)),
                "conviction_score": score_200,
                "conviction_score_200": score_200,
                "conviction_tier": conv_tier,
                "expected_basis_pct": exp_basis_pct,
                "whale_badge": whale_badge,
                "catalyst_tag": er_txt,
                "notes": f"Surface Optimizer ({dot_dte_val}D): {_struct_note} | Est ROI {_roi_s:+.1f}%",
            }
            st.session_state["schwab_prefill"] = _surf_prefill
            st.session_state["schwab_prefill_needs_sync"] = True
            st.session_state.pop("schwab_active_leg", None)
            diary_views.render_schwab_order_dialog(_surf_prefill, active_cand)

        anatomy_fig = rbc.create_trade_anatomy_visual(
            active_ticker,
            metrics,
            opt_telem=scrub_telem,
            gamma_walls=gw_info,
            near_opt=near_opt,
            height=280,
        )
        st.plotly_chart(anatomy_fig, width="stretch", config={"displayModeBar": False, "responsive": True})
        edu.render_edu_drawer(
            "trade_anatomy",
            live_ctx={
                "symbol": active_ticker,
                "spot": curr_price,
                "vwma20": metrics.get("vwma20", curr_price),
                "strike": scrub_telem.get("strike_used", t_strike),
                "breakeven": scrub_telem.get("breakeven_hold_price", curr_price),
                "target_price": tgt_p,
                "stop_price": inv_p,
                "call_wall": cw_k,
                "put_wall": pw_k,
                "gamma_flip": g_flip_k,
            },
            compact=True,
            align="right",
        )

        strike_dot_fig = rbc.create_ticker_options_strike_dot_matrix(
            active_ticker,
            metrics,
            fundamentals,
            dte=dot_dte_val,
            hold_days=hold_days_val,
            iv_shift_pct=iv_shift_val,
            chain_df=surf_chain_df,
            skew_optimizer=skew_opt,
        )
        st.plotly_chart(strike_dot_fig, width="stretch", config={"displayModeBar": "hover", "displaylogo": False, "responsive": True})

        svi_term_fig = rbc.create_iv_smile_and_term_structure_chart(active_cand, chain_df=surf_chain_df)
        st.plotly_chart(svi_term_fig, width="stretch", config={"displayModeBar": False, "responsive": True})

        scen = scrub_telem.get("scenario_matrix") or {}
        scen_rows = scen.get("rows") or []
        scen_days = scen.get("day_cols") or [1, 3, 5, 10]
        if scen_rows:
            _hdr_cols = "".join(
                f'<th style="padding:7px 8px;text-align:center;color:#94A3B8;font-size:0.68rem;text-transform:uppercase;">Day +{int(d)}</th>'
                for d in scen_days
            )
            _body_trs = ""
            for s_row in scen_rows:
                _sp_pct = float(s_row.get("spot_pct", 0.0) or 0.0)
                _sp_px = float(s_row.get("spot_price", curr_price) or curr_price)
                _td_cells = ""
                for cell in s_row.get("cells", []):
                    _roi_v = float(cell.get("spread_roi_pct" if pref_sp else "naked_roi_pct", 0.0) or 0.0)
                    _pnl_v = float(cell.get("spread_pnl" if pref_sp else "naked_pnl", 0.0) or 0.0)
                    _alt_roi = float(cell.get("naked_roi_pct" if pref_sp else "spread_roi_pct", 0.0) or 0.0)
                    _bg = "rgba(16,185,129,0.16)" if _roi_v >= 15 else ("rgba(16,185,129,0.08)" if _roi_v > 0 else ("rgba(244,63,94,0.18)" if _roi_v <= -25 else "rgba(244,63,94,0.08)"))
                    _fg = "#34D399" if _roi_v > 0 else "#FB7185"
                    _td_cells += (
                        f'<td style="padding:7px 8px;text-align:center;background:{_bg};border:1px solid rgba(255,255,255,0.05);">'
                        f'<div style="font-family:JetBrains Mono,monospace;font-weight:800;font-size:0.78rem;color:{_fg};">{_pnl_v:+,.0f}$ ({_roi_v:+.0f}%)</div>'
                        f'<div style="font-family:JetBrains Mono,monospace;font-size:0.63rem;color:#94A3B8;">Alt {_alt_roi:+.0f}%</div>'
                        f'</td>'
                    )
                _body_trs += (
                    f'<tr>'
                    f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;font-size:0.74rem;font-weight:800;color:#F8FAFC;border:1px solid rgba(255,255,255,0.05);white-space:nowrap;">{_sp_pct:+.1f}% (${_sp_px:.2f})</td>'
                    f'{_td_cells}'
                    f'</tr>'
                )
            st.markdown(
                clean_html(f"""
                <div class="rm-glass-panel" style="margin-top:10px !important;">
                  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="font-size:0.80rem;font-weight:800;color:#FF8533;">5&times;4 Spot Shock &times; Hold-Day American CRR P&amp;L Matrix ($1,000 Risk Budget &bull; Active: {'Vertical Spread' if pref_sp else 'Naked'} &bull; Spot-Vol Skew Adjusted)</span>
                  </div>
                  <div style="overflow-x:auto;">
                    <table style="width:100%;border-collapse:collapse;">
                      <thead><tr><th style="padding:7px 10px;text-align:left;color:#94A3B8;font-size:0.68rem;text-transform:uppercase;">Spot Shock</th>{_hdr_cols}</tr></thead>
                      <tbody>{_body_trs}</tbody>
                    </table>
                  </div>
                </div>
                """),
                unsafe_allow_html=True,
            )

    _render_tab_surface_fragment()


# -------------------------------------------------------------------------
# TAB 2: DEEP FUNDAMENTALS & FLOAT
# -------------------------------------------------------------------------
with tab_fund:
    f_score_val = float(fundamentals.get("fund_score", 68.0 if is_etf_active else 55.0))
    altman_z = float(fundamentals.get("altman_z", 3.0))
    piotroski_f = int(fundamentals.get("piotroski_score", 6))
    curr_ratio = float(fundamentals.get("current_ratio", 1.5))
    debt_eq = float(fundamentals.get("debt_to_equity", 0.6))
    fcf_yield = float(fundamentals.get("fcf_yield_pct", 0.0))
    rev_yoy = float(fundamentals.get("rev_growth_yoy_pct", fundamentals.get("rev_growth_pct", 0.0)))
    an_tgt = float(analyst.get("target_consensus", curr_price) or curr_price)
    an_upside = float(analyst.get("implied_upside_pct", 0.0) or 0.0)

    if is_etf_active:
        st.markdown(
            clean_html(f"""
            <div class="rm-glass-panel" style="border-color:rgba(255,107,0,0.40) !important;">
              <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                <div>
                  <span style="font-size:0.86rem;font-weight:800;color:#FF8533;"><i class="fa-solid fa-layer-group" style="margin-right:6px;"></i>ETF Basket Shield Active ({_html.escape(active_ticker)})</span>
                  <div style="font-size:0.76rem;color:#CBD5E1;margin-top:3px;">
                    Thematic ETF baskets bypass corporate balance-sheet &amp; single-name earnings traps with diversified constituent liquidity.
                  </div>
                </div>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.86rem;font-weight:800;color:#10B981;background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.35);padding:4px 12px;border-radius:9999px;">
                  ETF Basket &middot; {f_score_val:.1f}/100
                </span>
              </div>
            </div>
            """),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            clean_html(f"""
            <div class="rm-glass-panel">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="font-size:0.84rem;font-weight:800;color:#FF8533;"><i class="fa-solid fa-shield-halved" style="margin-right:6px;"></i>FMP Ultra Solvency Scorecard ({_html.escape(active_ticker)})</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:0.82rem;font-weight:800;color:{'#10B981' if f_score_val >= 62 else ('#F43F5E' if f_score_val < 46 else '#FB923C')};">{f_score_val:.1f} / 100</span>
              </div>
              <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;font-size:0.76rem;">
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">Altman Z / Piotroski</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#F8FAFC;margin-top:2px;">Z {altman_z:.2f} &bull; F {piotroski_f}/9</div>
                </div>
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">Liquidity / Leverage</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#F8FAFC;margin-top:2px;">CR {curr_ratio:.2f}x &bull; D/E {debt_eq:.2f}x</div>
                </div>
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">FCF Yield / Rev YoY</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:#F8FAFC;margin-top:2px;">{fcf_yield:.1f}% / {rev_yoy:+.1f}%</div>
                </div>
                <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:9px 11px;">
                  <div style="font-size:0.64rem;color:#94A3B8;text-transform:uppercase;">Analyst Consensus</div>
                  <div style="font-family:'JetBrains Mono',monospace;font-weight:800;color:{'#10B981' if an_upside >= 0 else '#F43F5E'};margin-top:2px;">${an_tgt:.2f} ({an_upside:+.1f}%)</div>
                </div>
              </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    active_float_data = cached_get_equity_float(active_ticker)
    st.markdown(clean_html(rbc.create_float_topology_card_html(active_ticker, active_float_data)), unsafe_allow_html=True)
    edu.render_edu_drawer(
        "fundamentals_float",
        live_ctx={
            "altman_z": altman_z,
            "piotroski_score": piotroski_f,
            "short_pct": active_float_data.get("short_pct", 0.0) if isinstance(active_float_data, dict) else 0.0,
            "is_etf": is_etf_active,
        },
    )

    st.markdown("<div style='font-size:0.84rem;font-weight:800;color:#E2E8F0;margin:12px 0 6px 0;'>Sector Bifurcation Matrix (Stretch vs. Quality)</div>", unsafe_allow_html=True)
    matrix_fig = rbc.create_rubberband_tension_matrix(ranked_by_conv, active_ticker=active_ticker)
    st.plotly_chart(matrix_fig, width="stretch", config={"displayModeBar": "hover", "displaylogo": False, "responsive": True})


# -------------------------------------------------------------------------
# TAB 3: MACRO & 13F WHALES
# -------------------------------------------------------------------------
with tab_macro:
    compass_data = cached_get_cross_asset_compass()
    econ_7_data = cached_get_macro_econ_7pillar_spider()
    sm_radar = cached_get_smart_money_radar()

    # Cross-Asset Rotation Compass
    st.markdown(
        clean_html(f"""
        <div class="rm-compass-hero-hdr">
          <div>
            <div class="rm-compass-title-grad">Cross-Asset Capital Rotation &amp; Liquidity Matrix</div>
            <div style="font-size:0.76rem;color:#CBD5E1;margin-top:3px;">{_html.escape(str(compass_data.get('rotation_summary', '')))}</div>
          </div>
          <div class="rm-compass-kpi-row">
            <div class="rm-glass-kpi-pill">
              <span class="rm-glass-kpi-lbl">Regime</span>
              <span class="rm-glass-kpi-val" style="color:#FF8533;">{_html.escape(str(compass_data.get('rotation_badge', 'ROTATION')))}</span>
            </div>
            <div class="rm-glass-kpi-pill">
              <span class="rm-glass-kpi-lbl">Risk vs Haven</span>
              <span class="rm-glass-kpi-val">{float(compass_data.get('risk_appetite_spread', 0.0)):+.2f}&sigma;</span>
            </div>
          </div>
        </div>
        """),
        unsafe_allow_html=True,
    )
    compass_fig = rbc.create_cross_asset_rotation_compass(compass_data, active_benchmark=benchmark_symbol, height=480)
    st.plotly_chart(compass_fig, width="stretch", config={"displayModeBar": False, "responsive": True})
    edu.render_edu_drawer(
        "cross_asset_macro",
        live_ctx={
            "rotation_badge": compass_data.get("rotation_badge", "MACRO ROTATION"),
            "smart_money_score": sm_radar.get("smart_money_score", 70.0),
        },
    )

    # 7-Pillar US Economic Spider + 6-Pillar Macro Impulse
    m_c1, m_c2 = st.columns(2, gap="medium")
    with m_c1:
        st.markdown("<div style='font-size:0.82rem;font-weight:800;color:#FF8533;margin-bottom:4px;'>7-Pillar US Economic Spider</div>", unsafe_allow_html=True)
        st.plotly_chart(rbc.create_macro_economic_7pillar_spider(econ_7_data), width="stretch", config={"displayModeBar": False, "responsive": True})
    with m_c2:
        st.markdown("<div style='font-size:0.82rem;font-weight:800;color:#FF8533;margin-bottom:4px;'>6-Pillar Macro Impulse</div>", unsafe_allow_html=True)
        st.plotly_chart(rbc.create_macro_6pillar_impulse_chart(radar_24_48), width="stretch", config={"displayModeBar": False, "responsive": True})

    # Smart Money 13F Whale & Insider Cluster Radar
    sm_score = float(sm_radar.get("smart_money_score", 70.0) or 70.0)
    insider_ratio = float(sm_radar.get("insider_intensity_ratio", 65.0) or 65.0)
    stealth_gems = sm_radar.get("stealth_gems", []) or []
    opra_sweeps = sm_radar.get("opra_sweeps", []) or []

    sm_col1, sm_col2 = st.columns([1.0, 1.8], gap="medium")
    with sm_col1:
        try:
            st.plotly_chart(rbc.create_smart_money_convergence_gauge(sm_score, insider_ratio), width="stretch", config={"displayModeBar": False, "responsive": True})
        except Exception:
            st.info(f"13F Whale Score: {sm_score:.0f}/100 | Insider: {insider_ratio:.0f}/100")
    with sm_col2:
        gems_cards = ""
        for g in stealth_gems[:4]:
            gems_cards += (
                f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:9px 11px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<b style="font-family:JetBrains Mono,monospace;color:#F8FAFC;">{_html.escape(str(g.get("symbol", "")))}</b>'
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.70rem;color:#FF8533;">{g.get("cluster_conviction", 80)}/100</span>'
                f'</div>'
                f'<div style="font-size:0.71rem;color:#94A3B8;margin-top:2px;">{_html.escape(str(g.get("signal_tag", "Insider Buy")))} &bull; ${float(g.get("price", 0.0)):.2f}</div>'
                f'</div>'
            )
        sweeps_cards = ""
        for sw in opra_sweeps[:4]:
            sw_side = str(sw.get("side", "CALL"))
            sw_col = "#10B981" if sw_side == "CALL" else "#F43F5E"
            sweeps_cards += (
                f'<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(255,255,255,0.07);border-radius:9px;padding:6px 10px;display:flex;justify-content:space-between;font-family:JetBrains Mono,monospace;font-size:0.72rem;">'
                f'<b style="color:#F8FAFC;">{_html.escape(str(sw.get("symbol", "")))} ${float(sw.get("strike", 0.0)):g}{_html.escape(sw_side[:1])}</b>'
                f'<span style="color:{sw_col};">{float(sw.get("ratio", 1.0)):.1f}x Vol/OI</span>'
                f'</div>'
            )
        st.markdown(
            clean_html(f"""
            <div class="rm-glass-panel" style="margin-bottom:0 !important;">
              <div style="font-size:0.78rem;font-weight:800;color:#FF8533;text-transform:uppercase;margin-bottom:8px;">Smart Money Stealth Gems &amp; OPRA Sweeps</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px;">{gems_cards}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">{sweeps_cards}</div>
            </div>
            """),
            unsafe_allow_html=True,
        )

    with st.expander("📡 ASUS GX10 Karpathy Wiki & Discovery Intel Bus", expanded=False):
        if st.checkbox("Load & Audit GX10 Intel Bus Signals", value=False, key="chk_load_gx10_bus"):
            ib_cands = cached_scan_intel_bus(st.session_state.moneyness_mode)
            for ib in ib_cands[:12]:
                st.markdown(
                    f"**{ib['symbol']}** · `{ib['track_name']}` · Wiki `{ib['wiki_score']}/100` · {ib['status_badge']} — _{ib['thesis_hook']}_"
                )


# -------------------------------------------------------------------------
# TAB 4: BACKTEST LOGS, AI ARBITER & PM AUDIT
# -------------------------------------------------------------------------
with tab_audit:
    @st.fragment
    def _render_tab_audit_fragment():
        st.markdown(
            f"<div style='font-size:0.84rem;font-weight:800;color:#FF8533;margin-bottom:6px;'>5-Year Empirical MFE/MAE Excursion Profile ({_html.escape(active_ticker)} · n={emp_n} · {emp_win_pct:.0f}% Win)</div>",
            unsafe_allow_html=True,
        )
        emp_exc_fig = rbc.create_empirical_excursion_profile_chart(active_ticker, metrics)
        st.plotly_chart(emp_exc_fig, width="stretch", config={"displayModeBar": False, "responsive": True})
        edu.render_edu_drawer(
            "ev_kelly_backtest",
            live_ctx={
                "net_ev_pct": quant_edge.get("net_ev_pct", 0.0),
                "bayesian_win_prob_pct": quant_edge.get("bayesian_win_prob_pct", emp_win_pct),
                "empirical_win_rate_pct": emp_win_pct,
                "quarter_kelly_pct": quant_edge.get("quarter_kelly_pct", 0.0),
                "spread_friction_pct": (skew_opt.get("spread_friction_pct") if isinstance(skew_opt, dict) else None) or quant_edge.get("spread_friction_pct", 6.0),
                "edge_t_stat": quant_edge.get("edge_t_stat", 0.0),
            },
        )

        if ranked_by_conv:
            tbl_rows = []
            for r_i, c in enumerate(ranked_by_conv, start=1):
                cm = c.get("metrics", {})
                cbp = c.get("blueprint", {})
                cqe = c.get("quant_edge") or cm.get("quant_edge") or {}
                ctel = c.get("options_telemetry") or cm.get("options_telemetry") or {}
                tbl_rows.append({
                    "Rank": f"#{r_i}",
                    "Ticker": c["symbol"],
                    "Conviction (-200..+200)": int(c.get("conviction_score_200", cbp.get("conviction_score_200", 0))),
                    "Tier": c.get("conviction_tier", cbp.get("conviction_tier", "WATCH")),
                    "DTE": f"{int(c.get('recommended_dte', cbp.get('recommended_dte', 35)))}D",
                    "Structure": "SPREAD" if ctel.get("prefer_spread") else "NAKED",
                    "VRP (v)": f"{float(ctel.get('vrp_vol_pts', 0.0)):+.1f}",
                    "Playbook": cm.get("playbook", "EQUILIBRIUM"),
                    "Price": f"${float(cm.get('price', 0.0)):.2f}",
                    "5D Net EV": f"{float(cqe.get('net_ev_pct', 0.0)):+.1f}%",
                    "5Y MFE / MAE": f"{float(cm.get('expected_up_basis_pct', 0.0)):+.1f}% / {float(cm.get('expected_down_basis_pct', 0.0)):+.1f}%",
                    "Dual Z": f"{float(cm.get('z_score_5d', 0.0)):+.2f}σ",
                    "ER Days": "ETF" if c.get("is_etf") else f"{int(cm.get('days_to_earnings', 45))}d",
                })
            st.dataframe(pd.DataFrame(tbl_rows), width="stretch", hide_index=True)

        st.markdown("---")
        st.markdown(f"#### <i class='fa-solid fa-brain' style='color:#FF6B00;'></i> {_html.escape(active_model_name)} Trade Arbiter ({_html.escape(active_ticker)})", unsafe_allow_html=True)
        arb_cols = st.columns(5, gap="small")
        arb_modes = [
            ("Trade Thesis", "thesis"),
            ("Moat", "karpathy_moat"),
            ("Red Team Audit", "red_team"),
            ("Catalyst & IV", "catalyst"),
            ("200-DMA Macro", "confluence"),
        ]
        chosen_arb_mode = None
        for a_col, (a_lbl, a_code) in zip(arb_cols, arb_modes):
            with a_col:
                if st.button(a_lbl, key=f"arb_btn_{a_code}_{active_ticker}", width="stretch"):
                    chosen_arb_mode = a_code

        if chosen_arb_mode:
            with st.spinner(f"{active_model_name} running {chosen_arb_mode.upper()} audit on {active_ticker}..."):
                news_items = rbe3.get_recent_news(active_ticker, limit=5)
                payload_arb = {
                    "ticker": active_ticker,
                    "metrics": metrics,
                    "fundamentals": fundamentals,
                    "news": news_items,
                    "days_to_earnings": days_to_er,
                    "earnings_date": er_date_str,
                    "profile": {"companyName": company_name, "image": company_logo, "description": active_cand.get("description", "")},
                }
                st.session_state[f"active_audit_result_{active_ticker}"] = rba.generate_options_thesis(
                    payload_arb, st.session_state.selected_sector, benchmark_symbol, mode=chosen_arb_mode
                )

        if st.session_state.get(f"active_audit_result_{active_ticker}"):
            with st.container(border=True):
                st.markdown(str(st.session_state[f"active_audit_result_{active_ticker}"]))

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_q = st.chat_input(f"Ask {active_model_name} about {active_ticker}'s {effective_dte}-DTE High-Delta setup, catalysts, or risks...")
        if user_q:
            st.session_state.chat_history.append({"role": "user", "content": user_q})
            with st.chat_message("assistant"):
                with st.spinner(f"{active_model_name} evaluating..."):
                    ctx_prefix = (
                        f"[Ticker: {active_ticker}, Conviction: {score_200:+d}/±200 ({conv_tier}), "
                        f"DTE: {effective_dte}D, Dual Z: {z_val:+.2f}σ, O-U τ½: {ou_hl:.1f}d, Regime: {reg_label}] "
                    )
                    ans = st.session_state.agent_session.query(ctx_prefix + user_q, st.session_state.chat_history[:-1])
                    st.markdown(ans.get("text", ""))
                    st.session_state.chat_history.append({"role": "assistant", "content": ans.get("text", "")})
                    st.rerun(scope="fragment")

        with st.expander("🏛️ PM Keep / Tab / 86 Audit", expanded=False):
            st.markdown(
                """
                - **KEPT ON MAIN COCKPIT (ABOVE THE FOLD)**: Single Macro Symbolism HUD Strip (Regime, VIX Term, Credit Z, 10Y, SPY/QQQ Tape, Exposure Cap, 30/45 DTE tag); Unified 5-Trading-Day Circular Catalyst Ring Bento + collapsible SEC 8-K / Fed & Macro / FMP News Wire; High-Delta 30-45 DTE Scanner Matrix sorted by `|Conviction Score|` (`-200..+200`) with VRP, Hit Rate, Naked/Spread & ER pills; Active Setup Telemetry + 5-Pillar Orthogonal Breakdown + O-U Envelope & Conviction Gauge + Trade Ticket with `⚡ Arm Order in Schwab Simulator`.
                - **MOVED TO 4 SECONDARY TABS**: `Options Surface & Convexity` (`@st.fragment`: GEX/Vanna/Charm + Gamma Flip, 25D SVI Skew + Carry/Borrow, Hold/IV Scrubber, Strike Dot Matrix, SVI Smile & Term Structure, 5×4 P&L Matrix); `Deep Fundamentals & Float` (FMP Solvency + ETF Basket Shield, Float Topology, Bifurcation Matrix); `Macro & 13F Whales` (Cross-Asset Compass, 7-Pillar Econ Spider, 6-Pillar Impulse, 13F Stealth Radar, GX10 Intel Bus); `Backtest Logs, AI Arbiter & PM Audit` (`@st.fragment`: 5Y MFE/MAE Profile, Ranked Screener DataFrame, Qwen/Gemini Arbiter & Chat).
                - **86'D (REMOVED)**: Random startup sector (`random.choice`) & `Shuffle Sector` button; duplicate `.rm-hud-bar` + Regime Diagnosis banner; `ZONE 1/2/3` headers & 6-way top Macro Flight Deck segmented control; redundant `3x2` `.rm-card` grid; repetitive `Plain-English Decoder` walls & bottom `Educational Synthesis` card.
                """
            )

    _render_tab_audit_fragment()
