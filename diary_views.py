"""
Charles Schwab Options Order Entry Desk, Practice Diary, & Daily Top-5 Recommendation Ledger Views
Built for Rubberband Man v4.0 Ultra (Obsidian Frosted-Glass + Rich Hyper-Orange Terminal)
Features:
1. Unified Master-Detail Terminal: Single coordinated workspace with no duplicate inputs.
2. Rich Ticker Intelligence Cockpit: Full company profile, market cap / ETF basket status, spot price, and -200..+200 Conviction.
3. All Calls & Puts up to 90 Days: Interactive Charles Schwab options chain using 1-credit cached OPRA feed (`feed="cached"`).
4. Authentic Charles Schwab Order Ticket: $0.65 regulatory fee, Day/GTC, Breakeven, Max Profit/Loss, 30D vs 45D DTE Posture.
5. Gamified Practice Diary: $100k simulated margin capital, zero risk, live OPRA mark-to-market pricing, and trade retrospectives.
6. 24/7 GX10 Autonomous Daily Top-5 Recommendation Ledger & Empirical Performance Auditing across 5 expanded sectors.
"""

import html as _html
import math
import json
import time
import inspect
import datetime
from typing import List, Dict, Any, Optional, Tuple
import streamlit as st
import pandas as pd
import numpy as np

import diary_db
import marketdata_client
import quant_kernel as qk
import rubberband_engine_v3 as rbe3
import rubberband_charts as rbc

try:
    import ui_kit as _ui_kit
except Exception:
    _ui_kit = None

try:
    import edu_annotations as _edu
except Exception:
    _edu = None


def _esc(val: Any) -> str:
    return _html.escape(str(val if val is not None else ""), quote=True)


def _safe_http_url(url: Any) -> str:
    s = str(url or "").strip()
    if s.startswith("https://") or s.startswith("http://"):
        return _html.escape(s, quote=True)
    return ""


_TICKET_RESET_KEYS = (
    "ticket_action_rail", "ticket_type_rail", "ticket_strategy_rail",
    "ticket_strike_rail", "ticket_short_strike_rail", "ticket_qty_rail",
    "ticket_limit_rail", "ticket_tgt_spot_rail", "ticket_stp_spot_rail",
    "ticket_notes_rail", "ticket_conv_rail", "dlg_strategy", "dlg_action", "dlg_ord_type",
    "dlg_qty", "dlg_limit", "dlg_short_strike", "dlg_tgt_val", "dlg_stp_val", "dlg_notes",
)


def _reset_ticket_widget_state() -> None:
    for _k in _TICKET_RESET_KEYS:
        if _k in st.session_state:
            del st.session_state[_k]


def _compute_order_payoff_summary(
    spot_price: float,
    strike_p: float,
    limit_p: float,
    qty: int,
    dte: int,
    sigma: float,
    opt_type: str,
    opt_action: str,
    strategy: str,
    short_strike: Optional[float],
    tgt_val: float,
    stp_val: float,
) -> Dict[str, Any]:
    """Shared payoff & Greek summary for both the Schwab modal and order rail (supports BUY & SELL)."""
    is_call = (str(opt_type).upper() == "CALL")
    is_sell = ("SELL" in str(opt_action).upper())
    is_spread = (
        str(strategy).upper() == "VERTICAL_DEBIT_SPREAD"
        and short_strike is not None
        and abs(float(short_strike) - float(strike_p)) > 0.01
    )
    k2 = float(short_strike) if is_spread else 0.0

    leg_mult = 2 if is_spread else 1
    schwab_comm = round(qty * 0.65 * leg_mult, 2)
    gross_principal = round(qty * limit_p * 100.0, 2)
    if is_sell:
        net_credit = round(max(0.0, gross_principal - schwab_comm), 2)
        if is_spread:
            width_dollars = abs(k2 - strike_p) * 100.0 * qty
            total_cash_or_risk = round(max(1.0, width_dollars - net_credit), 2)
        else:
            total_cash_or_risk = round(max(1.0, gross_principal), 2)
        be_price = round((strike_p + limit_p) if is_call else max(0.01, strike_p - limit_p), 2)
    else:
        total_cash_or_risk = round(gross_principal + schwab_comm, 2)
        net_credit = 0.0
        be_price = round((strike_p + limit_p) if is_call else max(0.01, strike_p - limit_p), 2)

    be_pct = ((be_price - spot_price) / spot_price) * 100.0 if spot_price else 0.0

    t_entry = max(1, dte) / 365.0
    t_exit = max(1, dte - 4) / 365.0
    g_long = _exact_leg_greeks(s=spot_price, k=strike_p, t=t_entry, r=0.0425, sigma=sigma, opt_type=opt_type)
    if is_spread:
        g_short = _exact_leg_greeks(s=spot_price, k=k2, t=t_entry, r=0.0425, sigma=sigma, opt_type=opt_type)
        raw_delta = float(g_long["delta"] - g_short["delta"])
        raw_theta = float(g_long["theta"] - g_short["theta"])
        raw_vega = float(g_long["vega"] - g_short["vega"])
    else:
        raw_delta = float(g_long["delta"])
        raw_theta = float(g_long["theta"])
        raw_vega = float(g_long["vega"])

    dir_sgn = -1.0 if is_sell else 1.0
    pos_delta_shares = round(dir_sgn * raw_delta * 100.0 * qty, 0)
    pos_theta_daily = round(dir_sgn * raw_theta * 100.0 * qty, 2)
    pos_vega_vol = round(dir_sgn * raw_vega * 100.0 * qty, 2)

    if is_call:
        bs_now, _ = rbe3.bs_call_price_delta(spot_price, strike_p, t_entry, 0.0425, sigma)
        bs_tgt, _ = rbe3.bs_call_price_delta(tgt_val, strike_p, t_exit, 0.0425, sigma)
        bs_stp, _ = rbe3.bs_call_price_delta(stp_val, strike_p, t_exit, 0.0425, sigma)
        target_intrinsic = max(0.0, tgt_val - strike_p)
        if is_spread:
            s_now, _ = rbe3.bs_call_price_delta(spot_price, k2, t_entry, 0.0425, sigma)
            s_tgt, _ = rbe3.bs_call_price_delta(tgt_val, k2, t_exit, 0.0425, sigma)
            s_stp, _ = rbe3.bs_call_price_delta(stp_val, k2, t_exit, 0.0425, sigma)
            bs_now = max(0.05, bs_now - s_now)
            bs_tgt = max(0.01, min(abs(k2 - strike_p), bs_tgt - s_tgt))
            bs_stp = max(0.01, min(abs(k2 - strike_p), bs_stp - s_stp))
            target_intrinsic = max(0.0, min(abs(k2 - strike_p), target_intrinsic - max(0.0, tgt_val - k2)))
    else:
        bs_now, _ = rbe3.bs_put_price_delta(spot_price, strike_p, t_entry, 0.0425, sigma)
        bs_tgt, _ = rbe3.bs_put_price_delta(tgt_val, strike_p, t_exit, 0.0425, sigma)
        bs_stp, _ = rbe3.bs_put_price_delta(stp_val, strike_p, t_exit, 0.0425, sigma)
        target_intrinsic = max(0.0, strike_p - tgt_val)
        if is_spread:
            s_now, _ = rbe3.bs_put_price_delta(spot_price, k2, t_entry, 0.0425, sigma)
            s_tgt, _ = rbe3.bs_put_price_delta(tgt_val, k2, t_exit, 0.0425, sigma)
            s_stp, _ = rbe3.bs_put_price_delta(stp_val, k2, t_exit, 0.0425, sigma)
            bs_now = max(0.05, bs_now - s_now)
            bs_tgt = max(0.01, min(abs(k2 - strike_p), bs_tgt - s_tgt))
            bs_stp = max(0.01, min(abs(k2 - strike_p), bs_stp - s_stp))
            target_intrinsic = max(0.0, min(abs(k2 - strike_p), target_intrinsic - max(0.0, k2 - tgt_val)))

    prem_scale = (limit_p / bs_now) if bs_now > 0.05 else 1.0
    opt_val_at_tgt = max(0.01 if is_sell else target_intrinsic, bs_tgt * prem_scale)
    opt_val_at_stop = max(0.01, bs_stp * prem_scale)
    if is_spread:
        opt_val_at_tgt = min(abs(k2 - strike_p), opt_val_at_tgt)
        opt_val_at_stop = min(abs(k2 - strike_p), opt_val_at_stop)

    if is_sell:
        close_at_tgt = qty * opt_val_at_tgt * 100.0 + schwab_comm
        close_at_stp = qty * opt_val_at_stop * 100.0 + schwab_comm
        net_profit_at_tgt = round(net_credit - close_at_tgt, 2)
        est_loss_at_stop = round(max(0.0, close_at_stp - net_credit), 2)
    else:
        gross_payout_at_tgt = round(qty * opt_val_at_tgt * 100.0, 2)
        net_profit_at_tgt = round(gross_payout_at_tgt - schwab_comm - total_cash_or_risk, 2)
        gross_val_at_stop = round(qty * opt_val_at_stop * 100.0, 2)
        est_loss_at_stop = round(max(0.0, total_cash_or_risk - (gross_val_at_stop - schwab_comm)), 2)

    roi_at_tgt_pct = (net_profit_at_tgt / total_cash_or_risk * 100.0) if total_cash_or_risk > 0 else 0.0
    stop_loss_pct = (est_loss_at_stop / total_cash_or_risk * 100.0) if total_cash_or_risk > 0 else 100.0

    return {
        "is_spread": is_spread,
        "is_sell": is_sell,
        "schwab_comm": schwab_comm,
        "total_outlay": total_cash_or_risk,
        "net_credit": net_credit,
        "be_price": be_price,
        "be_pct": be_pct,
        "pos_delta_shares": pos_delta_shares,
        "pos_theta_daily": pos_theta_daily,
        "pos_vega_vol": pos_vega_vol,
        "net_profit_at_tgt": net_profit_at_tgt,
        "roi_at_tgt_pct": roi_at_tgt_pct,
        "est_loss_at_stop": est_loss_at_stop,
        "stop_loss_pct": stop_loss_pct,
    }


_FALLBACK_SECTOR_ALIASES = {
    "Nuclear & Next-Gen Energy": "Energy, Grid & Materials",
    "Nuclear Energy": "Energy, Grid & Materials",
    "Robotics & Automation": "Robotics & Autonomous",
    "Robotics": "Robotics & Autonomous",
    "Edge AI": "Edge AI & Next-Gen Compute",
}

_THEMATIC_ETF_CHIPS = ["REMX", "SRVR", "ROBO", "JEDI", "SMH", "URA", "QTUM", "IGV"]


def _normalize_sector_safe(sec_name: str) -> str:
    """Normalizes legacy sector aliases cleanly to the 5 expanded sector names."""
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


def _is_etf_symbol(sym: str, cand_intel: Optional[Dict[str, Any]] = None) -> bool:
    """Detects whether symbol is a Thematic ETF basket."""
    s = str(sym or "").strip().upper()
    etf_set = set(getattr(rbe3, "THEMATIC_ETFS", set())) | set(_THEMATIC_ETF_CHIPS)
    if s in etf_set:
        return True
    if isinstance(cand_intel, dict):
        f = cand_intel.get("fundamentals", {}) or {}
        if f.get("is_etf") or f.get("solvency_tier") == "ETF Basket":
            return True
    return False


def _inject_obsidian_desk_css() -> None:
    """Injects self-contained Obsidian Frosted-Glass + Hyper-Orange (#FF6B00) styles for Desk & Ledger."""
    st.markdown("""
    <style>
    .obs-mono {
        font-family: 'JetBrains Mono', monospace !important;
        font-variant-numeric: tabular-nums !important;
    }
    .schwab-ribbon,
    .schwab-ticket-card,
    .schwab-strike-visualizer,
    .schwab-order-rail,
    .schwab-pos-card,
    .schwab-receipt-banner,
    .ledger-rec-card,
    .obs-glass-card {
        background: rgba(15, 18, 26, 0.68) !important;
        backdrop-filter: blur(20px) saturate(145%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(145%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 16px !important;
        box-shadow: 0 14px 38px -10px rgba(0, 0, 0, 0.72), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
        transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    .schwab-ribbon {
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        border-left: 3px solid #FF6B00 !important;
    }
    .schwab-strike-visualizer {
        padding: 18px 22px !important;
        margin-bottom: 16px !important;
    }
    .schwab-strike-visualizer:hover,
    .schwab-pos-card:hover,
    .ledger-rec-card:hover {
        border-color: rgba(255, 107, 0, 0.36) !important;
        box-shadow: 0 18px 44px -10px rgba(0, 0, 0, 0.80), 0 0 22px rgba(255, 107, 0, 0.08) !important;
    }
    .schwab-order-rail {
        padding: 18px 20px !important;
        margin-bottom: 12px !important;
    }
    .schwab-pos-card {
        padding: 16px 20px !important;
        margin-bottom: 12px !important;
    }
    .schwab-receipt-banner {
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        border: 1px solid rgba(255, 107, 0, 0.48) !important;
        box-shadow: 0 10px 32px rgba(255, 107, 0, 0.14) !important;
    }
    .ledger-rec-card {
        padding: 16px 20px !important;
        margin-bottom: 14px !important;
    }
    .rm-command-card {
        background: rgba(15, 18, 26, 0.68) !important;
        backdrop-filter: blur(20px) saturate(140%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.13) !important;
        border-radius: 14px !important;
        padding: 12px 16px !important;
        box-shadow: 0 10px 28px -8px rgba(0, 0, 0, 0.65) !important;
    }
    .rm-command-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-variant-numeric: tabular-nums !important;
    }
    .obs-pill-orange {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        background: rgba(255, 107, 0, 0.16);
        color: #FF8533;
        border: 1px solid rgba(255, 107, 0, 0.42);
        font-size: 0.70rem;
        font-weight: 800;
        padding: 2px 9px;
        border-radius: 9999px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        white-space: nowrap;
    }
    .obs-conv-badge,
    .obs-dte-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-family: 'JetBrains Mono', monospace;
        font-variant-numeric: tabular-nums;
        font-size: 0.72rem;
        font-weight: 800;
        padding: 3px 9px;
        border-radius: 9999px;
        letter-spacing: 0.02em;
        white-space: nowrap;
    }
    .obs-subpanel {
        background: rgba(8, 10, 16, 0.56);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 10px 12px;
    }
    </style>
    """, unsafe_allow_html=True)


def render_clean_html(html_str: str):
    """
    Renders HTML in Streamlit ensuring CommonMark does not interpret indented lines
    or blank lines as markdown code blocks (<pre><code>).
    """
    cleaned = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def get_schwab_svg_logo(size: int = 24) -> str:
    """Crisp obsidian & hyper-orange Charles Schwab execution desk vector badge."""
    s = max(18, int(size))
    return f"""
    <div style="display: inline-flex; align-items: center; gap: 10px; vertical-align: middle;">
        <span style="display: inline-flex; align-items: center; justify-content: center; width: {s + 8}px; height: {s + 8}px; border-radius: 8px; background: rgba(15, 18, 26, 0.85); border: 1px solid rgba(255, 107, 0, 0.45); box-shadow: 0 4px 14px rgba(255, 107, 0, 0.18);">
            <svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 17L10 11L14 14.5L20 7" stroke="#FF6B00" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M16 7H20V11" stroke="#FF8533" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                <rect x="2.5" y="2.5" width="19" height="19" rx="4.5" stroke="rgba(255,255,255,0.22)" stroke-width="1.2"/>
            </svg>
        </span>
        <span style="background: rgba(255, 107, 0, 0.16); color: #FF8533; border: 1px solid rgba(255, 107, 0, 0.42); font-weight: 900; font-size: 0.74rem; padding: 3px 9px; border-radius: 6px; letter-spacing: 0.06em; font-family: 'Plus Jakarta Sans', sans-serif;">SCHWAB</span>
        <span style="font-weight: 800; font-size: 1.05rem; color: #F1F5F9; letter-spacing: -0.02em;">Charles Schwab Options Desk</span>
    </div>
    """


def _get_conviction_tier_style(score_200: int) -> Tuple[str, str, str, str]:
    """Returns (tier_label, fg_hex, bg_rgba, bdr_rgba) for a signed -200..+200 conviction score."""
    abs_s = abs(int(score_200))
    is_pos = int(score_200) >= 0
    if abs_s >= 150:
        return (
            "ASYMMETRIC CONVICTION",
            "#FF8533",
            "rgba(255, 107, 0, 0.18)",
            "rgba(255, 107, 0, 0.50)",
        )
    if abs_s >= 110:
        return (
            "HIGH CONVICTION",
            "#34D399" if is_pos else "#FB7185",
            "rgba(16, 185, 129, 0.16)" if is_pos else "rgba(244, 63, 94, 0.16)",
            "rgba(16, 185, 129, 0.42)" if is_pos else "rgba(244, 63, 94, 0.42)",
        )
    if abs_s >= 70:
        return (
            "TACTICAL EDGE",
            "#FB923C",
            "rgba(251, 146, 60, 0.14)",
            "rgba(251, 146, 60, 0.36)",
        )
    if abs_s >= 36:
        return (
            "WATCH / DEVELOPING",
            "#FBBF24",
            "rgba(245, 158, 11, 0.13)",
            "rgba(245, 158, 11, 0.34)",
        )
    return (
        "NEUTRAL / NOISE",
        "#94A3B8",
        "rgba(148, 163, 184, 0.12)",
        "rgba(148, 163, 184, 0.28)",
    )


def _format_conviction_badge_html(
    score_val: float,
    opt_type: str = "",
    is_legacy_100: bool = False,
    show_tier: bool = False
) -> str:
    """
    Renders a crisp obsidian frosted-glass badge for signed -200..+200 conviction
    (e.g. `+168 CALL` / `-154 PUT`), while gracefully formatting legacy 0..100 historical records.
    """
    opt_u = str(opt_type or "").strip().upper()
    if "CALL" in opt_u:
        dir_lbl = "CALL"
    elif "PUT" in opt_u:
        dir_lbl = "PUT"
    else:
        dir_lbl = ""

    if is_legacy_100:
        sc_int = int(round(float(score_val or 0)))
        dir_sfx = f" {dir_lbl}" if dir_lbl else ""
        fg = "#34D399" if dir_lbl == "CALL" else ("#FB7185" if dir_lbl == "PUT" else "#CBD5E1")
        return (
            f'<span class="obs-conv-badge" style="color: {fg}; background: rgba(255, 255, 255, 0.05); '
            f'border: 1px solid rgba(255, 255, 255, 0.14);">'
            f'LEGACY {sc_int}/100{dir_sfx}</span>'
        )

    sc_int = max(-200, min(200, int(round(float(score_val or 0)))))
    if not dir_lbl and sc_int != 0:
        dir_lbl = "CALL" if sc_int > 0 else "PUT"

    tier_lbl, fg, bg, bdr = _get_conviction_tier_style(sc_int)
    signed_str = f"{sc_int:+d}"
    text = f"{signed_str} {dir_lbl}".strip()
    if show_tier:
        text = f"{text} · {tier_lbl}"
    glow = "box-shadow: 0 0 14px rgba(255, 107, 0, 0.22);" if abs(sc_int) >= 150 else ""
    return (
        f'<span class="obs-conv-badge" style="color: {fg}; background: {bg}; '
        f'border: 1px solid {bdr}; {glow}">{text}</span>'
    )


def _format_dte_badge_html(dte_val: int, rationale: str = "", exact_dte: Optional[int] = None) -> str:
    """Renders 30D vs 45D duration awareness pill in obsidian frosted glass."""
    d_int = int(dte_val or 35)
    bucket = 45 if d_int >= 38 else 30
    if bucket == 45:
        fg, bg, bdr = "#FF8533", "rgba(255, 107, 0, 0.15)", "rgba(255, 107, 0, 0.40)"
        tag = "45D SWING"
    else:
        fg, bg, bdr = "#34D399", "rgba(16, 185, 129, 0.14)", "rgba(16, 185, 129, 0.36)"
        tag = "30D TACTICAL"

    extra = f" · {int(exact_dte)}d" if (exact_dte is not None and int(exact_dte) != bucket) else ""
    title_attr = f' title="{str(rationale).replace(chr(34), "")}"' if rationale else ""
    return (
        f'<span class="obs-dte-badge"{title_attr} style="color: {fg}; background: {bg}; '
        f'border: 1px solid {bdr};">{tag}{extra}</span>'
    )


def _resolve_conviction_and_dte(
    prefill: Dict[str, Any],
    active_leg: Optional[Dict[str, Any]] = None,
    cand_intel: Optional[Dict[str, Any]] = None,
    opt_type: str = "",
    fallback_dte: int = 35
) -> Tuple[int, bool, int, str]:
    """
    Resolves (score_200, is_200_scale, recommended_dte, dte_rationale)
    from prefill, active_leg, and cand_intel.
    """
    prefill = prefill or {}
    active_leg = active_leg or {}
    cand_intel = cand_intel or {}
    bp = cand_intel.get("blueprint", {}) if isinstance(cand_intel, dict) else {}
    m = cand_intel.get("metrics", {}) if isinstance(cand_intel, dict) else {}

    # 1. Resolve conviction score (-200..+200 preferred)
    score_val = None
    is_200_scale = False
    for src in (
        prefill.get("conviction_score_200"),
        active_leg.get("conviction_score_200"),
        bp.get("conviction_score_200"),
        m.get("conviction_score_200"),
    ):
        if src is not None:
            score_val = src
            is_200_scale = True
            break

    if score_val is None:
        for src in (
            prefill.get("conviction_score"),
            active_leg.get("conviction_score"),
        ):
            if src is not None:
                score_val = src
                val_f = float(src)
                is_200_scale = (val_f < 0 or abs(val_f) > 100)
                break

    if score_val is None:
        score_val = bp.get("composite_score", 0)
        is_200_scale = False

    score_int = int(round(float(score_val or 0)))

    # Ensure sign matches option type when in 200-scale if magnitude was passed unsigned
    eff_type = str(opt_type or active_leg.get("option_type") or prefill.get("option_type") or "").upper()
    if is_200_scale and "PUT" in eff_type and score_int > 0:
        score_int = -score_int

    # 2. Resolve recommended 30 vs 45 DTE
    rec_dte_raw = (
        active_leg.get("recommended_dte")
        or prefill.get("recommended_dte")
        or bp.get("recommended_dte")
        or m.get("recommended_dte")
        or active_leg.get("dte")
        or prefill.get("dte")
        or fallback_dte
    )
    try:
        rec_dte_int = int(rec_dte_raw)
    except Exception:
        rec_dte_int = int(fallback_dte)
    rec_dte_bucket = 45 if rec_dte_int >= 38 else 30

    dte_rationale = str(
        active_leg.get("dte_rationale")
        or prefill.get("dte_rationale")
        or bp.get("dte_rationale")
        or m.get("dte_rationale")
        or ("45D cushion against binary/IV compression" if rec_dte_bucket == 45 else "30D tighter gamma velocity")
    )

    return score_int, is_200_scale, rec_dte_bucket, dte_rationale


