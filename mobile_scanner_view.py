"""
Rubberband Man - Mobile Companion Experience for 1–5D Scanner & Options Desk
Obsidian Frosted-Glass + Rich Hyper-Orange (#FF6B00) Executive Workflow
with Circular 5-Day Catalyst Rings, -200..+200 Conviction Scores, 30/45 DTE High-Delta Contracts,
5 Expanded Sectors + Thematic ETF Quick-Filters, and 1-Tap Schwab Simulator Execution.
"""

import datetime
import html as _html
import inspect
import streamlit as st
from typing import Dict, Any, List, Optional, Tuple
import rubberband_charts as rbc
import rubberband_engine_v3 as rbe3

try:
    import ui_kit as _ui_kit
except Exception:
    _ui_kit = None

try:
    import edu_annotations as _edu
except Exception:
    _edu = None


@st.cache_data(ttl=300, show_spinner=False)
def _cached_mobile_hist_series(symbol: str):
    return rbe3.get_historical_series(symbol)


_FALLBACK_SECTOR_ALIASES = {
    "Nuclear & Next-Gen Energy": "Energy, Grid & Materials",
    "Nuclear Energy": "Energy, Grid & Materials",
    "Robotics & Automation": "Robotics & Autonomous",
    "Robotics": "Robotics & Autonomous",
    "Edge AI": "Edge AI & Next-Gen Compute",
}

_THEMATIC_ETF_CHIPS = ["REMX", "SRVR", "ROBO", "JEDI", "SMH", "URA", "QTUM", "IGV"]


def _esc(val: Any) -> str:
    return _html.escape(str(val if val is not None else ""), quote=True)


def _normalize_sector_safe(sec_name: str) -> str:
    raw = str(sec_name or "Semiconductors").strip()
    if hasattr(rbe3, "normalize_sector_name"):
        try:
            return rbe3.normalize_sector_name(raw)
        except Exception:
            pass
    mapped = _FALLBACK_SECTOR_ALIASES.get(raw, raw)
    sectors = getattr(rbe3, "SECTORS", {})
    if mapped in sectors:
        return mapped
    return next(iter(sectors.keys()), "Semiconductors")


def _inject_mobile_obsidian_css() -> None:
    st.markdown("""
    <style>
    .mob-mono {
        font-family: 'JetBrains Mono', monospace !important;
        font-variant-numeric: tabular-nums !important;
    }
    .rm-mobile-hero-card,
    .rm-mobile-cand-card,
    .mob-glass-card {
        background: rgba(15, 18, 26, 0.68) !important;
        backdrop-filter: blur(20px) saturate(145%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(145%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 18px !important;
        box-shadow: 0 14px 36px -10px rgba(0, 0, 0, 0.72), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    }
    .rm-mobile-hero-card {
        padding: 18px 18px !important;
        margin-bottom: 14px !important;
        border-color: rgba(255, 107, 0, 0.34) !important;
    }
    .rm-mobile-play-box {
        background: rgba(8, 10, 16, 0.68) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 12px 14px !important;
        margin: 12px 0 !important;
    }
    .mob-glass-card {
        padding: 12px 14px !important;
        margin-bottom: 12px !important;
        border-radius: 16px !important;
    }
    .mob-ring-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 4px;
        align-items: stretch;
        margin-top: 8px;
    }
    .mob-ring-grid .rm-day-card {
        min-width: 0 !important;
        padding: 6px 2px !important;
    }
    .mob-ring-grid svg {
        max-width: 44px !important;
        height: auto !important;
    }
    .mob-ring-cell {
        background: rgba(8, 10, 16, 0.55);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 6px 2px;
        text-align: center;
        min-width: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: space-between;
    }
    .mob-ring-cell.active {
        border-color: rgba(255, 107, 0, 0.45);
        background: rgba(255, 107, 0, 0.10);
    }
    </style>
    """, unsafe_allow_html=True)


def _extract_cand_conviction_and_dte(
    cand: Dict[str, Any],
    action: str = "",
) -> Tuple[int, str, int, str]:
    """Returns (score_200, tier, recommended_dte, dte_rationale)."""
    cand = cand or {}
    m = cand.get("metrics", {}) or {}
    bp = cand.get("blueprint", {}) or {}

    raw_s200 = bp.get("conviction_score_200")
    if raw_s200 is None:
        raw_s200 = m.get("conviction_score_200")
    if raw_s200 is not None:
        s200 = int(round(float(raw_s200)))
    else:
        comp = float(bp.get("composite_score", 55.0) or 55.0)
        mag = int(round(max(0, min(200, (comp - 20.0) / 0.395))))
        s200 = -mag if "PUT" in str(action).upper() else mag

    abs_s = abs(s200)
    tier = str(
        bp.get("conviction_tier")
        or m.get("conviction_tier")
        or (
            "ASYMMETRIC CONVICTION" if abs_s >= 150
            else "HIGH CONVICTION" if abs_s >= 110
            else "TACTICAL EDGE" if abs_s >= 70
            else "WATCH / DEVELOPING" if abs_s >= 36
            else "NEUTRAL / NOISE"
        )
    )

    rec_dte_raw = bp.get("recommended_dte") or m.get("recommended_dte") or 35
    try:
        rec_dte = 45 if int(rec_dte_raw) >= 38 else 30
    except Exception:
        rec_dte = 30
    dte_rat = str(
        bp.get("dte_rationale")
        or m.get("dte_rationale")
        or ("45D macro/catalyst cushion" if rec_dte == 45 else "30D High-Delta velocity")
    )
    return s200, tier, rec_dte, dte_rat


