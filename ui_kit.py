"""
Rubberband Man - Uniform UI Kit
================================
Single source of truth for page-level layout primitives, conviction badges,
and 5-day circular catalyst ring SVGs in the Obsidian Frosted-Glass + Hyper-Orange design system.

Semantic palette:
  POS  #10B981  (emerald bullish / healthy / MFE)
  NEG  #F43F5E  (rose bearish / stress / MAE)
  WARN #FB923C  (hyper-orange / warm caution)
  INFO #FF6B00  (primary Hyper-Orange accent)
"""
from __future__ import annotations

import html as _html
import math
import streamlit as st

POS = "#10B981"
NEG = "#F43F5E"
WARN = "#FB923C"
INFO = "#FF6B00"


def tone(value: float, hi: float, lo: float, invert: bool = False) -> str:
    """Map a value onto the semantic POS / WARN / NEG hex palette.

    ``value >= hi`` is POS and ``value <= lo`` is NEG (swapped when ``invert``).
    """
    if invert:
        return NEG if value >= hi else (POS if value <= lo else WARN)
    return POS if value >= hi else (NEG if value <= lo else WARN)


def _flat(raw_html: str) -> str:
    """Collapse indentation/newlines so Streamlit markdown never treats HTML as code blocks."""
    return "".join(line.strip() for line in raw_html.strip().splitlines())


def zone_header(index: str, title: str, subtitle: str = "", icon: str = "") -> None:
    """Large page-zone divider (e.g. "01 · Market Regime")."""
    icon_html = f'<i class="fa-solid {icon}"></i>' if icon else ""
    sub_html = f'<div class="rmz-zone-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(_flat(f"""
    <div class="rmz-zone">
      <div class="rmz-zone-left">
        <span class="rmz-zone-idx">{index}</span>
        <div>
          <div class="rmz-zone-title">{icon_html}<span>{title}</span></div>
          {sub_html}
        </div>
      </div>
    </div>
    """), unsafe_allow_html=True)


def section_header_html(title: str, icon: str = "", subtitle: str = "", meta_html: str = "",
                        icon_color: str = "") -> str:
    """Card-level section header HTML: title (+ optional icon & subtitle) left, meta chips right."""
    icon_style = f' style="color: {icon_color};"' if icon_color else ""
    icon_html = f'<i class="fa-solid {icon}"{icon_style}></i>' if icon else ""
    sub_html = f'<div class="rmz-sec-sub">{subtitle}</div>' if subtitle else ""
    meta = f'<div class="rmz-sec-meta">{meta_html}</div>' if meta_html else ""
    return _flat(f"""
    <div class="rmz-sec">
      <div class="rmz-sec-left">
        <div class="rmz-sec-title">{icon_html}<span>{title}</span></div>
        {sub_html}
      </div>
      {meta}
    </div>
    """)


def section_header(title: str, icon: str = "", subtitle: str = "", meta_html: str = "",
                   icon_color: str = "") -> None:
    """Render a card-level section header in Streamlit."""
    st.markdown(section_header_html(title, icon, subtitle, meta_html, icon_color), unsafe_allow_html=True)


def format_conviction_200_badge(score_200: int, opt_type: str = "") -> str:
    """Return a frosted-glass HTML pill showing signed -200..+200 conviction and CALL/PUT tone."""
    try:
        val = int(round(float(score_200)))
    except (TypeError, ValueError):
        val = 0
    val = max(-200, min(200, val))
    abs_val = abs(val)
    score_str = f"{val:+d}" if val != 0 else "0"

    opt_upper = (opt_type or "").strip().upper()
    if "CALL" in opt_upper:
        dir_label = "CALL"
    elif "PUT" in opt_upper:
        dir_label = "PUT"
    elif val > 35:
        dir_label = "CALL"
    elif val < -35:
        dir_label = "PUT"
    else:
        dir_label = "NEUTRAL"

    is_asymmetric = abs_val >= 150
    if dir_label == "CALL":
        tone_cls = "is-call"
        dot_col = "#10B981"
        dir_col = "#34D399"
    elif dir_label == "PUT":
        tone_cls = "is-put"
        dot_col = "#F43F5E"
        dir_col = "#FB7185"
    else:
        tone_cls = "is-neutral"
        dot_col = "#64748B"
        dir_col = "#94A3B8"

    asym_cls = " is-asymmetric" if is_asymmetric else ""
    score_col = "#FF8533" if is_asymmetric else ("#E2E8F0" if abs_val >= 70 else "#94A3B8")
    tier_tag = '<span class="rm-conv-tier">ASYM</span>' if is_asymmetric else ""

    return _flat(f"""
    <span class="rm-conviction-pill {tone_cls}{asym_cls}" title="Signed Conviction Score: {score_str} / ±200 ({dir_label})">
      <span class="rm-conv-dot" style="background: {dot_col}; box-shadow: 0 0 8px {dot_col};"></span>
      <span class="rm-conv-score" style="color: {score_col};">{score_str}</span>
      <span class="rm-conv-dir" style="color: {dir_col};">{dir_label}</span>
      {tier_tag}
    </span>
    """)


def render_5day_ring_svg(
    pct: int,
    label: str,
    sub: str,
    is_active: bool = False,
    tone_hex: str = "#FF6B00",
) -> str:
    """Return a crisp dark-mode frosted circular progress ring card for the 5-day catalyst strip."""
    try:
        clamped = max(0, min(100, int(round(float(pct)))))
    except (TypeError, ValueError):
        clamped = 0

    safe_label = _html.escape(str(label or ""))
    safe_sub = _html.escape(str(sub or ""))
    ring_col = (tone_hex or "#FF6B00").strip()
    if not ring_col.startswith("#"):
        ring_col = "#FF6B00"

    radius = 31.0
    circumference = 2.0 * math.pi * radius
    offset = circumference * (1.0 - (clamped / 100.0))

    active_cls = " is-active" if is_active else ""
    glow_style = f"filter: drop-shadow(0 0 8px {ring_col}88);" if (is_active or clamped >= 65) else ""
    pct_color = "#F8FAFC" if (is_active or clamped >= 50) else "#CBD5E1"
    label_color = "#FF8533" if is_active else "#E2E8F0"

    return _flat(f"""
    <div class="rm-day-card{active_cls}">
      <div class="rm-day-ring-wrap">
        <svg viewBox="0 0 80 80" width="62" height="62" aria-label="{safe_label}: {clamped}%">
          <circle cx="40" cy="40" r="{radius:.1f}" fill="rgba(10, 12, 18, 0.65)" stroke="rgba(255, 255, 255, 0.08)" stroke-width="5.5" />
          <circle cx="40" cy="40" r="{radius:.1f}" fill="none" stroke="{ring_col}" stroke-width="5.5" stroke-linecap="round"
                  stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}"
                  transform="rotate(-90 40 40)" style="{glow_style}" />
          <text x="40" y="44" text-anchor="middle" fill="{pct_color}"
                font-family="JetBrains Mono, monospace" font-size="14" font-weight="700"
                style="font-variant-numeric: tabular-nums;">{clamped}%</text>
        </svg>
      </div>
      <div class="rm-day-label" style="color: {label_color};">{safe_label}</div>
      <div class="rm-day-sub">{safe_sub}</div>
    </div>
    """)