def _fetch_cached_option_chain_df(
    symbol: str,
    expiration: Optional[str] = None,
    dte: Optional[int] = 35,
    strike_limit: int = 60,
    ttl: int = 900
) -> Optional[pd.DataFrame]:
    """
    Fetches OPRA option chain via `marketdata_client.get_option_chain_native(..., feed="cached")`
    so Schwab Simulator & live mark-to-market share the 1-credit cached OPRA feed without redundant calls.
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None

    cache_key = f"{sym}|{expiration or ''}|{dte or ''}|{strike_limit}"
    now_ts = time.time()
    try:
        mem_cache = st.session_state.setdefault("_opra_cached_chain_df_map", {})
        cached_entry = mem_cache.get(cache_key)
        if isinstance(cached_entry, dict) and (now_ts - float(cached_entry.get("ts", 0))) < 120:
            return cached_entry.get("df")
    except Exception:
        mem_cache = None

    df = None
    try:
        sig = inspect.signature(marketdata_client.get_option_chain_native)
        kwargs: Dict[str, Any] = {
            "expiration": expiration,
            "dte": None if expiration else dte,
            "side": None,
            "strike_limit": strike_limit,
            "ttl": ttl,
        }
        if "feed" in sig.parameters:
            kwargs["feed"] = "cached"
        df = marketdata_client.get_option_chain_native(sym, **kwargs)
    except TypeError:
        try:
            df = marketdata_client.get_option_chain_native(
                sym,
                expiration=expiration,
                dte=None if expiration else dte,
                side=None,
                strike_limit=strike_limit,
                ttl=ttl,
            )
        except Exception:
            df = None
    except Exception:
        df = None

    if mem_cache is not None and df is not None and not df.empty:
        try:
            mem_cache[cache_key] = {"ts": now_ts, "df": df}
        except Exception:
            pass
    return df


def resolve_best_expiration_index(fridays: List[Dict[str, Any]], target_exp: str = "", target_dte: Optional[int] = None) -> int:
    """
    Robustly resolves the best expiration cycle index from fridays_90d matching
    either a target expiration date string (ISO date, formatted date, or label)
    or a target DTE integer (1-2W, 30D, 45D, 60D, 90D).
    """
    if not fridays:
        return 0

    if target_exp:
        t_clean = str(target_exp).strip()
        for idx, f in enumerate(fridays):
            if t_clean == f.get("iso_date") or t_clean == f.get("date_str"):
                return idx
        for idx, f in enumerate(fridays):
            if t_clean in f.get("label", "") or f.get("date_str", "") in t_clean or f.get("iso_date", "") in t_clean:
                return idx
        for fmt in ["%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"]:
            try:
                dt = datetime.datetime.strptime(t_clean[:10], fmt).date()
                for idx, f in enumerate(fridays):
                    if f.get("iso_date") == dt.isoformat():
                        return idx
            except Exception:
                pass

    if target_dte is not None:
        try:
            d_val = int(target_dte)
            return min(range(len(fridays)), key=lambda i: abs(int(fridays[i].get("dte", 35)) - d_val))
        except Exception:
            pass

    monthlies = [(idx, f) for idx, f in enumerate(fridays) if f.get("is_monthly", False)]
    if monthlies:
        return min(monthlies, key=lambda pair: abs(int(pair[1].get("dte", 35)) - 35))[0]

    return min(range(len(fridays)), key=lambda i: abs(int(fridays[i].get("dte", 35)) - 35))


def get_upcoming_option_fridays(max_dte: int = 90) -> List[Dict[str, Any]]:
    """
    Generates all standard Friday option expiration cycles from 1 week up to 90 DTE.
    Includes weekly expirations and standard 3rd Friday monthly cycles.
    """
    today = datetime.date.today()
    fridays = []
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday = today + datetime.timedelta(days=days_until_friday)

    i = 0
    while True:
        fri = next_friday + datetime.timedelta(weeks=i)
        dte = (fri - today).days
        if dte > max_dte:
            break
        is_monthly = (15 <= fri.day <= 21)
        cycle_tag = "Monthly" if is_monthly else "Weekly"
        label = f"{fri.strftime('%b %d, %Y')} ({dte} DTE · {cycle_tag})"
        fridays.append({
            "label": label,
            "date_str": fri.strftime("%b %d, %Y"),
            "iso_date": fri.isoformat(),
            "dte": dte,
            "is_monthly": is_monthly,
            "cycle_tag": cycle_tag
        })
        i += 1
    return fridays


def calculate_option_greeks(s: float, k: float, t: float, r: float = 0.0425, sigma: float = 0.40, opt_type: str = "CALL") -> Dict[str, float]:
    """
    Computes exact Black-Scholes Greeks (Delta, Gamma, Theta, Vega) using standard Gaussian CDF/PDF.
    Theta is reported in standard calendar dollars per day per share.
    """
    t = max(0.001, float(t))
    s = max(0.01, float(s))
    k = max(0.01, float(k))
    sigma = max(0.05, float(sigma))
    d1 = (math.log(s / k) + (r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    pdf_d1 = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)
    gamma = pdf_d1 / (s * sigma * math.sqrt(t))
    vega = (s * math.sqrt(t) * pdf_d1) / 100.0
    norm_cdf_d1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
    norm_cdf_d2 = 0.5 * (1.0 + math.erf(d2 / math.sqrt(2.0)))
    if opt_type.upper() == "CALL":
        delta = norm_cdf_d1
        theta = (-(s * pdf_d1 * sigma) / (2.0 * math.sqrt(t)) - r * k * math.exp(-r * t) * norm_cdf_d2) / 365.0
    else:
        delta = norm_cdf_d1 - 1.0
        norm_cdf_minus_d2 = 0.5 * (1.0 + math.erf(-d2 / math.sqrt(2.0)))
        theta = (-(s * pdf_d1 * sigma) / (2.0 * math.sqrt(t)) + r * k * math.exp(-r * t) * norm_cdf_minus_d2) / 365.0
    return {
        "delta": round(delta, 2),
        "gamma": round(gamma, 4),
        "theta": round(theta, 2),
        "vega": round(vega, 2)
    }


def generate_options_chain_up_to_90d(
    symbol: str,
    spot_price: float,
    dte: int = 35,
    moneyness_span_pct: float = 20.0,
    vol: float = 0.40,
    r: float = 0.0425,
    expiry_date: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Retrieves cached exchange option chain from MarketData.app OPRA (`feed="cached"`, 1-credit)
    with fallback to `rbe3.get_near_live_option_chain_dataframe` and calibrated Black-Scholes.
    Enforces strict no-arbitrage bounds and monotonicity across the strike spectrum.
    Returns (chain_rows, is_live_chain).
    """
    spot = max(1.0, float(spot_price))
    t_years = max(1, dte) / 365.0
    sym = str(symbol or "").strip().upper()

    calls_df = None
    puts_df = None
    is_live_chain = False

    # 1. Primary: 1-credit cached OPRA chain via marketdata_client.get_option_chain_native(..., feed="cached")
    md_df = _fetch_cached_option_chain_df(
        sym,
        expiration=expiry_date,
        dte=dte,
        strike_limit=60,
        ttl=900,
    )
    if md_df is not None and not md_df.empty and "side" in md_df.columns:
        calls_df = md_df[md_df["side"].astype(str).str.lower() == "call"].sort_values("strike").reset_index(drop=True)
        puts_df = md_df[md_df["side"].astype(str).str.lower() == "put"].sort_values("strike").reset_index(drop=True)
        is_live_chain = (not calls_df.empty) or (not puts_df.empty)

    # 2. Secondary fallback via engine helper if direct cached chain returned empty
    if not is_live_chain:
        real_chain = rbe3.get_near_live_option_chain_dataframe(sym, expiry=expiry_date)
        if isinstance(real_chain, dict):
            c_obj = real_chain.get("calls")
            p_obj = real_chain.get("puts")
            if c_obj is not None and not c_obj.empty:
                calls_df = c_obj
                puts_df = p_obj
                is_live_chain = True

    if not is_live_chain:
        calibrated_iv = vol if 0.10 <= vol <= 2.0 else 0.45
        step = 5.0 if spot > 100.0 else (2.5 if spot > 40.0 else (1.0 if spot > 15.0 else 0.5))
        base_center = round(spot / step) * step
        strikes = [round(base_center + (i * step), 2) for i in range(-7, 8) if (base_center + (i * step)) > 0]
        chain_rows = []
        for k in strikes:
            bs_c_p, bs_c_d = rbe3.bs_call_price_delta(spot, k, t_years, r, calibrated_iv)
            bs_p_p, bs_p_d = rbe3.bs_put_price_delta(spot, k, t_years, r, calibrated_iv)
            c_mark = max(0.05, round(bs_c_p, 2))
            p_mark = max(0.05, round(bs_p_p, 2))
            chain_rows.append({
                "strike": k,
                "is_atm": abs(k - spot) < (step * 0.55),
                "call_mark": c_mark,
                "call_bid": max(0.01, round(c_mark * 0.95, 2)),
                "call_ask": round(c_mark * 1.05, 2),
                "call_delta": round(bs_c_d, 2),
                "call_breakeven": round(k + c_mark, 2),
                "call_itm": spot > k,
                "call_iv": calibrated_iv,
                "call_oi": 650,
                "call_vol": 120,
                "put_mark": p_mark,
                "put_bid": max(0.01, round(p_mark * 0.95, 2)),
                "put_ask": round(p_mark * 1.05, 2),
                "put_delta": round(bs_p_d, 2),
                "put_breakeven": round(k - p_mark, 2),
                "put_itm": spot < k,
                "put_iv": calibrated_iv,
                "put_oi": 520,
                "put_vol": 95,
                "is_synthetic": True
            })
        return chain_rows, False

    # 1. Calibrate Chain Implied Volatility across all active two-sided strikes
    valid_call_ivs = pd.Series(dtype=float)
    if calls_df is not None and not calls_df.empty:
        c_mask = (
            (calls_df["bid"] > 0)
            & (calls_df["ask"] > 0)
            & (calls_df["ask"] >= calls_df["bid"])
            & ((calls_df["ask"] - calls_df["bid"]) <= max(3.0, 0.45 * spot))
            & (calls_df["impliedVolatility"] > 0.08)
            & (calls_df["impliedVolatility"] < 2.50)
        )
        valid_call_ivs = calls_df.loc[c_mask, "impliedVolatility"]

    valid_put_ivs = pd.Series(dtype=float)
    if puts_df is not None and not puts_df.empty:
        p_mask = (
            (puts_df["bid"] > 0)
            & (puts_df["ask"] > 0)
            & (puts_df["ask"] >= puts_df["bid"])
            & ((puts_df["ask"] - puts_df["bid"]) <= max(3.0, 0.45 * spot))
            & (puts_df["impliedVolatility"] > 0.08)
            & (puts_df["impliedVolatility"] < 2.50)
        )
        valid_put_ivs = puts_df.loc[p_mask, "impliedVolatility"]

    all_valid_ivs = pd.concat([valid_call_ivs, valid_put_ivs]).dropna()
    if not all_valid_ivs.empty and len(all_valid_ivs) >= 2:
        calibrated_iv = float(all_valid_ivs.median())
    else:
        calibrated_iv = vol

    calibrated_iv = min(max(calibrated_iv, 0.12), 2.20)

    c_map = {}
    if calls_df is not None and not calls_df.empty:
        for _, r_row in calls_df.iterrows():
            try:
                c_map[float(r_row["strike"])] = r_row
            except Exception:
                continue

    p_map = {}
    if puts_df is not None and not puts_df.empty:
        for _, r_row in puts_df.iterrows():
            try:
                p_map[float(r_row["strike"])] = r_row
            except Exception:
                continue

    min_price = spot * (1.0 - (moneyness_span_pct / 100.0))
    max_price = spot * (1.0 + (moneyness_span_pct / 100.0))

    all_k = sorted(list(set(list(c_map.keys()) + list(p_map.keys()))))
    filtered_k = [k for k in all_k if (min_price <= k <= max_price)]
    if not filtered_k and all_k:
        filtered_k = sorted(sorted(all_k, key=lambda x: abs(x - spot))[:16])

    today = datetime.date.today()
    chain_rows = []

    for k in filtered_k:
        c_item = c_map.get(k)
        p_item = p_map.get(k)

        bs_c_p, bs_c_d = rbe3.bs_call_price_delta(spot, k, t_years, r, calibrated_iv)
        bs_p_p, bs_p_d = rbe3.bs_put_price_delta(spot, k, t_years, r, calibrated_iv)

        # Evaluate Call Leg
        c_bid = float(c_item.get("bid", 0.0) or 0.0) if c_item is not None else 0.0
        c_ask = float(c_item.get("ask", 0.0) or 0.0) if c_item is not None else 0.0
        c_last = float(c_item.get("lastPrice", 0.0) or 0.0) if c_item is not None else 0.0
        c_iv_raw = c_item.get("impliedVolatility") if c_item is not None else None
        c_iv_val = float(c_iv_raw) if (c_iv_raw is not None and not pd.isna(c_iv_raw)) else calibrated_iv
        c_oi = int(c_item.get("openInterest", 0) or 0) if (c_item is not None and not pd.isna(c_item.get("openInterest", 0))) else 0
        c_vol = int(c_item.get("volume", 0) or 0) if (c_item is not None and not pd.isna(c_item.get("volume", 0))) else 0
        c_trade_date_str = str(c_item.get("lastTradeDate", "")) if c_item is not None else ""

        is_c_trade_recent = False
        if c_trade_date_str:
            try:
                t_date = datetime.date.fromisoformat(c_trade_date_str[:10])
                is_c_trade_recent = (today - t_date).days <= 3
            except Exception:
                pass

        c_intrinsic = max(0.0, spot - k)
        c_has_two_sided = (c_bid > 0 and c_ask > 0 and c_ask >= c_bid and (c_ask - c_bid) <= max(3.0, 0.40 * spot))

        if c_has_two_sided:
            mid_c = round((c_bid + c_ask) / 2.0, 2)
            call_mark = mid_c if (c_intrinsic <= mid_c <= spot) else max(0.05, round(bs_c_p, 2))
        elif is_c_trade_recent and (c_intrinsic <= c_last <= spot) and abs(c_last - bs_c_p) <= max(2.50, bs_c_p * 0.30):
            call_mark = round(c_last, 2)
            c_bid = max(0.01, round(call_mark * 0.95, 2))
            c_ask = round(call_mark * 1.05, 2)
        else:
            call_mark = max(0.05, round(bs_c_p, 2))
            c_bid = max(0.01, round(call_mark * 0.95, 2))
            c_ask = round(call_mark * 1.05, 2)

        eff_c_iv = c_iv_val if (0.10 <= c_iv_val <= 2.50) else calibrated_iv

        # Evaluate Put Leg
        p_bid = float(p_item.get("bid", 0.0) or 0.0) if p_item is not None else 0.0
        p_ask = float(p_item.get("ask", 0.0) or 0.0) if p_item is not None else 0.0
        p_last = float(p_item.get("lastPrice", 0.0) or 0.0) if p_item is not None else 0.0
        p_iv_raw = p_item.get("impliedVolatility") if p_item is not None else None
        p_iv_val = float(p_iv_raw) if (p_iv_raw is not None and not pd.isna(p_iv_raw)) else calibrated_iv
        p_oi = int(p_item.get("openInterest", 0) or 0) if (p_item is not None and not pd.isna(p_item.get("openInterest", 0))) else 0
        p_vol = int(p_item.get("volume", 0) or 0) if (p_item is not None and not pd.isna(p_item.get("volume", 0))) else 0
        p_trade_date_str = str(p_item.get("lastTradeDate", "")) if p_item is not None else ""

        is_p_trade_recent = False
        if p_trade_date_str:
            try:
                t_date = datetime.date.fromisoformat(p_trade_date_str[:10])
                is_p_trade_recent = (today - t_date).days <= 3
            except Exception:
                pass

        p_intrinsic = max(0.0, k - spot)
        p_has_two_sided = (p_bid > 0 and p_ask > 0 and p_ask >= p_bid and (p_ask - p_bid) <= max(3.0, 0.40 * spot))

        if p_has_two_sided:
            mid_p = round((p_bid + p_ask) / 2.0, 2)
            put_mark = mid_p if (p_intrinsic <= mid_p <= k) else max(0.05, round(bs_p_p, 2))
        elif is_p_trade_recent and (p_intrinsic <= p_last <= k) and abs(p_last - bs_p_p) <= max(2.50, bs_p_p * 0.30):
            put_mark = round(p_last, 2)
            p_bid = max(0.01, round(put_mark * 0.95, 2))
            p_ask = round(put_mark * 1.05, 2)
        else:
            put_mark = max(0.05, round(bs_p_p, 2))
            p_bid = max(0.01, round(put_mark * 0.95, 2))
            p_ask = round(put_mark * 1.05, 2)

        eff_p_iv = p_iv_val if (0.10 <= p_iv_val <= 2.50) else calibrated_iv

        dist_pct = round(((k - spot) / spot) * 100.0, 1)
        step_approx = (filtered_k[1] - filtered_k[0]) if len(filtered_k) > 1 else 2.5
        is_atm = abs(k - spot) <= (step_approx * 0.6)

        c_delta_raw = c_item.get("delta") if c_item is not None else None
        c_delta_val = float(c_delta_raw) if (c_delta_raw is not None and not pd.isna(c_delta_raw) and abs(float(c_delta_raw)) > 0.005) else bs_c_d
        p_delta_raw = p_item.get("delta") if p_item is not None else None
        p_delta_val = float(p_delta_raw) if (p_delta_raw is not None and not pd.isna(p_delta_raw) and abs(float(p_delta_raw)) > 0.005) else bs_p_d

        chain_rows.append({
            "strike": k,
            "dist_pct": dist_pct,
            "is_atm": is_atm,
            "call_mark": call_mark,
            "call_delta": round(c_delta_val, 2),
            "call_bid": c_bid,
            "call_ask": c_ask,
            "call_last": c_last,
            "call_iv": eff_c_iv,
            "call_oi": c_oi,
            "call_vol": c_vol,
            "call_breakeven": round(k + call_mark, 2),
            "call_itm": (k < spot),
            "put_mark": put_mark,
            "put_delta": round(p_delta_val, 2),
            "put_bid": p_bid,
            "put_ask": p_ask,
            "put_last": p_last,
            "put_iv": eff_p_iv,
            "put_oi": p_oi,
            "put_vol": p_vol,
            "put_breakeven": round(k - put_mark, 2),
            "put_itm": (k > spot),
            "is_live_quote": is_live_chain
        })

    # Enforce Monotonicity & No-Arbitrage across Strike Spectrum
    for i in range(1, len(chain_rows)):
        if chain_rows[i]["call_mark"] > chain_rows[i - 1]["call_mark"]:
            chain_rows[i]["call_mark"] = chain_rows[i - 1]["call_mark"]
        if chain_rows[i]["call_delta"] > chain_rows[i - 1]["call_delta"]:
            chain_rows[i]["call_delta"] = chain_rows[i - 1]["call_delta"]
        chain_rows[i]["call_breakeven"] = round(chain_rows[i]["strike"] + chain_rows[i]["call_mark"], 2)

    for i in range(len(chain_rows) - 2, -1, -1):
        if chain_rows[i]["put_mark"] > chain_rows[i + 1]["put_mark"]:
            chain_rows[i]["put_mark"] = chain_rows[i + 1]["put_mark"]
        if chain_rows[i]["put_delta"] < chain_rows[i + 1]["put_delta"]:
            chain_rows[i]["put_delta"] = chain_rows[i + 1]["put_delta"]
        chain_rows[i]["put_breakeven"] = round(chain_rows[i]["strike"] - chain_rows[i]["put_mark"], 2)

    return chain_rows, True


def _parse_iso_expiration(exp_str: str) -> Optional[str]:
    """Best-effort parser converting stored expiration strings into YYYY-MM-DD."""
    raw = str(exp_str or "").split("(")[0].strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(raw[:12].strip(), fmt).date().isoformat()
        except Exception:
            continue
    return None