def _format_mobile_conv_pill(score_200: int, opt_dir: str = "") -> str:
    if _ui_kit is not None and hasattr(_ui_kit, "format_conviction_200_badge"):
        try:
            return _ui_kit.format_conviction_200_badge(int(score_200), opt_dir)
        except Exception:
            pass
    abs_s = abs(int(score_200))
    d = _esc(opt_dir or ("CALL" if score_200 >= 0 else "PUT"))
    if abs_s >= 150:
        fg, bg, bdr = "#FF8533", "rgba(255, 107, 0, 0.18)", "rgba(255, 107, 0, 0.48)"
    elif abs_s >= 110:
        fg = "#34D399" if score_200 >= 0 else "#FB7185"
        bg = "rgba(16, 185, 129, 0.16)" if score_200 >= 0 else "rgba(244, 63, 94, 0.16)"
        bdr = "rgba(16, 185, 129, 0.42)" if score_200 >= 0 else "rgba(244, 63, 94, 0.42)"
    else:
        fg, bg, bdr = "#FBBF24", "rgba(245, 158, 11, 0.14)", "rgba(245, 158, 11, 0.36)"
    return (
        f'<span class="mob-mono" style="background:{bg}; color:{fg}; border:1px solid {bdr}; '
        f'font-size:0.72rem; font-weight:800; padding:3px 9px; border-radius:9999px; white-space:nowrap;">'
        f'{int(score_200):+d} {d}</span>'
    )


def _render_ring_svg(pct: int, label: str, sub: str, is_active: bool = False, tone_hex: str = "#FF6B00") -> str:
    """Uses ui_kit.render_5day_ring_svg when compatible, else crisp inline SVG ring."""
    if _ui_kit is not None and hasattr(_ui_kit, "render_5day_ring_svg"):
        try:
            sig = inspect.signature(_ui_kit.render_5day_ring_svg)
            if len(sig.parameters) >= 4:
                return _ui_kit.render_5day_ring_svg(pct, label, sub, is_active=is_active, tone_hex=tone_hex)
        except Exception:
            pass

    clamped = max(6, min(100, int(pct)))
    radius = 20.0
    circum = 2.0 * 3.14159265 * radius
    offset = circum * (1.0 - clamped / 100.0)
    safe_tone = tone_hex if (isinstance(tone_hex, str) and tone_hex.startswith("#") and len(tone_hex) in (4, 7)) else "#FF6B00"
    stroke_col = "#FF6B00" if is_active else safe_tone
    return (
        f'<div class="mob-ring-cell {"active" if is_active else ""}">'
        f'<div style="font-size:0.62rem; font-weight:800; color:{"#FF8533" if is_active else "#94A3B8"}; text-transform:uppercase;">{_esc(label)}</div>'
        f'<svg width="44" height="44" viewBox="0 0 52 52" style="margin:3px 0;">'
        f'<circle cx="26" cy="26" r="{radius}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="4.5"/>'
        f'<circle cx="26" cy="26" r="{radius}" fill="none" stroke="{stroke_col}" stroke-width="4.5" '
        f'stroke-linecap="round" stroke-dasharray="{circum:.2f}" stroke-dashoffset="{offset:.2f}" '
        f'transform="rotate(-90 26 26)"/>'
        f'<text x="26" y="30" text-anchor="middle" fill="#F1F5F9" font-family="JetBrains Mono, monospace" font-size="11" font-weight="800">{clamped}%</text>'
        f'</svg>'
        f'<div style="font-size:0.60rem; color:#CBD5E1; font-weight:600; line-height:1.15; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{_esc(sub)}</div>'
        f'</div>'
    )


def _get_5day_catalyst_safe(sector_name: str, active_ticker: str, radar_24_48: Dict[str, Any], catalyst_outlook: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Resolves 5-day catalyst outlook safely with fallback if engine function is absent."""
    if isinstance(catalyst_outlook, dict) and catalyst_outlook.get("days"):
        return catalyst_outlook
    if hasattr(rbe3, "get_unified_5day_catalyst_outlook"):
        try:
            res = rbe3.get_unified_5day_catalyst_outlook(sector_name, active_ticker)
            if isinstance(res, dict) and res.get("days"):
                return res
        except Exception:
            pass

    days = []
    d_cursor = rbe3.get_ny_now().date() if hasattr(rbe3, "get_ny_now") else datetime.date.today()
    while len(days) < 5:
        if d_cursor.weekday() < 5:
            is_today = (len(days) == 0)
            days.append({
                "date": d_cursor.isoformat(),
                "day_short": d_cursor.strftime("%a").upper(),
                "day_num": d_cursor.strftime("%d"),
                "is_today": is_today,
                "intensity_pct": 72 if is_today else max(28, 65 - len(days) * 9),
                "risk_tone": "ELEVATED" if is_today else "BALANCED",
                "event_count": 2 if is_today else 1,
                "headline_tag": str(radar_24_48.get("signage_title", "TAPE FLOW"))[:14] if is_today else "MACRO",
                "events": [],
            })
        d_cursor += datetime.timedelta(days=1)
    return {
        "directional_bias": "CONSTRUCTIVE",
        "bias_score": 18,
        "binary_risk_level": "MODERATE",
        "recommended_dte": 30,
        "dte_rationale": "Standard 30D High-Delta setup",
        "days": days,
        "sec_8k_filings": [],
        "fed_and_macro_events": [],
        "sector_news": [],
    }


def render_mobile_scanner_page(
    active_cand: Dict[str, Any],
    active_ticker: str,
    benchmark_symbol: str,
    ranked_sector_candidates: List[Dict[str, Any]],
    macro_pulse: Dict[str, Any],
    radar_24_48: Dict[str, Any],
    sm_radar: Dict[str, Any],
    cur_spal: Dict[str, str],
    cached_get_near_live_option,
    catalyst_outlook: Optional[Dict[str, Any]] = None
) -> None:
    """Renders the Obsidian Frosted-Glass Mobile Companion deck for the 1–5D Scanner & Options Desk."""
    _inject_mobile_obsidian_css()

    active_cand = active_cand or {}
    metrics = active_cand.get("metrics", {}) or {}
    fundamentals = active_cand.get("fundamentals", {}) or {}
    company_name = str(active_cand.get("company_name", active_ticker) or active_ticker)
    curr_price = float(metrics.get("price", 0.0) or 0.0)
    z_val = float(metrics.get("z_score_5d", 0.0) or 0.0)
    action = str(metrics.get("action", "MONITOR"))
    target_strike = float(metrics.get("recommended_strike", curr_price) or curr_price)
    exp_basis_pct = float(metrics.get("expected_basis_pct", 0.0) or 0.0)
    emp_win_pct = float(metrics.get("empirical_win_rate_pct", 55.0) or 55.0)
    ou_hl = float(metrics.get("ou_half_life", 5.0) or 5.0)
    playbook_name = str(metrics.get("playbook", "EQUILIBRIUM REVERSION"))
    whale_score = float(metrics.get("whale_score", 0.0) or 0.0)
    tgt_p = float(metrics.get("target_price", curr_price * 1.06) or curr_price * 1.06)
    inv_p = float(metrics.get("invalidation_price", curr_price * 0.95) or curr_price * 0.95)

    tape_conv = float(macro_pulse.get("tape_conviction_score", 50.0) or 50.0)
    regime_badge = str(macro_pulse.get("market_regime_badge", "TAPE REGIME"))
    spy_ret = float(macro_pulse.get("spy_change", 0.0) or 0.0)
    spy_rvol = float(macro_pulse.get("spy_rvol", 1.0) or 1.0)

    is_etf = bool(fundamentals.get("is_etf") or active_ticker in set(getattr(rbe3, "THEMATIC_ETFS", set())) | set(_THEMATIC_ETF_CHIPS))

    score_200, conv_tier, rec_dte, dte_rat = _extract_cand_conviction_and_dte(active_cand, action)

    # Fetch 30 vs 45 DTE High-Delta option
    near_opt = metrics.get("near_live_option")
    if not near_opt or abs(int(near_opt.get("dte", rec_dte)) - rec_dte) > 12:
        near_opt = cached_get_near_live_option(
            active_ticker,
            action,
            target_strike,
            target_dte=rec_dte
        )

    near_opt = near_opt or {}
    opt_exp = str(near_opt.get("expiry", near_opt.get("expiration", f"{rec_dte} DTE")))
    opt_dte = int(near_opt.get("dte", rec_dte) if near_opt.get("dte") is not None else rec_dte)
    opt_mid = float(near_opt.get("mid", 3.20) or 3.20)
    opt_strike = float(near_opt.get("strike", target_strike) or target_strike)
    opt_delta = float(near_opt.get("delta", metrics.get("estimated_delta", 0.50 if "CALL" in action else -0.50)) or 0.50)
    opt_be = float(near_opt.get("breakeven", opt_strike + opt_mid if "CALL" in action else opt_strike - opt_mid))
    opt_cost = opt_mid * 100.0
    is_high_delta = (0.40 <= abs(opt_delta) <= 0.65)

    is_call = "CALL" in action.upper()
    act_col = "#34D399" if is_call else ("#FB7185" if "PUT" in action.upper() else "#FBBF24")
    act_badge_bg = "rgba(16, 185, 129, 0.16)" if is_call else ("rgba(244, 63, 94, 0.16)" if "PUT" in action.upper() else "rgba(245, 158, 11, 0.16)")
    act_bdr = "rgba(16, 185, 129, 0.42)" if is_call else ("rgba(244, 63, 94, 0.42)" if "PUT" in action.upper() else "rgba(245, 158, 11, 0.42)")
    z_col_mob = "#34D399" if z_val <= -1.55 else ("#FB7185" if z_val >= 1.55 else "#FBBF24")
    win_col_mob = "#34D399" if emp_win_pct >= 60 else ("#FB7185" if emp_win_pct < 50 else "#FBBF24")
    hl_col_mob = "#34D399" if ou_hl <= 4.5 else ("#FB7185" if ou_hl > 7.5 else "#FBBF24")
    wh_col_mob = "#34D399" if whale_score >= 10 else ("#FB7185" if whale_score <= -10 else "#FBBF24")

    # 1. EXPANDED 5-SECTOR & THEMATIC ETF SWITCHER
    st.markdown("<div style='font-size: 0.72rem; font-weight: 800; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px;'>Active Sector &amp; ETF Fast Switcher</div>", unsafe_allow_html=True)

    sec_list = list(getattr(rbe3, "SECTORS", {}).keys()) or [
        "Semiconductors",
        "AI Infrastructure",
        "Energy, Grid & Materials",
        "Robotics & Autonomous",
        "Edge AI & Next-Gen Compute",
    ]
    curr_sec = _normalize_sector_safe(st.session_state.get("selected_sector", sec_list[0]))
    if curr_sec != st.session_state.get("selected_sector"):
        st.session_state.selected_sector = curr_sec

    col_sec, col_tk = st.columns([1.6, 1.4], gap="small")
    with col_sec:
        curr_sec_idx = sec_list.index(curr_sec) if curr_sec in sec_list else 0
        new_sec = st.selectbox(
            "Sector",
            options=sec_list,
            index=curr_sec_idx,
            key="mobile_sec_select",
            label_visibility="collapsed"
        )
        if new_sec != curr_sec:
            st.session_state.selected_sector = new_sec
            st.session_state.benchmark_override = rbe3.SECTORS[new_sec]["benchmark"]
            sec_cands = rbe3.SECTORS.get(new_sec, {}).get("tickers", [])
            if sec_cands:
                st.session_state.selected_ticker = sec_cands[0]
            st.rerun()

    with col_tk:
        def _on_mobile_quick_search() -> None:
            raw = str(st.session_state.get("mobile_quick_search_input", "") or "").strip().upper()
            clean_sym = "".join(ch for ch in raw if ch.isalnum() or ch in (".", "-", "^"))[:10]
            if clean_sym:
                st.session_state.selected_ticker = clean_sym
                try:
                    st.query_params["ticker"] = clean_sym
                except Exception:
                    pass
            st.session_state["mobile_quick_search_input"] = ""

        st.text_input(
            "Quick Ticker",
            placeholder=f"🔍 e.g. {active_ticker}",
            key="mobile_quick_search_input",
            label_visibility="collapsed",
            on_change=_on_mobile_quick_search,
        )

    # Compact Thematic ETF Horizontal Pill Rail (Zero Vertical Stacking)
    def _on_mob_etf_pick() -> None:
        picked = st.session_state.get("mob_etf_pills")
        cur_tk = st.session_state.get("selected_ticker")
        if picked and picked != cur_tk:
            st.session_state.selected_ticker = picked
            st.session_state["_mob_pills_synced_tk"] = picked
        elif picked is None and cur_tk in _THEMATIC_ETF_CHIPS:
            st.session_state["mob_etf_pills"] = cur_tk

    top5_labels: List[str] = []
    top5_map: Dict[str, str] = {}
    top5_default: Optional[str] = None
    if ranked_sector_candidates:
        for c in ranked_sector_candidates[:5]:
            c_sym = str(c.get("symbol", "")).strip()
            c_act = str((c.get("metrics") or {}).get("action", ""))
            c_s200, _, _, _ = _extract_cand_conviction_and_dte(c, c_act)
            lbl = f"{c_sym} {c_s200:+d}"
            top5_labels.append(lbl)
            top5_map[lbl] = c_sym
            if c_sym == active_ticker:
                top5_default = lbl

    def _on_mob_top5_pick() -> None:
        picked_lbl = st.session_state.get("mob_top5_pills")
        picked_sym = top5_map.get(picked_lbl) if picked_lbl else None
        cur_tk = st.session_state.get("selected_ticker")
        if picked_sym and picked_sym != cur_tk:
            st.session_state.selected_ticker = picked_sym
            st.session_state["_mob_pills_synced_tk"] = picked_sym
        elif picked_lbl is None and cur_tk in top5_map.values():
            st.session_state["mob_top5_pills"] = next((k for k, v in top5_map.items() if v == cur_tk), None)

    etf_default = active_ticker if active_ticker in _THEMATIC_ETF_CHIPS else None
    if st.session_state.get("_mob_pills_synced_tk") != active_ticker:
        st.session_state["mob_etf_pills"] = etf_default
        st.session_state["mob_top5_pills"] = top5_default
        st.session_state["_mob_pills_synced_tk"] = active_ticker

    st.pills(
        "Thematic ETFs",
        options=_THEMATIC_ETF_CHIPS,
        selection_mode="single",
        key="mob_etf_pills",
        on_change=_on_mob_etf_pick,
        label_visibility="collapsed",
    )

    if top5_labels:
        st.pills(
            "Sector Top-5",
            options=top5_labels,
            selection_mode="single",
            key="mob_top5_pills",
            on_change=_on_mob_top5_pick,
            label_visibility="collapsed",
        )

    # 2. CIRCULAR 5-DAY CATALYST RING STRIP (FROSTED GLASS)
    cat_data = _get_5day_catalyst_safe(curr_sec, active_ticker, radar_24_48, catalyst_outlook)
    cat_bias = str(cat_data.get("directional_bias", "NEUTRAL"))
    cat_risk = str(cat_data.get("binary_risk_level", "MODERATE"))
    cat_dte = int(cat_data.get("recommended_dte", rec_dte) or rec_dte)
    days_list = (cat_data.get("days") or [])[:5]

    rings_html = "".join(
        _render_ring_svg(
            pct=int(d.get("intensity_pct", 50) or 50),
            label=f"{d.get('day_short', '')} {d.get('day_num', '')}".strip(),
            sub=str(d.get("headline_tag", "FLOW"))[:10],
            is_active=bool(d.get("is_today", False)),
            tone_hex="#FF6B00" if d.get("risk_tone") in ("HIGH", "BINARY") else ("#34D399" if d.get("risk_tone") == "CLEAR" else "#FBBF24"),
        )
        for d in days_list
    )

    st.markdown(f"""
    <div class="mob-glass-card">
        <div style="display: flex; justify-content: space-between; align-items: center; gap: 6px; flex-wrap: wrap;">
            <span style="font-size: 0.70rem; font-weight: 800; color: #FF8533; text-transform: uppercase; letter-spacing: 0.05em;">
                <i class="fa-solid fa-calendar-week fa-icon-inline"></i> 5-Day Catalyst Rings
            </span>
            <div style="display: flex; gap: 5px; align-items: center;">
                <span style="font-size: 0.65rem; font-weight: 800; color: #CBD5E1; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.10); padding: 2px 7px; border-radius: 9999px;">{_esc(cat_bias)}</span>
                <span class="mob-mono" style="font-size: 0.65rem; font-weight: 800; color: #FF8533; background: rgba(255,107,0,0.14); border: 1px solid rgba(255,107,0,0.38); padding: 2px 7px; border-radius: 9999px;">{cat_dte}D POSTURE</span>
            </div>
        </div>
        <div class="mob-ring-grid">{rings_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # 3. HERO ACTIVE CANDIDATE CARD (OBSIDIAN FROSTED-GLASS + -200..+200 + 30/45D HIGH-DELTA)
    conv_pill_html = _format_mobile_conv_pill(score_200, "CALL" if is_call else ("PUT" if "PUT" in action.upper() else ""))
    etf_tag = '<span style="background: rgba(255,107,0,0.15); color: #FF8533; border: 1px solid rgba(255,107,0,0.38); font-size: 0.64rem; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">ETF</span>' if is_etf else ""
    dte_bucket_lbl = "45D SWING" if rec_dte >= 38 else "30D TACTICAL"
    delta_mode_pill = (
        '<span style="background: rgba(16,185,129,0.16); color: #34D399; border: 1px solid rgba(16,185,129,0.38); font-size: 0.64rem; font-weight: 800; padding: 2px 6px; border-radius: 9999px;">HIGH-DELTA</span>'
        if is_high_delta else ""
    )

    _hero_html = "".join(line.strip() for line in f"""
    <div class="rm-mobile-hero-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 10px;">
            <div>
                <div style="display: flex; align-items: center; gap: 7px; flex-wrap: wrap;">
                    <span class="mob-mono" style="font-size: 1.55rem; font-weight: 900; color: #F1F5F9; letter-spacing: -0.02em;">
                        {_esc(active_ticker)}
                    </span>
                    {etf_tag}
                    <span style="font-size: 0.74rem; color: #94A3B8; font-weight: 600;">
                        {_esc(company_name[:22])}
                    </span>
                </div>
                <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 3px;">
                    <span class="mob-mono" style="font-size: 1.15rem; font-weight: 800; color: #F1F5F9;">
                        ${curr_price:.2f}
                    </span>
                    <span style="font-size: 0.72rem; color: #94A3B8;">
                        Bench: <b>{_esc(benchmark_symbol)}</b>
                    </span>
                </div>
            </div>
            <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 5px;">
                <span style="background: {act_badge_bg}; color: {act_col}; border: 1px solid {act_bdr}; font-size: 0.72rem; font-weight: 900; padding: 3px 10px; border-radius: 9999px; letter-spacing: 0.04em;">
                    {_esc(action)}
                </span>
                {conv_pill_html}
                <div class="mob-mono" style="font-size: 0.70rem; color: {z_col_mob}; font-weight: 700;">
                    {z_val:+.2f}&sigma; STRETCH &bull; {_esc(conv_tier[:14])}
                </div>
            </div>
        </div>
        <div class="rm-mobile-play-box">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 6px; flex-wrap: wrap; gap: 4px;">
                <span style="font-size: 0.70rem; font-weight: 800; color: #FF8533; text-transform: uppercase; letter-spacing: 0.05em;">
                    <i class="fa-solid fa-bolt fa-icon-inline"></i> {dte_bucket_lbl} ({opt_dte}d)
                </span>
                <div style="display: flex; align-items: center; gap: 5px;">
                    {delta_mode_pill}
                    <span class="mob-mono" style="font-size: 0.70rem; color: #CBD5E1;">Exp: {_esc(opt_exp)}</span>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                <span class="mob-mono" style="font-size: 1.05rem; font-weight: 800; color: #F1F5F9;">
                    ${opt_strike:.2f} {_esc(action.split()[-1] if ' ' in action else action)}
                </span>
                <span class="mob-mono" style="font-size: 1.05rem; font-weight: 800; color: #34D399;">
                    ${opt_mid:.2f} <span style="font-size: 0.70rem; color: #94A3B8;">(${opt_cost:.0f}/ct)</span>
                </span>
            </div>
            <div class="mob-mono" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; font-size: 0.70rem; color: #94A3B8; text-align: center; background: rgba(0,0,0,0.28); border-radius: 8px; padding: 6px 4px;">
                <div>Delta: <b style="color: {'#34D399' if 0.40 <= abs(opt_delta) <= 0.65 else '#FBBF24'};">{opt_delta:+.2f}</b></div>
                <div>BE: <b style="color: #F1F5F9;">${opt_be:.2f}</b></div>
                <div>Risk: <b style="color: #FB7185;">${opt_cost:.0f}</b></div>
            </div>
        </div>
        <div class="mob-mono" style="display: flex; justify-content: space-between; align-items: center; font-size: 0.70rem; color: #94A3B8;">
            <span><i class="fa-solid fa-trophy fa-icon-inline" style="color: {win_col_mob};"></i> 5Y Win: <b style="color: {win_col_mob};">{emp_win_pct:.0f}%</b></span>
            <span><i class="fa-solid fa-clock fa-icon-inline" style="color: {hl_col_mob};"></i> &tau;&frac12;: <b style="color: {hl_col_mob};">{ou_hl:.1f}d</b></span>
            <span><i class="fa-solid fa-shield fa-icon-inline" style="color: {wh_col_mob};"></i> 13F: <b style="color: {wh_col_mob};">{whale_score:+.0f}</b></span>
        </div>
    </div>
    """.splitlines())
    st.markdown(_hero_html, unsafe_allow_html=True)

    # RESTRAINED ACTION CTA + LOW-PROFILE ◈ HERO LEARN CHIP
    col_cta, col_learn = st.columns([1.35, 1.15], gap="small", vertical_alignment="center")
    with col_cta:
        if st.button("⚡ Simulate in Schwab", key=f"mobile_btn_sim_schwab_{active_ticker}", type="primary", width="stretch"):
            mob_dte = opt_dte or rec_dte
            if opt_exp and len(str(opt_exp)) >= 10:
                try:
                    exp_dt = datetime.date.fromisoformat(str(opt_exp)[:10])
                    today_ny = rbe3.get_ny_now().date() if hasattr(rbe3, "get_ny_now") else datetime.date.today()
                    mob_dte = max(1, (exp_dt - today_ny).days)
                except Exception:
                    pass
            st.session_state["schwab_prefill"] = {
                "symbol": active_ticker,
                "action": "BUY_TO_OPEN",
                "option_type": "CALL" if is_call else "PUT",
                "strike": opt_strike,
                "expiration": opt_exp,
                "expiration_date": opt_exp,
                "dte": mob_dte,
                "recommended_dte": rec_dte,
                "dte_rationale": dte_rat,
                "conviction_score_200": score_200,
                "conviction_score": score_200,
                "contracts": 1,
                "order_type": "LIMIT",
                "limit_price": opt_mid,
                "current_mid": opt_mid,
                "spot_price": curr_price,
                "current_stock_price": curr_price,
                "target_price": tgt_p,
                "stop_price": inv_p,
                "notes": f"Mobile 1-Tap Signal: {action} on {active_ticker} ({playbook_name} | Conv {score_200:+d} | {z_val:+.2f}σ). Target Exp: {opt_exp}."
            }
            if "schwab_active_leg" in st.session_state:
                del st.session_state["schwab_active_leg"]
            st.session_state["schwab_prefill_needs_sync"] = True
            st.session_state["pending_workspace_view"] = "Charles Schwab Practice Desk & Diary"
            st.session_state["active_app_view"] = "Charles Schwab Practice Desk & Diary"
            st.session_state["mobile_workspace_nav_select_top"] = "Charles Schwab Practice Desk & Diary"
            try:
                st.query_params["page"] = "schwab"
            except Exception:
                pass
            st.rerun()
    with col_learn:
        if _edu is not None:
            _edu.render_edu_drawer(
                "mobile_hero",
                {
                    "symbol": active_ticker,
                    "z_score_5d": z_val,
                    "ou_half_life": ou_hl,
                    "conviction_score_200": score_200,
                    "contract_cost": opt_cost,
                    "breakeven": opt_be,
                },
                compact=True,
                align="right",
            )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 4. MOBILE TABBED EXPLORATION
    m_tab_chart, m_tab_cands, m_tab_greeks, m_tab_radar = st.tabs([
        "📈 Chart",
        "🎯 Sector Top-5",
        "⚡ Greeks & Payoff",
        "🏛️ Catalysts & Whales"
    ])

    with m_tab_chart:
        st.markdown(f"<div style='font-size: 0.74rem; font-weight: 700; color: #94A3B8; margin-bottom: 6px;'>{_esc(active_ticker)} Elasticity Channel &amp; 5D Projection Cone</div>", unsafe_allow_html=True)
        try:
            t_series = _cached_mobile_hist_series(active_ticker)
            chart_fig = rbc.create_rubberband_envelope_visual(active_ticker, metrics, t_series)
            chart_fig.update_layout(
                height=300,
                margin=dict(l=8, r=8, t=18, b=24),
                showlegend=False,
                autosize=True,
            )
            st.plotly_chart(chart_fig, width="stretch", config={"displayModeBar": False, "responsive": True})
        except Exception:
            st.info(f"Chart temporarily syncing for {active_ticker}...")

        st.caption("Orange: VWMA-20 · Green/Red Bands: ±2σ Stretch · Cone: 5D Projection.")

        _mob_gw = active_cand.get("gamma_walls") or metrics.get("gamma_walls") or {}
        _mob_telem = active_cand.get("options_telemetry") or metrics.get("options_telemetry") or {}
        if hasattr(rbc, "create_trade_anatomy_visual"):
            try:
                anatomy_fig = rbc.create_trade_anatomy_visual(
                    active_ticker,
                    metrics,
                    opt_telem=_mob_telem,
                    gamma_walls=_mob_gw,
                    near_opt=near_opt,
                    height=245,
                )
                st.plotly_chart(anatomy_fig, width="stretch", config={"displayModeBar": False, "responsive": True})
                if _edu is not None:
                    _edu.render_edu_drawer(
                        "trade_anatomy",
                        {
                            "symbol": active_ticker,
                            "spot": curr_price,
                            "vwma20": metrics.get("vwma20", curr_price),
                            "strike": opt_strike,
                            "breakeven": opt_be,
                            "target_price": tgt_p,
                            "stop_price": inv_p,
                            "call_wall": _mob_gw.get("call_wall_strike", 0.0),
                            "put_wall": _mob_gw.get("put_wall_strike", 0.0),
                            "gamma_flip": _mob_gw.get("gamma_flip_strike", 0.0),
                        },
                        compact=True,
                        align="right",
                    )
            except Exception:
                pass

    with m_tab_cands:
        st.markdown(f"<div style='font-size: 0.74rem; font-weight: 800; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px;'>Top Vetted &amp; Sector Candidates ({_esc(curr_sec)})</div>", unsafe_allow_html=True)
        for rank_idx, cand in enumerate(ranked_sector_candidates, start=1):
            c_m = cand.get("metrics", {}) or {}
            c_opt_t = cand.get("options_telemetry") or c_m.get("options_telemetry") or {}
            c_sym = str(cand.get("symbol", ""))
            c_name = str(cand.get("company_name", cand.get("name", c_sym)) or c_sym)
            c_p = float(c_m.get("price", cand.get("price", 0.0)) or 0.0)
            c_z = float(c_m.get("z_score_5d", cand.get("z_score_5d", 0.0)) or 0.0)
            c_exp = float(c_m.get("expected_basis_pct", 0.0) or 0.0)
            c_win = float(c_m.get("empirical_win_rate_pct", 55.0) or 55.0)
            c_whale = str(c_m.get("whale_badge", "FLOW"))
            c_vega = str(c_opt_t.get("vega_badge", "FAIR VEGA"))
            c_act = str(c_m.get("action", cand.get("rubberband_action", cand.get("action", "MONITOR"))))
            c_s200, _, c_dte_rec, _ = _extract_cand_conviction_and_dte(cand, c_act)
            is_top5 = bool(cand.get("is_top5_vetted", False))
            is_cur = (c_sym == active_ticker)

            c_bdr = "rgba(255, 107, 0, 0.55)" if is_cur else ("rgba(255, 133, 51, 0.34)" if is_top5 else "rgba(255, 255, 255, 0.08)")
            c_bg = "rgba(255, 107, 0, 0.10)" if is_cur else "rgba(15, 18, 26, 0.68)"
            c_act_col = "#34D399" if "CALL" in c_act else ("#FB7185" if "PUT" in c_act else "#FBBF24")
            c_z_col = "#34D399" if c_z <= -1.55 else ("#FB7185" if c_z >= 1.55 else "#FBBF24")
            top5_pill = "<span style='color:#FF8533; font-size:0.64rem; font-weight:800; margin-left:4px;'>★ TOP-5</span>" if is_top5 else ""

            col_c_info, col_c_btn = st.columns([2.35, 0.95], gap="small")
            with col_c_info:
                st.markdown(f"""
                <div style="background: {c_bg}; backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px); border: 1px solid {c_bdr}; border-radius: 14px; padding: 10px 12px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; gap: 6px;">
                        <span class="mob-mono" style="font-size: 0.92rem; font-weight: 800; color: #F1F5F9;">
                            #{rank_idx} {_esc(c_sym)} <span style="font-size: 0.68rem; color: #94A3B8; font-weight: 500;">{_esc(c_name[:12])}</span>{top5_pill}
                        </span>
                        <span class="mob-mono" style="font-size: 0.80rem; font-weight: 800; color: #F1F5F9;">
                            ${c_p:.2f} &middot; <span style="color:#FF8533;">{c_s200:+d}</span> &middot; <span style="color:#CBD5E1;">{c_dte_rec}D</span>
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px; font-size: 0.70rem;">
                        <span style="color: {c_act_col}; font-weight: 800;">{_esc(c_act)} ({c_exp:+.1f}% | {c_win:.0f}% Win)</span>
                        <span class="mob-mono" style="color: {c_z_col}; font-weight: 700;">Z: {c_z:+.2f}&sigma;</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 3px; font-size: 0.66rem; color: #94A3B8;">
                        <span>{_esc(c_whale)}</span>
                        <span>{_esc(c_vega)}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col_c_btn:
                if not is_cur:
                    if st.button("Select", key=f"m_btn_pick_{c_sym}", width="stretch"):
                        st.session_state.selected_ticker = c_sym
                        st.rerun()
                else:
                    st.button("Active", key=f"m_btn_act_{c_sym}", disabled=True, width="stretch")

    with m_tab_greeks:
        st.markdown(f"<div style='font-size: 0.74rem; font-weight: 800; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px;'>Institutional Telemetry &amp; High-Delta Greeks ({_esc(active_ticker)})</div>", unsafe_allow_html=True)
        mob_opt_telem = active_cand.get("options_telemetry") or metrics.get("options_telemetry") or rbe3.calculate_options_volatility_and_spread_telemetry(
            active_ticker, metrics, live_option=metrics.get("near_live_option"), dte=rec_dte, hold_days=5, iv_shift_pct=0.0
        )
        g1, g2 = st.columns(2, gap="small")
        with g1:
            st.metric("Conviction (-200..+200)", f"{score_200:+d}")
            st.metric("Expected Basis Gain", f"{exp_basis_pct:+.1f}%")
            st.metric("O-U Half-Life", f"{ou_hl:.1f} days")
            st.metric("5D Theta Drag ($1k)", f"-${abs(mob_opt_telem.get('theta_hold_dollar', 35.0)):.0f}")
        with g2:
            st.metric("Duration Posture", f"{rec_dte} DTE")
            st.metric("Empirical Win Rate", f"{emp_win_pct:.0f}%")
            st.metric("Day-5 Breakeven", f"${mob_opt_telem.get('breakeven_hold_price', opt_be):.2f}")
            st.metric("25Δ Skew", str(mob_opt_telem.get("skew_label", "NEUTRAL"))[:14])

        st.markdown(f"""
        <div class="mob-glass-card" style="border-color: rgba(255, 107, 0, 0.34); font-size: 0.74rem; color: #CBD5E1; line-height: 1.45;">
            <b style="color: #FF8533;">Optimal Structure ({_esc(mob_opt_telem.get('recommended_structure', f'{rec_dte}D HIGH-DELTA'))}):</b> {_esc(mob_opt_telem.get('vega_advice', dte_rat))}
        </div>
        """, unsafe_allow_html=True)

        if _edu is not None:
            _gw = active_cand.get("gamma_walls") or metrics.get("gamma_walls") or {}
            _edu.render_edu_drawer(
                "options_surface",
                {
                    "opra_iv": mob_opt_telem.get("iv_pct", 35.0),
                    "hv20": mob_opt_telem.get("hv20_pct", 35.0),
                    "net_gex_m": _gw.get("net_gex_m", 0.0),
                    "gamma_flip_strike": _gw.get("gamma_flip_strike", curr_price),
                    "net_vanna_m": _gw.get("net_vanna_m", 0.0),
                    "variance_rent_ratio": mob_opt_telem.get("variance_rent_ratio", 1.0),
                    "prefer_spread": mob_opt_telem.get("prefer_spread", False),
                },
                compact=True,
            )

    with m_tab_radar:
        st.markdown("<div style='font-size: 0.74rem; font-weight: 800; color: #94A3B8; text-transform: uppercase; margin-bottom: 8px;'>5-Day Catalysts, Macro Pulse &amp; 13F Whales</div>", unsafe_allow_html=True)

        signage_title = str(radar_24_48.get("signage_title", "24-48H OUTLOOK"))
        signage_col = str(radar_24_48.get("signage_color", "#FBBF24"))
        st.markdown(f"""
        <div class="mob-glass-card">
            <div style="font-size: 0.68rem; font-weight: 800; color: #94A3B8; text-transform: uppercase;">24–48h Market Outlook &amp; Binary Risk ({_esc(cat_risk)})</div>
            <div style="font-size: 0.90rem; font-weight: 800; color: {_esc(signage_col)}; margin-top: 2px;">{_esc(signage_title)}</div>
            <div class="mob-mono" style="font-size: 0.72rem; color: #CBD5E1; margin-top: 4px;">
                SPY: <b style="color: {'#34D399' if spy_ret >= 0.15 else ('#FB7185' if spy_ret <= -0.15 else '#FBBF24')};">{spy_ret:+.2f}%</b> (<b style="color: {'#34D399' if spy_rvol >= 1.15 else ('#FB7185' if spy_rvol < 0.80 else '#FBBF24')};">{spy_rvol:.2f}x</b> Vol) &bull; {_esc(regime_badge)} &bull; Tape {tape_conv:.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if _edu is not None:
            _sym_d = (cat_data.get("symbolism") if isinstance(cat_data, dict) else None) or macro_pulse.get("symbolism") or {}
            _edu.render_edu_drawer(
                "macro_regime",
                {
                    "vix_ratio": _sym_d.get("vix_ratio", 0.94),
                    "credit_z": _sym_d.get("credit_z", 0.0),
                    "tnx_yield": _sym_d.get("tnx_yield", 4.25),
                    "exposure_cap_pct": _sym_d.get("exposure_cap_pct", 100),
                    "regime_label": _sym_d.get("regime_label", regime_badge),
                },
                compact=True,
            )

        macro_ev = cat_data.get("fed_and_macro_events", [])[:3]
        if macro_ev:
            st.markdown("<div style='font-size: 0.70rem; font-weight: 800; color: #FF8533; text-transform: uppercase; margin-bottom: 6px;'>Upcoming Fed / US Macro Prints</div>", unsafe_allow_html=True)
            for ev in macro_ev:
                ev_title = ev.get("event") or ev.get("title") or str(ev)
                ev_date = ev.get("date", "")
                st.markdown(f"""
                <div style="background: rgba(15,18,26,0.68); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 7px 11px; margin-bottom: 5px; font-size: 0.72rem; color: #CBD5E1;">
                    <b style="color:#FF8533;">{_esc(str(ev_date)[:10])}</b> &middot; {_esc(str(ev_title)[:58])}
                </div>
                """, unsafe_allow_html=True)

        stealth_gems = sm_radar.get("stealth_gems", [])
        if stealth_gems:
            st.markdown("<div style='font-size: 0.70rem; font-weight: 800; color: #FF8533; text-transform: uppercase; margin: 8px 0 6px 0;'>Top Stealth Insider Clusters</div>", unsafe_allow_html=True)
            for g in stealth_gems[:2]:
                g_c = int(g.get('cluster_conviction', 80))
                g_c_col = "#34D399" if g_c >= 70 else ("#FB7185" if g_c < 50 else "#FBBF24")
                st.markdown(f"""
                <div style="background: rgba(15,18,26,0.68); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 8px 12px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span class="mob-mono" style="font-size: 0.88rem; font-weight: 800; color: #F1F5F9;">{_esc(g.get('symbol'))}</span>
                        <div style="font-size: 0.68rem; color: #94A3B8;">{_esc(str(g.get('name', ''))[:20])}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="mob-mono" style="font-size: 0.82rem; font-weight: 700; color: #F1F5F9;">${float(g.get('price', 0.0) or 0.0):.2f}</span>
                        <div style="font-size: 0.65rem; color: {g_c_col}; font-weight: 700;">{g_c}/100 Conv</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