def _exact_leg_greeks(
    s: float, k: float, t: float, r: float = 0.0425, sigma: float = 0.40, opt_type: str = "CALL"
) -> Dict[str, float]:
    """High-precision Black-Scholes Greeks without 2-decimal rounding loss."""
    t_v = max(1.0 / 365.0, float(t))
    s_v = max(0.01, float(s))
    k_v = max(0.01, float(k))
    sig = max(0.05, float(sigma))
    sqrt_t = math.sqrt(t_v)
    d1 = (math.log(s_v / k_v) + (r + 0.5 * sig * sig) * t_v) / (sig * sqrt_t)
    d2 = d1 - sig * sqrt_t
    pdf_d1 = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)
    gamma = pdf_d1 / (s_v * sig * sqrt_t)
    vega = (s_v * sqrt_t * pdf_d1) / 100.0
    norm_d1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
    norm_d2 = 0.5 * (1.0 + math.erf(d2 / math.sqrt(2.0)))
    if str(opt_type).upper() == "CALL":
        delta = norm_d1
        theta = (-(s_v * pdf_d1 * sig) / (2.0 * sqrt_t) - r * k_v * math.exp(-r * t_v) * norm_d2) / 365.0
    else:
        delta = norm_d1 - 1.0
        norm_m_d2 = 0.5 * (1.0 + math.erf(-d2 / math.sqrt(2.0)))
        theta = (-(s_v * pdf_d1 * sig) / (2.0 * sqrt_t) + r * k_v * math.exp(-r * t_v) * norm_m_d2) / 365.0
    return {"delta": float(delta), "gamma": float(gamma), "theta": float(theta), "vega": float(vega)}


def estimate_live_option_mark(
    trade: Dict[str, Any], current_spot: float, mark_mode: str = "MID"
) -> Dict[str, Any]:
    """
    Computes realistic mark-to-market option pricing anchored to the 1-credit cached OPRA feed
    (`marketdata_client.get_option_chain_native(..., feed="cached")`) with Black-Scholes
    structural fallback. Supports both single-leg options and vertical debit spreads (`short_strike`)
    as well as `"MID"` vs `"BID_LIQUIDATION"` valuation modes.
    """
    entry_prem = float(trade.get("limit_price", 1.0))
    entry_spot = float(trade.get("stock_price_at_entry", current_spot))
    strike = float(trade.get("strike", current_spot))
    opt_type = str(trade.get("option_type", "CALL")).upper()
    qty = int(trade.get("quantity", 1))
    total_cost = float(trade.get("total_cost", qty * entry_prem * 100.0 + qty * 0.65))
    strategy = str(trade.get("strategy", "SINGLE_LEG") or "SINGLE_LEG").upper()
    raw_k2 = trade.get("short_strike")
    short_k = float(raw_k2) if raw_k2 is not None and float(raw_k2) > 0.0 else None
    is_spread = (strategy == "VERTICAL_DEBIT_SPREAD") and (short_k is not None) and (abs(short_k - strike) > 0.01)
    is_bid_mode = str(mark_mode).upper().startswith("BID")

    entry_time_str = str(trade.get("entry_timestamp", ""))[:10]
    try:
        entry_date = datetime.date.fromisoformat(entry_time_str)
        days_held = max(0, (datetime.date.today() - entry_date).days)
    except Exception:
        days_held = 0

    dte_entry = int(trade.get("dte_at_entry", trade.get("dte", 35)))
    dte_remaining = max(1, dte_entry - days_held)

    t_entry = max(1, dte_entry) / 365.0
    t_rem = dte_remaining / 365.0
    r = 0.0425

    stored_iv = trade.get("implied_vol_at_entry") or trade.get("iv")
    if stored_iv and float(stored_iv) > 0.05:
        raw_iv = float(stored_iv)
        sigma_est = raw_iv / 100.0 if raw_iv > 3.0 else max(0.12, raw_iv)
    else:
        intrinsic_entry = max(0.0, entry_spot - strike) if opt_type == "CALL" else max(0.0, strike - entry_spot)
        if is_spread and short_k is not None:
            short_intr_e = max(0.0, entry_spot - short_k) if opt_type == "CALL" else max(0.0, short_k - entry_spot)
            intrinsic_entry = max(0.0, intrinsic_entry - short_intr_e)
        if entry_prem <= intrinsic_entry:
            sigma_est = 0.25
        else:
            sigma_est = 0.42
            sqrt_t = math.sqrt(t_entry)
            for _ in range(8):
                if opt_type == "CALL":
                    m_l, _ = rbe3.bs_call_price_delta(entry_spot, strike, t_entry, r, sigma_est)
                    m_s, _ = (rbe3.bs_call_price_delta(entry_spot, short_k, t_entry, r, sigma_est) if is_spread and short_k else (0.0, 0.0))
                else:
                    m_l, _ = rbe3.bs_put_price_delta(entry_spot, strike, t_entry, r, sigma_est)
                    m_s, _ = (rbe3.bs_put_price_delta(entry_spot, short_k, t_entry, r, sigma_est) if is_spread and short_k else (0.0, 0.0))
                m_p = m_l - m_s
                diff = entry_prem - m_p
                if abs(diff) < 0.005:
                    break
                d1 = (math.log(max(1e-4, entry_spot / strike)) + (r + 0.5 * sigma_est**2) * t_entry) / (sigma_est * sqrt_t)
                phi_d1 = math.exp(-0.5 * d1 * d1) / 2.5066282746310002
                true_vega = max(0.01, entry_spot * sqrt_t * phi_d1)
                sigma_est = float(np.clip(sigma_est + diff / true_vega, 0.10, 2.50))
            trade["implied_vol_at_entry"] = round(sigma_est, 4)

    if opt_type == "CALL":
        bs_entry, _ = rbe3.bs_call_price_delta(entry_spot, strike, t_entry, r, sigma_est)
        bs_now, _ = rbe3.bs_call_price_delta(current_spot, strike, t_rem, r, sigma_est)
        intrinsic_now = max(0.0, current_spot - strike)
    else:
        bs_entry, _ = rbe3.bs_put_price_delta(entry_spot, strike, t_entry, r, sigma_est)
        bs_now, _ = rbe3.bs_put_price_delta(current_spot, strike, t_rem, r, sigma_est)
        intrinsic_now = max(0.0, strike - current_spot)

    short_bs_entry = 0.0
    short_bs_now = 0.0
    if is_spread and short_k is not None:
        if opt_type == "CALL":
            short_bs_entry, _ = rbe3.bs_call_price_delta(entry_spot, short_k, t_entry, r, sigma_est)
            short_bs_now, _ = rbe3.bs_call_price_delta(current_spot, short_k, t_rem, r, sigma_est)
            intrinsic_now = max(0.0, min(abs(short_k - strike), intrinsic_now - max(0.0, current_spot - short_k)))
        else:
            short_bs_entry, _ = rbe3.bs_put_price_delta(entry_spot, short_k, t_entry, r, sigma_est)
            short_bs_now, _ = rbe3.bs_put_price_delta(current_spot, short_k, t_rem, r, sigma_est)
            intrinsic_now = max(0.0, min(abs(short_k - strike), intrinsic_now - max(0.0, short_k - current_spot)))

    # Anchor mark to 1-credit cached OPRA exchange chain when available
    live_long_mark = None
    live_short_mark = None
    try:
        t_sym = str(trade.get("symbol", "")).strip().upper()
        if t_sym:
            exp_iso = _parse_iso_expiration(str(trade.get("expiration_date", "")))
            md_df = _fetch_cached_option_chain_df(
                t_sym,
                expiration=exp_iso,
                dte=dte_remaining,
                strike_limit=60,
                ttl=900,
            )
            if md_df is not None and not md_df.empty and "side" in md_df.columns:
                side_df = md_df[md_df["side"].astype(str).str.lower() == opt_type.lower()].copy()
                if not side_df.empty and "strike" in side_df.columns:
                    side_df["_k_diff"] = (side_df["strike"].astype(float) - strike).abs()
                    best_row = side_df.sort_values("_k_diff").iloc[0]
                    if float(best_row["_k_diff"]) <= max(1.0, strike * 0.02):
                        b_v = float(best_row.get("bid", 0.0) or 0.0)
                        a_v = float(best_row.get("ask", 0.0) or 0.0)
                        m_val = float(best_row.get("mid", 0.0) or 0.0)
                        if m_val <= 0.01 and b_v > 0 and a_v >= b_v:
                            m_val = (b_v + a_v) / 2.0
                        if is_bid_mode and b_v > 0.0:
                            live_long_mark = b_v
                        elif m_val > 0.01:
                            live_long_mark = m_val

                    if is_spread and short_k is not None:
                        side_df["_k2_diff"] = (side_df["strike"].astype(float) - short_k).abs()
                        best_k2 = side_df.sort_values("_k2_diff").iloc[0]
                        if float(best_k2["_k2_diff"]) <= max(1.0, short_k * 0.02):
                            b2 = float(best_k2.get("bid", 0.0) or 0.0)
                            a2 = float(best_k2.get("ask", 0.0) or 0.0)
                            m2 = float(best_k2.get("mid", 0.0) or 0.0)
                            if m2 <= 0.01 and b2 > 0 and a2 >= b2:
                                m2 = (b2 + a2) / 2.0
                            if is_bid_mode and a2 > 0.0:
                                live_short_mark = a2  # Closing short leg pays ask
                            elif m2 > 0.01:
                                live_short_mark = m2
    except Exception:
        live_long_mark = None
        live_short_mark = None

    if is_spread and short_k is not None:
        spread_width = abs(short_k - strike)
        if live_long_mark is not None:
            s_leg_m = live_short_mark if live_short_mark is not None else short_bs_now
            raw_mark = max(0.01, min(spread_width, live_long_mark - s_leg_m))
        else:
            bs_sp_entry = max(0.05, bs_entry - short_bs_entry)
            bs_sp_now = max(0.01, min(spread_width, bs_now - short_bs_now))
            raw_mark = entry_prem + (bs_sp_now - bs_sp_entry)
            if is_bid_mode:
                raw_mark *= 0.96
            raw_mark = min(spread_width, max(0.01, raw_mark))
        est_mark = max(0.01, min(spread_width, max(intrinsic_now, raw_mark)))
    else:
        if live_long_mark is not None:
            est_mark = max(0.01, intrinsic_now, live_long_mark)
        else:
            raw_mark = entry_prem + (bs_now - bs_entry)
            if is_bid_mode:
                raw_mark = max(intrinsic_now, raw_mark * 0.97)
            est_mark = max(0.01, intrinsic_now, raw_mark)

    # Exact Net Position Greeks
    g_long = _exact_leg_greeks(current_spot, strike, t_rem, r=r, sigma=sigma_est, opt_type=opt_type)
    if is_spread and short_k is not None:
        g_short = _exact_leg_greeks(current_spot, short_k, t_rem, r=r, sigma=sigma_est, opt_type=opt_type)
        net_delta_per_sh = g_long["delta"] - g_short["delta"]
        net_theta_per_sh = g_long["theta"] - g_short["theta"]
        net_vega_per_sh = g_long["vega"] - g_short["vega"]
    else:
        net_delta_per_sh = g_long["delta"]
        net_theta_per_sh = g_long["theta"]
        net_vega_per_sh = g_long["vega"]

    is_sell_pos = "SELL" in str(trade.get("action", "BUY")).upper()
    sign_pos = -1.0 if is_sell_pos else 1.0
    net_delta_shares = round(sign_pos * net_delta_per_sh * 100.0 * qty, 1)
    net_delta_dollars = round(net_delta_shares * current_spot, 2)
    daily_theta_dollars = round(sign_pos * net_theta_per_sh * 100.0 * qty, 2)
    net_vega_dollars = round(sign_pos * net_vega_per_sh * 100.0 * qty, 2)

    est_mark = round(est_mark, 2)
    current_value = round(qty * est_mark * 100.0, 2)
    if is_sell_pos:
        # Short option / credit: unrealized gain when buyback cost drops below credit received
        unrealized_dollar = round(total_cost - current_value, 2)
        if is_spread and short_k is not None:
            risk_denom = max(1.0, abs(short_k - strike) * 100.0 * qty - total_cost)
        else:
            risk_denom = max(1.0, total_cost)
        unrealized_pct = round((unrealized_dollar / risk_denom) * 100.0, 1)
    else:
        unrealized_dollar = round(current_value - total_cost, 2)
        unrealized_pct = round((unrealized_dollar / max(1.0, total_cost)) * 100.0, 1)

    return {
        "current_spot": round(current_spot, 2),
        "spot_change_pct": round(((current_spot - entry_spot) / max(0.01, entry_spot)) * 100.0, 2),
        "current_mark": est_mark,
        "current_value": current_value,
        "unrealized_dollar": unrealized_dollar,
        "unrealized_pct": unrealized_pct,
        "dte_remaining": dte_remaining,
        "days_held": days_held,
        "strategy": strategy,
        "short_strike": short_k,
        "net_delta_shares": net_delta_shares,
        "net_delta_dollars": net_delta_dollars,
        "daily_theta_dollars": daily_theta_dollars,
        "net_vega_dollars": net_vega_dollars,
    }


# =========================================================================
# VIEW 1: CHARLES SCHWAB PRACTICE DESK & PAPER DIARY ("WHOLE PAGE TO MYSELF")
# =========================================================================

@st.dialog("⚡ Charles Schwab Order Execution & What-If Analyzer", width="large")
def render_schwab_order_dialog(active_leg: Dict[str, Any], cand_intel: Optional[Dict[str, Any]] = None):
    """
    Obsidian Frosted-Glass Charles Schwab Order Execution Dialog.
    Accepts either `(active_leg, cand_intel)` or a single `prefill` dict `(active_leg)`.
    Persists signed `-200..+200` Conviction Score via `diary_db.create_simulated_trade`.
    """
    _inject_obsidian_desk_css()
    prefill = st.session_state.get("schwab_prefill") or {}
    active_leg = active_leg or prefill or {}
    cand_intel = cand_intel or {}

    m = cand_intel.get("metrics", {}) if isinstance(cand_intel, dict) else {}
    spot_price = float(
        m.get("price")
        or active_leg.get("spot_price")
        or active_leg.get("current_stock_price")
        or prefill.get("spot_price")
        or prefill.get("current_stock_price")
        or 100.0
    )
    tgt_p = float(m.get("target_price") or active_leg.get("target_price") or prefill.get("target_price") or spot_price * 1.08)
    inv_p = float(m.get("invalidation_price") or active_leg.get("stop_price") or prefill.get("stop_price") or spot_price * 0.94)

    leg_sym = str(active_leg.get("symbol") or prefill.get("symbol") or "TICKER").upper()
    leg_type = str(active_leg.get("option_type") or prefill.get("option_type") or "CALL").upper()
    leg_action = str(active_leg.get("action") or prefill.get("action") or "BUY_TO_OPEN")
    leg_strike = float(active_leg.get("strike") or prefill.get("strike") or spot_price)
    leg_limit = float(active_leg.get("limit_price") or prefill.get("limit_price") or 1.0 or 1.0)
    leg_dte = int(active_leg.get("dte") or prefill.get("dte") or 35)
    leg_exp = str(active_leg.get("expiration_date") or active_leg.get("expiration") or prefill.get("expiration_date") or prefill.get("expiration") or "Cycle")
    leg_iv = float(active_leg.get("iv") or prefill.get("iv") or 0.40)
    leg_notes = str(active_leg.get("notes") or prefill.get("notes") or "")

    # Read -200..+200 Conviction Score (checking prefill contract + fallbacks)
    score_200 = int(
        prefill.get("conviction_score_200")
        or prefill.get("conviction_score")
        or active_leg.get("conviction_score_200")
        or active_leg.get("conviction_score")
        or cand_intel.get("blueprint", {}).get("conviction_score_200")
        or cand_intel.get("blueprint", {}).get("composite_score")
        or 0
    )
    _, is_200_scale, rec_dte_bucket, dte_rationale = _resolve_conviction_and_dte(
        prefill=prefill,
        active_leg=active_leg,
        cand_intel=cand_intel,
        opt_type=leg_type,
        fallback_dte=leg_dte,
    )
    conv_badge_html = _format_conviction_badge_html(score_200, leg_type, is_legacy_100=False, show_tier=True)
    dte_badge_html = _format_dte_badge_html(rec_dte_bucket, rationale=dte_rationale, exact_dte=leg_dte)

    # Header Ribbon (Obsidian Frosted-Glass + Rich Hyper-Orange)
    def_strat = str(active_leg.get("strategy") or prefill.get("strategy") or "SINGLE_LEG").upper()
    if def_strat not in ("SINGLE_LEG", "VERTICAL_DEBIT_SPREAD"):
        def_strat = "SINGLE_LEG"
    def_short_k = active_leg.get("short_strike") or prefill.get("short_strike")
    if not def_short_k or float(def_short_k) <= 0:
        def_short_k = round(leg_strike * (1.05 if leg_type == "CALL" else 0.95), 1)
    else:
        def_short_k = float(def_short_k)

    render_clean_html(f"""
    <div style="background: rgba(15, 18, 26, 0.78); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 107, 0, 0.35); border-top: 1px solid rgba(255, 255, 255, 0.14); border-radius: 14px; padding: 14px 18px; margin-bottom: 14px; box-shadow: 0 12px 32px rgba(0,0,0,0.65);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">
                <span class="obs-pill-orange">SCHWAB ARMED ORDER</span>
                <span class="obs-mono" style="font-size: 1.15rem; font-weight: 800; color: {'#34D399' if leg_type=='CALL' else '#FB7185'};">
                    {_esc(leg_sym)} ${leg_strike:.2f} {_esc(leg_type)}
                </span>
                <span style="font-size: 0.80rem; color: #94A3B8;">({leg_dte} DTE &bull; {_esc(leg_exp)})</span>
                {conv_badge_html}
                {dte_badge_html}
            </div>
            <div class="obs-mono" style="font-size: 0.98rem; color: #E2E8F0;">
                Underlying Spot: <b style="color: #F8FAFC;">${spot_price:.2f}</b>
            </div>
        </div>
    </div>
    """)

    # Order Specification Row
    st.session_state.setdefault(
        "dlg_strategy",
        "VERTICAL_DEBIT_SPREAD" if def_strat == "VERTICAL_DEBIT_SPREAD" else "SINGLE_LEG",
    )
    st.session_state.setdefault(
        "dlg_action",
        "BUY_TO_OPEN" if "BUY" in leg_action else "SELL_TO_OPEN",
    )
    st.session_state.setdefault("dlg_ord_type", "LIMIT")
    st.session_state.setdefault("dlg_qty", 1)

    col_k0, col_k1, col_k2, col_k3, col_k4 = st.columns([1.3, 1.1, 1.0, 0.9, 1.1])
    with col_k0:
        sel_strategy = st.selectbox(
            "Strategy Structure",
            ["SINGLE_LEG", "VERTICAL_DEBIT_SPREAD"],
            key="dlg_strategy",
            help="SINGLE_LEG buys pure directional convexity; VERTICAL_DEBIT_SPREAD sells a further OTM wing to cut cost & IV crush.",
        )
    with col_k1:
        opt_action = st.selectbox(
            "Action",
            ["BUY_TO_OPEN", "SELL_TO_OPEN"],
            key="dlg_action",
            help="BUY_TO_OPEN pays cash up front for limited risk; SELL_TO_OPEN collects credit up front.",
        )
    with col_k2:
        opt_ord_type = st.selectbox("Order Type", ["LIMIT", "MARKET"], key="dlg_ord_type", help="LIMIT caps your entry fill price; avoid MARKET orders on wide spreads.")
    with col_k3:
        opt_qty = st.number_input("Contracts", min_value=1, max_value=100, step=1, key="dlg_qty")
    with col_k4:
        def_dlg_limit = (
            float(active_leg.get("net_debit") or prefill.get("net_debit") or leg_limit)
            if sel_strategy == "VERTICAL_DEBIT_SPREAD"
            else float(leg_limit)
        )
        st.session_state.setdefault("dlg_limit", round(max(0.01, def_dlg_limit), 2))
        opt_limit = st.number_input("Limit Price ($)", min_value=0.01, max_value=2500.0, step=0.01, format="%.2f", key="dlg_limit", help="Price per share (multiply by 100 for per-contract cash cost).")

    short_k_val: Optional[float] = None
    if sel_strategy == "VERTICAL_DEBIT_SPREAD":
        st.session_state.setdefault("dlg_short_strike", float(def_short_k))
        short_k_val = float(
            st.number_input(
                "Short Strike K2 ($)",
                min_value=0.5,
                max_value=5000.0,
                step=0.5,
                format="%.2f",
                key="dlg_short_strike",
                help="The further-OTM wing sold to subsidize your long strike and reduce daily Theta bleed.",
            )
        )

    sigma_dlg = leg_iv / 100.0 if leg_iv > 3.0 else max(0.15, leg_iv)
    st.session_state.setdefault("dlg_tgt_val", float(tgt_p if leg_type == "CALL" else inv_p))
    st.session_state.setdefault("dlg_stp_val", float(inv_p if leg_type == "CALL" else tgt_p))
    col_sim_tgt, col_sim_stp = st.columns(2)
    with col_sim_tgt:
        tgt_val = st.number_input("1–5D Underlying Target ($)", step=0.5, format="%.2f", key="dlg_tgt_val")
    with col_sim_stp:
        stp_val = st.number_input("Hard Stock Invalidation / Stop ($)", step=0.5, format="%.2f", key="dlg_stp_val")

    pay_dlg = _compute_order_payoff_summary(
        spot_price=spot_price,
        strike_p=leg_strike,
        limit_p=opt_limit,
        qty=int(opt_qty),
        dte=leg_dte,
        sigma=sigma_dlg,
        opt_type=leg_type,
        opt_action=opt_action,
        strategy=sel_strategy,
        short_strike=short_k_val,
        tgt_val=tgt_val,
        stp_val=stp_val,
    )
    is_spread_dlg = pay_dlg["is_spread"]
    is_sell_dlg = pay_dlg["is_sell"]
    outlay_lbl = "Collateral / Risk Basis" if is_sell_dlg else "Cash Outlay (Max Risk)"
    credit_note = f"Net Credit: +${pay_dlg['net_credit']:,.2f} &bull; " if is_sell_dlg else ""

    render_clean_html(f"""
    <div style="background: rgba(15, 18, 26, 0.68); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 16px; margin: 12px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 0.74rem; font-weight: 800; color: #FF8533; text-transform: uppercase; letter-spacing: 0.05em;">
                <i class="fa-solid fa-chart-line fa-icon-inline"></i> Live Payoff What-If Matrix ({'Vertical Spread' if is_spread_dlg else 'Single Leg'})
            </span>
            <span style="font-size: 0.70rem; color: #94A3B8;">{_esc(dte_rationale)}</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 10px;">
            <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; padding: 9px 11px;">
                <div style="font-size: 0.68rem; color: #94A3B8;">{outlay_lbl}</div>
                <div class="obs-mono" style="font-size: 0.98rem; font-weight: 800; color: #F1F5F9;">${pay_dlg['total_outlay']:,.2f}</div>
                <div style="font-size: 0.66rem; color: #64748B;">{credit_note}Includes $0.65/leg Schwab fee</div>
            </div>
            <div style="background: rgba(16, 185, 129, 0.10); border: 1px solid rgba(16, 185, 129, 0.28); border-radius: 10px; padding: 9px 11px;">
                <div style="font-size: 0.68rem; color: #34D399; font-weight: 700;">At Target (${tgt_val:.2f})</div>
                <div class="obs-mono" style="font-size: 0.98rem; font-weight: 800; color: #34D399;">{'+' if pay_dlg['net_profit_at_tgt']>=0 else ''}${pay_dlg['net_profit_at_tgt']:,.2f}</div>
                <div class="obs-mono" style="font-size: 0.66rem; color: #34D399;">{'+' if pay_dlg['roi_at_tgt_pct']>=0 else ''}{pay_dlg['roi_at_tgt_pct']:.1f}% ROI</div>
            </div>
            <div style="background: rgba(244, 63, 94, 0.10); border: 1px solid rgba(244, 63, 94, 0.28); border-radius: 10px; padding: 9px 11px;">
                <div style="font-size: 0.68rem; color: #FB7185; font-weight: 700;">At Stop (${stp_val:.2f})</div>
                <div class="obs-mono" style="font-size: 0.98rem; font-weight: 800; color: #FB7185;">-${pay_dlg['est_loss_at_stop']:,.2f}</div>
                <div class="obs-mono" style="font-size: 0.66rem; color: #FB7185;">-{pay_dlg['stop_loss_pct']:.1f}% Drawdown</div>
            </div>
        </div>
        <div class="obs-mono" style="display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; font-size: 0.74rem; color: #CBD5E1; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 8px;">
            <span>Breakeven: <b style="color: #FBBF24;">${pay_dlg['be_price']:.2f} ({pay_dlg['be_pct']:+.1f}%)</b></span>
            <span>Net Delta: <b style="color: #F1F5F9;">{pay_dlg['pos_delta_shares']:+.0f} shares</b></span>
            <span>Daily Theta: <b style="color: #FB7185;">${pay_dlg['pos_theta_daily']:+.2f}/d</b></span>
            <span>Net Vega: <b style="color: #FF8533;">${pay_dlg['pos_vega_vol']:+.2f}/%</b></span>
        </div>
    </div>
    """)

    dlg_payoff_fig = rbc.create_schwab_payoff_curve_chart(
        symbol=leg_sym,
        spot_price=spot_price,
        strike=leg_strike,
        opt_type=leg_type,
        limit_price=opt_limit,
        qty=opt_qty,
        dte=leg_dte,
        iv=sigma_dlg,
        target_price=tgt_val,
        stop_price=stp_val,
        strategy=sel_strategy,
        short_strike=short_k_val,
    )
    st.plotly_chart(dlg_payoff_fig, width="stretch", config={"displayModeBar": False, "responsive": True})

    st.session_state.setdefault(
        "dlg_notes",
        leg_notes or f"Simulated {leg_dte}-DTE {leg_type} trade on {leg_sym} ${leg_strike:.2f} (Conviction {score_200:+d}).",
    )
    diary_notes_in = st.text_area(
        'Trading Diary Rationale ("Why am I taking this trade?")',
        height=60,
        key="dlg_notes"
    )

    col_btn_trans, col_btn_cancel = st.columns([2.0, 1.0])
    with col_btn_trans:
        if st.button("⚡ Transmit Simulated Order to Schwab Ledger", type="primary", width="stretch", key="btn_dlg_transmit"):
            _dlg_tif_raw = str(active_leg.get("time_in_force") or prefill.get("time_in_force") or "DAY").upper()
            _dlg_tif = "GTC" if "GTC" in _dlg_tif_raw else "DAY"
            _dlg_kwargs: Dict[str, Any] = {
                "symbol": leg_sym,
                "action": opt_action,
                "option_type": leg_type,
                "strike": leg_strike,
                "expiration_date": leg_exp,
                "quantity": opt_qty,
                "limit_price": opt_limit,
                "stock_price_at_entry": spot_price,
                "strategy": sel_strategy,
                "order_type": opt_ord_type,
                "target_stock_price": tgt_val,
                "stop_stock_price": stp_val,
                "conviction_score": score_200,
                "expected_basis_pct": float(m.get("expected_basis_pct", prefill.get("expected_basis_pct", 0.0)) or 0.0),
                "whale_badge": str(m.get("whale_badge", prefill.get("whale_badge", "⚪ TWO-WAY FLOW"))),
                "catalyst_tag": str(active_leg.get("catalyst_tag") or prefill.get("catalyst_tag") or ""),
                "notes": diary_notes_in,
                "dte": leg_dte,
                "short_strike": short_k_val if is_spread_dlg else None,
                "implied_vol_at_entry": sigma_dlg,
            }
            if "time_in_force" in inspect.signature(diary_db.create_simulated_trade).parameters:
                _dlg_kwargs["time_in_force"] = _dlg_tif
            trade_res = diary_db.create_simulated_trade(**_dlg_kwargs)
            st.session_state["schwab_last_receipt"] = trade_res
            if "schwab_active_leg" in st.session_state:
                del st.session_state["schwab_active_leg"]
            st.session_state["schwab_show_order_modal"] = False
            st.rerun()
    with col_btn_cancel:
        if st.button("Close Window", width="stretch", key="btn_dlg_close"):
            st.session_state["schwab_show_order_modal"] = False
            st.rerun()


def render_schwab_practice_diary_page():
    """Renders the full-page Obsidian Frosted-Glass Charles Schwab options practice desk and diary."""
    _inject_obsidian_desk_css()

    try:
        import ui_navigation
        ui_navigation.render_top_navigation_strip("Charles Schwab Practice Desk & Diary")
    except Exception:
        ui_navigation = None

    logo_html = get_schwab_svg_logo(22)
    render_clean_html(f"""
    <div class="schwab-ribbon">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    {logo_html}
                    <span class="obs-pill-orange">PAPER MARGIN &bull; 30/45D HIGH-DELTA &amp; 90D CHAIN</span>
                </div>
                <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 6px;">
                    Account: <b style="color: #E2E8F0;">Simulated Margin (XX-774921)</b> &bull; Standard Charles Schwab Options Structure ($0.65 contract fee, $0.00 base commission)
                </div>
            </div>
            <div style="font-size: 0.74rem; color: #34D399; background: rgba(16, 185, 129, 0.12); padding: 5px 12px; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.34);">
                <i class="fa-solid fa-database fa-icon-inline"></i> SQLite WAL Persistent Database Active
            </div>
        </div>
    </div>
    """)

    # 1. Fetch Open Trades & Live Batch Quotes to compute live portfolio mark-to-market
    open_trades = diary_db.get_open_trades()
    open_symbols = list(set([t["symbol"] for t in open_trades]))
    quote_universe = list(set(open_symbols + ["SPY"])) if open_symbols else ["SPY"]
    live_quotes = rbe3.fmp_batch_quotes(quote_universe, ttl=30)
    spy_spot = float((live_quotes.get("SPY") or {}).get("price") or 580.0)

    mark_mode_sel = st.radio(
        "Mark-to-Market Valuation Mode",
        options=["MID (Fair Value)", "BID_LIQUIDATION (Conservative Exit)"],
        index=0,
        horizontal=True,
        key="schwab_mark_mode_toggle",
    )
    mark_mode_arg = "BID_LIQUIDATION" if "BID" in mark_mode_sel else "MID"

    trades_with_live = []
    sym_cost_map: Dict[str, float] = {}
    for t in open_trades:
        sym = t["symbol"]
        q = live_quotes.get(sym, {})
        spot = float(q.get("price", t.get("stock_price_at_entry", 100.0)) or t.get("stock_price_at_entry", 100.0))
        m = estimate_live_option_mark(t, spot, mark_mode=mark_mode_arg)
        t_live = dict(t)
        t_live.update({
            "live_spot": m["current_spot"],
            "live_mark": m["current_mark"],
            "live_current_value": m["current_value"],
            "live_unrealized_pnl_dollar": m["unrealized_dollar"],
            "live_unrealized_pnl_pct": m["unrealized_pct"],
            "dte_remaining": m.get("dte_remaining", 35),
            "days_held": m["days_held"],
            "net_delta_shares": m.get("net_delta_shares", 0.0),
            "net_delta_dollars": m.get("net_delta_dollars", 0.0),
            "daily_theta_dollars": m.get("daily_theta_dollars", 0.0),
            "net_vega_dollars": m.get("net_vega_dollars", 0.0),
        })
        trades_with_live.append(t_live)
        sym_cost_map[sym] = sym_cost_map.get(sym, 0.0) + float(t.get("total_cost", 0.0) or 0.0)

    summary = diary_db.get_diary_portfolio_summary(trades_with_live)
    port_delta_dlr = sum(float(x.get("net_delta_dollars", 0.0) or 0.0) for x in trades_with_live)
    port_theta_dlr = sum(float(x.get("daily_theta_dollars", 0.0) or 0.0) for x in trades_with_live)
    port_vega_dlr = sum(float(x.get("net_vega_dollars", 0.0) or 0.0) for x in trades_with_live)
    spy_equiv_sh = port_delta_dlr / max(1.0, spy_spot)
    total_deployed = max(1.0, float(summary.get("active_capital_deployed", 0.0) or 0.0))
    max_single_sym, max_single_cost = max(sym_cost_map.items(), key=lambda kv: kv[1]) if sym_cost_map else ("NONE", 0.0)
    max_conc_pct = (max_single_cost / total_deployed * 100.0) if sym_cost_map else 0.0

    p_val = summary["current_portfolio_value"]
    realized_d = summary["realized_pnl_dollars"]
    unrealized_d = summary["unrealized_pnl_dollars"]
    win_rate = summary["win_rate_pct"]
    p_factor = summary["profit_factor"]
    active_cnt = summary["open_trades_count"]
    buying_power = max(0.0, 100_000.0 - summary["active_capital_deployed"] + realized_d)

    unreal_col = "#34D399" if unrealized_d >= 0 else "#FB7185"
    real_col = "#34D399" if realized_d >= 0 else "#FB7185"

    render_clean_html(f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 12px;">
        <div class="rm-command-card" style="border-left: 3px solid #FF6B00;">
            <div class="rm-command-label">Simulated Portfolio Equity</div>
            <div class="rm-command-value" style="color: #F1F5F9;">${p_val:,.2f}</div>
            <div class="rm-command-sub">Starting Paper Capital: $100,000.00</div>
        </div>
        <div class="rm-command-card">
            <div class="rm-command-label">Options Buying Power</div>
            <div class="rm-command-value" style="color: #FF8533;">${buying_power:,.2f}</div>
            <div class="rm-command-sub">Deployed in Open Contracts: ${summary['active_capital_deployed']:,.2f}</div>
        </div>
        <div class="rm-command-card" style="border-left: 3px solid {unreal_col};">
            <div class="rm-command-label">Open Mark-to-Market P&amp;L ({'BID' if mark_mode_arg.startswith('BID') else 'MID'})</div>
            <div class="rm-command-value" style="color: {unreal_col};">{'+' if unrealized_d >= 0 else ''}${unrealized_d:,.2f}</div>
            <div class="rm-command-sub">Active Positions: <b>{active_cnt}</b> contracts</div>
        </div>
        <div class="rm-command-card" style="border-left: 3px solid {real_col};">
            <div class="rm-command-label">Realized Closed P&amp;L</div>
            <div class="rm-command-value" style="color: {real_col};">{'+' if realized_d >= 0 else ''}${realized_d:,.2f}</div>
            <div class="rm-command-sub">Closed Trades: <b>{summary['total_closed_trades']}</b> ({summary['winning_trades_count']}W / {summary['losing_trades_count']}L)</div>
        </div>
        <div class="rm-command-card">
            <div class="rm-command-label">Discipline &amp; Win Rate</div>
            <div class="rm-command-value" style="color: #FBBF24;">{win_rate:.1f}%</div>
            <div class="rm-command-sub">Profit Factor: <b>{p_factor:.2f}</b> | Edge Practice</div>
        </div>
    </div>
    <div class="obs-glass-card obs-mono" style="padding: 10px 16px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; font-size: 0.78rem; color: #CBD5E1; border-left: 3px solid #38BDF8;">
        <span><b style="color: #FF8533;">PORTFOLIO RISK &amp; NET GREEKS</b></span>
        <span>Net $&Delta;: <b style="color: {'#34D399' if port_delta_dlr >= 0 else '#FB7185'};">${port_delta_dlr:+,.0f}</b> ({spy_equiv_sh:+.1f} SPY-Equiv sh @ ${spy_spot:.2f})</span>
        <span>Daily Theta Burn: <b style="color: {'#FB7185' if port_theta_dlr < 0 else '#34D399'};">${port_theta_dlr:+.2f}/day</b></span>
        <span>Net Vega: <b style="color: #FF8533;">${port_vega_dlr:+.2f}/1% IV</b></span>
        <span>Max Underlying Conc.: <b style="color: {'#FB7185' if max_conc_pct > 45 else '#34D399'};">{max_single_sym} ({max_conc_pct:.0f}%)</b></span>
    </div>
    """)

    # Order Confirmation Receipt
    if "schwab_last_receipt" in st.session_state:
        rec = st.session_state["schwab_last_receipt"]
        _rec_oid = _esc(rec.get("schwab_order_id", ""))
        _rec_act = _esc(rec.get("action", ""))
        _rec_sym = _esc(rec.get("symbol", ""))
        _rec_exp = _esc(rec.get("expiration_date", ""))
        _rec_type = _esc(rec.get("option_type", ""))
        render_clean_html(f"""
        <div class="schwab-receipt-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="obs-pill-orange">CHARLES SCHWAB CONFIRMATION</span>
                    <span style="font-weight: 800; font-size: 0.95rem; color: #F1F5F9;">Order ID: <code class="obs-mono">{_rec_oid}</code></span>
                </div>
                <span style="background: rgba(16, 185, 129, 0.18); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.42); font-size: 0.74rem; font-weight: 800; padding: 2px 10px; border-radius: 9999px;">
                    FILLED AT LIMIT
                </span>
            </div>
            <div class="obs-mono" style="font-size: 0.82rem; color: #CBD5E1; line-height: 1.5;">
                Simulated execution: <b style="color: #F8FAFC;">{_rec_act} {rec['quantity']} Contract(s) {_rec_sym} {_rec_exp} ${rec['strike']:.2f} {_rec_type}</b> @ <b style="color: #FF8533;">${rec['limit_price']:.2f}</b> Limit.<br>
                Total Debit: <b style="color: #F1F5F9;">${rec['total_cost']:.2f}</b> (includes ${rec['commission_fee']:.2f} Schwab fee). Stock spot at entry: <b>${rec['stock_price_at_entry']:.2f}</b>.
            </div>
        </div>
        """)
        if st.button("Dismiss Receipt", key="btn_dismiss_receipt"):
            del st.session_state["schwab_last_receipt"]
            st.rerun()

    # =========================================================================
    # STEP 2: ACTIVE TICKER SELECTION & COMPREHENSIVE INSTITUTIONAL INTEL COCKPIT
    # =========================================================================
    prefill = st.session_state.get("schwab_prefill", {})

    if "sim_active_symbol" not in st.session_state:
        init_sym = prefill.get("symbol", st.session_state.get("selected_ticker", "MPWR")).upper()
        st.session_state["sim_active_symbol"] = init_sym
        st.session_state["sim_ticker_sym_unified"] = init_sym

    if "schwab_prefill" in st.session_state and "symbol" in st.session_state["schwab_prefill"]:
        ext_sym = st.session_state["schwab_prefill"]["symbol"].upper()
        if ext_sym != st.session_state["sim_active_symbol"] or st.session_state.get("schwab_prefill_needs_sync", False):
            st.session_state["sim_active_symbol"] = ext_sym
            st.session_state["sim_ticker_sym_unified"] = ext_sym
            exp_k = f"unified_chain_exp_{ext_sym}"
            if exp_k in st.session_state:
                del st.session_state[exp_k]
            st.session_state.pop(f"sb_{exp_k}", None)
            if "schwab_active_leg" in st.session_state:
                del st.session_state["schwab_active_leg"]
            st.session_state.pop("schwab_show_order_modal", None)
            _reset_ticket_widget_state()

    if "sim_ticker_sym_unified" in st.session_state and st.session_state["sim_ticker_sym_unified"] != st.session_state["sim_active_symbol"]:
        st.session_state["sim_ticker_sym_unified"] = st.session_state["sim_active_symbol"]

    active_sym = st.session_state["sim_active_symbol"]

    sector_list = list(rbe3.SECTORS.keys())
    curr_sec = _normalize_sector_safe(st.session_state.get("sim_selected_sector", sector_list[0] if sector_list else "Semiconductors"))
    if curr_sec not in sector_list and sector_list:
        curr_sec = sector_list[0]
    st.session_state["sim_selected_sector"] = curr_sec

    def set_active_sim_symbol(target_sym: str, sector_name: Optional[str] = None):
        target_sym = target_sym.strip().upper()
        if not target_sym:
            return
        st.session_state["sim_active_symbol"] = target_sym
        st.session_state["selected_ticker"] = target_sym
        st.session_state["schwab_prefill"] = {"symbol": target_sym}
        exp_k = f"unified_chain_exp_{target_sym}"
        if exp_k in st.session_state:
            del st.session_state[exp_k]
        st.session_state.pop(f"sb_{exp_k}", None)
        st.session_state["schwab_prefill_needs_sync"] = True
        if sector_name:
            st.session_state["sim_selected_sector"] = _normalize_sector_safe(sector_name)
        else:
            for s_k, s_v in rbe3.SECTORS.items():
                if target_sym in s_v.get("tickers", []):
                    st.session_state["sim_selected_sector"] = s_k
                    break
        if "schwab_active_leg" in st.session_state:
            del st.session_state["schwab_active_leg"]
        st.session_state.pop("schwab_show_order_modal", None)
        _reset_ticket_widget_state()

    sec_col1, sec_col2 = st.columns([1.8, 1.4], gap="medium")
    with sec_col1:
        chosen_sec = st.selectbox(
            "Select Target Sector (5 Desks)",
            options=sector_list,
            index=sector_list.index(curr_sec) if curr_sec in sector_list else 0,
            key="sim_sec_dropdown"
        )
        if chosen_sec != curr_sec:
            st.session_state["sim_selected_sector"] = chosen_sec
            first_ticker = rbe3.SECTORS[chosen_sec]["tickers"][0]
            set_active_sim_symbol(first_ticker, sector_name=chosen_sec)
            st.rerun()

    with sec_col2:
        def on_symbol_change():
            val = st.session_state.get("sim_ticker_sym_unified", "").strip().upper()
            if val:
                set_active_sim_symbol(val)

        st.text_input(
            "Symbol / ETF",
            key="sim_ticker_sym_unified",
            on_change=on_symbol_change,
            help="Type any US equity or Thematic ETF (REMX, SRVR, ROBO, JEDI) and press Enter"
        )

    sec_tickers = rbe3.SECTORS[chosen_sec]["tickers"][:8]
    st.caption(f"{chosen_sec} Constituents:")
    for row_start in range(0, len(sec_tickers), 6):
        row_slice = sec_tickers[row_start:row_start + 6]
        chip_cols = st.columns(6, gap="small")
        for idx, chip in enumerate(row_slice):
            with chip_cols[idx]:
                is_active_chip = (chip == active_sym)
                if st.button(
                    chip,
                    key=f"btn_sim_chip_{chosen_sec}_{chip}",
                    width="stretch",
                    type="primary" if is_active_chip else "secondary"
                ):
                    set_active_sim_symbol(chip)
                    st.rerun()

    # Quick Thematic ETF Jump Bar (REMX, SRVR, ROBO, JEDI, SMH, URA, QTUM, IGV)
    st.caption("Thematic ETF Baskets (1-Click Jump):")

    def _on_sim_etf_pick() -> None:
        picked_etf = st.session_state.get("sim_etf_pills")
        cur_sym = st.session_state.get("sim_active_symbol") or active_sym
        if picked_etf and picked_etf != cur_sym:
            set_active_sim_symbol(picked_etf)
            st.session_state["_sim_etf_synced_sym"] = picked_etf

    _sim_etf_def = active_sym if active_sym in _THEMATIC_ETF_CHIPS else None
    if st.session_state.get("_sim_etf_synced_sym") != active_sym:
        st.session_state["sim_etf_pills"] = _sim_etf_def
        st.session_state["_sim_etf_synced_sym"] = active_sym

    st.pills(
        "Thematic ETFs",
        options=_THEMATIC_ETF_CHIPS,
        selection_mode="single",
        key="sim_etf_pills",
        on_change=_on_sim_etf_pick,
        label_visibility="collapsed",
    )

    # Fetch Comprehensive Ticker Intelligence
    with st.spinner(f"Retrieving market intelligence & Rubberband edge for {active_sym}..."):
        cand_intel = rbe3.get_due_diligence_candidate(active_sym, vet_deep=True)

    if not cand_intel:
        st.error(f"Unable to retrieve quote data for {active_sym}. Check ticker or FMP API key.")
        return

    company_name = cand_intel.get("company_name", active_sym)
    company_logo = cand_intel.get("company_logo", "")
    is_etf = _is_etf_symbol(active_sym, cand_intel)
    sector_name = "Thematic ETF Basket" if is_etf else _normalize_sector_safe(cand_intel.get("sector", "Equities"))
    industry_name = cand_intel.get("industry", "Exchange-Traded Basket" if is_etf else "")
    mkt_cap = float(cand_intel.get("market_cap", 0.0) or 0.0)
    if mkt_cap >= 1e9:
        mkt_cap_str = f"${mkt_cap/1e9:.1f}B"
    elif mkt_cap >= 1e6:
        mkt_cap_str = f"${mkt_cap/1e6:.0f}M"
    else:
        mkt_cap_str = "ETF Basket" if is_etf else "Mid-Cap"
    description = cand_intel.get("description", "")

    m = cand_intel.get("metrics", {})
    bp = cand_intel.get("blueprint", {})

    spot_price = float(m.get("price", 100.0))
    spot_chg = float(m.get("change_pct_1d", 0.0))
    tgt_p = float(m.get("target_price", spot_price * 1.08))
    inv_p = float(m.get("invalidation_price", spot_price * 0.94))
    playbook_dir = str(bp.get("direction", m.get("action", "BUY CALL")))

    chg_col = "#34D399" if spot_chg >= 0 else "#FB7185"
    chg_sign = "+" if spot_chg >= 0 else ""

    # Target Strike Setup & Armed Leg Status
    prefill = st.session_state.get("schwab_prefill", {})
    raw_strike = prefill.get("strike")
    rec_strike = float(raw_strike) if raw_strike is not None else float(m.get("recommended_strike", spot_price))
    rec_opt_type = str(prefill.get("option_type", "CALL" if "CALL" in playbook_dir else "PUT")).upper()
    raw_dte = prefill.get("dte") or bp.get("recommended_dte") or m.get("recommended_dte")
    rec_dte = int(raw_dte) if raw_dte is not None else 35
    raw_limit = prefill.get("limit_price")
    rec_limit = float(raw_limit) if raw_limit is not None else 0.0

    has_active_leg = bool("schwab_active_leg" in st.session_state)
    active_leg_obj = st.session_state.get("schwab_active_leg", {})
    if has_active_leg and active_leg_obj.get("symbol") != active_sym:
        has_active_leg = False
        if "schwab_active_leg" in st.session_state:
            del st.session_state["schwab_active_leg"]
        active_leg_obj = {}

    if has_active_leg:
        display_strike = float(active_leg_obj.get("strike", rec_strike))
        display_type = str(active_leg_obj.get("option_type", rec_opt_type)).upper()
        display_limit = float(active_leg_obj.get("limit_price", rec_limit))
        display_dte = int(active_leg_obj.get("dte", rec_dte))
        raw_leg_iv = float(active_leg_obj.get("iv", 0.45))
        display_iv = raw_leg_iv / 100.0 if raw_leg_iv > 3.0 else max(0.12, raw_leg_iv)
        display_oi = int(active_leg_obj.get("oi", 1420))
        display_vol = int(active_leg_obj.get("vol", 380))
        display_bid = float(active_leg_obj.get("bid", display_limit * 0.96))
        display_ask = float(active_leg_obj.get("ask", display_limit * 1.04))
        setup_status_tag = "⚡ ARMED SCHWAB ORDER TICKET"
        setup_status_bg = "linear-gradient(135deg, #FF6B00 0%, #FF8533 100%)"
        setup_status_color = "#06070A"
    else:
        display_strike = rec_strike
        display_type = rec_opt_type
        display_dte = rec_dte
        raw_rv30 = float(m.get("realized_vol_30d", 45.0))
        display_iv = raw_rv30 / 100.0 if raw_rv30 > 3.0 else max(0.12, raw_rv30)
        def_c, _ = rbe3.bs_call_price_delta(spot_price, display_strike, display_dte / 365.0, 0.0425, display_iv)
        def_p, _ = rbe3.bs_put_price_delta(spot_price, display_strike, display_dte / 365.0, 0.0425, display_iv)
        display_limit = float(rec_limit if rec_limit > 0 else (def_c if display_type == "CALL" else def_p))
        display_oi = 850
        display_vol = 190
        display_bid = round(display_limit * 0.95, 2)
        display_ask = round(display_limit * 1.05, 2)
        setup_status_tag = "🎯 RECOMMENDED STRIKE SETUP"
        setup_status_bg = "rgba(255, 107, 0, 0.16)"
        setup_status_color = "#FF8533"

    score_200, is_200_scale, rec_dte_bucket, dte_rationale = _resolve_conviction_and_dte(
        prefill=prefill,
        active_leg=active_leg_obj,
        cand_intel=cand_intel,
        opt_type=display_type,
        fallback_dte=display_dte,
    )
    conv_badge_html = _format_conviction_badge_html(score_200, display_type, is_legacy_100=not is_200_scale, show_tier=True)
    dte_badge_html = _format_dte_badge_html(rec_dte_bucket, rationale=dte_rationale, exact_dte=display_dte)

    strike_greeks = calculate_option_greeks(
        s=spot_price,
        k=display_strike,
        t=display_dte / 365.0,
        r=0.0425,
        sigma=display_iv,
        opt_type=display_type
    )

    is_call = (display_type == "CALL")
    if is_call:
        is_itm = (spot_price > display_strike)
        be_spot = round(display_strike + display_limit, 2)
        diff_from_spot = display_strike - spot_price
        moneyness_tag = f"ITM (+${abs(diff_from_spot):.2f})" if is_itm else f"OTM (-${abs(diff_from_spot):.2f})"
        moneyness_badge_bg = "rgba(16, 185, 129, 0.16)" if is_itm else "rgba(245, 158, 11, 0.15)"
        moneyness_badge_col = "#34D399" if is_itm else "#FBBF24"
    else:
        is_itm = (spot_price < display_strike)
        be_spot = round(display_strike - display_limit, 2)
        diff_from_spot = spot_price - display_strike
        moneyness_tag = f"ITM (+${abs(diff_from_spot):.2f})" if is_itm else f"OTM (-${abs(diff_from_spot):.2f})"
        moneyness_badge_bg = "rgba(244, 63, 94, 0.16)" if is_itm else "rgba(245, 158, 11, 0.15)"
        moneyness_badge_col = "#FB7185" if is_itm else "#FBBF24"

    be_diff = be_spot - spot_price
    be_pct = (be_diff / spot_price) * 100.0 if spot_price else 0.0

    p_nodes = [inv_p, spot_price, display_strike, be_spot, tgt_p]
    min_scale = min(p_nodes) * 0.96
    max_scale = max(p_nodes) * 1.04
    span_scale = max(1.0, max_scale - min_scale)

    def to_pct(val: float) -> float:
        return max(5.0, min(95.0, ((val - min_scale) / span_scale) * 100.0))

    pct_stop = to_pct(inv_p)
    pct_spot = to_pct(spot_price)
    pct_strike = to_pct(display_strike)
    pct_be = to_pct(be_spot)
    pct_tgt = to_pct(tgt_p)

    etf_pill_html = (
        '<span style="background: rgba(255, 107, 0, 0.14); color: #FF8533; border: 1px solid rgba(255, 107, 0, 0.35); font-size: 0.70rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">ETF BASKET</span>'
        if is_etf else ""
    )

    _logo_safe = _safe_http_url(company_logo)
    _sym_safe = _esc(active_sym)
    _comp_safe = _esc(company_name)
    _sec_safe = _esc(sector_name)
    _mcap_safe = _esc(mkt_cap_str)
    _ind_safe = _esc(industry_name)
    _desc_short = (description[:110] + "...") if len(description) > 110 else description
    _desc_safe = _esc(_desc_short)
    _exp_lbl_safe = _esc(active_leg_obj.get("expiration_date", prefill.get("expiration_date", "Cycle")))

    # Obsidian Frosted-Glass Ticker HUD & Strike Risk Profile Visualizer
    render_clean_html(f"""
    <div class="schwab-strike-visualizer">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <img src="{_logo_safe}" style="width: 44px; height: 44px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.12); object-fit: contain; background: rgba(10,12,18,0.85);" onerror="this.style.display='none'"/>
                <div>
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span style="font-size: 1.50rem; font-weight: 800; color: #F1F5F9; letter-spacing: -0.02em;">{_sym_safe}</span>
                        <span style="font-size: 0.95rem; font-weight: 600; color: #CBD5E1;">{_comp_safe}</span>
                        <span style="background: rgba(255, 255, 255, 0.06); color: #CBD5E1; border: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.72rem; font-weight: 700; padding: 2px 9px; border-radius: 9999px;">
                            {_sec_safe} &bull; {_mcap_safe}
                        </span>
                        {etf_pill_html}
                        {conv_badge_html}
                    </div>
                    <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 4px;">
                        {_ind_safe} &bull; <i>"{_desc_safe}"</i>
                    </div>
                </div>
            </div>
            <div style="text-align: right;">
                <div class="obs-mono" style="font-size: 1.60rem; font-weight: 800; color: #F1F5F9;">
                    ${spot_price:.2f}
                    <span style="font-size: 1.05rem; color: {chg_col}; font-weight: 700;">({chg_sign}{spot_chg:.2f}%)</span>
                </div>
                <div class="obs-mono" style="font-size: 0.75rem; color: #94A3B8;">OPRA Cached &amp; FMP Stream &bull; Bid ${display_bid:.2f} &times; Ask ${display_ask:.2f}</div>
            </div>
        </div>
        <div style="margin-top: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                <span style="background: {setup_status_bg}; color: {setup_status_color}; border: 1px solid rgba(255, 107, 0, 0.40); font-size: 0.68rem; font-weight: 800; padding: 3px 10px; border-radius: 9999px; letter-spacing: 0.05em; text-transform: uppercase;">
                    {setup_status_tag}
                </span>
                <span class="obs-mono" style="font-size: 1.25rem; font-weight: 800; color: {'#34D399' if is_call else '#FB7185'}; letter-spacing: -0.01em;">
                    {_sym_safe} ${display_strike:.2f} {_esc(display_type)}
                </span>
                {dte_badge_html}
                <span style="font-size: 0.82rem; color: #94A3B8; font-weight: 600;">
                    (Exp: {_exp_lbl_safe})
                </span>
                <span style="background: {moneyness_badge_bg}; color: {moneyness_badge_col}; border: 1px solid {moneyness_badge_col}40; font-size: 0.74rem; font-weight: 800; padding: 2px 8px; border-radius: 6px;">
                    {moneyness_tag}
                </span>
                <span class="obs-mono" style="background: rgba(255, 107, 0, 0.14); color: #FF8533; border: 1px solid rgba(255, 107, 0, 0.36); font-size: 0.75rem; font-weight: 800; padding: 2px 8px; border-radius: 6px;">
                    Mid: ${display_limit:.2f}
                </span>
            </div>
            <div class="obs-mono" style="display: flex; align-items: center; gap: 12px; font-size: 0.80rem; color: #CBD5E1;">
                <span>Breakeven: <b style="color: #C084FC;">${be_spot:.2f}</b> <span style="color: {'#34D399' if be_diff<=0 else '#FBBF24'}; font-size: 0.72rem;">({be_diff:+.2f} / {be_pct:+.1f}%)</span></span>
                <span>1–5D Target: <b style="color: #34D399;">${tgt_p:.2f}</b></span>
                <span>Hard Stop: <b style="color: #FB7185;">${inv_p:.2f}</b></span>
            </div>
        </div>
        <div style="position: relative; height: 80px; margin: 20px 0 10px 0; background: rgba(8, 10, 16, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 0 10px;">
            <div style="position: absolute; top: 36px; left: 16px; right: 16px; height: 8px; border-radius: 4px; background: linear-gradient(90deg, #F43F5E 0%, #F59E0B 35%, #FF6B00 62%, #10B981 100%);"></div>
            <div style="position: absolute; left: calc({pct_stop}% - 26px); top: 10px; text-align: center; width: 52px; z-index: 2;">
                <div style="font-size: 0.64rem; color: #FB7185; font-weight: 800; letter-spacing: 0.04em;">STOP</div>
                <div style="width: 10px; height: 10px; background: #F43F5E; border: 2px solid #F1F5F9; border-radius: 50%; margin: 3px auto; box-shadow: 0 0 6px #F43F5E;"></div>
                <div class="obs-mono" style="font-size: 0.72rem; color: #FDA4AF; font-weight: 700;">${inv_p:.1f}</div>
            </div>
            <div style="position: absolute; left: calc({pct_spot}% - 32px); top: 8px; text-align: center; width: 64px; z-index: 5;">
                <div style="font-size: 0.65rem; color: #FF8533; font-weight: 900; letter-spacing: 0.04em;">SPOT</div>
                <div style="width: 13px; height: 13px; background: #FF6B00; border: 2.5px solid #F1F5F9; border-radius: 50%; margin: 2px auto; box-shadow: 0 0 12px #FF6B00;"></div>
                <div class="obs-mono" style="font-size: 0.76rem; color: #F1F5F9; font-weight: 800;">${spot_price:.2f}</div>
            </div>
            <div style="position: absolute; left: calc({pct_strike}% - 30px); top: 10px; text-align: center; width: 60px; z-index: 4;">
                <div style="font-size: 0.64rem; color: #FBBF24; font-weight: 800; letter-spacing: 0.04em;">STRIKE</div>
                <div style="width: 11px; height: 11px; background: #F59E0B; border: 2px solid #F1F5F9; border-radius: 50%; margin: 2px auto; box-shadow: 0 0 8px #F59E0B;"></div>
                <div class="obs-mono" style="font-size: 0.74rem; color: #FDE68A; font-weight: 800;">${display_strike:.1f}</div>
            </div>
            <div style="position: absolute; left: calc({pct_be}% - 28px); top: 10px; text-align: center; width: 56px; z-index: 3;">
                <div style="font-size: 0.64rem; color: #C084FC; font-weight: 800; letter-spacing: 0.04em;">BE</div>
                <div style="width: 10px; height: 10px; background: #8B5CF6; border: 2px solid #F1F5F9; border-radius: 50%; margin: 3px auto; box-shadow: 0 0 6px #8B5CF6;"></div>
                <div class="obs-mono" style="font-size: 0.72rem; color: #DDD6FE; font-weight: 700;">${be_spot:.1f}</div>
            </div>
            <div style="position: absolute; left: calc({pct_tgt}% - 30px); top: 8px; text-align: center; width: 60px; z-index: 4;">
                <div style="font-size: 0.65rem; color: #34D399; font-weight: 900; letter-spacing: 0.04em;">TARGET</div>
                <div style="width: 13px; height: 13px; background: #10B981; border: 2.5px solid #F1F5F9; border-radius: 50%; margin: 2px auto; box-shadow: 0 0 12px #10B981;"></div>
                <div class="obs-mono" style="font-size: 0.76rem; color: #A7F3D0; font-weight: 800;">${tgt_p:.1f}</div>
            </div>
        </div>
        <div class="obs-subpanel obs-mono" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; margin-top: 10px; font-size: 0.75rem;">
            <div>
                <span style="color: #94A3B8;">Delta (Δ):</span>
                <b style="color: {'#34D399' if strike_greeks['delta']>=0 else '#FB7185'};">{strike_greeks['delta']:+.2f}</b>
                <span style="color: #64748B; font-size: 0.68rem;">({abs(strike_greeks['delta']*100):.0f} sh/ct)</span>
            </div>
            <div>
                <span style="color: #94A3B8;">Theta (Θ):</span>
                <b style="color: #FB7185;">${strike_greeks['theta']:.2f}/d</b>
                <span style="color: #64748B; font-size: 0.68rem;">(decay)</span>
            </div>
            <div>
                <span style="color: #94A3B8;">Gamma (Γ):</span>
                <b style="color: #CBD5E1;">{strike_greeks['gamma']:.4f}</b>
                <span style="color: #64748B; font-size: 0.68rem;">(accel)</span>
            </div>
            <div>
                <span style="color: #94A3B8;">Vega (ν):</span>
                <b style="color: #FF8533;">+${strike_greeks['vega']:.2f}</b>
                <span style="color: #64748B; font-size: 0.68rem;">(/+1% IV)</span>
            </div>
            <div>
                <span style="color: #94A3B8;">Implied Vol:</span>
                <b style="color: #FBBF24;">{display_iv*100:.1f}%</b>
                <span style="color: #64748B; font-size: 0.68rem;">OPRA</span>
            </div>
            <div>
                <span style="color: #94A3B8;">Open Interest:</span>
                <b style="color: #F1F5F9;">{display_oi:,}</b>
                <span style="color: #64748B; font-size: 0.68rem;">Vol: {display_vol:,}</span>
            </div>
        </div>
    </div>
    """)

    tab_desk, tab_ledger = st.tabs([
        "Unified Charles Schwab Options Desk & 90-Day Chain",
        f"Live Open Positions Desk ({len(open_trades)}) & Historical Diary Ledger"
    ])

    with tab_desk:
        real_expiries = rbe3.get_real_exchange_expiries(active_sym)
        has_exchange_options = bool(real_expiries)

        if not has_exchange_options:
            fridays_90d = get_upcoming_option_fridays(max_dte=90)
            friday_labels = [f["label"] for f in fridays_90d]
            render_clean_html(f"""
            <div class="obs-glass-card" style="padding: 10px 14px; margin-bottom: 12px; border-color: rgba(245, 158, 11, 0.32);">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-circle-info" style="color: #FBBF24;"></i>
                        <span style="font-size: 0.78rem; font-weight: 700; color: #FDE68A;">
                            Simulated Options Practice Feed Active for {active_sym}
                        </span>
                    </div>
                    <span class="obs-mono" style="font-size: 0.68rem; color: #94A3B8;">
                        STANDARD MODEL CALIBRATION (FMP VOLATILITY)
                    </span>
                </div>
            </div>
            """)
        else:
            fridays_90d = real_expiries
            friday_labels = [f["label"] for f in fridays_90d]

        target_prefill_exp = prefill.get("expiration_date") or prefill.get("expiration") or active_leg_obj.get("expiration_date", "")
        target_prefill_dte = prefill.get("dte") or prefill.get("recommended_dte") or active_leg_obj.get("dte")
        default_fri_idx = resolve_best_expiration_index(
            fridays_90d,
            target_exp=target_prefill_exp,
            target_dte=target_prefill_dte
        )

        col_chain_pane, col_ticket_pane = st.columns([1.55, 1.05], gap="medium")

        with col_chain_pane:
            render_clean_html("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 6px;">
                <span style="font-size: 0.95rem; font-weight: 800; color: #F1F5F9; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #FF6B00;"><i class="fa-solid fa-layer-group"></i></span>
                    <span>Charles Schwab Interactive Options Chain (Cached OPRA Feed)</span>
                </span>
                <span class="obs-pill-orange">Tap any Call or Put to arm ticket</span>
            </div>
            """)

            def get_closest_friday(target_dte: int) -> Dict[str, Any]:
                if not fridays_90d:
                    return {}
                return min(fridays_90d, key=lambda f: abs(int(f.get("dte", 35)) - target_dte))

            f_weekly = get_closest_friday(10)
            f_30d = get_closest_friday(30)
            f_45d = get_closest_friday(45)
            f_60d = get_closest_friday(60)
            f_90d = get_closest_friday(90)

            lbl_weekly = f_weekly.get("label", friday_labels[0] if friday_labels else "")
            lbl_30d = f_30d.get("label", friday_labels[0] if friday_labels else "")
            lbl_45d = f_45d.get("label", friday_labels[0] if friday_labels else "")
            lbl_60d = f_60d.get("label", friday_labels[0] if friday_labels else "")
            lbl_90d = f_90d.get("label", friday_labels[-1] if friday_labels else "")

            exp_key = f"unified_chain_exp_{active_sym}"
            sb_exp_key = f"sb_{exp_key}"
            needs_sync = st.session_state.pop("schwab_prefill_needs_sync", False)
            if needs_sync or exp_key not in st.session_state or st.session_state[exp_key] not in friday_labels:
                st.session_state[exp_key] = friday_labels[default_fri_idx] if (friday_labels and default_fri_idx < len(friday_labels)) else (friday_labels[0] if friday_labels else "")

            curr_exp_selected = st.session_state.get(exp_key, friday_labels[default_fri_idx] if friday_labels else "")
            if needs_sync or sb_exp_key not in st.session_state or st.session_state[sb_exp_key] not in friday_labels:
                st.session_state[sb_exp_key] = curr_exp_selected

            def on_select_dte_horizon(target_label: str, sym: str):
                st.session_state[f"unified_chain_exp_{sym}"] = target_label
                st.session_state[f"sb_unified_chain_exp_{sym}"] = target_label
                meta = next((f for f in fridays_90d if f.get("label") == target_label), None)
                if meta:
                    target_d = int(meta.get("dte", 35))
                    target_e = str(meta.get("date_str", meta.get("iso_date", "")))
                    if "schwab_active_leg" in st.session_state:
                        st.session_state["schwab_active_leg"]["dte"] = target_d
                        st.session_state["schwab_active_leg"]["expiration_date"] = target_e
                    if "schwab_prefill" in st.session_state:
                        st.session_state["schwab_prefill"]["dte"] = target_d
                        st.session_state["schwab_prefill"]["expiration_date"] = target_e

            q_cols = st.columns(5)
            with q_cols[0]:
                is_w = (curr_exp_selected == lbl_weekly)
                st.button(f"1–2W ({f_weekly.get('dte', 10)}d)", key=f"btn_q_weekly_{active_sym}", width="stretch", type="primary" if is_w else "secondary", help="Short-dated weekly cycle", on_click=on_select_dte_horizon, args=(lbl_weekly, active_sym))
            with q_cols[1]:
                is_30 = (curr_exp_selected == lbl_30d)
                st.button(f"30D ({f_30d.get('dte', 30)}d)", key=f"btn_q_30_{active_sym}", width="stretch", type="primary" if is_30 else "secondary", help="30-day tactical cycle", on_click=on_select_dte_horizon, args=(lbl_30d, active_sym))
            with q_cols[2]:
                is_45 = (curr_exp_selected == lbl_45d)
                st.button(f"45D ({f_45d.get('dte', 45)}d)", key=f"btn_q_45_{active_sym}", width="stretch", type="primary" if is_45 else "secondary", help="45-day swing sweet spot", on_click=on_select_dte_horizon, args=(lbl_45d, active_sym))
            with q_cols[3]:
                is_60 = (curr_exp_selected == lbl_60d)
                st.button(f"60D ({f_60d.get('dte', 60)}d)", key=f"btn_q_60_{active_sym}", width="stretch", type="primary" if is_60 else "secondary", help="60-day intermediate cycle", on_click=on_select_dte_horizon, args=(lbl_60d, active_sym))
            with q_cols[4]:
                is_90 = (curr_exp_selected == lbl_90d)
                st.button(f"90D ({f_90d.get('dte', 90)}d)", key=f"btn_q_90_{active_sym}", width="stretch", type="primary" if is_90 else "secondary", help="90-day macro horizon", on_click=on_select_dte_horizon, args=(lbl_90d, active_sym))

            col_exp_sel, col_span_sel = st.columns([1.8, 1.2])
            with col_exp_sel:
                selected_exp_label = st.selectbox(
                    "Expiration Cycle (Cached OPRA)",
                    options=friday_labels,
                    key=sb_exp_key,
                )
                if selected_exp_label != curr_exp_selected:
                    st.session_state[exp_key] = selected_exp_label
                selected_fri_meta = next((f for f in fridays_90d if f.get("label") == selected_exp_label), fridays_90d[0])
                active_dte = int(selected_fri_meta.get("dte", 35))
                active_exp_date = str(selected_fri_meta.get("date_str", "N/A"))
                active_iso_date = selected_fri_meta.get("iso_date", active_exp_date)

            with col_span_sel:
                st.session_state.setdefault("unified_chain_span", "All Strikes (±20%)")
                moneyness_view = st.selectbox(
                    "Strike Span",
                    options=["All Strikes (±20%)", "Near the Money (±10%)", "Deep Convexity (±25%)"],
                    key="unified_chain_span",
                )
                span_pct = 10.0 if "10%" in moneyness_view else (25.0 if "25%" in moneyness_view else 20.0)

            chain_rows, is_live_chain = generate_options_chain_up_to_90d(
                symbol=active_sym,
                spot_price=spot_price,
                dte=active_dte,
                moneyness_span_pct=span_pct,
                expiry_date=active_iso_date
            )

            live_badge = '<span style="margin-left: 8px; background: rgba(16,185,129,0.16); color: #34D399; border: 1px solid rgba(16,185,129,0.34); font-size: 0.65rem; font-weight: 800; padding: 2px 7px; border-radius: 9999px;">CACHED OPRA FEED</span>' if is_live_chain else ''
            render_clean_html(f"""
            <div class="obs-glass-card obs-mono" style="border-radius: 10px !important; padding: 8px 12px; margin-bottom: 10px; font-size: 0.74rem; display: flex; justify-content: space-between; align-items: center; color: #CBD5E1; flex-wrap: wrap; gap: 6px;">
                <div><b style="color: #F1F5F9;">{active_sym}</b> Exp: <b style="color: #FF8533;">{active_exp_date}</b> (<b style="color: #34D399;">{active_dte} DTE</b> &middot; {selected_fri_meta['cycle_tag']}){live_badge}</div>
                <div><span style="color: #34D399; font-weight: 700;">CALLS (Mid/Δ)</span> | <span style="color: #F1F5F9;">STRIKE</span> | <span style="color: #FB7185; font-weight: 700;">PUTS (Mid/Δ)</span></div>
            </div>
            """)

            base_s200 = bp.get("conviction_score_200")
            if base_s200 is None:
                base_s200 = score_200

            for row in chain_rows:
                k = row["strike"]
                is_atm = row["is_atm"]
                c_mark = row["call_mark"]
                c_delta = row["call_delta"]
                c_be = row["call_breakeven"]
                c_itm = row["call_itm"]
                c_bid = row.get("call_bid", 0.0)
                c_ask = row.get("call_ask", 0.0)
                c_iv = row.get("call_iv", 0.40)
                c_oi = row.get("call_oi", 0)
                c_vol = row.get("call_vol", 0)

                p_mark = row["put_mark"]
                p_delta = row["put_delta"]
                p_be = row["put_breakeven"]
                p_itm = row["put_itm"]
                p_bid = row.get("put_bid", 0.0)
                p_ask = row.get("put_ask", 0.0)
                p_iv = row.get("put_iv", 0.40)
                p_oi = row.get("put_oi", 0)
                p_vol = row.get("put_vol", 0)

                c_help = f"OPRA Call · Bid ${c_bid:.2f} / Ask ${c_ask:.2f} · Mid ${c_mark:.2f} · IV {c_iv*100:.0f}% · OI {c_oi:,} · BE ${c_be:.2f}"
                p_help = f"OPRA Put · Bid ${p_bid:.2f} / Ask ${p_ask:.2f} · Mid ${p_mark:.2f} · IV {p_iv*100:.0f}% · OI {p_oi:,} · BE ${p_be:.2f}"

                rc1, rc2, rc3, rc4, rc5 = st.columns([1.8, 1.1, 1.2, 1.1, 1.8])
                is_armed_call = bool(has_active_leg and active_leg_obj.get("option_type") == "CALL" and abs(float(active_leg_obj.get("strike", 0)) - k) < 0.01)
                is_armed_put = bool(has_active_leg and active_leg_obj.get("option_type") == "PUT" and abs(float(active_leg_obj.get("strike", 0)) - k) < 0.01)

                with rc1:
                    btn_c_txt = f"⚡ CALL ${c_mark:.2f}" if is_armed_call else f"Call ${c_mark:.2f}"
                    if st.button(btn_c_txt, key=f"chain_call_{k}_{active_dte}", width="stretch", type="primary" if is_armed_call else "secondary", help=c_help):
                        _reset_ticket_widget_state()
                        c_score_200 = abs(int(base_s200)) if base_s200 is not None else 0
                        leg_payload = {
                            "symbol": active_sym,
                            "action": "BUY_TO_OPEN",
                            "option_type": "CALL",
                            "strike": float(k),
                            "expiration_date": active_exp_date,
                            "dte": int(active_dte),
                            "recommended_dte": 45 if active_dte >= 38 else 30,
                            "conviction_score_200": c_score_200,
                            "conviction_score": c_score_200,
                            "limit_price": float(c_mark),
                            "bid": float(c_bid),
                            "ask": float(c_ask),
                            "iv": float(c_iv),
                            "oi": int(c_oi),
                            "vol": int(c_vol),
                            "delta": float(c_delta),
                            "spot_price": spot_price,
                            "target_price": tgt_p,
                            "stop_price": inv_p,
                            "notes": f"Simulated {active_dte}-DTE Call on {active_sym}. Strike: ${k:.2f} (Δ {c_delta:+.2f}). Breakeven: ${c_be:.2f}."
                        }
                        st.session_state["schwab_active_leg"] = leg_payload
                        st.session_state["schwab_prefill"] = leg_payload
                        st.session_state["ticket_strike_rail"] = float(k)
                        st.session_state["ticket_limit_rail"] = max(0.01, round(float(c_mark), 2))
                        st.session_state["ticket_type_rail"] = "CALL"
                        st.session_state["ticket_action_rail"] = "BUY_TO_OPEN"
                        st.session_state["ticket_strategy_rail"] = "SINGLE_LEG"
                        st.session_state["ticket_qty_rail"] = 1
                        st.session_state["ticket_tgt_spot_rail"] = float(tgt_p)
                        st.session_state["ticket_stp_spot_rail"] = float(inv_p)
                        st.session_state["ticket_dte_rail"] = int(active_dte)
                        st.session_state["ticket_exp_rail"] = active_exp_date
                        st.session_state["dlg_limit"] = max(0.01, round(float(c_mark), 2))
                        st.session_state["dlg_qty"] = 1
                        st.session_state["schwab_show_order_modal"] = True
                        st.rerun()

                with rc2:
                    st.markdown(f"<div class='obs-mono' style='font-size:0.72rem; text-align:right; color:{'#34D399' if c_itm else '#94A3B8'}; line-height:2.2;'>Δ {c_delta:+.2f}</div>", unsafe_allow_html=True)

                with rc3:
                    is_row_armed = is_armed_call or is_armed_put
                    if is_row_armed:
                        strike_style = "border: 1.5px solid #FF6B00; color: #F1F5F9; background: rgba(255, 107, 0, 0.28); box-shadow: 0 0 12px rgba(255, 107, 0, 0.45);"
                    elif is_atm:
                        strike_style = "border: 1px solid rgba(245, 158, 11, 0.65); color: #FBBF24; background: rgba(245, 158, 11, 0.14);"
                    else:
                        strike_style = "border: 1px solid rgba(255,255,255,0.08); color: #E2E8F0; background: rgba(15, 18, 26, 0.72);"
                    st.markdown(f"<div style='text-align:center;'><span class='obs-mono' style='font-size:0.82rem; font-weight:800; padding:3px 7px; border-radius:6px; display:inline-block; {strike_style}'>${k:.2f}</span></div>", unsafe_allow_html=True)

                with rc4:
                    st.markdown(f"<div class='obs-mono' style='font-size:0.72rem; text-align:left; color:{'#FB7185' if p_itm else '#94A3B8'}; line-height:2.2;'>Δ {p_delta:+.2f}</div>", unsafe_allow_html=True)

                with rc5:
                    btn_p_txt = f"⚡ PUT ${p_mark:.2f}" if is_armed_put else f"Put ${p_mark:.2f}"
                    if st.button(btn_p_txt, key=f"chain_put_{k}_{active_dte}", width="stretch", type="primary" if is_armed_put else "secondary", help=p_help):
                        _reset_ticket_widget_state()
                        p_score_200 = -abs(int(base_s200)) if base_s200 is not None else 0
                        leg_payload = {
                            "symbol": active_sym,
                            "action": "BUY_TO_OPEN",
                            "option_type": "PUT",
                            "strike": float(k),
                            "expiration_date": active_exp_date,
                            "dte": int(active_dte),
                            "recommended_dte": 45 if active_dte >= 38 else 30,
                            "conviction_score_200": p_score_200,
                            "conviction_score": p_score_200,
                            "limit_price": float(p_mark),
                            "bid": float(p_bid),
                            "ask": float(p_ask),
                            "iv": float(p_iv),
                            "oi": int(p_oi),
                            "vol": int(p_vol),
                            "delta": float(p_delta),
                            "spot_price": spot_price,
                            "target_price": inv_p,
                            "stop_price": tgt_p,
                            "notes": f"Simulated {active_dte}-DTE Put on {active_sym}. Strike: ${k:.2f} (Δ {p_delta:+.2f}). Breakeven: ${p_be:.2f}."
                        }
                        st.session_state["schwab_active_leg"] = leg_payload
                        st.session_state["schwab_prefill"] = leg_payload
                        st.session_state["ticket_strike_rail"] = float(k)
                        st.session_state["ticket_limit_rail"] = max(0.01, round(float(p_mark), 2))
                        st.session_state["ticket_type_rail"] = "PUT"
                        st.session_state["ticket_action_rail"] = "BUY_TO_OPEN"
                        st.session_state["ticket_strategy_rail"] = "SINGLE_LEG"
                        st.session_state["ticket_qty_rail"] = 1
                        st.session_state["ticket_tgt_spot_rail"] = float(inv_p)
                        st.session_state["ticket_stp_spot_rail"] = float(tgt_p)
                        st.session_state["ticket_dte_rail"] = int(active_dte)
                        st.session_state["ticket_exp_rail"] = active_exp_date
                        st.session_state["dlg_limit"] = max(0.01, round(float(p_mark), 2))
                        st.session_state["dlg_qty"] = 1
                        st.session_state["schwab_show_order_modal"] = True
                        st.rerun()

        # =====================================================================
        # RIGHT STAGE / ORDER EXECUTION RAIL (THE SINGLE UNIFIED SCHWAB TICKET)
        # =====================================================================
        with col_ticket_pane:
            active_leg = st.session_state.get("schwab_active_leg", prefill)
            leg_sym = active_leg.get("symbol", active_sym)
            leg_type = str(active_leg.get("option_type", display_type)).upper()
            leg_action = str(active_leg.get("action", "BUY_TO_OPEN"))
            leg_strike = float(active_leg.get("strike", 0.0))
            leg_dte = int(active_leg.get("dte", active_dte))
            leg_exp = str(active_leg.get("expiration_date", active_exp_date))

            if leg_strike <= 0:
                leg_strike = float(chain_rows[len(chain_rows) // 2]["strike"]) if chain_rows else spot_price

            leg_limit = float(active_leg.get("limit_price", 0.0))
            if leg_limit <= 0:
                def_c, _ = rbe3.bs_call_price_delta(spot_price, leg_strike, leg_dte / 365.0, 0.0425, 0.40)
                def_p, _ = rbe3.bs_put_price_delta(spot_price, leg_strike, leg_dte / 365.0, 0.0425, 0.40)
                leg_limit = round(def_c if leg_type == "CALL" else def_p, 2)

            leg_tgt = float(active_leg.get("target_price", tgt_p if leg_type == "CALL" else inv_p))
            leg_stop = float(active_leg.get("stop_price", inv_p if leg_type == "CALL" else tgt_p))
            leg_notes = active_leg.get("notes", "")
            leg_bid = float(active_leg.get("bid", 0.0) or 0.0)
            leg_ask = float(active_leg.get("ask", 0.0) or 0.0)

            rail_s200, rail_is_200, rail_dte_bucket, rail_dte_rat = _resolve_conviction_and_dte(
                prefill=prefill,
                active_leg=active_leg,
                cand_intel=cand_intel,
                opt_type=leg_type,
                fallback_dte=leg_dte,
            )
            rail_conv_badge = _format_conviction_badge_html(rail_s200, leg_type, is_legacy_100=False)
            rail_dte_badge = _format_dte_badge_html(rail_dte_bucket, rationale=rail_dte_rat, exact_dte=leg_dte)

            render_clean_html(f"""
            <div class="schwab-order-rail">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 6px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="obs-pill-orange">SCHWAB TICKET</span>
                        <span style="font-weight: 800; font-size: 0.95rem; color: #F1F5F9;">Order Entry Desk</span>
                    </div>
                    <span style="font-size: 0.68rem; color: #34D399; background: rgba(16, 185, 129, 0.14); border: 1px solid rgba(16, 185, 129, 0.34); padding: 2px 8px; border-radius: 9999px; font-weight: 800;">
                        ● CACHED OPRA SPREAD
                    </span>
                </div>
                <div class="obs-subpanel" style="border-color: rgba(255, 107, 0, 0.32);">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                        <span style="font-size: 0.68rem; color: #94A3B8; text-transform: uppercase; font-weight: 700;">Armed Option Contract Leg</span>
                        <div style="display: flex; gap: 6px; flex-wrap: wrap;">{rail_conv_badge}{rail_dte_badge}</div>
                    </div>
                    <div class="obs-mono" style="font-size: 0.96rem; font-weight: 800; color: {'#34D399' if leg_type == 'CALL' else '#FB7185'}; margin-top: 6px;">
                        {_esc(leg_action)} {_esc(leg_sym)} {_esc(leg_exp)} ${leg_strike:.2f} {_esc(leg_type)}
                        <span style="font-size: 0.78rem; color: #FF8533; font-weight: 700; margin-left: 6px;">({leg_dte} DTE)</span>
                    </div>
                    <div class="obs-mono" style="font-size: 0.72rem; color: #CBD5E1; margin-top: 6px; display: flex; justify-content: space-between; align-items: center;">
                        <span>Bid: <b style="color: #F1F5F9;">${leg_bid:.2f}</b> &bull; Ask: <b style="color: #F1F5F9;">${leg_ask:.2f}</b> (Sprd: ${(max(0.0, leg_ask - leg_bid)):.2f})</span>
                        <span style="color: #FF8533; font-weight: 800;">Mid: ${leg_limit:.2f}</span>
                    </div>
                </div>
            </div>
            """)

            with st.container():
                _rail_def_strat = str(active_leg.get("strategy") or prefill.get("strategy") or "SINGLE_LEG").upper()
                if _rail_def_strat not in ("SINGLE_LEG", "VERTICAL_DEBIT_SPREAD"):
                    _rail_def_strat = "SINGLE_LEG"
                _def_action_rail = "BUY_TO_OPEN" if "BUY" in leg_action.upper() else "SELL_TO_OPEN"
                _def_type_rail = "CALL" if leg_type == "CALL" else "PUT"
                _def_strike_rail = float(leg_strike)
                _def_k2_raw = active_leg.get("short_strike") or prefill.get("short_strike")
                if not _def_k2_raw or float(_def_k2_raw) <= 0:
                    _def_k2_rail = round(_def_strike_rail * (1.05 if _def_type_rail == "CALL" else 0.95), 1)
                else:
                    _def_k2_rail = float(_def_k2_raw)
                _def_notes_rail = leg_notes or f"Simulated {active_dte}-DTE trade on {leg_sym}. Testing asymmetric convexity on {active_exp_date} ${_def_strike_rail:.2f} {_def_type_rail}."
                _def_conv_rail = max(-200, min(200, int(rail_s200)))

                st.session_state.setdefault("ticket_action_rail", _def_action_rail)
                st.session_state.setdefault("ticket_type_rail", _def_type_rail)
                st.session_state.setdefault("ticket_strategy_rail", _rail_def_strat)
                st.session_state.setdefault("ticket_tif_rail", "Good 'Til Canceled (GTC)")
                st.session_state.setdefault("ticket_strike_rail", _def_strike_rail)
                st.session_state.setdefault("ticket_short_strike_rail", float(_def_k2_rail))
                st.session_state.setdefault("ticket_qty_rail", 1)
                st.session_state.setdefault("ticket_ord_type_rail", "LIMIT")
                st.session_state.setdefault("ticket_limit_rail", max(0.01, round(float(leg_limit), 2)))
                st.session_state.setdefault("ticket_tgt_spot_rail", float(leg_tgt))
                st.session_state.setdefault("ticket_stp_spot_rail", float(leg_stop))
                st.session_state.setdefault("ticket_notes_rail", _def_notes_rail)
                st.session_state.setdefault("ticket_conv_rail", _def_conv_rail)

                def _set_rail_qty(val: int) -> None:
                    st.session_state["ticket_qty_rail"] = int(max(1, min(500, val)))

                def _step_rail_qty(delta: int) -> None:
                    curr_q = int(st.session_state.get("ticket_qty_rail", 1) or 1)
                    st.session_state["ticket_qty_rail"] = int(max(1, min(500, curr_q + delta)))

                def _set_rail_limit(px: float) -> None:
                    st.session_state["ticket_limit_rail"] = max(0.01, round(float(px), 2))

                col_tk_act, col_tk_type = st.columns(2)
                with col_tk_act:
                    opt_action = st.radio(
                        "Action",
                        options=["BUY_TO_OPEN", "SELL_TO_OPEN"],
                        horizontal=True,
                        key="ticket_action_rail"
                    )
                with col_tk_type:
                    opt_type_sel = st.radio(
                        "Leg Type",
                        options=["CALL", "PUT"],
                        horizontal=True,
                        key="ticket_type_rail"
                    )

                col_tk_strat, col_tk_tif = st.columns(2)
                with col_tk_strat:
                    opt_strat_rail = st.selectbox(
                        "Strategy Structure",
                        options=["SINGLE_LEG", "VERTICAL_DEBIT_SPREAD"],
                        key="ticket_strategy_rail",
                    )
                with col_tk_tif:
                    st.selectbox(
                        "Timing / Duration",
                        options=["Good 'Til Canceled (GTC)", "Day"],
                        key="ticket_tif_rail"
                    )

                col_tk_k, col_tk_k2 = st.columns(2)
                with col_tk_k:
                    opt_strike_in = st.number_input(
                        "Strike ($)",
                        step=1.0,
                        format="%.2f",
                        key="ticket_strike_rail"
                    )
                with col_tk_k2:
                    if opt_strat_rail == "VERTICAL_DEBIT_SPREAD":
                        opt_short_k_rail: Optional[float] = float(
                            st.number_input(
                                "Short Strike K2 ($)",
                                min_value=0.5,
                                max_value=5000.0,
                                step=0.5,
                                format="%.2f",
                                key="ticket_short_strike_rail",
                            )
                        )
                    else:
                        opt_short_k_rail = None
                        st.caption("Single-Leg Long Convexity")

                st.markdown("<div style='font-size: 0.72rem; font-weight: 700; color: #94A3B8; margin-top: 4px; margin-bottom: 2px;'>CONTRACT QUANTITY (1 CT = 100 SHARES)</div>", unsafe_allow_html=True)
                chip_q_cols = st.columns(6)
                qty_presets = [1, 2, 5, 10, 25, 50]
                for q_idx, q_val in enumerate(qty_presets):
                    with chip_q_cols[q_idx]:
                        st.button(
                            f"{q_val}x",
                            key=f"btn_quick_qty_{q_val}",
                            width="stretch",
                            on_click=_set_rail_qty,
                            args=(q_val,),
                        )

                col_dec, col_q_in, col_inc = st.columns([1, 2.8, 1])
                with col_dec:
                    st.button(
                        "➖",
                        key="btn_dec_qty",
                        width="stretch",
                        help="Decrease 1 contract",
                        on_click=_step_rail_qty,
                        args=(-1,),
                    )
                with col_q_in:
                    opt_qty_in = st.number_input(
                        "Contracts",
                        min_value=1,
                        max_value=500,
                        step=1,
                        key="ticket_qty_rail",
                        label_visibility="collapsed"
                    )
                with col_inc:
                    st.button(
                        "➕",
                        key="btn_inc_qty",
                        width="stretch",
                        help="Increase 1 contract",
                        on_click=_step_rail_qty,
                        args=(1,),
                    )

                st.markdown(f"<div class='obs-mono' style='font-size: 0.74rem; color: #FF8533; font-weight: 700; margin-top: -6px; margin-bottom: 8px;'>Controls {int(opt_qty_in) * 100:,} Shares of {_esc(leg_sym)}</div>", unsafe_allow_html=True)

                st.markdown("<div style='font-size: 0.72rem; font-weight: 700; color: #94A3B8; margin-top: 2px; margin-bottom: 2px;'>LIMIT PRICE &amp; SPREAD EXECUTION</div>", unsafe_allow_html=True)
                chip_p_cols = st.columns(3)
                with chip_p_cols[0]:
                    if leg_bid > 0:
                        st.button(f"Bid ${leg_bid:.2f}", key="btn_chip_bid", width="stretch", on_click=_set_rail_limit, args=(leg_bid,))
                with chip_p_cols[1]:
                    if leg_limit > 0:
                        st.button(f"Mid ${leg_limit:.2f}", key="btn_chip_mid", width="stretch", on_click=_set_rail_limit, args=(leg_limit,))
                with chip_p_cols[2]:
                    if leg_ask > 0:
                        st.button(f"Ask ${leg_ask:.2f}", key="btn_chip_ask", width="stretch", on_click=_set_rail_limit, args=(leg_ask,))

                col_tk_ord, col_tk_lim = st.columns(2)
                with col_tk_ord:
                    opt_ord_type = st.selectbox(
                        "Order Type",
                        options=["LIMIT", "MARKET", "STOP ON QUOTE"],
                        key="ticket_ord_type_rail"
                    )
                with col_tk_lim:
                    opt_limit_in = st.number_input(
                        "Limit Price ($)",
                        min_value=0.01,
                        max_value=2500.0,
                        step=0.01,
                        format="%.2f",
                        key="ticket_limit_rail"
                    )

                col_r_tgt, col_r_stp = st.columns(2)
                with col_r_tgt:
                    in_tgt_val = st.number_input(
                        "Target Stock ($)",
                        step=1.0,
                        format="%.2f",
                        key="ticket_tgt_spot_rail"
                    )
                with col_r_stp:
                    in_stp_val = st.number_input(
                        "Stop Stock ($)",
                        step=1.0,
                        format="%.2f",
                        key="ticket_stp_spot_rail"
                    )

                qty = int(opt_qty_in)
                limit_p = float(opt_limit_in)
                strike_p = float(opt_strike_in)
                shares_ctrl = qty * 100
                tgt_spot = float(in_tgt_val)
                stp_spot = float(in_stp_val)
                raw_ticket_iv = float(active_leg.get("iv", display_iv))
                sigma_ticket = raw_ticket_iv / 100.0 if raw_ticket_iv > 3.0 else max(0.15, raw_ticket_iv)

                pay_rail = _compute_order_payoff_summary(
                    spot_price=spot_price,
                    strike_p=strike_p,
                    limit_p=limit_p,
                    qty=qty,
                    dte=leg_dte,
                    sigma=sigma_ticket,
                    opt_type=opt_type_sel,
                    opt_action=opt_action,
                    strategy=opt_strat_rail,
                    short_strike=opt_short_k_rail,
                    tgt_val=tgt_spot,
                    stp_val=stp_spot,
                )
                is_spread_rail = pay_rail["is_spread"]
                is_sell_rail = pay_rail["is_sell"]
                schwab_comm = pay_rail["schwab_comm"]
                gross_principal = round(qty * limit_p * 100.0, 2)
                total_max_risk = pay_rail["total_outlay"]
                be_price = pay_rail["be_price"]
                be_diff = be_price - spot_price
                be_pct = pay_rail["be_pct"]
                net_profit_at_tgt = pay_rail["net_profit_at_tgt"]
                roi_at_tgt_pct = pay_rail["roi_at_tgt_pct"]
                est_loss_at_stop = pay_rail["est_loss_at_stop"]
                stop_loss_pct = pay_rail["stop_loss_pct"]
                pos_delta_shares = pay_rail["pos_delta_shares"]
                pos_theta_daily = pay_rail["pos_theta_daily"]
                pos_vega_vol = pay_rail["pos_vega_vol"]
                outlay_label_rail = "Collateral / Risk Basis:" if is_sell_rail else "Total Cash Outlay (Max Risk):"
                principal_label_rail = "Gross Credit Proceeds:" if is_sell_rail else "Gross Principal Debit:"

                render_clean_html(f"""
                <div class="obs-glass-card" style="padding: 14px 16px; margin: 12px 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px; margin-bottom: 10px;">
                        <span style="font-size: 0.76rem; font-weight: 800; color: #FF8533; text-transform: uppercase; letter-spacing: 0.05em;">Charles Schwab Dynamic Order Math ({'Spread' if is_spread_rail else 'Single Leg'})</span>
                        <span class="obs-mono" style="font-size: 0.70rem; color: #34D399; font-weight: 700;">100x &bull; $0.65/leg</span>
                    </div>
                    <div class="obs-mono" style="display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 6px;">
                        <span style="color: #94A3B8;">Contracts / Shares:</span>
                        <b style="color: #F1F5F9;">{qty} ct ({shares_ctrl:,} sh)</b>
                    </div>
                    <div class="obs-mono" style="display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 6px;">
                        <span style="color: #94A3B8;">{principal_label_rail}</span>
                        <b style="color: #F1F5F9;">${gross_principal:,.2f}</b>
                    </div>
                    <div class="obs-mono" style="display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 6px;">
                        <span style="color: #94A3B8;">Schwab Fee ($0.65/leg):</span>
                        <b style="color: #CBD5E1;">${schwab_comm:.2f}</b>
                    </div>
                    <div class="obs-mono" style="display: flex; justify-content: space-between; font-size: 0.88rem; font-weight: 800; background: rgba(255, 107, 0, 0.14); padding: 7px 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(255, 107, 0, 0.34);">
                        <span style="color: #FF8533;">{outlay_label_rail}</span>
                        <b style="color: #F1F5F9;">${total_max_risk:,.2f}</b>
                    </div>
                    <div class="obs-mono" style="display: flex; justify-content: space-between; font-size: 0.80rem; margin-bottom: 6px;">
                        <span style="color: #94A3B8;">Breakeven Underlying:</span>
                        <b style="color: #FBBF24;">${be_price:.2f} ({be_diff:+.2f} / {be_pct:+.1f}%)</b>
                    </div>
                    <div class="obs-mono" style="display: flex; justify-content: space-between; font-size: 0.82rem; background: rgba(16, 185, 129, 0.12); padding: 6px 10px; border-radius: 8px; margin-bottom: 6px; border: 1px solid rgba(16, 185, 129, 0.28);">
                        <span style="color: #34D399; font-weight: 700;">Gain at 1–5D Target (${tgt_spot:.2f}):</span>
                        <b style="color: #34D399;">{'+' if net_profit_at_tgt>=0 else ''}${net_profit_at_tgt:,.2f} ({'+' if roi_at_tgt_pct>=0 else ''}{roi_at_tgt_pct:.1f}% ROI)</b>
                    </div>
                    <div class="obs-mono" style="display: flex; justify-content: space-between; font-size: 0.82rem; background: rgba(244, 63, 94, 0.12); padding: 6px 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(244, 63, 94, 0.28);">
                        <span style="color: #FB7185; font-weight: 700;">Loss at Stock Stop (${stp_spot:.2f}):</span>
                        <b style="color: #FB7185;">-${est_loss_at_stop:,.2f} (-{stop_loss_pct:.1f}%)</b>
                    </div>
                    <div class="obs-mono" style="border-top: 1px solid rgba(255,255,255,0.08); padding-top: 8px; display: flex; justify-content: space-between; font-size: 0.74rem; color: #94A3B8;">
                        <span>Net Delta: <b style="color: #F1F5F9;">{pos_delta_shares:+.0f} sh</b></span>
                        <span>Theta: <b style="color: #FB7185;">${pos_theta_daily:+.2f}/d</b></span>
                        <span>Vega: <b style="color: #FF8533;">${pos_vega_vol:+.2f}/%</b></span>
                    </div>
                </div>
                """)
                _spr_pct_rail = ((leg_ask - leg_bid) / max(0.01, leg_limit) * 100.0) if (leg_ask > leg_bid > 0 and leg_limit > 0) else 4.0
                if _edu is not None:
                    _edu.render_edu_drawer(
                        "schwab_ticket",
                        live_ctx={
                            "symbol": leg_sym,
                            "strategy": opt_strat_rail,
                            "dte": leg_dte,
                            "spread_pct": _spr_pct_rail,
                            "be_pct": be_pct,
                            "daily_theta": pos_theta_daily,
                        },
                    )

                in_notes_rail = st.text_area(
                    'Trading Diary Thesis Notes ("Why am I taking this trade?")',
                    height=65,
                    key="ticket_notes_rail"
                )

                col_c_slider, col_c_btn = st.columns([1.8, 1.2])
                with col_c_slider:
                    in_conv_rail = st.slider("Conviction (-200..+200)", min_value=-200, max_value=200, key="ticket_conv_rail")
                with col_c_btn:
                    st.write("")
                    submit_schwab_order = st.button("⚡ Transmit to Schwab", type="primary", width="stretch", key="btn_submit_unified_schwab")

                if submit_schwab_order:
                    _tif_raw_rail = str(st.session_state.get("ticket_tif_rail", "GTC") or "GTC").upper()
                    _rail_tif = "GTC" if "GTC" in _tif_raw_rail else "DAY"
                    _rail_cat_tag = str(
                        active_leg.get("catalyst_tag")
                        or prefill.get("catalyst_tag")
                        or m.get("earnings_date")
                        or ""
                    )
                    _rail_kwargs: Dict[str, Any] = {
                        "symbol": leg_sym,
                        "action": opt_action,
                        "option_type": opt_type_sel,
                        "strike": opt_strike_in,
                        "expiration_date": leg_exp,
                        "quantity": opt_qty_in,
                        "limit_price": opt_limit_in,
                        "stock_price_at_entry": spot_price,
                        "strategy": opt_strat_rail,
                        "order_type": opt_ord_type,
                        "target_stock_price": in_tgt_val,
                        "stop_stock_price": in_stp_val,
                        "conviction_score": int(in_conv_rail),
                        "expected_basis_pct": float(m.get("expected_basis_pct", 0.0) or 0.0),
                        "whale_badge": str(m.get("whale_badge", "⚪ TWO-WAY FLOW")),
                        "catalyst_tag": _rail_cat_tag,
                        "notes": in_notes_rail,
                        "dte": leg_dte,
                        "short_strike": opt_short_k_rail if is_spread_rail else None,
                        "implied_vol_at_entry": sigma_ticket,
                    }
                    if "time_in_force" in inspect.signature(diary_db.create_simulated_trade).parameters:
                        _rail_kwargs["time_in_force"] = _rail_tif
                    trade_res = diary_db.create_simulated_trade(**_rail_kwargs)
                    st.session_state["schwab_last_receipt"] = trade_res
                    if "schwab_active_leg" in st.session_state:
                        del st.session_state["schwab_active_leg"]
                    st.success(f"Order {trade_res['schwab_order_id']} confirmed!")
                    st.rerun()

        if st.session_state.pop("schwab_show_order_modal", False) and "schwab_active_leg" in st.session_state:
            render_schwab_order_dialog(st.session_state["schwab_active_leg"], cand_intel)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        with st.expander(f"📈 Multi-Horizon P&L Payoff Curve & 1–90 Day Options Decay Matrix for {active_sym} (${strike_p:.2f} {opt_type_sel} • {leg_dte} DTE)", expanded=True):
            st.caption(f"Visualizes Net Dollar P&L across underlying prices at 1–5D Swing Exit (T+4d), Mid-Cycle (50% DTE), and Expiration (0 DTE) for the {leg_dte}-DTE ({leg_exp}) contract:")
            rail_payoff_fig = rbc.create_schwab_payoff_curve_chart(
                symbol=active_sym,
                spot_price=spot_price,
                strike=strike_p,
                opt_type=opt_type_sel,
                limit_price=limit_p,
                qty=qty,
                dte=leg_dte,
                iv=sigma_ticket,
                target_price=tgt_spot,
                stop_price=stp_spot,
                strategy=opt_strat_rail,
                short_strike=opt_short_k_rail if is_spread_rail else None,
            )
            st.plotly_chart(rail_payoff_fig, width="stretch", config={"displayModeBar": False, "responsive": True})

            horizon_dtes = [7, 14, 21, 30, 45, 60, 75, 90]
            horizon_rows = []
            for d in horizon_dtes:
                c_p, c_d = rbe3.bs_call_price_delta(spot_price, strike_p, d / 365.0, 0.0425, sigma_ticket)
                p_p, p_d = rbe3.bs_put_price_delta(spot_price, strike_p, d / 365.0, 0.0425, sigma_ticket)
                g_c = calculate_option_greeks(spot_price, strike_p, d / 365.0, 0.0425, sigma_ticket, "CALL")
                g_p = calculate_option_greeks(spot_price, strike_p, d / 365.0, 0.0425, sigma_ticket, "PUT")
                horizon_rows.append({
                    "DTE": f"{d} Days",
                    "Cycle Type": "Weekly" if d < 20 else ("Monthly" if d in [30, 60, 90] else "Cycle"),
                    "Call Mark ($)": f"${c_p:.2f}",
                    "Call Delta": f"{c_d:+.2f}",
                    "Call Theta/Day": f"${g_c['theta']:.2f}/d",
                    "Put Mark ($)": f"${p_p:.2f}",
                    "Put Delta": f"{p_d:+.2f}",
                    "Put Theta/Day": f"${g_p['theta']:.2f}/d",
                    "Leverage Ratio": f"{(spot_price / max(0.1, c_p if opt_type_sel=='CALL' else p_p)):.1f}x"
                })
            st.dataframe(pd.DataFrame(horizon_rows), hide_index=True)

    with tab_ledger:
        st.markdown(f"### <i class='fa-solid fa-list-check' style='color:#FF6B00;'></i> Active Open Positions ({len(trades_with_live)})", unsafe_allow_html=True)
        if not trades_with_live:
            st.info("No open simulated options positions currently active. Use the Options Desk tab above to execute paper trades across any expiration up to 90 days.")
        else:
            for trade in trades_with_live:
                t_id = trade["id"]
                t_order_id = trade["schwab_order_id"]
                t_sym = trade["symbol"]
                t_act = trade["action"]
                t_type = trade["option_type"]
                t_strike = trade["strike"]
                t_exp = trade["expiration_date"]
                t_qty = trade["quantity"]
                t_entry_prem = trade["limit_price"]
                t_entry_spot = trade["stock_price_at_entry"]
                t_cost = trade["total_cost"]

                t_cur_spot = trade["live_spot"]
                t_cur_mark = trade["live_mark"]
                t_cur_val = trade["live_current_value"]
                t_pnl_d = trade["live_unrealized_pnl_dollar"]
                t_pnl_pct = trade["live_unrealized_pnl_pct"]
                t_dte = int(trade.get("dte_remaining", 35))
                t_dte_entry = int(trade.get("dte_at_entry", t_dte))
                t_held = trade["days_held"]
                t_notes = trade.get("notes", "")
                t_tgt = trade.get("target_stock_price")
                t_stop = trade.get("stop_stock_price")
                t_strat = str(trade.get("strategy", "SINGLE_LEG") or "SINGLE_LEG").upper()
                t_short_k = trade.get("short_strike")
                t_spread_tag = (
                    f"/ ${float(t_short_k):.2f} SPREAD"
                    if (t_strat == "VERTICAL_DEBIT_SPREAD" and t_short_k and float(t_short_k) > 0)
                    else ""
                )
                t_net_d = float(trade.get("net_delta_shares", 0.0) or 0.0)
                t_net_th = float(trade.get("daily_theta_dollars", 0.0) or 0.0)
                t_net_vg = float(trade.get("net_vega_dollars", 0.0) or 0.0)
                t_conv_raw = float(trade.get("conviction_score", 0.0) or 0.0)
                t_conv_signed = int(round(t_conv_raw))
                if t_type == "PUT" and t_conv_signed > 0 and t_conv_signed > 100:
                    t_conv_signed = -t_conv_signed

                conv_pill = _format_conviction_badge_html(t_conv_signed, t_type, is_legacy_100=False)
                dte_pill = _format_dte_badge_html(t_dte_entry, exact_dte=t_dte)

                pnl_color = "#34D399" if t_pnl_d >= 0 else "#FB7185"
                pnl_sign = "+" if t_pnl_d >= 0 else ""

                status_badge = '<span style="color: #94A3B8; font-size: 0.72rem; font-weight: 700;">IN PLAY</span>'
                if t_tgt and ((t_type == "CALL" and t_cur_spot >= t_tgt) or (t_type == "PUT" and t_cur_spot <= t_tgt)):
                    status_badge = '<span style="background: rgba(16, 185, 129, 0.18); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.45); font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">TARGET BREACHED</span>'
                elif t_stop and ((t_type == "CALL" and t_cur_spot <= t_stop) or (t_type == "PUT" and t_cur_spot >= t_stop)):
                    status_badge = '<span style="background: rgba(244, 63, 94, 0.18); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.45); font-size: 0.72rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">STOP-LOSS HIT</span>'

                _t_sym_s = _esc(t_sym)
                _t_act_s = _esc(t_act)
                _t_exp_s = _esc(t_exp)
                _t_type_s = _esc(t_type)
                _t_spread_s = _esc(t_spread_tag)
                _t_notes_trunc = (t_notes[:140] + "...") if len(t_notes) > 140 else t_notes
                _t_notes_s = _esc(_t_notes_trunc)

                render_clean_html(f"""
                <div class="schwab-pos-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            <span style="font-size: 1.15rem; font-weight: 800; color: #F1F5F9;">{_t_sym_s}</span>
                            <span class="obs-mono" style="background: rgba(255, 107, 0, 0.14); color: #FF8533; border: 1px solid rgba(255, 107, 0, 0.36); font-size: 0.74rem; font-weight: 700; padding: 2px 9px; border-radius: 9999px;">
                                {_t_act_s} {t_qty}x {_t_exp_s} ${t_strike:.2f} {_t_type_s} {_t_spread_s}
                            </span>
                            {conv_pill}
                            {dte_pill}
                            <span style="font-size: 0.72rem; color: #94A3B8;">Held {t_held}d</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            {status_badge}
                            <span class="obs-mono" style="font-size: 1.10rem; font-weight: 800; color: {pnl_color};">
                                {pnl_sign}${t_pnl_d:,.2f} ({pnl_sign}{t_pnl_pct:.1f}%)
                            </span>
                        </div>
                    </div>
                    <div class="obs-subpanel obs-mono" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 6px; font-size: 0.78rem; color: #CBD5E1; margin-bottom: 8px;">
                        <div>Entry Limit: <b style="color: #F1F5F9;">${t_entry_prem:.2f}</b></div>
                        <div>Current Mark: <b style="color: {pnl_color};">${t_cur_mark:.2f}</b></div>
                        <div>Cost Basis: <b style="color: #F1F5F9;">${t_cost:,.2f}</b></div>
                        <div>Market Value: <b style="color: #F1F5F9;">${t_cur_val:,.2f}</b></div>
                        <div>Entry / Spot: <b style="color: #F1F5F9;">${t_entry_spot:.2f} &rarr; ${t_cur_spot:.2f}</b></div>
                        <div>Net &Delta; / &Theta; / V: <b style="color: #FF8533;">{t_net_d:+.0f}sh &bull; ${t_net_th:+.1f}/d &bull; ${t_net_vg:+.1f}/v</b></div>
                    </div>
                    <div style="font-size: 0.75rem; color: #94A3B8; font-style: italic;">
                        "{_t_notes_s}"
                    </div>
                </div>
                """)

                col_c1, col_c2 = st.columns([4.0, 1.0])
                with col_c1:
                    with st.expander(f"Close Trade / Post-Mortem (Order {t_order_id})", expanded=False):
                        c_col1, c_col2 = st.columns(2)
                        with c_col1:
                            exit_p = st.number_input("Exit Option Premium ($)", value=round(float(t_cur_mark), 2), min_value=0.01, step=0.01, format="%.2f", key=f"exit_prem_{t_id}")
                        with c_col2:
                            exit_s = st.number_input("Exit Stock Price ($)", value=float(t_cur_spot), step=0.5, key=f"exit_spot_{t_id}")
                        exit_notes_in = st.text_area("Exit Notes & Post-Mortem Lesson", placeholder="Did I stick to my target or stop? What did the rubberband do?", key=f"exit_notes_{t_id}", height=60)

                        if st.button("Confirm Close Position (Sell to Close)", key=f"btn_close_trade_{t_id}", type="primary"):
                            diary_db.close_simulated_trade(t_id, exit_p, exit_s, exit_notes_in)
                            st.success(f"Position {t_order_id} closed and realized in database!")
                            st.rerun()
                with col_c2:
                    if st.button("Delete", key=f"btn_del_trade_{t_id}", help="Delete test order"):
                        diary_db.delete_simulated_trade(t_id)
                        st.rerun()

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("### <i class='fa-solid fa-clock-rotate-left' style='color:#FF6B00;'></i> Closed Positions & Historical Journal Review", unsafe_allow_html=True)
        closed_trades = diary_db.get_closed_trades(limit=50)
        if not closed_trades:
            st.caption("No closed trades recorded yet.")
        else:
            closed_rows = []
            for ct in closed_trades:
                pnl_d = ct["realized_pnl_dollar"]
                pnl_p = ct["realized_pnl_pct"]
                c_score = int(round(float(ct.get("conviction_score", 0) or 0)))
                c_dte = int(ct.get("dte_at_entry", 35) or 35)
                c_bucket = "45D" if c_dte >= 38 else "30D"
                closed_rows.append({
                    "Order Ref": ct["schwab_order_id"],
                    "Ticker": ct["symbol"],
                    "Contract": f"{ct['quantity']}x {ct['expiration_date']} ${ct['strike']:.2f} {ct['option_type']}",
                    "Conviction": f"{c_score:+d} {ct['option_type']}",
                    "DTE": f"{c_bucket} ({c_dte}d)",
                    "Entry Prem": f"${ct['limit_price']:.2f}",
                    "Exit Prem": f"${ct.get('exit_premium', 0.0):.2f}",
                    "Total Cost": f"${ct['total_cost']:,.2f}",
                    "Realized P&L ($)": f"{'+' if pnl_d >= 0 else ''}${pnl_d:,.2f}",
                    "Return (%)": f"{'+' if pnl_p >= 0 else ''}{pnl_p:.1f}%",
                    "Status": "WIN" if pnl_d > 0 else "LOSS",
                    "Exit Date": (ct.get("exit_timestamp") or "")[:10],
                    "Notes & Lessons": ct.get("notes", "")
                })
            st.dataframe(pd.DataFrame(closed_rows), width="stretch", hide_index=True)

    if ui_navigation is not None:
        ui_navigation.render_mobile_bottom_dock("Charles Schwab Practice Desk & Diary")


# =========================================================================
# VIEW 2: DAILY TOP-5 RECOMMENDATION LEDGER & EMPIRICAL PERFORMANCE AUDIT
# =========================================================================

def render_daily_recommendation_ledger_page():
    """Renders the Obsidian Frosted-Glass daily Top-5 recommendation ledger and historical audit page."""
    _inject_obsidian_desk_css()

    try:
        import ui_navigation
        ui_navigation.render_top_navigation_strip("Daily Top-5 Recommendation Ledger")
    except Exception:
        ui_navigation = None

    render_clean_html("""
    <div class="schwab-ribbon">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="obs-pill-orange">AUTONOMOUS LEDGER</span>
                    <span style="font-size: 1.25rem; font-weight: 800; color: #F1F5F9; letter-spacing: -0.02em;">Daily Top-5 Recommendation Ledger &amp; Live Audit</span>
                    <span style="background: rgba(255, 255, 255, 0.06); color: #CBD5E1; font-size: 0.70rem; font-weight: 700; padding: 2px 9px; border-radius: 9999px; border: 1px solid rgba(255, 255, 255, 0.12);">24/7 GX10 DAEMON</span>
                </div>
                <div style="font-size: 0.78rem; color: #94A3B8; margin-top: 5px;">
                    Empirical daily logging across 5 core sectors &amp; thematic ETFs. Audits whether recommendations achieved their predicted 1–5 day basis moves.
                </div>
            </div>
            <div style="font-size: 0.74rem; color: #34D399; background: rgba(16, 185, 129, 0.12); padding: 5px 12px; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.34);">
                <i class="fa-solid fa-server fa-icon-inline"></i> SQLite WAL: <code class="obs-mono">data/simulated_diary.db</code>
            </div>
        </div>
    </div>
    """)

    available_dates = diary_db.get_all_snapshot_dates()
    if not available_dates:
        st.warning("No daily recommendation snapshots found in database. The 24/7 daemon will record today's snapshot shortly, or click 'Run Immediate Snapshot' below.")
        if st.button("Run Immediate Snapshot of All 5 Sectors", type="primary"):
            with st.spinner("Executing Top-5 vetting across all 5 sectors..."):
                import daily_tracker_daemon
                daily_tracker_daemon.capture_all_sectors_snapshot(force=True)
            st.success("Top-5 snapshots captured!")
            st.rerun()
        return

    col_f1, col_f2, col_f3 = st.columns([1.5, 2.0, 1.2])
    with col_f1:
        sel_date = st.selectbox("Snapshot Date", options=available_dates, index=0, key="rec_ledger_date")
    with col_f2:
        sec_options = ["All Sectors"] + list(rbe3.SECTORS.keys())
        sel_sector = st.selectbox("Sector Universe", options=sec_options, index=0, key="rec_ledger_sector")
    with col_f3:
        st.write("")
        if st.button("Refresh Quotes", key="rec_ledger_refresh"):
            st.rerun()

    # Fetch snapshots (normalize legacy sector names so old snapshots map cleanly under the 5 expanded sectors)
    if sel_sector == "All Sectors":
        snapshots = diary_db.get_historical_snapshots(snapshot_date=sel_date, sector_name="All Sectors")
    else:
        all_for_date = diary_db.get_historical_snapshots(snapshot_date=sel_date, sector_name=None)
        snapshots = [
            row for row in all_for_date
            if _normalize_sector_safe(row.get("sector", "")) == sel_sector
        ]

    if not snapshots:
        st.info(f"No snapshot entries found for {sel_date} in '{sel_sector}'.")
        return

    symbols = list(set([s["symbol"] for s in snapshots]))
    live_quotes = rbe3.fmp_batch_quotes(symbols, ttl=60)
    hist_series_map: Dict[str, Any] = {}
    for sym in symbols:
        try:
            hdf_s, _, _ = rbe3.get_hybrid_price_series(sym, fetch_4h=False)
            hist_series_map[sym] = hdf_s
        except Exception:
            hist_series_map[sym] = None

    snap_ts = pd.Timestamp(str(sel_date)[:10])
    audited_recs = []
    wins_count = 0
    target_hits_count = 0
    total_dir_ret = 0.0
    total_opt_roi = 0.0

    for s in snapshots:
        sym = s["symbol"]
        snap_price = float(s["price_at_snapshot"])
        act = s["action"].upper()
        q = live_quotes.get(sym, {})
        cur_price = float(q.get("price", snap_price) or snap_price)

        delta_dollar = round(cur_price - snap_price, 2)
        delta_pct = round(((cur_price - snap_price) / max(0.01, snap_price)) * 100.0, 2)

        # Parse raw_meta_json safely to detect -200..+200 conviction & recommended_dte if stored
        meta_json = {}
        try:
            if s.get("raw_meta_json"):
                meta_json = json.loads(s["raw_meta_json"])
        except Exception:
            meta_json = {}

        rec_s200 = meta_json.get("conviction_score_200")
        has_200 = (rec_s200 is not None)
        rec_dte_val = int(meta_json.get("recommended_dte") or 35)
        rec_dte_rat = str(meta_json.get("dte_rationale") or "")
        tgt_p_rec = float(s.get("target_price") or snap_price)
        inv_p_rec = float(s.get("invalidation_price") or snap_price * 0.95)
        rec_strike = float(s.get("recommended_strike") or snap_price)

        # Evaluate actual T+1..T+5 trading-day path when elapsed
        mfe_5d_pct = delta_pct if "CALL" in act else (-delta_pct if "PUT" in act else 0.0)
        mae_5d_pct = mfe_5d_pct
        t5_close_pct = mfe_5d_pct
        hit_target_5d = False
        hit_stop_5d = False
        fwd_bars_n = 0
        end_spot_eval = cur_price

        hdf = hist_series_map.get(sym)
        if hdf is not None and not hdf.empty:
            try:
                if "date" in hdf.columns:
                    dt_ser = pd.to_datetime(hdf["date"], errors="coerce")
                else:
                    dt_ser = pd.to_datetime(hdf.index, errors="coerce")
                fwd = hdf[dt_ser > snap_ts].head(5)
                if not fwd.empty:
                    fwd_bars_n = int(len(fwd))
                    hi_col = "high" if "high" in fwd.columns else "close"
                    lo_col = "low" if "low" in fwd.columns else "close"
                    cl_col = "close" if "close" in fwd.columns else hi_col
                    hi_max = float(fwd[hi_col].max())
                    lo_min = float(fwd[lo_col].min())
                    cl_end = float(fwd[cl_col].iloc[-1])
                    end_spot_eval = cl_end
                    if "PUT" in act:
                        mfe_5d_pct = ((snap_price - lo_min) / max(0.01, snap_price)) * 100.0
                        mae_5d_pct = ((snap_price - hi_max) / max(0.01, snap_price)) * 100.0
                        t5_close_pct = ((snap_price - cl_end) / max(0.01, snap_price)) * 100.0
                        hit_target_5d = bool(0 < tgt_p_rec < snap_price and lo_min <= tgt_p_rec)
                        hit_stop_5d = bool(inv_p_rec > snap_price and hi_max >= inv_p_rec)
                    else:
                        mfe_5d_pct = ((hi_max - snap_price) / max(0.01, snap_price)) * 100.0
                        mae_5d_pct = ((lo_min - snap_price) / max(0.01, snap_price)) * 100.0
                        t5_close_pct = ((cl_end - snap_price) / max(0.01, snap_price)) * 100.0
                        hit_target_5d = bool(tgt_p_rec > snap_price and hi_max >= tgt_p_rec)
                        hit_stop_5d = bool(inv_p_rec > 0 and lo_min <= inv_p_rec)
            except Exception:
                pass

        # Estimate option ROI over the evaluated horizon (T+1..T+5 or live)
        sigma_eval = float(meta_json.get("iv_pct") or 40.0)
        sigma_eval = sigma_eval / 100.0 if sigma_eval > 3.0 else max(0.15, sigma_eval)
        t_in_e = max(5, rec_dte_val) / 365.0
        t_out_e = max(1, rec_dte_val - max(1, fwd_bars_n)) / 365.0
        if "PUT" in act:
            p_in_e, _ = rbe3.bs_put_price_delta(snap_price, rec_strike, t_in_e, 0.0425, sigma_eval)
            p_out_e, _ = rbe3.bs_put_price_delta(end_spot_eval, rec_strike, t_out_e, 0.0425, sigma_eval)
        else:
            p_in_e, _ = rbe3.bs_call_price_delta(snap_price, rec_strike, t_in_e, 0.0425, sigma_eval)
            p_out_e, _ = rbe3.bs_call_price_delta(end_spot_eval, rec_strike, t_out_e, 0.0425, sigma_eval)
        est_opt_roi_pct = ((p_out_e - p_in_e) / max(0.05, p_in_e)) * 100.0 if p_in_e > 0.05 else 0.0
        est_opt_roi_pct = max(-100.0, est_opt_roi_pct)

        if "CALL" in act or "PUT" in act:
            is_win = bool(hit_target_5d or t5_close_pct > 0.0)
        else:
            is_win = (abs(delta_pct) < 2.0)

        if is_win:
            wins_count += 1
        if hit_target_5d:
            target_hits_count += 1
        total_dir_ret += t5_close_pct
        total_opt_roi += est_opt_roi_pct

        rec_item = dict(s)
        rec_item.update({
            "normalized_sector": _normalize_sector_safe(s.get("sector", "")),
            "current_price": cur_price,
            "delta_dollar": delta_dollar,
            "delta_pct": delta_pct,
            "is_win": is_win,
            "mfe_5d_pct": round(mfe_5d_pct, 2),
            "mae_5d_pct": round(mae_5d_pct, 2),
            "t5_close_pct": round(t5_close_pct, 2),
            "hit_target_5d": hit_target_5d,
            "hit_stop_5d": hit_stop_5d,
            "fwd_bars_n": fwd_bars_n,
            "est_opt_roi_5d_pct": round(est_opt_roi_pct, 1),
            "conviction_score_200": int(round(float(rec_s200))) if has_200 else None,
            "recommended_dte": rec_dte_val,
            "dte_rationale": rec_dte_rat,
        })
        audited_recs.append(rec_item)

    win_rate = (wins_count / len(audited_recs) * 100.0) if audited_recs else 0.0
    avg_delta = (total_dir_ret / len(audited_recs)) if audited_recs else 0.0
    avg_opt_roi = (total_opt_roi / len(audited_recs)) if audited_recs else 0.0

    render_clean_html(f"""
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 20px;">
        <div class="rm-command-card" style="border-left: 3px solid #FF6B00;">
            <div class="rm-command-label">Audited Snapshot Date</div>
            <div class="rm-command-value" style="color: #FF8533;">{sel_date}</div>
            <div class="rm-command-sub">Vetted Picks: <b>{len(audited_recs)}</b> &bull; Target Hits: <b>{target_hits_count}</b></div>
        </div>
        <div class="rm-command-card">
            <div class="rm-command-label">T+1..T+5 Hit Rate</div>
            <div class="rm-command-value" style="color: {'#34D399' if win_rate >= 50 else '#FB7185'};">{win_rate:.1f}%</div>
            <div class="rm-command-sub"><b>{wins_count}</b> / {len(audited_recs)} Positive Horizon Expectancy</div>
        </div>
        <div class="rm-command-card">
            <div class="rm-command-label">Avg T+5 Directional Edge</div>
            <div class="rm-command-value" style="color: {'#34D399' if avg_delta >= 0 else '#FB7185'};">{'+' if avg_delta >= 0 else ''}{avg_delta:.2f}%</div>
            <div class="rm-command-sub">5-Day Trading Window Return</div>
        </div>
        <div class="rm-command-card">
            <div class="rm-command-label">Est. 35D Option ROI</div>
            <div class="rm-command-value" style="color: {'#34D399' if avg_opt_roi >= 0 else '#FB7185'};">{'+' if avg_opt_roi >= 0 else ''}{avg_opt_roi:.1f}%</div>
            <div class="rm-command-sub">Horizon BS Mark Across Picks</div>
        </div>
    </div>
    """)

    if _edu is not None:
        _edu.render_edu_drawer(
            "journal_audit",
            live_ctx={
                "snapshot_date": sel_date,
                "win_rate_pct": win_rate,
                "avg_dir_pct": avg_delta,
                "avg_opt_roi_pct": avg_opt_roi,
                "count": len(audited_recs),
            },
            compact=True,
            align="right",
        )

    st.markdown("### <i class='fa-solid fa-trophy' style='color:#FF6B00;'></i> Top 5 Vetted Candidates by Sector", unsafe_allow_html=True)

    sectors_in_snap: Dict[str, List[Dict[str, Any]]] = {}
    for r in audited_recs:
        sec = r["normalized_sector"]
        sectors_in_snap.setdefault(sec, []).append(r)

    for sec_name, rec_list in sectors_in_snap.items():
        st.markdown(f"#### <i class='fa-solid fa-layer-group' style='color:#FF8533;'></i> {_esc(sec_name)}", unsafe_allow_html=True)
        for rec_idx, r in enumerate(rec_list):
            rank = r["rank"]
            sym = r["symbol"]
            act = r["action"]
            comp_score = r["composite_score"]
            snap_p = r["price_at_snapshot"]
            cur_p = r["current_price"]
            d_pct = r["delta_pct"]
            d_dol = r["delta_dollar"]
            is_win = r["is_win"]
            exp_basis = r.get("expected_basis_pct", 0.0)
            whale_b = r.get("whale_badge", "TWO-WAY FLOW")
            days_er = r.get("days_to_earnings", 45)
            rec_strike = r.get("recommended_strike", snap_p)
            tgt_p_rec = r.get("target_price", snap_p)
            inv_p_rec = r.get("invalidation_price", snap_p * 0.95)
            s200 = r.get("conviction_score_200")
            rec_dte_val = int(r.get("recommended_dte", 35))
            dte_rat = r.get("dte_rationale", "")
            r_mfe = float(r.get("mfe_5d_pct", 0.0))
            r_t5 = float(r.get("t5_close_pct", 0.0))
            r_opt_roi = float(r.get("est_opt_roi_5d_pct", 0.0))
            r_bars = int(r.get("fwd_bars_n", 0))
            r_hit_tgt = bool(r.get("hit_target_5d", False))
            r_hit_stp = bool(r.get("hit_stop_5d", False))

            opt_dir = "CALL" if "CALL" in act.upper() else ("PUT" if "PUT" in act.upper() else "")
            if s200 is not None:
                conv_badge_html = _format_conviction_badge_html(s200, opt_dir, is_legacy_100=False)
            else:
                conv_badge_html = _format_conviction_badge_html(comp_score, opt_dir, is_legacy_100=True)
            dte_badge_html = _format_dte_badge_html(rec_dte_val, rationale=dte_rat)
            etf_badge_html = (
                '<span class="obs-pill-orange" style="font-size:0.64rem; padding:2px 7px;">ETF</span>'
                if _is_etf_symbol(sym) else ""
            )

            delta_col = "#34D399" if d_pct >= 0 else "#FB7185"
            sign_char = "+" if d_pct >= 0 else ""
            win_pill = (
                '<span style="background: rgba(16,185,129,0.16); color: #34D399; border: 1px solid rgba(16,185,129,0.42); font-size: 0.72rem; font-weight: 800; padding: 2px 9px; border-radius: 9999px;">WINNING MOVE</span>'
                if is_win else
                '<span style="background: rgba(244,63,94,0.16); color: #FB7185; border: 1px solid rgba(244,63,94,0.42); font-size: 0.72rem; font-weight: 800; padding: 2px 9px; border-radius: 9999px;">ADVERSE MOVE</span>'
            )
            tgt_pill = (
                '<span style="background: rgba(56,189,248,0.14); color: #38BDF8; border: 1px solid rgba(56,189,248,0.38); font-size: 0.68rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">TARGET HIT (5D)</span>'
                if r_hit_tgt else (
                    '<span style="background: rgba(244,63,94,0.14); color: #FB7185; border: 1px solid rgba(244,63,94,0.38); font-size: 0.68rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px;">STOP HIT</span>'
                    if r_hit_stp else ""
                )
            )
            horizon_tag = f"T+{r_bars}d" if r_bars > 0 else "Intraday"

            render_clean_html(f"""
            <div class="ledger-rec-card">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 10px;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span style="font-size: 1.15rem; font-weight: 800; color: #F1F5F9;">#{rank} {_esc(sym)}</span>
                        {etf_badge_html}
                        <span style="background: {'rgba(16,185,129,0.15)' if 'CALL' in act else 'rgba(244,63,94,0.15)'}; color: {'#34D399' if 'CALL' in act else '#FB7185'}; border: 1px solid {'rgba(16,185,129,0.35)' if 'CALL' in act else 'rgba(244,63,94,0.35)'}; font-size: 0.72rem; font-weight: 800; padding: 2px 9px; border-radius: 9999px;">
                            {_esc(act)}
                        </span>
                        {conv_badge_html}
                        {dte_badge_html}
                        {win_pill}
                        {tgt_pill}
                    </div>
                    <div class="obs-mono" style="font-size: 1.05rem; font-weight: 800; color: {delta_col};">
                        {sign_char}${d_dol:.2f} ({sign_char}{d_pct:.2f}%)
                    </div>
                </div>
                <div class="obs-subpanel obs-mono" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 6px; font-size: 0.76rem; color: #CBD5E1;">
                    <div>Snapshot Spot: <b style="color: #94A3B8;">${snap_p:.2f}</b></div>
                    <div>Live Spot: <b style="color: #F1F5F9;">${cur_p:.2f}</b></div>
                    <div>{horizon_tag} Dir / MFE: <b style="color: {'#34D399' if r_t5 >= 0 else '#FB7185'};">{r_t5:+.2f}%</b> / <b style="color: #34D399;">{r_mfe:+.2f}%</b></div>
                    <div>Est Opt ROI ({horizon_tag}): <b style="color: {'#34D399' if r_opt_roi >= 0 else '#FB7185'};">{r_opt_roi:+.1f}%</b></div>
                    <div>5Y Exp Basis: <b style="color: #FF8533;">{exp_basis:+.2f}%</b></div>
                    <div>Whale Tape: <b style="color: #F1F5F9;">{_esc(whale_b)}</b></div>
                    <div>ER / Strike: <b>{f'ER {days_er}d' if (days_er and days_er <= 25) else 'Clear'} &bull; ${rec_strike:.2f}</b></div>
                </div>
            </div>
            """)

            col_btn1, _ = st.columns([1.6, 4.0])
            with col_btn1:
                if st.button(f"Simulate {sym} in Schwab Diary ↗", key=f"btn_sim_rec_{sec_name}_{sym}_{rank}_{rec_idx}"):
                    prefill_payload: Dict[str, Any] = {
                        "symbol": sym,
                        "action": "BUY_TO_OPEN",
                        "option_type": "CALL" if "CALL" in act else "PUT",
                        "strike": rec_strike,
                        "dte": rec_dte_val,
                        "recommended_dte": 45 if rec_dte_val >= 38 else 30,
                        "spot_price": cur_p,
                        "target_price": tgt_p_rec,
                        "stop_price": inv_p_rec,
                        "conviction_score": s200 if s200 is not None else comp_score,
                        "expected_basis_pct": exp_basis,
                        "whale_badge": whale_b,
                        "notes": f"Simulated from Daily Recommendation Ledger ({sel_date} #{rank} {sec_name}). Action: {act}."
                    }
                    if s200 is not None:
                        prefill_payload["conviction_score_200"] = s200
                    st.session_state["schwab_prefill"] = prefill_payload
                    if "schwab_active_leg" in st.session_state:
                        del st.session_state["schwab_active_leg"]
                    st.session_state["schwab_prefill_needs_sync"] = True
                    st.session_state["pending_workspace_view"] = "Charles Schwab Practice Desk & Diary"
                    st.session_state["active_app_view"] = "Charles Schwab Practice Desk & Diary"
                    st.rerun()

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
    with st.expander(f"Full Quantitative Ledger Data for {sel_date} ({len(audited_recs)} Records)", expanded=False):
        table_rows = []
        for r in audited_recs:
            s200 = r.get("conviction_score_200")
            dte_b = "45D" if int(r.get("recommended_dte", 35)) >= 38 else "30D"
            conv_str = f"{s200:+d}" if s200 is not None else f"{r['composite_score']:.0f}/100 (Legacy)"
            table_rows.append({
                "Date": r["snapshot_date"],
                "Sector": r["normalized_sector"],
                "Rank": f"#{r['rank']}",
                "Symbol": r["symbol"],
                "Action": r["action"],
                "Conviction": conv_str,
                "DTE": dte_b,
                "Snapshot $": f"${r['price_at_snapshot']:.2f}",
                "Live Spot $": f"${r['current_price']:.2f}",
                "Delta %": f"{r['delta_pct']:+.2f}%",
                "Exp Basis %": f"{r.get('expected_basis_pct', 0.0):+.2f}%",
                "Whale": r.get("whale_badge", ""),
                "Strike": f"${r.get('recommended_strike', 0.0):.2f}"
            })
        st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)

    if ui_navigation is not None:
        ui_navigation.render_mobile_bottom_dock("Daily Top-5 Recommendation Ledger")
