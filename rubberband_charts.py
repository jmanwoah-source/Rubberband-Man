"""
Rubberband Visual Depiction Engine v3.5 - Flagship Institutional Dark OLED Theme
100% Aligned with the Dual-Coordinate Kinetic Engine (VWMA-20, ATR-14, O-U Half-Life,
FMP Pro Altman Z / Piotroski Bifurcation, and 6-Pillar 24/48H Macro Radar).
"""

import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional


def create_rubberband_gauge(
    z_score: float,
    ticker: str,
    action: str,
    half_life: float = 4.0,
    hurst: float = 0.45,
    ou_half_life: Optional[float] = None,
    playbook: str = "",
    conviction_score_200: Optional[float] = None,
    axis_range: Optional[Tuple[float, float]] = None,
    metric_label: Optional[str] = None,
    suffix: Optional[str] = None,
) -> go.Figure:
    """
    Renders an Obsidian Glass Rubberband Tension or Signed Conviction Gauge.
    Supports both Dual-Coordinate Z-Score (-3.5σ to +3.5σ) and Signed Conviction (-200 to +200)
    without label clipping.
    """
    if ou_half_life is not None:
        half_life = ou_half_life

    is_conv_mode = (
        conviction_score_200 is not None
        or (axis_range is not None and abs(float(axis_range[1]) - float(axis_range[0])) > 20.0)
        or abs(float(z_score or 0.0)) > 10.0
    )

    if is_conv_mode:
        val = float(conviction_score_200 if conviction_score_200 is not None else z_score)
        rng_lo, rng_hi = axis_range if axis_range is not None else (-200.0, 200.0)
        val = max(rng_lo, min(rng_hi, val))
        abs_val = abs(val)
        if abs_val >= 150.0:
            bar_color = "#FF6B00"
        elif val > 35.0:
            bar_color = "#10B981"
        elif val < -35.0:
            bar_color = "#F43F5E"
        else:
            bar_color = "#64748B"

        tier_txt = (
            "ASYMMETRIC CONVICTION" if abs_val >= 150
            else "HIGH CONVICTION" if abs_val >= 110
            else "TACTICAL EDGE" if abs_val >= 70
            else "WATCH / DEVELOPING" if abs_val >= 36
            else "NEUTRAL / NOISE"
        )
        tier_col = "#FF8533" if abs_val >= 150 else ("#10B981" if val > 35 else ("#F43F5E" if val < -35 else "#94A3B8"))

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=val,
            domain={'x': [0.10, 0.90], 'y': [0.19, 0.90]},
            delta={'reference': 0.0, 'position': "bottom", 'valueformat': "+.0f", 'font': {'color': '#94A3B8', 'size': 12}},
            number={
                'valueformat': "+.0f",
                'suffix': suffix or "",
                'font': {'size': 34, 'family': 'JetBrains Mono', 'color': '#E2E8F0'}
            },
            gauge={
                'axis': {
                    'range': [rng_lo, rng_hi],
                    'tickvals': [-200, -150, -100, -35, 0, 35, 100, 150, 200],
                    'ticktext': ["-200", "-150", "-100", "-35", "0", "+35", "+100", "+150", "+200"],
                    'tickwidth': 1,
                    'tickcolor': "rgba(255, 255, 255, 0.14)",
                    'tickfont': {'color': '#94A3B8', 'size': 9.5, 'family': 'JetBrains Mono'}
                },
                'bar': {'color': bar_color, 'thickness': 0.28},
                'bgcolor': "rgba(12, 15, 22, 0.55)",
                'borderwidth': 1,
                'bordercolor': "rgba(255, 255, 255, 0.08)",
                'steps': [
                    {'range': [-200, -150], 'color': 'rgba(244, 63, 94, 0.26)'},
                    {'range': [-150, -35], 'color': 'rgba(244, 63, 94, 0.10)'},
                    {'range': [-35, 35], 'color': 'rgba(148, 163, 184, 0.07)'},
                    {'range': [35, 150], 'color': 'rgba(16, 185, 129, 0.10)'},
                    {'range': [150, 200], 'color': 'rgba(255, 107, 0, 0.26)'}
                ],
                'threshold': {
                    'line': {'color': "#FF8533" if abs_val >= 150 else "#E2E8F0", 'width': 3},
                    'thickness': 0.76,
                    'value': val
                }
            }
        ))

        sub_lbl = metric_label or f"<b style='color:{tier_col}'>{tier_txt}</b>"
        fig.add_annotation(
            x=0.5, y=0.01, xref="paper", yref="paper",
            text=f"<span style='color:#94A3B8;font-size:11px;'>{sub_lbl} • τ½: <b style='color:#E2E8F0'>{half_life:.1f}d</b> • H={hurst:.2f}</span>",
            showarrow=False, align="center"
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1"),
            height=320,
            autosize=True,
            margin=dict(l=28, r=28, t=22, b=26)
        )
        return fig

    if z_score <= -1.65:
        bar_color = "#10B981"  # Emerald (Oversold Call Zone)
    elif z_score >= 1.65:
        bar_color = "#F43F5E"  # Rose (Overbought Put Zone)
    elif "CALL" in action:
        bar_color = "#10B981"
    elif "PUT" in action:
        bar_color = "#F43F5E"
    else:
        bar_color = "#FB923C"  # Hyper-Orange Equilibrium / Coil

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=z_score,
        domain={'x': [0.08, 0.92], 'y': [0.17, 0.92]},
        delta={'reference': 0.0, 'position': "bottom", 'valueformat': "+.2f", 'font': {'color': '#94A3B8', 'size': 12.5}},
        number={'suffix': suffix or "σ", 'font': {'size': 35, 'family': 'JetBrains Mono', 'color': '#E2E8F0'}},
        gauge={
            'axis': {
                'range': list(axis_range) if axis_range else [-3.5, 3.5],
                'tickwidth': 1,
                'tickcolor': "rgba(255, 255, 255, 0.14)",
                'ticksuffix': suffix or "σ",
                'tickfont': {'color': '#94A3B8', 'size': 10.5, 'family': 'JetBrains Mono'}
            },
            'bar': {'color': bar_color, 'thickness': 0.26},
            'bgcolor': "rgba(12, 15, 22, 0.55)",
            'borderwidth': 1,
            'bordercolor': "rgba(255, 255, 255, 0.08)",
            'steps': [
                {'range': [-3.5, -1.65], 'color': 'rgba(16, 185, 129, 0.20)'},
                {'range': [-1.65, 1.65], 'color': 'rgba(255, 255, 255, 0.04)'},
                {'range': [1.65, 3.5], 'color': 'rgba(244, 63, 94, 0.20)'}
            ],
            'threshold': {
                'line': {'color': "#FF6B00", 'width': 3},
                'thickness': 0.74,
                'value': z_score
            }
        }
    ))

    regime_txt = "Mean-Reverting Spring" if hurst < 0.48 else ("Momentum Runner" if hurst > 0.53 else "Coiled Swing")
    fig.add_annotation(
        x=0.5, y=0.01, xref="paper", yref="paper",
        text=f"<span style='color:#94A3B8;font-size:11px;'>O-U Snap Half-Life: <b style='color:#E2E8F0'>{half_life:.1f} Days</b> • Hurst H={hurst:.2f} (<b style='color:#FB923C'>{regime_txt}</b>)</span>",
        showarrow=False, align="center"
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1"),
        height=320,
        autosize=True,
        margin=dict(l=22, r=22, t=20, b=26)
    )
    return fig


def create_rubberband_envelope_visual(ticker: str, metrics: Dict[str, Any], t_closes: Any) -> go.Figure:
    """
    Renders the AAA 35-Day Institutional VWMA-20 & ATR Elasticity Channel + 5-Day Forward Projection Cone:
    - Computes full 20-day VWMA/EMA & ATR on the complete historical series BEFORE slicing the 35-day window
      (eliminating left-side warmup lag and right-edge crowding).
    - Layered Overbought (+1.6σ to +2.4σ) Coral Zone & Oversold (-1.6σ to -2.4σ) Emerald Snapback Zone
    - Glowing Amber-Gold VWMA-20 Institutional Equilibrium Centerline
    - 1-5 Day Ornstein-Uhlenbeck Forward Snapback Trajectory Cone (+1D to +5D)
    - Non-overlapping right-side callouts for 30-45 DTE Strike, 1-5D Target, and Hard Invalidation Stop
    """
    if isinstance(t_closes, pd.DataFrame):
        full_df = t_closes.copy()
        if "close" not in full_df.columns:
            return go.Figure()
    else:
        full_df = pd.DataFrame({"close": t_closes}).dropna()

    if full_df.empty or len(full_df) < 12:
        return go.Figure()

    full_df = full_df.dropna(subset=["close"]).copy()
    if "volume" in full_df.columns and full_df["volume"].sum() > 0:
        pv = full_df["close"] * full_df["volume"]
        vwma20_s = pv.rolling(20, min_periods=5).sum() / full_df["volume"].rolling(20, min_periods=5).sum()
    else:
        vwma20_s = full_df["close"].rolling(20, min_periods=5).mean()

    ema20_s = full_df["close"].ewm(span=20, adjust=False).mean()
    full_df["equil"] = 0.55 * vwma20_s + 0.45 * ema20_s
    full_df["std20"] = full_df["close"].rolling(20, min_periods=5).std().bfill().fillna(full_df["close"] * 0.03)

    if "high" in full_df.columns and "low" in full_df.columns:
        prev_c = full_df["close"].shift(1)
        tr = pd.concat([
            (full_df["high"] - full_df["low"]).abs(),
            (full_df["high"] - prev_c).abs(),
            (full_df["low"] - prev_c).abs()
        ], axis=1).max(axis=1)
        atr_s = tr.ewm(alpha=1.0 / 14.0, adjust=False).mean().bfill()
    else:
        atr_val_fallback = float(metrics.get("atr14", full_df["std20"].iloc[-1]))
        atr_s = pd.Series(atr_val_fallback, index=full_df.index)

    unit_stretch = np.maximum(full_df["std20"], 1.35 * atr_s)
    full_df["upper_outer"] = full_df["equil"] + 2.00 * unit_stretch
    full_df["upper_inner"] = full_df["equil"] + 1.35 * unit_stretch
    full_df["lower_inner"] = np.maximum(0.5, full_df["equil"] - 1.35 * unit_stretch)
    full_df["lower_outer"] = np.maximum(0.5, full_df["equil"] - 2.00 * unit_stretch)

    # Slice the clean 35-day window AFTER all rolling bands are fully warmed up
    df = full_df.tail(35).copy()
    # Ensure live point matches exact metrics
    live_p = float(metrics.get("price", df["close"].iloc[-1]))
    df.iloc[-1, df.columns.get_loc("close")] = live_p

    fig = go.Figure()

    # 1. Upper Overbought Exhaustion Zone (+1.5σ to +2.35σ)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["upper_outer"],
        mode="lines",
        line=dict(color="rgba(244, 63, 94, 0.55)", width=1.2, dash="dot"),
        name="Overbought Exhaustion (+2.35σ)",
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["upper_inner"],
        mode="lines",
        line=dict(color="rgba(244, 63, 94, 0.25)", width=1.0, dash="dot"),
        fill="tonexty",
        fillcolor="rgba(244, 63, 94, 0.11)",
        name="Upper Stretch Zone (+1.5σ)",
        hoverinfo="skip",
        showlegend=False
    ))

    # 2. Inner Equilibrium Corridor (+1.5σ to -1.5σ)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["lower_inner"],
        mode="lines",
        line=dict(color="rgba(16, 185, 129, 0.25)", width=1.0, dash="dot"),
        fill="tonexty",
        fillcolor="rgba(255, 255, 255, 0.025)",
        name="Equilibrium Corridor",
        hoverinfo="skip",
        showlegend=False
    ))

    # 3. Lower Oversold Snapback Zone (-1.5σ to -2.35σ)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["lower_outer"],
        mode="lines",
        line=dict(color="rgba(16, 185, 129, 0.55)", width=1.2, dash="dot"),
        fill="tonexty",
        fillcolor="rgba(16, 185, 129, 0.12)",
        name="Oversold Snapback (-2.35σ)",
        hoverinfo="skip"
    ))

    # 4. Institutional VWMA-20 / EMA-20 Equilibrium Centerline
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["equil"],
        mode="lines",
        line=dict(color="#FB923C", width=2.4),
        name="VWMA-20 Institutional Equilibrium",
        hovertemplate="<b>VWMA-20 Equilibrium:</b> $%{y:.2f}<extra></extra>"
    ))

    # 5. Price Trajectory (Subtle Glow + Crisp Foreground Line)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["close"],
        mode="lines",
        line=dict(color="rgba(255, 107, 0, 0.20)", width=6.5),
        hoverinfo="skip",
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["close"],
        mode="lines+markers",
        line=dict(color="#E2E8F0", width=2.5),
        marker=dict(size=4.5, color="#E2E8F0", line=dict(color="#06070A", width=1)),
        name=f"{ticker} Close",
        hovertemplate=f"<b>{ticker} Close:</b> $%{{y:.2f}}<extra></extra>"
    ))

    # 6. 1-5 Day Forward Projection Cone
    strike = float(metrics.get("recommended_strike", live_p))
    target_p = float(metrics.get("target_price", df["equil"].iloc[-1]))
    invalidation = metrics.get("invalidation_price")
    action = str(metrics.get("action", "WAIT"))
    ou_hl = float(metrics.get("ou_half_life", 4.0))
    strike_color = "#10B981" if "CALL" in action else "#F43F5E" if "PUT" in action else "#FF6B00"
    cone_fill = "rgba(16, 185, 129, 0.14)" if "CALL" in action else "rgba(244, 63, 94, 0.14)" if "PUT" in action else "rgba(255, 107, 0, 0.12)"

    last_dt = pd.to_datetime(df.index[-1])
    future_dates = pd.bdate_range(start=last_dt, periods=6)  # Today + 5 business days
    steps = np.linspace(0.0, 1.0, len(future_dates))
    decay_rate = max(0.35, min(1.2, 3.0 / max(1.5, ou_hl)))
    norm_curve = (1.0 - np.exp(-decay_rate * steps * 2.2)) / (1.0 - np.exp(-decay_rate * 2.2))
    proj_target_path = live_p + (target_p - live_p) * norm_curve
    proj_strike_path = live_p + (strike - live_p) * (steps ** 0.85)

    fig.add_trace(go.Scatter(
        x=future_dates,
        y=proj_strike_path,
        mode="lines",
        line=dict(color=strike_color, width=1.6, dash="dot"),
        name=f"30–45D Strike Path (${strike:.2f})",
        hovertemplate="<b>Projected Strike Path:</b> $%{y:.2f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=future_dates,
        y=proj_target_path,
        mode="lines+markers",
        line=dict(color="#FF6B00", width=2.4, dash="dash"),
        marker=dict(size=[0, 4, 4, 4, 4, 8], color="#FF6B00", symbol="diamond"),
        fill="tonexty",
        fillcolor=cone_fill,
        name=f"1–5D O-U Snap Cone (${target_p:.2f})",
        hovertemplate="<b>1–5D Projected Target:</b> $%{y:.2f}<extra></extra>"
    ))

    # Glowing Live Spot Beacon on Today (t=0)
    fig.add_trace(go.Scatter(
        x=[last_dt],
        y=[live_p],
        mode="markers",
        marker=dict(
            size=11,
            color="#FF6B00",
            line=dict(color="#E2E8F0", width=2.2),
            symbol="circle"
        ),
        name="Live Spot",
        showlegend=False,
        hovertemplate=f"<b>LIVE SPOT ({ticker}):</b> ${live_p:.2f}<extra></extra>"
    ))

    # Reference Horizontal Lines
    fig.add_hline(
        y=strike,
        line_dash="dash",
        line_color=strike_color,
        line_width=1.8,
        annotation_text=f" 🎯 30–45D {action} Strike: ${strike:.2f} (Δ {metrics.get('estimated_delta', 0.50):+.2f}) ",
        annotation_position="top left",
        annotation_font=dict(color=strike_color, size=10.5, family="Plus Jakarta Sans"),
        annotation_bgcolor="rgba(10, 12, 18, 0.90)",
        annotation_bordercolor=strike_color,
        annotation_borderwidth=1,
        annotation_borderpad=3
    )

    if abs(target_p - strike) / max(1.0, strike) > 0.012:
        fig.add_hline(
            y=target_p,
            line_dash="dashdot",
            line_color="#FF6B00",
            line_width=1.5,
            annotation_text=f" 🧲 1–5D Target: ${target_p:.2f} ",
            annotation_position="bottom left",
            annotation_font=dict(color="#FB923C", size=10, family="Plus Jakarta Sans"),
            annotation_bgcolor="rgba(10, 12, 18, 0.88)",
            annotation_bordercolor="rgba(255, 107, 0, 0.50)",
            annotation_borderwidth=1,
            annotation_borderpad=2
        )

    if invalidation and action in ["BUY CALL", "BUY PUT"]:
        fig.add_hline(
            y=invalidation,
            line_dash="dot",
            line_color="rgba(244, 63, 94, 0.85)",
            line_width=1.5,
            annotation_text=f" 🛑 Hard Stop: ${invalidation:.2f} ",
            annotation_position="bottom right",
            annotation_font=dict(color="#F43F5E", size=10, family="Plus Jakarta Sans"),
            annotation_bgcolor="rgba(10, 12, 18, 0.88)",
            annotation_bordercolor="rgba(244, 63, 94, 0.45)",
            annotation_borderwidth=1,
            annotation_borderpad=2
        )

    # 7. Shared-Axis OPRA Call Wall & Put Wall Overlay
    gw = metrics.get("gamma_walls") or {}
    cw_k = float(gw.get("call_wall_strike", 0.0) or 0.0)
    cw_oi = int(gw.get("call_wall_oi", 0) or 0)
    pw_k = float(gw.get("put_wall_strike", 0.0) or 0.0)
    pw_oi = int(gw.get("put_wall_oi", 0) or 0)

    extra_wall_y = []
    if cw_k > 0 and cw_oi >= 50 and abs(cw_k - live_p) / max(1.0, live_p) <= 0.22 and abs(cw_k - strike) / max(1.0, strike) > 0.015:
        fig.add_hline(
            y=cw_k,
            line_dash="longdash",
            line_color="rgba(251, 146, 60, 0.65)",
            line_width=1.3,
            annotation_text=f" 🧱 OPRA Call Wall: ${cw_k:g} ({cw_oi:,} OI) ",
            annotation_position="top right",
            annotation_font=dict(color="#FB923C", size=9.5, family="Plus Jakarta Sans"),
            annotation_bgcolor="rgba(10, 12, 18, 0.88)",
            annotation_bordercolor="rgba(251, 146, 60, 0.40)",
            annotation_borderwidth=1,
            annotation_borderpad=2
        )
        extra_wall_y.append(cw_k)

    if pw_k > 0 and pw_oi >= 50 and abs(pw_k - live_p) / max(1.0, live_p) <= 0.22 and abs(pw_k - strike) / max(1.0, strike) > 0.015:
        fig.add_hline(
            y=pw_k,
            line_dash="longdash",
            line_color="rgba(167, 139, 250, 0.65)",
            line_width=1.3,
            annotation_text=f" 🛡️ OPRA Put Wall: ${pw_k:g} ({pw_oi:,} OI) ",
            annotation_position="bottom left",
            annotation_font=dict(color="#A78BFA", size=9.5, family="Plus Jakarta Sans"),
            annotation_bgcolor="rgba(10, 12, 18, 0.88)",
            annotation_bordercolor="rgba(167, 139, 250, 0.40)",
            annotation_borderwidth=1,
            annotation_borderpad=2
        )
        extra_wall_y.append(pw_k)

    all_y = list(df["upper_outer"].dropna()) + list(df["lower_outer"].dropna()) + list(df["close"].dropna()) + [strike, target_p] + extra_wall_y
    if invalidation:
        all_y.append(float(invalidation))
    y_min, y_max = min(all_y), max(all_y)
    y_pad = max(0.5, (y_max - y_min) * 0.12)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1", size=11),
        margin=dict(l=52, r=24, t=34, b=32),
        height=335,
        autosize=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            bgcolor="rgba(12, 15, 22, 0.72)",
            bordercolor="rgba(255, 255, 255, 0.08)",
            borderwidth=1,
            font=dict(size=10, color="#CBD5E1")
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            tickfont=dict(color="#94A3B8", size=10, family="JetBrains Mono"),
            range=[df.index[0] - pd.Timedelta(days=1), future_dates[-1] + pd.Timedelta(days=1)]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            tickprefix="$",
            tickfont=dict(color="#94A3B8", size=10.5, family="JetBrains Mono"),
            range=[max(0.0, y_min - y_pad), y_max + y_pad]
        ),
        hoverlabel=dict(
            bgcolor="rgba(10, 12, 18, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.48)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0")
        ),
        hovermode="x unified"
    )
    return fig


# =====================================================================
# AAA 6-PILLAR CROSS-ASSET MACRO IMPULSE CHART (TOP OF APP)
# Bonds, Credit Stress, Crude Oil, Gold, Silver, Bitcoin
# =====================================================================

def create_macro_6pillar_impulse_chart(radar_data: Dict[str, Any]) -> go.Figure:
    """
    Renders an AAA Horizontal Diverging Impulse & Z-Score Chart for the 6 Core Macro Pillars:
    1. Bonds (TLT / 10Y Duration)
    2. Credit Stress (HYG / LQD Ratio)
    3. Crude Oil (CLUSD / USO)
    4. Gold (GLD Safe-Haven)
    5. Silver (SLV Industrial/Electrification)
    6. Bitcoin (BTCUSD 24/7 Speculative Liquidity)
    """
    pillars = radar_data.get("pillars", [])
    if not pillars:
        return go.Figure()

    # Reverse order so Pillar 1 (Bonds) appears at top of horizontal chart
    p_rev = list(reversed(pillars))
    # Crisp, non-jumbled labels
    labels = [f"<b>{p['title']}</b><br><span style='font-size:10px;color:#94A3B8'>{p['ticker']}</span>" for p in p_rev]
    z_vals = [float(p.get("z_5d", 0.0)) for p in p_rev]
    chg_1d = [float(p.get("chg_1d", 0.0)) for p in p_rev]
    colors = [p.get("color", "#8AB4F8") for p in p_rev]
    text_labels = [f"{p['chg_1d']:+.1f}% ({p['z_5d']:+.1f}σ)" for p in p_rev]
    hover_texts = [
        f"<b>{p['title']}</b> ({p['ticker']}: {p['price_str']})<br>"
        f"1-Day Move: <b>{p['chg_1d']:+.2f}%</b> | 5-Day Move: <b>{p['chg_5d']:+.2f}%</b><br>"
        f"5-Day Impulse Z-Score: <b>{p['z_5d']:+.2f}σ</b> ({p['extra_metric']})<br>"
        f"Regime Status: <b>{p['status']}</b><br><br>"
        f"🎓 <b>How to Read This:</b><br>{p['lesson']}"
        for p in p_rev
    ]

    fig = go.Figure()

    # Shaded Reference Corridor (-1.0σ to +1.0σ normal range)
    fig.add_vrect(
        x0=-1.0, x1=1.0,
        fillcolor="rgba(148, 163, 184, 0.05)",
        line_width=1, line_dash="dot",
        line_color="rgba(255, 255, 255, 0.10)",
        layer="below"
    )

    fig.add_trace(go.Bar(
        y=labels,
        x=z_vals,
        orientation="h",
        marker=dict(
            color=colors,
            opacity=0.86,
            line=dict(color="rgba(255,255,255,0.22)", width=1)
        ),
        text=text_labels,
        textposition="outside",
        textfont=dict(family="JetBrains Mono, monospace", size=10.5, color="#F1F5F9"),
        hovertext=hover_texts,
        hoverinfo="text",
        cliponaxis=False
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1", size=11),
        height=380,
        autosize=True,
        showlegend=False,
        margin=dict(l=150, r=90, t=30, b=40),
        xaxis=dict(
            title=dict(text="<b>5-Day Cross-Asset Impulse (σ) • Hover Any Bar for Context</b>", font=dict(size=10.5, color="#94A3B8")),
            range=[-3.5, 3.5],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=True,
            zerolinecolor="rgba(255,255,255,0.24)",
            zerolinewidth=1.6,
            tickvals=[-3, -2, -1, 0, 1, 2, 3],
            ticktext=["-3σ", "-2σ", "-1σ", "0σ", "+1σ", "+2σ", "+3σ"],
            tickfont=dict(color="#94A3B8", size=10, family="JetBrains Mono")
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(color="#E2E8F0", size=11)
        ),
        hoverlabel=dict(
            bgcolor="rgba(10, 12, 18, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.48)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0"),
            align="left"
        )
    )
    return fig


# =====================================================================
# AAA INSTITUTIONAL SANKEY LIQUIDITY PATH ENGINE
# =====================================================================

_SK_FONT = "Plus Jakarta Sans, Inter, -apple-system, sans-serif"
_SK_UP = "#10B981"        # Crisp Emerald for Inflows
_SK_DOWN = "#F43F5E"      # Crisp Rose for Outflows
_SK_HUB = "#FF6B00"       # Hyper-Orange for Central Clearing Hub
_SK_DRAIN = "#64748B"     # Slate Gray for Neutral Cash / Reserve Sinks
_SK_TEXT = "#E2E8F0"
_SK_MUTED = "#94A3B8"


def _sk_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _sk_shares(weights: List[float], ky: float, min_px: float = 22.0) -> List[float]:
    if not weights:
        return []
    floor = min(min_px / ky, 100.0 / len(weights) * 0.9)
    spare = 100.0 - floor * len(weights)
    tot = sum(weights) or 1.0
    return [floor + spare * (w / tot) for w in weights]


def _sk_centers(shares: List[float], ky: float, pad: float, plot_h: float) -> List[float]:
    heights = [s * ky for s in shares]
    total = sum(heights) + pad * max(len(heights) - 1, 0)
    y = (plot_h - total) / 2.0
    centers = []
    for h in heights:
        centers.append(y + h / 2.0)
        y += h + pad
    return centers


def _render_flow_sankey(left: List[Dict[str, Any]], right: List[Dict[str, Any]], hub_title: str, height: int = 340) -> go.Figure:
    left = sorted(left, key=lambda d: d.get("weight", 1.0), reverse=True)
    right = sorted(right, key=lambda d: d.get("weight", 1.0), reverse=True)
    if not left or not right:
        return go.Figure()

    m_top, m_bot = 38, 10
    plot_h = height - m_top - m_bot
    pad = 11
    thick = 6
    n_max = max(len(left), len(right))
    ky = (plot_h - (n_max - 1) * pad) / 100.0
    min_px = 20.0

    l_sh = _sk_shares([d.get("weight", 1.0) for d in left], ky, min_px)
    r_sh = _sk_shares([d.get("weight", 1.0) for d in right], ky, min_px)
    l_cy = _sk_centers(l_sh, ky, pad, plot_h)
    r_cy = _sk_centers(r_sh, ky, pad, plot_h)
    hub_cy = plot_h / 2.0

    dom_x0, dom_x1 = 0.24, 0.76
    nx_l, nx_h, nx_r = 0.01, 0.50, 0.99

    n_l = len(left)
    hub_i = n_l
    node_x = [nx_l] * n_l + [nx_h] + [nx_r] * len(right)
    node_y = [c / plot_h for c in l_cy] + [hub_cy / plot_h] + [c / plot_h for c in r_cy]
    node_c = [
        (_SK_DOWN if not d.get("is_neutral") else _SK_DRAIN) for d in left
    ] + [_SK_HUB] + [
        (_SK_UP if d.get("is_gain") else _SK_DRAIN) for d in right
    ]

    def _hover_node(d, flow_type):
        if d.get("is_neutral"):
            return f"<b>{d['ticker']}</b> &bull; {d['name']}<br><span style='color:{_SK_MUTED}'>Neutral Reserve Absorption</span>"
        sign = "+" if d.get("pct", 0) >= 0 else "−"
        return (f"<b>{d['ticker']}</b> &bull; {d['name']}<br>"
                f"<span style='color:{_SK_MUTED}'>Session Return:</span> {sign}{abs(d['pct']):.2f}% ({flow_type})<br>"
                f"<span style='color:{_SK_MUTED}'>Flow Intensity:</span> {d.get('weight', 1.0):.1f}")

    node_cd = ([_hover_node(d, "Outflow") for d in left]
               + [f"<b>{hub_title}</b><br><span style='color:{_SK_MUTED}'>Net Institutional Clearing & Settlement Hub</span>"]
               + [_hover_node(d, "Inflow") for d in right])

    src, tgt, val, lcol, lhov, lcd = [], [], [], [], [], []
    for i, (d, s) in enumerate(zip(left, l_sh)):
        src.append(i); tgt.append(hub_i); val.append(s)
        base_c = _SK_DRAIN if d.get("is_neutral") else _SK_DOWN
        lcol.append(_sk_rgba(base_c, 0.20))
        lhov.append(_sk_rgba(base_c, 0.50))
        lcd.append(f"<b>{d['ticker']}</b> &rarr; <b>{hub_title}</b><br>"
                   f"<span style='color:{_SK_MUTED}'>Outflow Share:</span> {s:.1f}%")

    for j, (d, s) in enumerate(zip(right, r_sh)):
        src.append(hub_i); tgt.append(hub_i + 1 + j); val.append(s)
        base_c = _SK_UP if d.get("is_gain") else _SK_DRAIN
        lcol.append(_sk_rgba(base_c, 0.22))
        lhov.append(_sk_rgba(base_c, 0.55))
        lcd.append(f"<b>{hub_title}</b> &rarr; <b>{d['ticker']}</b><br>"
                   f"<span style='color:{_SK_MUTED}'>Inflow Share:</span> {s:.1f}%")

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        domain=dict(x=[dom_x0, dom_x1], y=[0, 1]),
        node=dict(
            pad=pad, thickness=thick,
            x=node_x, y=node_y,
            label=[""] * len(node_x),
            color=node_c,
            line=dict(width=0),
            customdata=node_cd,
            hovertemplate="%{customdata}<extra></extra>",
        ),
        link=dict(
            source=src, target=tgt, value=val,
            color=lcol, hovercolor=lhov,
            customdata=lcd,
            hovertemplate="%{customdata}<extra></extra>",
        ),
        hoverlabel=dict(
            bgcolor="#12151B", bordercolor="rgba(255,255,255,0.12)",
            font=dict(family=_SK_FONT, size=12, color=_SK_TEXT), align="left",
        ),
    ))

    def _x_paper(nx):
        return dom_x0 + nx * (dom_x1 - dom_x0)

    def _format_label(d):
        if d.get("is_neutral"):
            return (f"<span style='font-weight:700;color:{_SK_MUTED};'>{d['ticker']}</span>  "
                    f"<span style='color:{_SK_DRAIN};font-size:10px;'>RESERVE</span><br>"
                    f"<span style='font-size:8.5px;letter-spacing:0.04em;color:{_SK_DRAIN};'>{d['name'].upper()}</span>")
        color = _SK_UP if d.get("is_gain") else _SK_DOWN
        sign = "+" if d.get("pct", 0) >= 0 else "−"
        return (f"<span style='font-weight:700;color:{_SK_TEXT};'>{d['ticker']}</span>  "
                f"<span style='font-weight:600;color:{color};'>{sign}{abs(d['pct']):.2f}%</span><br>"
                f"<span style='font-size:8.5px;letter-spacing:0.04em;color:{_SK_MUTED};'>{d['name'].upper()}</span>")

    ann = []
    for d, cy in zip(left, l_cy):
        ann.append(dict(x=_x_paper(nx_l), y=1 - cy / plot_h, xref="paper", yref="paper",
                        xanchor="right", yanchor="middle", xshift=-(thick / 2 + 10),
                        align="right", showarrow=False, text=_format_label(d),
                        font=dict(family=_SK_FONT, size=10.5, color=_SK_TEXT)))
    for d, cy in zip(right, r_cy):
        ann.append(dict(x=_x_paper(nx_r), y=1 - cy / plot_h, xref="paper", yref="paper",
                        xanchor="left", yanchor="middle", xshift=(thick / 2 + 10),
                        align="left", showarrow=False, text=_format_label(d),
                        font=dict(family=_SK_FONT, size=10.5, color=_SK_TEXT)))

    eyebrow = dict(family=_SK_FONT, size=9, color=_SK_MUTED)
    ann += [
        dict(x=_x_paper(nx_l), y=1, xref="paper", yref="paper", xanchor="right", yanchor="bottom",
             xshift=-(thick / 2 + 10), yshift=10, showarrow=False, font=eyebrow,
             text=f"<span style='color:{_SK_DOWN}'>●</span>  CAPITAL OUTFLOW"),
        dict(x=0.50, y=1, xref="paper", yref="paper", xanchor="center", yanchor="bottom",
             yshift=10, showarrow=False, font=eyebrow,
             text="  ".join(hub_title.upper())),
        dict(x=_x_paper(nx_r), y=1, xref="paper", yref="paper", xanchor="left", yanchor="bottom",
             xshift=(thick / 2 + 10), yshift=10, showarrow=False, font=eyebrow,
             text=f"CAPITAL INFLOW  <span style='color:{_SK_UP}'>●</span>"),
    ]

    fig.update_layout(
        annotations=ann,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_SK_FONT, color=_SK_TEXT, size=11),
        margin=dict(l=4, r=4, t=m_top, b=m_bot),
        height=height, autosize=True,
    )
    return fig


def _split_flows_truthful(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    left = []
    right = []

    for d in items:
        pct = float(d.get("pct", 0.0) or 0.0)
        flow_w = float(d.get("flow_weight", abs(pct) * 1.5 + 0.8))
        d["weight"] = max(flow_w, 0.8)
        net_sign = d.get("net_flow_sign")
        is_outflow = (float(net_sign) < 0) if net_sign is not None else (pct < 0)
        if is_outflow:
            d["is_gain"] = False
            left.append(d)
        else:
            d["is_gain"] = True
            right.append(d)

    if not right:
        right = [{
            "ticker": "CASH",
            "name": "Reserve Absorption",
            "pct": 0.0,
            "weight": max(sum(d.get("weight", 1.0) for d in left) * 0.4, 2.0),
            "is_neutral": True,
            "is_gain": False
        }]

    if not left:
        left = [{
            "ticker": "LIQUIDITY",
            "name": "Margin Expansion",
            "pct": 0.0,
            "weight": max(sum(d.get("weight", 1.0) for d in right) * 0.4, 2.0),
            "is_neutral": True,
            "is_gain": False
        }]

    return left, right


_SECTOR_DISPLAY_MAP = {
    "Semiconductors": ("SMH", "Semiconductors"),
    "AI Infrastructure": ("SRVR", "AI Infrastructure"),
    "Energy, Grid & Materials": ("URA", "Energy & Grid"),
    "Robotics & Autonomous": ("ROBO", "Robotics & Auto"),
    "Edge AI & Next-Gen Compute": ("QTUM", "Edge AI & Compute"),
    "Robotics & Automation": ("BOTZ", "Robotics & Physical AI"),
    "Nuclear & Next-Gen Energy": ("URA", "Nuclear & Grid Energy"),
    "Energy & Material Science": ("URA", "Nuclear & Grid Energy"),
}


def create_sector_flow_sankey(macro_pulse: Dict[str, Any]) -> go.Figure:
    """Tactical Sector Rotation Sankey (Semis, AI Infra, Robotics, Nuclear Energy)."""
    sectors = macro_pulse.get("sectors", {})
    if not sectors:
        return go.Figure()

    items = []
    for s_name, s_data in sectors.items():
        bench, clean_name = _SECTOR_DISPLAY_MAP.get(
            s_name, (s_data.get("benchmark", "SEC"), s_name.split(" ")[0])
        )
        chg = float(s_data.get("change_pct", 0.0) or 0.0)
        flow_vol = float(s_data.get("flow_volume", abs(chg) * 1.5 + 0.8))
        items.append({
            "ticker": bench,
            "name": clean_name,
            "pct": chg,
            "flow_weight": flow_vol,
            "net_flow_sign": s_data.get("net_flow_sign")
        })

    left, right = _split_flows_truthful(items)
    return _render_flow_sankey(left, right, "Tactical Sector Pool", height=340)


_MACRO_DISPLAY_MAP = {
    "TLT": ("20Y+ Bonds", "Bonds"),
    "HYG": ("High-Yield Credit", "Credit"),
    "CLUSD": ("WTI Crude Oil", "Commodities"),
    "USO": ("Crude Oil Fund", "Commodities"),
    "GLD": ("Gold Safe-Haven", "Precious"),
    "SLV": ("Silver Industrial", "Metals"),
    "BTCUSD": ("Bitcoin 24/7", "Liquidity"),
    "UUP": ("USD Liquidity Index", "FX Funding"),
    "SPY": ("S&P 500", "Equities"),
    "SMH": ("Semiconductors", "Tech"),
    "BOTZ": ("AI & Robotics", "Robotics"),
    "URA": ("Nuclear Energy", "Nuclear"),
}


def create_overall_market_sankey(macro_data: Dict[str, Any]) -> go.Figure:
    """
    Global Cross-Asset Macro Liquidity Path Sankey.
    Bonds (TLT), Credit (HYG), Crude Oil (CLUSD/USO), Gold (GLD), Silver (SLV),
    Bitcoin (BTCUSD), Euro/Dollar (EURUSD), S&P 500 (SPY), SMH, BOTZ, URA.
    """
    assets = macro_data.get("assets", {})
    if not assets:
        return go.Figure()

    items = []
    for _, v in assets.items():
        sym = v.get("symbol", "")
        clean_name, _ = _MACRO_DISPLAY_MAP.get(sym, (v.get("category", sym), sym))
        chg = float(v.get("change_pct", v.get("changePercentage", 0.0)) or 0.0)
        items.append({
            "ticker": sym,
            "name": clean_name,
            "pct": chg,
            "flow_weight": abs(chg) * 1.6 + 0.8
        })

    left, right = _split_flows_truthful(items)
    return _render_flow_sankey(left, right, "Macro Clearing Hub", height=340)


def create_cross_asset_rotation_compass(
    compass_data: Dict[str, Any],
    active_benchmark: str = "SMH",
    height: int = 540
) -> go.Figure:
    """
    AAA Flagship Cross-Asset Relative Rotation & RVOL-Conditioned Risk-Appetite Compass:
    - Entire Card Width: Expanded canvas with generous breathing room
    - Full Zoom & Pan Controls: Enabled box zoom, pan, reset zoom, and hover tools
    - Minimal Clean Aesthetics: Clean orbs with subtle glow, uncluttered text pills
    - Collision Avoidance: Deterministic staggered pill layout
    """
    import math

    fig = go.Figure()
    nodes = (compass_data or {}).get("nodes", [])
    if not nodes:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(12, 15, 22, 0.42)",
            height=height,
            margin=dict(l=44, r=24, t=24, b=42),
            annotations=[dict(
                text="Synchronizing cross-asset telemetry...",
                showarrow=False,
                font=dict(color="#94A3B8", size=13, family="Plus Jakarta Sans, sans-serif")
            )]
        )
        return fig

    x_lim = 3.30
    y_lim = 3.10

    # 1. Disciplined Quadrant Glass Tints (Soft background atmosphere)
    quad_shapes = [
        # Top-Left: Rubberband Snapback Ignition (Hyper-Orange)
        dict(type="rect", x0=-x_lim, x1=0, y0=0, y1=y_lim, fillcolor="rgba(255, 107, 0, 0.042)", line_width=0, layer="below"),
        # Top-Right: Institutional Inflow Leaders (Emerald)
        dict(type="rect", x0=0, x1=x_lim, y0=0, y1=y_lim, fillcolor="rgba(16, 185, 129, 0.035)", line_width=0, layer="below"),
        # Bottom-Left: Liquidation Flush / Risk-Off (Rose)
        dict(type="rect", x0=-x_lim, x1=0, y0=-y_lim, y1=0, fillcolor="rgba(244, 63, 94, 0.032)", line_width=0, layer="below"),
        # Bottom-Right: Crowded Exhaustion / Distribution (Warm Amber)
        dict(type="rect", x0=0, x1=x_lim, y0=-y_lim, y1=0, fillcolor="rgba(251, 146, 60, 0.028)", line_width=0, layer="below"),
    ]
    for qs in quad_shapes:
        fig.add_shape(**qs)

    # 2. Concentric Polar Equilibrium Rings (1.0σ Equilibrium & 2.0σ Stretch Perimeter)
    angles = np.linspace(0.0, 2.0 * math.pi, 96)
    for rad, ring_col, ring_dash in [
        (1.0, "rgba(148, 163, 184, 0.14)", "dot"),
        (2.0, "rgba(148, 163, 184, 0.09)", "dash"),
    ]:
        fig.add_trace(go.Scatter(
            x=rad * np.cos(angles),
            y=rad * np.sin(angles),
            mode="lines",
            line=dict(color=ring_col, width=1.0, dash=ring_dash),
            hoverinfo="skip",
            showlegend=False,
        ))

    # Subtle ring callouts on 45-degree NE/SW axis
    for rad_lbl, r_val in [("1.0σ EQUIL", 1.0), ("2.0σ STRETCH", 2.0)]:
        fig.add_annotation(
            x=-r_val * 0.707,
            y=-r_val * 0.707,
            text=f"<span style='font-size:8.5px;color:rgba(148,163,184,0.40);font-family:JetBrains Mono,monospace;'>{rad_lbl}</span>",
            showarrow=False,
        )

    # Crosshair Zero Axes
    fig.add_hline(y=0, line_color="rgba(226, 232, 240, 0.14)", line_width=1.1)
    fig.add_vline(x=0, line_color="rgba(226, 232, 240, 0.14)", line_width=1.1)

    # 3. Corner Micro-Watermarks positioned safely outside the cluster
    corner_watermarks = [
        dict(
            x=-3.18, y=2.95, xanchor="left", yanchor="top", align="left",
            text="<span style='color:#FF8533;font-weight:800;font-size:10px;letter-spacing:0.06em;'>⚡ SNAPBACK IGNITION</span><br><span style='color:#64748B;font-size:8.5px;'>Oversold + Positive RVOL Hook</span>"
        ),
        dict(
            x=3.18, y=2.45, xanchor="right", yanchor="top", align="right",
            text="<span style='color:#10B981;font-weight:800;font-size:10px;letter-spacing:0.06em;'>🚀 INFLOW LEADERS</span><br><span style='color:#64748B;font-size:8.5px;'>Trend Expansion + Institutional Bid</span>"
        ),
        dict(
            x=-3.18, y=-2.95, xanchor="left", yanchor="bottom", align="left",
            text="<span style='color:#F43F5E;font-weight:800;font-size:10px;letter-spacing:0.06em;'>🩸 LIQUIDATION FLUSH</span><br><span style='color:#64748B;font-size:8.5px;'>Risk-Off Drain · Await Bottom Hook</span>"
        ),
        dict(
            x=3.18, y=-2.95, xanchor="right", yanchor="bottom", align="right",
            text="<span style='color:#FB923C;font-weight:800;font-size:10px;letter-spacing:0.06em;'>⚠️ CROWDED EXHAUSTION</span><br><span style='color:#64748B;font-size:8.5px;'>Upper Band + Fading Thrust</span>"
        ),
    ]
    for wm in corner_watermarks:
        fig.add_annotation(showarrow=False, **wm)

    quad_palette = {
        "INFLOW_LEADER": {
            "core": "#10B981",
            "halo": "rgba(16, 185, 129, 0.20)",
            "tail": "rgba(16, 185, 129, 0.45)",
            "txt": "#34D399",
            "bdr": "rgba(16, 185, 129, 0.35)",
        },
        "SNAPBACK_IGNITION": {
            "core": "#FF6B00",
            "halo": "rgba(255, 107, 0, 0.22)",
            "tail": "rgba(251, 146, 60, 0.48)",
            "txt": "#FF8533",
            "bdr": "rgba(255, 107, 0, 0.38)",
        },
        "CROWDED_EXHAUSTION": {
            "core": "#FB923C",
            "halo": "rgba(251, 146, 60, 0.18)",
            "tail": "rgba(251, 146, 60, 0.42)",
            "txt": "#FDBA74",
            "bdr": "rgba(251, 146, 60, 0.32)",
        },
        "LIQUIDATION_FLUSH": {
            "core": "#F43F5E",
            "halo": "rgba(244, 63, 94, 0.20)",
            "tail": "rgba(244, 63, 94, 0.45)",
            "txt": "#FB7185",
            "bdr": "rgba(244, 63, 94, 0.32)",
        },
    }

    # 4. Clean Vector Arrows for 3-Day Rotation (Only 1 sleek trajectory vector per node)
    for n in nodes:
        x3, y3 = float(n["x_3d"]), float(n["y_3d"])
        xn, yn = float(n["x_now"]), float(n["y_now"])
        pal = quad_palette.get(n["quadrant"], quad_palette["INFLOW_LEADER"])
        disp = math.hypot(xn - x3, yn - y3)
        if disp >= 0.14:
            fig.add_trace(go.Scatter(
                x=[x3, xn],
                y=[y3, yn],
                mode="lines",
                line=dict(
                    color=pal["tail"],
                    width=2.0 if n["tier"] == "POWER_SECTOR" else 1.3,
                    dash="dot"
                ),
                hoverinfo="skip",
                showlegend=False,
            ))

    # 5. Build 3-Layer Glowing Orbs
    halo_x, halo_y, halo_s, halo_c, halo_sym = [], [], [], [], []
    core_x, core_y, core_s, core_c, core_lc, core_lw, core_sym, hover_texts = [], [], [], [], [], [], [], []
    pip_x, pip_y, pip_s, pip_c = [], [], [], []

    # Pixel approximation for full-width canvas (~1150px wide x 480px plot area)
    px_w, px_h = 1150.0, 480.0
    def _to_px(xv: float, yv: float) -> Tuple[float, float]:
        return ((xv + x_lim) / (2.0 * x_lim)) * px_w, ((y_lim - yv) / (2.0 * y_lim)) * px_h

    orb_px_list: List[Tuple[float, float, float]] = []
    label_boxes: List[Dict[str, Any]] = []

    for idx, n in enumerate(nodes):
        sym = n["symbol"]
        short_sym = n["short"]
        tier = n["tier"]
        pal = quad_palette.get(n["quadrant"], quad_palette["INFLOW_LEADER"])
        is_active_bench = (sym == active_benchmark)

        rvol = float(n["rvol"])
        chg_1d = float(n["chg_1d"])
        chg_5d = float(n["chg_5d"])
        clv = float(n["clv"])
        dvol = float(n["dollar_vol_b"])
        xn, yn = float(n["x_now"]), float(n["y_now"])

        if tier == "POWER_SECTOR":
            base_sz = 22.0 if is_active_bench else float(np.clip(16.5 + rvol * 2.5, 17.0, 21.0))
            marker_shape = "circle"
            tier_badge = "TACTICAL POWER SECTOR"
        elif tier == "EQUITY_INDEX":
            base_sz = float(np.clip(13.5 + rvol * 2.0, 14.0, 17.5))
            marker_shape = "diamond"
            tier_badge = "BROAD EQUITY INDEX"
        else:
            base_sz = float(np.clip(11.5 + rvol * 1.5, 11.5, 15.0))
            marker_shape = "circle"
            tier_badge = "GLOBAL MACRO PLUMBING"

        if is_active_bench:
            # Active sector desk beacon (Hyper-Orange)
            fig.add_trace(go.Scatter(
                x=[xn], y=[yn],
                mode="markers",
                marker=dict(
                    size=[base_sz * 2.3],
                    color=["rgba(255, 107, 0, 0.14)"],
                    line=dict(color="rgba(255, 107, 0, 0.78)", width=1.6),
                ),
                hoverinfo="skip",
                showlegend=False,
            ))
            h_col = "rgba(255, 107, 0, 0.30)"
            l_col = "#FF6B00"
            l_wid = 2.4
            pip_col = "#FF8533"
        elif tier == "POWER_SECTOR":
            h_col = pal["halo"]
            l_col = "#F8FAFC"
            l_wid = 1.8
            pip_col = "#FFFFFF"
        elif tier == "EQUITY_INDEX":
            h_col = pal["halo"]
            l_col = "rgba(248, 250, 252, 0.75)"
            l_wid = 1.3
            pip_col = "#E2E8F0"
        else:
            h_col = pal["halo"].replace("0.20", "0.12").replace("0.22", "0.12").replace("0.18", "0.10")
            l_col = "rgba(203, 213, 225, 0.42)"
            l_wid = 1.0
            pip_col = "rgba(255, 255, 255, 0.75)"

        halo_x.append(xn)
        halo_y.append(yn)
        halo_s.append(base_sz * 1.7)
        halo_c.append(h_col)
        halo_sym.append(marker_shape)

        core_x.append(xn)
        core_y.append(yn)
        core_s.append(base_sz)
        core_c.append(pal["core"])
        core_lc.append(l_col)
        core_lw.append(l_wid)
        core_sym.append(marker_shape)

        pip_x.append(xn)
        pip_y.append(yn)
        pip_s.append(4.2 if is_active_bench else (3.6 if tier == "POWER_SECTOR" else 3.0))
        pip_c.append(pip_col)

        price_fmt = f"${n['price']:,.0f}" if sym == "BTCUSD" else f"${n['price']:,.2f}"
        ht = (
            f"<b>{short_sym}</b> &bull; {n['name']} <span style='color:#94A3B8;'>({tier_badge})</span><br>"
            f"────────────────────────────────────────<br>"
            f"<b>Regime Quadrant:</b> <b>{n['quad_label']}</b><br>"
            f"<b>Live Price:</b> {price_fmt} (<b>1D: {chg_1d:+.2f}%</b> | 5D: {chg_5d:+.2f}%)<br>"
            f"<b>20D Trend Stretch (X):</b> {xn:+.2f}σ (3D Shift: {n['delta_x_3d']:+.2f}σ)<br>"
            f"<b>Kinetic Thrust (Y):</b> {yn:+.2f}σ (3D Shift: {n['delta_y_3d']:+.2f}σ)<br>"
            f"<b>RVOL Conviction:</b> {rvol:.2f}x | <b>Intraday CLV:</b> {clv:+.2f} | <b>Turnover:</b> ${dvol:.2f}B<br>"
            f"<b>Options Desk Read:</b> {n['desk_implication']}"
        )
        hover_texts.append(ht)

        ox, oy = _to_px(xn, yn)
        orb_px_list.append((ox, oy, base_sz * 0.55))

        # Initial clean staggered angles to spread out tags
        angle_offsets = [0.0, 1.0, 2.1, 3.2, 4.3, 5.4, 0.7, 1.8, 2.9, 4.0, 5.1, 0.4, 1.5, 2.6, 3.7]
        ang = angle_offsets[idx % len(angle_offsets)]
        init_dx = math.cos(ang) * 32.0
        init_dy = math.sin(ang) * 24.0

        if is_active_bench:
            lbl_text = f"<b>★ {short_sym}</b> {chg_1d:+.1f}%"
            box_w, box_h = 76.0, 19.0
        else:
            lbl_text = f"<b>{short_sym}</b> {chg_1d:+.1f}%"
            box_w, box_h = 66.0, 18.0

        label_boxes.append({
            "xn": xn,
            "yn": yn,
            "ox": ox,
            "oy": oy,
            "lx": ox + init_dx,
            "ly": oy + init_dy,
            "w": box_w,
            "h": box_h,
            "text": lbl_text,
            "tier": tier,
            "is_active": is_active_bench,
            "pal": pal,
        })

    # Generous 2D repulsion solver across the wide canvas
    for _ in range(40):
        for i, lb in enumerate(label_boxes):
            fx, fy = 0.0, 0.0
            for j, other in enumerate(label_boxes):
                if i == j:
                    continue
                dx = lb["lx"] - other["lx"]
                dy = lb["ly"] - other["ly"]
                overlap_x = (lb["w"] + other["w"]) * 0.58 - abs(dx)
                overlap_y = (lb["h"] + other["h"]) * 0.65 - abs(dy)
                if overlap_x > 0 and overlap_y > 0:
                    if overlap_x < overlap_y:
                        fx += (overlap_x * 0.45) * (1.0 if dx >= 0 else -1.0)
                    else:
                        fy += (overlap_y * 0.45) * (1.0 if dy >= 0 else -1.0)
            for ox, oy, orad in orb_px_list:
                dx = lb["lx"] - ox
                dy = lb["ly"] - oy
                overlap_x = (lb["w"] * 0.5 + orad + 3.0) - abs(dx)
                overlap_y = (lb["h"] * 0.5 + orad + 3.0) - abs(dy)
                if overlap_x > 0 and overlap_y > 0:
                    fx += (overlap_x * 0.35) * (1.0 if dx >= 0 else -1.0)
                    fy += (overlap_y * 0.45) * (1.0 if dy >= 0 else -1.0)
            # Gentle tether back to source orb
            tether_dx = lb["lx"] - lb["ox"]
            tether_dy = lb["ly"] - lb["oy"]
            tether_dist = math.hypot(tether_dx, tether_dy)
            if tether_dist > 52.0:
                pull = (tether_dist - 52.0) * 0.25
                fx -= (tether_dx / tether_dist) * pull
                fy -= (tether_dy / tether_dist) * pull

            lb["lx"] = float(np.clip(lb["lx"] + fx, 50.0, px_w - 50.0))
            lb["ly"] = float(np.clip(lb["ly"] + fy, 28.0, px_h - 28.0))

    # Trace 1: Halos
    fig.add_trace(go.Scatter(
        x=halo_x, y=halo_y,
        mode="markers",
        marker=dict(size=halo_s, color=halo_c, symbol=halo_sym, line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Trace 2: Core Orbs
    fig.add_trace(go.Scatter(
        x=core_x, y=core_y,
        mode="markers",
        marker=dict(
            size=core_s,
            color=core_c,
            symbol=core_sym,
            line=dict(color=core_lc, width=core_lw),
            opacity=0.96,
        ),
        hoverinfo="text",
        hovertext=hover_texts,
        name="Cross-Asset Nodes",
    ))

    # Trace 3: Specular Pips
    fig.add_trace(go.Scatter(
        x=pip_x, y=pip_y,
        mode="markers",
        marker=dict(size=pip_s, color=pip_c, opacity=0.90),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Trace 4: Pill Labels
    for lb in label_boxes:
        ax_off = float(np.clip(lb["lx"] - lb["ox"], -65.0, 65.0))
        ay_off = float(np.clip(lb["ly"] - lb["oy"], -55.0, 55.0))
        pal = lb["pal"]
        is_act = lb["is_active"]
        tier = lb["tier"]
        dist_px = math.hypot(ax_off, ay_off)

        if is_act:
            bg_c = "rgba(28, 16, 10, 0.94)"
            bd_c = "rgba(255, 107, 0, 0.78)"
            tx_c = "#FF8533"
            f_sz = 9.8
            b_w = 1.2
        elif tier == "POWER_SECTOR":
            bg_c = "rgba(12, 15, 22, 0.90)"
            bd_c = pal["bdr"]
            tx_c = "#E2E8F0"
            f_sz = 9.4
            b_w = 1.0
        elif tier == "EQUITY_INDEX":
            bg_c = "rgba(12, 15, 22, 0.82)"
            bd_c = "rgba(255, 255, 255, 0.12)"
            tx_c = pal["txt"]
            f_sz = 9.0
            b_w = 1.0
        else:
            bg_c = "rgba(10, 13, 20, 0.74)"
            bd_c = "rgba(255, 255, 255, 0.08)"
            tx_c = "#CBD5E1"
            f_sz = 8.6
            b_w = 1.0

        fig.add_annotation(
            x=lb["xn"],
            y=lb["yn"],
            ax=ax_off,
            ay=ay_off,
            axref="pixel",
            ayref="pixel",
            text=lb["text"],
            showarrow=(dist_px >= 18.0),
            arrowhead=0,
            arrowwidth=1.0,
            arrowcolor="rgba(255, 107, 0, 0.55)" if is_act else "rgba(148, 163, 184, 0.25)",
            font=dict(family="JetBrains Mono, monospace", size=f_sz, color=tx_c),
            bgcolor=bg_c,
            bordercolor=bd_c,
            borderwidth=b_w,
            borderpad=2.5,
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1"),
        height=height,
        autosize=True,
        showlegend=False,
        dragmode="pan",
        margin=dict(l=48, r=24, t=44, b=42),
        xaxis=dict(
            title=dict(
                text="20-Day Institutional Trend Stretch (Z-Score vs. VWMA-20 / ATR-14)",
                font=dict(size=11, color="#94A3B8", family="Plus Jakarta Sans, sans-serif"),
                standoff=8,
            ),
            range=[-x_lim, x_lim],
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            tickvals=[-3, -2, -1, 0, 1, 2, 3],
            ticktext=["-3σ", "-2σ", "-1σ", "Equil", "+1σ", "+2σ", "+3σ"],
            tickfont=dict(family="JetBrains Mono, monospace", size=9.5, color="#64748B"),
        ),
        yaxis=dict(
            title=dict(
                text="RVOL & CLV Kinetic Velocity Thrust",
                font=dict(size=11, color="#94A3B8", family="Plus Jakarta Sans, sans-serif"),
                standoff=6,
            ),
            range=[-y_lim, y_lim],
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            tickvals=[-2, -1, 0, 1, 2],
            ticktext=["-2σ", "-1σ", "0", "+1σ", "+2σ"],
            tickfont=dict(family="JetBrains Mono, monospace", size=9.5, color="#64748B"),
        ),
        hoverlabel=dict(
            bgcolor="rgba(10, 12, 18, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.48)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=11.5, color="#E2E8F0"),
        ),
    )
    return fig



# =====================================================================
# AAA DOT GRAPH #1 (TAB 1): 30-45 DTE CALLS & PUTS STRIKE CONVEXITY MATRIX
# Placed directly below the 35-Day VWMA-20 & ATR Elasticity Channel
# =====================================================================

def _norm_cdf_chart(x: float) -> float:
    import math
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_option_eval(S: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> Tuple[float, float]:
    import math
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        intrinsic = max(0.01, S - K) if is_call else max(0.01, K - S)
        return intrinsic, (0.5 if is_call else -0.5)
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if is_call:
        price = S * _norm_cdf_chart(d1) - K * math.exp(-r * T) * _norm_cdf_chart(d2)
        delta = _norm_cdf_chart(d1)
    else:
        price = K * math.exp(-r * T) * _norm_cdf_chart(-d2) - S * _norm_cdf_chart(-d1)
        delta = _norm_cdf_chart(d1) - 1.0
    return max(0.05, price), delta


def _snap_strike(raw_p: float) -> float:
    if raw_p < 25:
        step = 0.5
    elif raw_p < 100:
        step = 1.0
    elif raw_p < 250:
        step = 2.5
    elif raw_p < 500:
        step = 5.0
    else:
        step = 10.0
    return round(round(raw_p / step) * step, 2)


def create_ticker_options_strike_dot_matrix(
    ticker: str,
    metrics: Dict[str, Any],
    fundamentals: Optional[Dict[str, Any]] = None,
    dte: int = 35,
    hold_days: int = 5,
    iv_shift_pct: float = 0.0,
    chain_df: Optional[pd.DataFrame] = None,
    skew_optimizer: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """
    Renders the Flagship AAA Calls vs. Puts Strike Convexity & Payoff Dot Graph
    for the active ticker:
    - Uses live OPRA exchange bids, asks, mids, and per-strike IVs when `chain_df` is supplied
      (falling back to Gatheral SVI or HV-calibrated skew only when offline).
    - Reprices each strike at the target move via American CRR + Spot-Vol skew beta, deducting
      round-trip OPRA spread slippage, WITHOUT artificial ROI floors or directional bias multipliers.
    - Negative expected ROI strikes render truthfully below the 0% breakeven line.
    """
    import quant_kernel

    spot = max(1.0, float(metrics.get("price", 100.0)))
    vwma20 = float(metrics.get("vwma20", metrics.get("sma20", spot)))
    target_p = float(metrics.get("target_price", vwma20))
    rec_strike = float(metrics.get("recommended_strike", spot * 1.05))
    call_rec = float(metrics.get("call_strike", rec_strike))
    put_rec = float(metrics.get("put_strike", spot * 0.95))
    action = str(metrics.get("action", "BUY CALL"))
    atr14 = float(metrics.get("atr14", spot * 0.035))
    vol_pct = max(16.0, float(metrics.get("realized_vol", 42.0)))
    vol_rank = float(metrics.get("vol_rank", 50.0))
    ou_hl = max(1.5, float(metrics.get("ou_half_life", 4.2)))

    sigma_base = vol_pct / 100.0
    dte_val = max(7, int(dte or 35))
    hold_d = max(1, min(dte_val - 2, int(hold_days or 5)))
    iv_shock_mult = max(0.55, 1.0 + (float(iv_shift_pct or 0.0) / 100.0))
    T_entry = dte_val / 365.0
    T_exit = max(1.0, float(dte_val - hold_d)) / 365.0
    r = 0.0425

    # Pace expected upside/downside move by Ornstein-Uhlenbeck Half-Life decay over hold_d
    ou_pace = (1.0 - (2.0 ** (-hold_d / ou_hl))) / max(0.18, (1.0 - (2.0 ** (-5.0 / ou_hl))))
    ou_pace = float(np.clip(ou_pace, 0.35, 1.38))
    base_up_5d = max(spot + max(1.85 * atr14, spot * 0.048), target_p if "CALL" in action else max(vwma20, spot + 1.55 * atr14))
    base_dn_5d = min(spot - max(1.85 * atr14, spot * 0.048), target_p if "PUT" in action else min(vwma20, spot - 1.55 * atr14))
    upside_swing_p = spot + (base_up_5d - spot) * ou_pace
    downside_swing_p = max(0.50, spot - (spot - base_dn_5d) * ou_pace)
    up_mv_frac = (upside_swing_p - spot) / spot
    dn_mv_frac = (downside_swing_p - spot) / spot

    svi_p = skew_optimizer.get("svi_params") if isinstance(skew_optimizer, dict) else None

    def _svi_iv_for_k(k_strike: float, fallback_sig: float) -> float:
        if isinstance(svi_p, dict) and all(x in svi_p for x in ("a", "b", "rho", "m", "sigma")):
            k_log = math.log(max(1e-2, k_strike) / spot)
            u = k_log - float(svi_p["m"])
            w = float(svi_p["a"]) + float(svi_p["b"]) * (float(svi_p["rho"]) * u + math.sqrt(u * u + float(svi_p["sigma"]) ** 2))
            if w > 1e-5:
                return max(0.08, min(2.50, math.sqrt(w / T_entry)))
        return fallback_sig

    def _pick_uniform(rows_list: List[Dict[str, Any]], anchor_k: float, limit: int = 6) -> List[Dict[str, Any]]:
        if len(rows_list) <= limit:
            return rows_list
        idxs = np.linspace(0, len(rows_list) - 1, limit, dtype=int).tolist()
        picked = [rows_list[i] for i in dict.fromkeys(idxs)]
        # Ensure recommended strike is present
        best_r = min(rows_list, key=lambda x: abs(x["strike"] - anchor_k))
        if all(abs(x["strike"] - best_r["strike"]) > 0.01 for x in picked):
            rep_i = int(np.argmin([abs(x["strike"] - best_r["strike"]) for x in picked]))
            picked[rep_i] = best_r
        return sorted(picked, key=lambda x: x["strike"])

    put_nodes = []
    call_nodes = []
    has_live_chain = (chain_df is not None and not chain_df.empty and "strike" in chain_df.columns and "side" in chain_df.columns)

    if has_live_chain:
        df_c = chain_df.copy()
        df_c["strike_f"] = pd.to_numeric(df_c["strike"], errors="coerce")
        df_c["bid_f"] = pd.to_numeric(df_c.get("bid", 0.0), errors="coerce").fillna(0.0)
        df_c["ask_f"] = pd.to_numeric(df_c.get("ask", 0.0), errors="coerce").fillna(0.0)
        df_c["mid_f"] = pd.to_numeric(df_c.get("mid", 0.0), errors="coerce").fillna((df_c["bid_f"] + df_c["ask_f"]) / 2.0)
        df_c["iv_f"] = pd.to_numeric(df_c.get("impliedVolatility", 0.0), errors="coerce").fillna(0.0)
        df_c["dte_f"] = pd.to_numeric(df_c.get("dte", dte_val), errors="coerce").fillna(dte_val)
        c_dte_med = int(max(7, df_c["dte_f"].median()))
        T_entry = c_dte_med / 365.0
        T_exit = max(1.0, float(c_dte_med - hold_d)) / 365.0
        dte_val = c_dte_med

        p_rows = df_c[(df_c["side"].str.lower() == "put") & (df_c["strike_f"].between(spot * 0.85, spot * 1.005)) & (df_c["mid_f"] >= 0.08)].sort_values("strike_f")
        c_rows = df_c[(df_c["side"].str.lower() == "call") & (df_c["strike_f"].between(spot * 0.995, spot * 1.15)) & (df_c["mid_f"] >= 0.08)].sort_values("strike_f")

        p_recs = []
        for _, row in p_rows.iterrows():
            iv_v = float(row["iv_f"])
            if iv_v > 3.5:
                iv_v /= 100.0
            iv_v = max(0.08, min(2.80, iv_v)) if iv_v > 0.03 else _svi_iv_for_k(float(row["strike_f"]), sigma_base)
            p_recs.append({
                "strike": float(row["strike_f"]),
                "bid": float(row["bid_f"]),
                "ask": float(row["ask_f"]),
                "mid": float(row["mid_f"]),
                "iv": iv_v,
                "delta": float(row["delta"]) if pd.notna(row.get("delta")) else None,
            })

        c_recs = []
        for _, row in c_rows.iterrows():
            iv_v = float(row["iv_f"])
            if iv_v > 3.5:
                iv_v /= 100.0
            iv_v = max(0.08, min(2.80, iv_v)) if iv_v > 0.03 else _svi_iv_for_k(float(row["strike_f"]), sigma_base)
            c_recs.append({
                "strike": float(row["strike_f"]),
                "bid": float(row["bid_f"]),
                "ask": float(row["ask_f"]),
                "mid": float(row["mid_f"]),
                "iv": iv_v,
                "delta": float(row["delta"]) if pd.notna(row.get("delta")) else None,
            })

        p_sel = _pick_uniform(p_recs, rec_strike if "PUT" in action else put_rec, limit=6)
        c_sel = _pick_uniform(c_recs, rec_strike if "CALL" in action else call_rec, limit=6)
    else:
        p_sel = []
        c_sel = []

    if not p_sel:
        raw_puts = [_snap_strike(spot * (1.0 + off)) for off in (-0.105, -0.080, -0.055, -0.035, -0.015)]
        if put_rec < spot and put_rec not in raw_puts:
            raw_puts[int(np.argmin([abs(k - put_rec) for k in raw_puts]))] = put_rec
        for k in sorted(list(dict.fromkeys([x for x in raw_puts if x < spot * 0.998]))):
            otm_pct = ((k - spot) / spot) * 100.0
            sig = _svi_iv_for_k(k, sigma_base * (1.0 + abs(otm_pct) * 0.0045))
            g0 = quant_kernel.american_crr_price_and_greeks(spot, k, T_entry, r, sig, is_call=False)
            p_sel.append({"strike": k, "bid": g0["price"] * 0.96, "ask": g0["price"] * 1.04, "mid": g0["price"], "iv": sig, "delta": g0["delta"]})

    if not c_sel:
        raw_calls = [_snap_strike(spot * (1.0 + off)) for off in (0.015, 0.035, 0.055, 0.080, 0.105)]
        if call_rec > spot and call_rec not in raw_calls:
            raw_calls[int(np.argmin([abs(k - call_rec) for k in raw_calls]))] = call_rec
        for k in sorted(list(dict.fromkeys([x for x in raw_calls if x > spot * 1.002]))):
            otm_pct = ((k - spot) / spot) * 100.0
            sig = _svi_iv_for_k(k, sigma_base * (1.0 - otm_pct * 0.002))
            g0 = quant_kernel.american_crr_price_and_greeks(spot, k, T_entry, r, sig, is_call=True)
            c_sel.append({"strike": k, "bid": g0["price"] * 0.96, "ask": g0["price"] * 1.04, "mid": g0["price"], "iv": sig, "delta": g0["delta"]})

    for idx, item in enumerate(p_sel):
        k = item["strike"]
        otm_pct = ((k - spot) / spot) * 100.0
        sig_in = item["iv"]
        # Spot-Vol negative leverage: selloff boosts IV slightly + user shock
        sig_out = max(0.08, min(2.50, sig_in * (1.0 - 0.35 * dn_mv_frac) * iv_shock_mult))
        g_in = quant_kernel.american_crr_price_and_greeks(spot, k, T_entry, r, sig_in, is_call=False)
        g_out = quant_kernel.american_crr_price_and_greeks(downside_swing_p, k, T_exit, r, sig_out, is_call=False)
        prem_mid = max(0.05, float(item["mid"] or g_in["price"]))
        spr = max(0.01, float(item["ask"] - item["bid"])) if item["ask"] >= item["bid"] else prem_mid * 0.06
        entry_fill = prem_mid + 0.25 * spr
        prem_scale = (prem_mid / max(0.03, g_in["price"])) if g_in["price"] > 0.05 else 1.0
        prem_scale = float(np.clip(prem_scale, 0.70, 1.45))
        prem_target = max(0.01, g_out["price"] * prem_scale)
        exit_fill = max(0.01, prem_target - 0.25 * spr)
        roi_honest = ((exit_fill - entry_fill) / max(0.05, entry_fill)) * 100.0
        delta_val = float(item["delta"]) if item["delta"] is not None else float(g_in["delta"])
        contracts_1k = max(1, int(round(1000.0 / (entry_fill * 100.0))))
        profit_1k = round(contracts_1k * (exit_fill - entry_fill) * 100.0, 0)
        is_rec = ("PUT" in action and abs(k - rec_strike) < 0.05) or (not ("CALL" in action) and abs(k - put_rec) < 0.05)
        put_nodes.append({
            "side": "PUT",
            "strike": k,
            "otm_pct": otm_pct,
            "delta": delta_val,
            "iv_pct": round(sig_in * 100.0, 1),
            "prem": round(entry_fill, 2),
            "prem_target": round(exit_fill, 2),
            "roi_pct": round(float(np.clip(roi_honest, -95.0, 350.0)), 1),
            "contracts": contracts_1k,
            "profit_1k": profit_1k,
            "is_rec": is_rec,
            "idx": idx,
            "is_live": has_live_chain,
        })

    for idx, item in enumerate(c_sel):
        k = item["strike"]
        otm_pct = ((k - spot) / spot) * 100.0
        sig_in = item["iv"]
        sig_out = max(0.08, min(2.50, sig_in * (1.0 - 0.35 * up_mv_frac) * iv_shock_mult))
        g_in = quant_kernel.american_crr_price_and_greeks(spot, k, T_entry, r, sig_in, is_call=True)
        g_out = quant_kernel.american_crr_price_and_greeks(upside_swing_p, k, T_exit, r, sig_out, is_call=True)
        prem_mid = max(0.05, float(item["mid"] or g_in["price"]))
        spr = max(0.01, float(item["ask"] - item["bid"])) if item["ask"] >= item["bid"] else prem_mid * 0.06
        entry_fill = prem_mid + 0.25 * spr
        prem_scale = (prem_mid / max(0.03, g_in["price"])) if g_in["price"] > 0.05 else 1.0
        prem_scale = float(np.clip(prem_scale, 0.70, 1.45))
        prem_target = max(0.01, g_out["price"] * prem_scale)
        exit_fill = max(0.01, prem_target - 0.25 * spr)
        roi_honest = ((exit_fill - entry_fill) / max(0.05, entry_fill)) * 100.0
        delta_val = float(item["delta"]) if item["delta"] is not None else float(g_in["delta"])
        contracts_1k = max(1, int(round(1000.0 / (entry_fill * 100.0))))
        profit_1k = round(contracts_1k * (exit_fill - entry_fill) * 100.0, 0)
        is_rec = ("CALL" in action and abs(k - rec_strike) < 0.05)
        call_nodes.append({
            "side": "CALL",
            "strike": k,
            "otm_pct": otm_pct,
            "delta": delta_val,
            "iv_pct": round(sig_in * 100.0, 1),
            "prem": round(entry_fill, 2),
            "prem_target": round(exit_fill, 2),
            "roi_pct": round(float(np.clip(roi_honest, -95.0, 350.0)), 1),
            "contracts": contracts_1k,
            "profit_1k": profit_1k,
            "is_rec": is_rec,
            "idx": idx,
            "is_live": has_live_chain,
        })

    fig = go.Figure()

    all_strikes = [n["strike"] for n in put_nodes + call_nodes] + [spot, vwma20, target_p]
    x_min = min(all_strikes) * 0.975
    x_max = max(all_strikes) * 1.025
    all_rois = [n["roi_pct"] for n in put_nodes + call_nodes] or [50.0]
    y_max = max(30.0, max(all_rois) * 1.28)
    y_min = min(-15.0, min(all_rois) * 1.22)

    # Zero Breakeven Reference Line
    fig.add_hline(
        y=0.0,
        line_width=1.4,
        line_dash="dot",
        line_color="rgba(226, 232, 240, 0.35)",
        annotation_text=" 0% BREAKEVEN ",
        annotation_position="bottom left",
        annotation_font=dict(size=9, color="#94A3B8", family="JetBrains Mono"),
    )

    # 1. Subtle Left (Put) & Right (Call) Background Gradient Corridors
    fig.add_vrect(
        x0=x_min, x1=spot,
        fillcolor="rgba(244, 63, 94, 0.045)",
        line_width=0, layer="below"
    )
    fig.add_vrect(
        x0=spot, x1=x_max,
        fillcolor="rgba(16, 185, 129, 0.045)",
        line_width=0, layer="below"
    )

    # Subtle Corner Watermarks (Non-colliding)
    fig.add_annotation(
        x=0.015, y=0.95, xref="paper", yref="paper",
        text=f"<span style='color:#F43F5E;font-weight:800;font-size:10.5px;letter-spacing:0.06em;'>🔴 {dte_val} DTE PUT STRIKE LADDER (DOWNSIDE CONVEXITY)</span>",
        showarrow=False, xanchor="left", yanchor="top"
    )
    fig.add_annotation(
        x=0.985, y=0.95, xref="paper", yref="paper",
        text=f"<span style='color:#10B981;font-weight:800;font-size:10.5px;letter-spacing:0.06em;'>🟢 {dte_val} DTE CALL STRIKE LADDER (UPSIDE CONVEXITY)</span>",
        showarrow=False, xanchor="right", yanchor="top"
    )

    # 2. Vertical Reference Lines: Spot Price, VWMA-20 Equilibrium, and 1-5D Target
    fig.add_vline(
        x=spot,
        line_width=2.0,
        line_dash="solid",
        line_color="rgba(226, 232, 240, 0.45)",
        annotation_text=f" ⚡ LIVE SPOT: ${spot:.2f} ",
        annotation_position="top",
        annotation_font=dict(size=10, color="#E2E8F0", family="JetBrains Mono"),
        annotation_bgcolor="rgba(10, 12, 18, 0.90)",
        annotation_bordercolor="rgba(226, 232, 240, 0.30)",
        annotation_borderwidth=1,
        annotation_borderpad=3
    )

    if abs(vwma20 - spot) / spot > 0.008:
        fig.add_vline(
            x=vwma20,
            line_width=1.4,
            line_dash="dot",
            line_color="rgba(251, 146, 60, 0.60)",
            annotation_text=f" VWMA-20: ${vwma20:.2f} ",
            annotation_position="bottom",
            annotation_font=dict(size=9.5, color="#FB923C", family="JetBrains Mono"),
            annotation_bgcolor="rgba(10, 12, 18, 0.88)"
        )

    if abs(target_p - spot) / spot > 0.012:
        t_col = "#10B981" if target_p > spot else "#F43F5E"
        fig.add_vline(
            x=target_p,
            line_width=1.6,
            line_dash="dash",
            line_color=t_col,
            annotation_text=f" 🧲 1–5D TARGET: ${target_p:.2f} ",
            annotation_position="bottom",
            annotation_font=dict(size=9.5, color=t_col, family="JetBrains Mono"),
            annotation_bgcolor="rgba(10, 12, 18, 0.90)",
            annotation_bordercolor=t_col,
            annotation_borderwidth=1,
            annotation_borderpad=2
        )

    # 3. Smooth Convexity Spline Curves for Puts & Calls
    if put_nodes:
        px = [n["strike"] for n in put_nodes]
        py = [n["roi_pct"] for n in put_nodes]
        fig.add_trace(go.Scatter(
            x=px, y=py,
            mode="lines",
            line=dict(color="rgba(244, 63, 94, 0.52)", width=2.4, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor="rgba(244, 63, 94, 0.07)",
            hoverinfo="skip",
            showlegend=False
        ))

    if call_nodes:
        cx = [n["strike"] for n in call_nodes]
        cy = [n["roi_pct"] for n in call_nodes]
        fig.add_trace(go.Scatter(
            x=cx, y=cy,
            mode="lines",
            line=dict(color="rgba(16, 185, 129, 0.52)", width=2.4, shape="spline", smoothing=1.0),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.07)",
            hoverinfo="skip",
            showlegend=False
        ))

    # 4. Render 3-Layer Glowing Orbs for PUTS and CALLS
    all_nodes = put_nodes + call_nodes
    halo_x, halo_y, halo_s, halo_c = [], [], [], []
    core_x, core_y, core_s, core_c, core_lc, core_lw, core_ht = [], [], [], [], [], [], []
    pip_x, pip_y, pip_c = [], [], []
    label_annotations = []

    for n in all_nodes:
        is_call = (n["side"] == "CALL")
        is_rec = n["is_rec"]
        base_size = 24 if is_rec else int(16 + abs(n["delta"]) * 16)

        if is_rec:
            aura_col = "rgba(255, 107, 0, 0.30)"
            orb_col = "#10B981" if is_call else "#F43F5E"
            ring_col = "#FF6B00"
            ring_w = 3.2
        elif is_call:
            aura_col = "rgba(16, 185, 129, 0.18)" if "CALL" in action else "rgba(251, 146, 60, 0.12)"
            orb_col = "#10B981" if "CALL" in action else "#34D399"
            ring_col = "rgba(226, 232, 240, 0.50)"
            ring_w = 1.5
        else:
            aura_col = "rgba(244, 63, 94, 0.18)"
            orb_col = "#F43F5E" if "PUT" in action else "#FB7185"
            ring_col = "rgba(226, 232, 240, 0.45)"
            ring_w = 1.5

        halo_x.append(n["strike"])
        halo_y.append(n["roi_pct"])
        halo_s.append(base_size * 1.95 if is_rec else base_size * 1.65)
        halo_c.append(aura_col)

        core_x.append(n["strike"])
        core_y.append(n["roi_pct"])
        core_s.append(base_size)
        core_c.append(orb_col)
        core_lc.append(ring_col)
        core_lw.append(ring_w)

        pip_x.append(n["strike"])
        pip_y.append(n["roi_pct"])
        pip_c.append("#FF8533" if is_rec else "#E2E8F0")

        swing_ref = upside_swing_p if is_call else downside_swing_p
        rec_tag = " 🎯 <b>[PRIMARY RECOMMENDED STRIKE]</b>" if is_rec else ""
        ht = (
            f"<b>{ticker} ${n['strike']:.2f} {n['side']}</b> ({n['otm_pct']:+.1f}% from Spot · {'OPRA LIVE' if n.get('is_live') else 'MODEL'}){rec_tag}<br>"
            f"───────────────────────────────────────<br>"
            f"<b>Option Delta (Δ):</b> {n['delta']:+.2f} | <b>Strike IV:</b> {n.get('iv_pct', 0.0):.1f}% | <b>{dte_val}-DTE Fill Est:</b> ${n['prem']:.2f}/sh<br>"
            f"<b>1–5D Swing Target Underlying:</b> ${swing_ref:.2f} (O-U Half-Life: {ou_hl:.1f}d)<br>"
            f"<b>Projected Exit Option Value:</b> ${n['prem_target']:.2f}/sh<br>"
            f"<b>Honest Net ROI (After Slippage):</b> <b>{n['roi_pct']:+.1f}%</b><br>"
            f"<b>$1,000 Sim Allocation:</b> {n['contracts']}x {n['side']}s &rarr; <b>${n['profit_1k']:+,.0f} Est. 5D P&L</b>"
        )
        core_ht.append(ht)

        y_shift = 20 if (n["idx"] % 2 == 0 or is_rec) else -22
        pill_col = "#FF8533" if is_rec else ("#94A3B8" if n["roi_pct"] < 0 else ("#10B981" if is_call else "#F43F5E"))
        star_prefix = "🎯 " if is_rec else ""
        label_annotations.append(dict(
            x=n["strike"],
            y=n["roi_pct"],
            yshift=y_shift,
            text=(
                f"<b>{star_prefix}${n['strike']:.2f} {'C' if is_call else 'P'}</b><br>"
                f"<span style='font-size:9px;color:#94A3B8'>Δ {n['delta']:+.2f} · {'+' if n['profit_1k'] >= 0 else ''}${n['profit_1k']:,.0f}</span>"
            ),
            showarrow=False,
            align="center",
            font=dict(family="JetBrains Mono, monospace", size=10, color=pill_col),
            bgcolor="rgba(10, 12, 18, 0.90)" if is_rec else "rgba(10, 12, 18, 0.74)",
            bordercolor="rgba(255, 107, 0, 0.65)" if is_rec else "rgba(255, 255, 255, 0.10)",
            borderwidth=1,
            borderpad=3
        ))

    # Layer 1: Outer Diffused Glow Halo
    fig.add_trace(go.Scatter(
        x=halo_x, y=halo_y,
        mode="markers",
        marker=dict(size=halo_s, color=halo_c, line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False
    ))

    # Layer 2: Crisp Core Option Orbs
    fig.add_trace(go.Scatter(
        x=core_x, y=core_y,
        mode="markers",
        marker=dict(
            size=core_s,
            color=core_c,
            line=dict(color=core_lc, width=core_lw),
            opacity=0.95
        ),
        hoverinfo="text",
        hovertext=core_ht,
        name="30–45 DTE Strikes"
    ))

    # Layer 3: Specular Center Pip
    fig.add_trace(go.Scatter(
        x=pip_x, y=pip_y,
        mode="markers",
        marker=dict(size=5, color=pip_c, opacity=0.90),
        hoverinfo="skip",
        showlegend=False
    ))

    for ann in label_annotations:
        fig.add_annotation(**ann)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1"),
        height=355,
        autosize=True,
        showlegend=False,
        dragmode="pan",
        margin=dict(l=54, r=28, t=32, b=42),
        xaxis=dict(
            title=dict(
                text=f"<b>{ticker} {dte_val} DTE Option Strike Ladder ($) • Left = Put Strikes | Right = Call Strikes</b>",
                font=dict(size=11, color="#94A3B8")
            ),
            range=[x_min, x_max],
            fixedrange=False,
            tickprefix="$",
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            tickfont=dict(color="#CBD5E1", size=10.5, family="JetBrains Mono")
        ),
        yaxis=dict(
            title=dict(
                text="<b>1–5D Convexity ROI Potential (%)</b>",
                font=dict(size=11, color="#94A3B8")
            ),
            range=[y_min, y_max],
            fixedrange=False,
            ticksuffix="%",
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=True,
            zerolinecolor="rgba(255, 255, 255, 0.14)",
            tickfont=dict(color="#94A3B8", size=10, family="JetBrains Mono")
        ),
        hoverlabel=dict(
            bgcolor="rgba(10, 12, 18, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.55)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0"),
            align="left"
        )
    )
    return fig


def create_iv_smile_and_term_structure_chart(
    cand_data: Dict[str, Any],
    chain_df: Optional[pd.DataFrame] = None,
) -> go.Figure:
    """
    2-Panel Institutional Volatility Surface Visual:
      - Left: Live OPRA Market Bid/Mid IV Smile vs. Calibrated Gatheral SVI Arbitrage-Free Curve
              with Cheapest Convexity Strike Highlighted.
      - Right: Multi-Expiry ATM IV Term Structure + Implied Straddle Move (%) vs. 20D Realized HV.
    """
    sym = str(cand_data.get("symbol", "")).upper()
    m = cand_data.get("metrics", {}) or {}
    spot = max(1.0, float(m.get("price", 100.0)))
    hv20_pct = float(m.get("realized_vol", 35.0) or 35.0)
    skew_opt = cand_data.get("skew_optimizer") or m.get("skew_optimizer") or {}
    ts = cand_data.get("term_structure") or m.get("term_structure") or {}
    svi_p = skew_opt.get("svi_params") if isinstance(skew_opt, dict) else {}
    hist_er_mv = float(m.get("hist_er_avg_move_pct", 0.0) or 0.0)

    fig = make_subplots(
        rows=1,
        cols=2,
        horizontal_spacing=0.10,
        subplot_titles=(
            f"{sym} OPRA Volatility Smile vs. Gatheral SVI Fit",
            f"{sym} Multi-Expiry IV Term Structure & Implied Move",
        ),
    )

    # --- LEFT PANEL: VOLATILITY SMILE & SVI ---
    plotted_smile = False
    t_smile = 35.0 / 365.0
    if chain_df is not None and not chain_df.empty and "strike" in chain_df.columns:
        df_s = chain_df.copy()
        df_s["strike_f"] = pd.to_numeric(df_s["strike"], errors="coerce")
        df_s["iv_f"] = pd.to_numeric(df_s.get("impliedVolatility", 0.0), errors="coerce")
        df_s["dte_f"] = pd.to_numeric(df_s.get("dte", 35), errors="coerce").fillna(35)
        t_smile = max(7.0, float(df_s["dte_f"].median())) / 365.0
        df_s = df_s[df_s["strike_f"].between(spot * 0.78, spot * 1.24) & df_s["iv_f"].between(0.04, 3.0)]
        puts_s = df_s[(df_s["side"].str.lower() == "put") & (df_s["strike_f"] <= spot * 1.01)].sort_values("strike_f")
        calls_s = df_s[(df_s["side"].str.lower() == "call") & (df_s["strike_f"] >= spot * 0.99)].sort_values("strike_f")

        if not puts_s.empty:
            plotted_smile = True
            fig.add_trace(go.Scatter(
                x=puts_s["strike_f"],
                y=puts_s["iv_f"] * 100.0,
                mode="markers",
                name="OPRA OTM Puts",
                marker=dict(size=8, color="#F43F5E", line=dict(width=1, color="#0B0E14")),
                hovertemplate="Put $%{x:.1f}<br>OPRA IV: <b>%{y:.1f}%</b><extra></extra>",
            ), row=1, col=1)
        if not calls_s.empty:
            plotted_smile = True
            fig.add_trace(go.Scatter(
                x=calls_s["strike_f"],
                y=calls_s["iv_f"] * 100.0,
                mode="markers",
                name="OPRA OTM Calls",
                marker=dict(size=8, color="#10B981", line=dict(width=1, color="#0B0E14")),
                hovertemplate="Call $%{x:.1f}<br>OPRA IV: <b>%{y:.1f}%</b><extra></extra>",
            ), row=1, col=1)

    if isinstance(svi_p, dict) and all(k in svi_p for k in ("a", "b", "rho", "m", "sigma")):
        plotted_smile = True
        k_grid_strikes = np.linspace(spot * 0.80, spot * 1.22, 48)
        fwd_px = spot * math.exp(0.0425 * t_smile)
        log_k = np.log(k_grid_strikes / fwd_px)
        u_arr = log_k - float(svi_p["m"])
        w_curve = np.maximum(
            1e-5,
            float(svi_p["a"]) + float(svi_p["b"]) * (float(svi_p["rho"]) * u_arr + np.sqrt(u_arr ** 2 + float(svi_p["sigma"]) ** 2)),
        )
        iv_curve_pct = np.sqrt(w_curve / t_smile) * 100.0
        fig.add_trace(go.Scatter(
            x=k_grid_strikes,
            y=iv_curve_pct,
            mode="lines",
            name="Gatheral SVI Curve",
            line=dict(color="#FF6B00", width=2.4),
            hovertemplate="SVI Fair IV ($%{x:.1f}): <b>%{y:.1f}%</b><extra></extra>",
        ), row=1, col=1)

        cheap_k = float(skew_opt.get("cheapest_call_strike" if "CALL" in str(m.get("action", "")).upper() else "cheapest_put_strike", 0.0) or skew_opt.get("cheapest_strike", 0.0) or 0.0)
        if spot * 0.80 <= cheap_k <= spot * 1.22:
            ck_log = math.log(cheap_k / fwd_px)
            cu = ck_log - float(svi_p["m"])
            cw = max(1e-5, float(svi_p["a"]) + float(svi_p["b"]) * (float(svi_p["rho"]) * cu + math.sqrt(cu ** 2 + float(svi_p["sigma"]) ** 2)))
            cheap_svi_iv = math.sqrt(cw / t_smile) * 100.0
            fig.add_trace(go.Scatter(
                x=[cheap_k],
                y=[cheap_svi_iv],
                mode="markers",
                name=f"Cheapest SVI (${cheap_k:.1f})",
                marker=dict(size=12, symbol="star", color="#38BDF8", line=dict(width=1.5, color="#FFFFFF")),
                hovertemplate=f"Cheapest Strike vs SVI: <b>${cheap_k:.1f}</b><extra></extra>",
            ), row=1, col=1)

    if plotted_smile:
        fig.add_vline(x=spot, line_width=1.3, line_dash="dot", line_color="rgba(226,232,240,0.45)", row=1, col=1)
        fig.add_hline(y=hv20_pct, line_width=1.2, line_dash="dash", line_color="rgba(56,189,248,0.55)", row=1, col=1)
    else:
        fig.add_annotation(
            x=0.5, y=0.5, xref="x domain", yref="y domain",
            text="OPRA Smile offline — using HV20 baseline",
            showarrow=False, font=dict(size=11, color="#94A3B8"), row=1, col=1,
        )

    # --- RIGHT PANEL: MULTI-EXPIRY TERM STRUCTURE & IMPLIED MOVES ---
    term_pts = ts.get("term_points", []) if isinstance(ts, dict) else []
    if term_pts:
        x_labels = [f"{p['label']}<br>({p['dte']}D)" for p in term_pts]
        y_ivs = [float(p["atm_iv_pct"]) for p in term_pts]
        y_moves = [float(p["implied_move_pct"]) for p in term_pts]
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=y_ivs,
            mode="lines+markers+text",
            name="Term ATM IV (%)",
            line=dict(color="#A78BFA", width=2.8),
            marker=dict(size=10, color="#FF6B00", line=dict(width=1.5, color="#0B0E14")),
            text=[f"<b>{v:.1f}%</b><br><span style='color:#94A3B8;font-size:9px'>±{mv:.1f}% mv</span>" for v, mv in zip(y_ivs, y_moves)],
            textposition="top center",
            textfont=dict(size=10, color="#E2E8F0", family="JetBrains Mono"),
            hovertemplate="%{x}<br>ATM IV: <b>%{y:.1f}%</b><extra></extra>",
        ), row=1, col=2)
        fig.add_hline(
            y=hv20_pct,
            line_width=1.4,
            line_dash="dash",
            line_color="#38BDF8",
            annotation_text=f"20D HV: {hv20_pct:.1f}%",
            annotation_position="bottom right",
            annotation_font=dict(size=9.5, color="#38BDF8", family="JetBrains Mono"),
            row=1, col=2,
        )
    else:
        ot = cand_data.get("options_telemetry") or {}
        iv_cur = float(ot.get("iv_pct", hv20_pct) or hv20_pct)
        fig.add_trace(go.Bar(
            x=["20D Realized HV", "35D Model IV"],
            y=[hv20_pct, iv_cur],
            marker_color=["#38BDF8", "#FF6B00"],
            showlegend=False,
        ), row=1, col=2)

    if hist_er_mv > 0:
        er_note = f"8Q Avg ER Move: ±{hist_er_mv:.1f}% vs 35D Straddle ±{float(ts.get('core_implied_move_pct', 0.0) or 0.0):.1f}%"
        fig.add_annotation(
            x=0.5, y=0.04, xref="x2 domain", yref="y2 domain",
            text=er_note, showarrow=False,
            font=dict(size=9.5, color="#FBBF24", family="JetBrains Mono"),
            bgcolor="rgba(10,12,18,0.75)", borderpad=3,
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1"),
        height=295,
        margin=dict(l=48, r=24, t=42, b=36),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5,
            font=dict(size=9.5, color="#94A3B8"),
        ),
        hoverlabel=dict(
            bgcolor="rgba(10, 12, 18, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.55)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=11.5, color="#E2E8F0"),
        ),
    )
    fig.update_annotations(font=dict(size=11.5, color="#E2E8F0", family="Plus Jakarta Sans"))
    fig.update_xaxes(tickprefix="$", showgrid=True, gridcolor="rgba(255,255,255,0.05)", row=1, col=1)
    fig.update_xaxes(showgrid=False, row=1, col=2)
    fig.update_yaxes(ticksuffix="%", showgrid=True, gridcolor="rgba(255,255,255,0.05)", row=1, col=1)
    fig.update_yaxes(ticksuffix="%", showgrid=True, gridcolor="rgba(255,255,255,0.05)", row=1, col=2)
    return fig


# =====================================================================
# AAA DOT GRAPH #2 (TAB 2): HORIZONTAL RUBBERBAND TENSION & BIFURCATION MATRIX
# Redesigned with 3-Layer Glowing Orbs, Staggered External Pill Labels,
# Calls vs. Puts Color Coding, and Zero Boxy Clutter
# =====================================================================

def create_rubberband_tension_matrix(candidates: List[Dict[str, Any]], active_ticker: Optional[str] = None) -> go.Figure:
    """
    Renders the Flagship AAA Horizontal Rubberband Tension & Quality Bifurcation Dot Matrix:
    - X-Axis: Dual-Coordinate Effective Stretch Z-Score (-3.5σ to +3.5σ)
    - Y-Axis: FMP Pro Fundamental & Solvency Quality Score (0 to 100)
    - 3-Layer Glowing Orbs (Outer Aura + Core Orb + Specular Highlight)
    - Color-Coded directly by Option Playbook:
        * Emerald (#10B981 / #34D399): Oversold / Pullback CALL Snapback
        * Electric Cyan (#38BDF8): Coiled Spring / Catalyst Breakout CALL
        * Neon Rose/Coral (#F43F5E / #FB7185): Overbought / Mirage PUT Breakdown
        * Slate (#64748B): Equilibrium Watchlist
    - External staggered pill labels above/below dots so ticker symbols never bleed or collide
    """
    fig = go.Figure()

    if not candidates:
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(12, 15, 22, 0.42)",
            xaxis=dict(range=[-3.5, 3.5], showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(range=[0, 100], showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
            height=470,
            margin=dict(l=45, r=40, t=35, b=45),
            annotations=[dict(text="No candidates scanned yet. Select a sector or ingest tickers.", showarrow=False, font=dict(color="#94A3B8", size=14))]
        )
        return fig

    # 1. Refined Subtle Background Zones
    fig.add_vrect(
        x0=-3.6, x1=-1.15,
        fillcolor="rgba(16, 185, 129, 0.05)",
        layer="below", line_width=1, line_dash="dot",
        line_color="rgba(16, 185, 129, 0.25)"
    )
    fig.add_vrect(
        x0=-1.15, x1=1.15,
        fillcolor="rgba(255, 107, 0, 0.02)",
        layer="below", line_width=0
    )
    fig.add_vrect(
        x0=1.15, x1=3.6,
        fillcolor="rgba(244, 63, 94, 0.05)",
        layer="below", line_width=1, line_dash="dot",
        line_color="rgba(244, 63, 94, 0.25)"
    )

    # Horizontal Solvency Bifurcation Line (Y = 50)
    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color="rgba(255, 255, 255, 0.14)",
        line_width=1.2
    )

    # Clean edge micro-watermarks
    edge_watermarks = [
        dict(x=-2.45, y=102.5, text="<span style='color:#10B981;font-weight:800;font-size:10px;letter-spacing:0.05em;'>💎 PRIME OVERSOLD CALLS (FORTRESS + PULLBACK)</span>"),
        dict(x=0.0, y=102.5, text="<span style='color:#FB923C;font-weight:800;font-size:10px;letter-spacing:0.05em;'>⚡ COILED SPRING & EQUILIBRIUM CORRIDOR</span>"),
        dict(x=2.45, y=102.5, text="<span style='color:#F43F5E;font-weight:800;font-size:10px;letter-spacing:0.05em;'>🔴 OVERBOUGHT EXHAUSTION PUTS (UPPER BAND)</span>"),
        dict(x=-2.45, y=2.5, text="<span style='color:#64748B;font-weight:700;font-size:9.5px;letter-spacing:0.05em;'>🚫 SOLVENCY QUARANTINE / VALUE TRAPS</span>"),
        dict(x=2.45, y=2.5, text="<span style='color:#F43F5E;font-weight:800;font-size:9.5px;letter-spacing:0.05em;'>🎯 PRIME MIRAGE PUTS (WEAK BALANCE SHEET)</span>"),
    ]
    for wm in edge_watermarks:
        fig.add_annotation(
            x=wm["x"], y=wm["y"],
            text=wm["text"],
            showarrow=False,
            align="center"
        )

    # 2. Draw Sleek 3-Day Kinetic Velocity Trajectory Vectors behind each orb
    for c in candidates:
        m = c.get("metrics", {})
        f = c.get("fundamentals", {})
        z_curr = float(m.get("z_score_5d", 0.0))
        z_prev = float(m.get("z_3d_ago", z_curr - float(m.get("delta_z_3d", 0.0))))
        q_score = float(f.get("fund_score", 50.0))
        if abs(z_curr - z_prev) >= 0.14:
            tail_col = "rgba(52, 211, 153, 0.30)" if z_curr > z_prev else "rgba(251, 113, 133, 0.30)"
            fig.add_trace(go.Scatter(
                x=[z_prev, z_curr],
                y=[q_score, q_score],
                mode="lines+markers",
                line=dict(color=tail_col, width=1.8, dash="dot"),
                marker=dict(size=[4.5, 0], color=tail_col),
                hoverinfo="skip",
                showlegend=False
            ))

    # 3. Build 3-Layer Glowing Orbs + Smart Staggered External Labels
    halo_x, halo_y, halo_s, halo_c = [], [], [], []
    core_x, core_y, core_s, core_c, core_lc, core_lw, hover_texts = [], [], [], [], [], [], []
    pip_x, pip_y, pip_c = [], [], []
    label_anns = []

    # Sort by X to alternate label vertical offsets and prevent horizontal neighbors from overlapping
    sorted_by_x = sorted(
        [(idx, c) for idx, c in enumerate(candidates)],
        key=lambda item: float(item[1].get("metrics", {}).get("z_score_5d", 0.0))
    )

    for x_order, (idx, c) in enumerate(sorted_by_x):
        sym = c.get("symbol", "")
        m = c.get("metrics", {})
        f = c.get("fundamentals", {})
        bp = c.get("blueprint", {})
        rank_num = c.get("sector_rank", idx + 1)

        z = float(m.get("z_score_5d", m.get("z_score", 0.0)))
        z_abs = float(m.get("z_abs", z))
        z_rel = float(m.get("z_rel_5d", z))
        q_score = float(f.get("fund_score", 50.0))
        rvol = float(m.get("rvol", 1.0))
        clv = float(m.get("clv", m.get("daily_clv", 0.0)))
        price = float(m.get("price", 0.0))
        vwma = float(m.get("vwma20", m.get("sma20", price)))
        target_p = float(m.get("target_price", vwma))
        half_life = float(m.get("ou_half_life", 4.2))
        hurst = float(m.get("hurst", 0.45))
        atr_pct = (float(m.get("atr14", price * 0.03)) / max(1.0, price)) * 100.0
        action = str(m.get("action", "WATCHLIST"))
        playbook = str(m.get("playbook_type", m.get("playbook", "EQUILIBRIUM")))
        edge_score = float(bp.get("composite_score", 50.0))
        struct = bp.get("structure", "Outright Directional")
        altman_z = f.get("altman_z", 3.0)
        pio = f.get("piotroski_score", 6)

        is_focused = (sym == active_ticker)
        # Scale orb size cleanly by 1-5D Move Score + Active Focus
        core_size = 24 if is_focused else int(np.clip(12 + (edge_score - 25.0) * 0.22, 13, 23))

        if "CALL" in action:
            if "COILED" in playbook or "CATALYST" in playbook:
                orb_color = "#FB923C"  # Hyper-Orange Coiled Call
                aura_color = "rgba(255, 107, 0, 0.22)"
                txt_color = "#FF8533"
            else:
                orb_color = "#10B981"  # Vibrant Emerald
                aura_color = "rgba(16, 185, 129, 0.24)"
                txt_color = "#34D399"
        elif "PUT" in action:
            orb_color = "#F43F5E"      # Rose Coral
            aura_color = "rgba(244, 63, 94, 0.24)"
            txt_color = "#FB7185"
        else:
            orb_color = "#475569"      # Disciplined Slate
            aura_color = "rgba(100, 116, 139, 0.10)"
            txt_color = "#94A3B8"

        if is_focused:
            aura_color = "rgba(255, 107, 0, 0.34)"
            l_col = "#FF6B00"
            l_wid = 3.2
            txt_color = "#FF8533"
        elif rank_num <= 3 and action in ["BUY CALL", "BUY PUT"]:
            l_col = "#E2E8F0"
            l_wid = 2.0
        else:
            l_col = "rgba(255, 255, 255, 0.35)"
            l_wid = 1.2

        halo_x.append(z)
        halo_y.append(q_score)
        halo_s.append(core_size * 1.95 if is_focused else core_size * 1.65)
        halo_c.append(aura_color)

        core_x.append(z)
        core_y.append(q_score)
        core_s.append(core_size)
        core_c.append(orb_color)
        core_lc.append(l_col)
        core_lw.append(l_wid)

        pip_x.append(z)
        pip_y.append(q_score)
        pip_c.append("#FF8533" if is_focused else "#E2E8F0")

        ht = (
            f"<b>#{rank_num} ${sym}</b> &bull; {c.get('company_name', sym)}<br>"
            f"───────────────────────────────────────<br>"
            f"<b>1–5D Move Score:</b> <b>{edge_score:.0f}/100</b> ({action} &bull; {playbook})<br>"
            f"<b>Effective Stretch Z:</b> {z:+.2f}σ (Raw VWMA/ATR Z: {z_abs:+.2f}σ | Rel ETF Z: {z_rel:+.2f}σ)<br>"
            f"<b>Daily Kinetic ATR%:</b> {atr_pct:.2f}%/day | <b>1D Hook (ΔZ):</b> {m.get('delta_z_1d', 0.0):+.2f}σ<br>"
            f"<b>O-U Snap Half-Life:</b> {half_life:.1f} Days | <b>Hurst H:</b> {hurst:.2f}<br>"
            f"<b>FMP Pro Quality Score:</b> {q_score:.0f}/100 (Altman Z: {altman_z:.2f} | Piotroski: {pio}/9)<br>"
            f"<b>Intraday CLV:</b> {clv:+.2f} | <b>RVOL:</b> {rvol:.2f}x<br>"
            f"<b>Live Price:</b> ${price:.2f} (VWMA-20: ${vwma:.2f}) &rarr; <b>1–5D Target:</b> ${target_p:.2f}<br>"
            f"<b>30–45 DTE Setup:</b> {struct}"
        )
        hover_texts.append(ht)

        # Staggered external pill label so text never overlaps inside small circles
        y_shift = 17 if (x_order % 2 == 0 or is_focused) else -17
        label_txt = f"<b>#{rank_num} {sym}</b> ({edge_score:.0f})" if (rank_num <= 5 or is_focused) else f"<b>{sym}</b>"
        label_anns.append(dict(
            x=z,
            y=q_score,
            yshift=y_shift,
            text=label_txt,
            showarrow=False,
            font=dict(family="JetBrains Mono, monospace", size=10 if (rank_num <= 5 or is_focused) else 9.5, color=txt_color),
            bgcolor="rgba(10, 12, 18, 0.90)" if (rank_num <= 5 or is_focused) else "rgba(10, 12, 18, 0.68)",
            bordercolor="rgba(255, 107, 0, 0.68)" if is_focused else ("rgba(255,255,255,0.12)" if rank_num <= 5 else "rgba(0,0,0,0)"),
            borderwidth=1 if (rank_num <= 5 or is_focused) else 0,
            borderpad=2
        ))

    # Layer 1: Diffused Outer Glow Halo
    fig.add_trace(go.Scatter(
        x=halo_x, y=halo_y,
        mode="markers",
        marker=dict(size=halo_s, color=halo_c, line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False
    ))

    # Layer 2: Crisp Core Orbs
    fig.add_trace(go.Scatter(
        x=core_x, y=core_y,
        mode="markers",
        marker=dict(
            size=core_s,
            color=core_c,
            line=dict(color=core_lc, width=core_lw),
            opacity=0.95
        ),
        hoverinfo="text",
        hovertext=hover_texts,
        name="Candidates"
    ))

    # Layer 3: Center Specular Highlight Pip
    fig.add_trace(go.Scatter(
        x=pip_x, y=pip_y,
        mode="markers",
        marker=dict(size=4.5, color=pip_c, opacity=0.88),
        hoverinfo="skip",
        showlegend=False
    ))

    for ann in label_anns:
        fig.add_annotation(**ann)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1"),
        height=470,
        autosize=True,
        showlegend=False,
        dragmode="pan",
        margin=dict(l=50, r=36, t=32, b=46),
        xaxis=dict(
            title=dict(
                text="<b>Dual-Coordinate Effective Stretch Z-Score (σ) • Emerald = Call Snapback | Orange = Coiled Call | Rose = Put Rejection</b>",
                font=dict(size=11, color="#94A3B8")
            ),
            range=[-3.5, 3.5],
            fixedrange=False,
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=True,
            zerolinecolor="rgba(255, 255, 255, 0.20)",
            zerolinewidth=1.5,
            tickvals=[-3, -2, -1.15, 0, 1.15, 2, 3],
            ticktext=["-3.0σ", "-2.0σ", "-1.15σ (Call Zone)", "0.0σ (VWMA)", "+1.15σ (Put Zone)", "+2.0σ", "+3.0σ"],
            tickfont=dict(color="#94A3B8", size=10, family="JetBrains Mono")
        ),
        yaxis=dict(
            title=dict(
                text="<b>FMP Pro Solvency & Moat Score (0–100)</b>",
                font=dict(size=11, color="#94A3B8")
            ),
            range=[-4, 108],
            fixedrange=False,
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            zeroline=False,
            tickvals=[0, 25, 50, 75, 100],
            tickfont=dict(color="#94A3B8", size=10, family="JetBrains Mono")
        ),
        hoverlabel=dict(
            bgcolor="rgba(10, 12, 18, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.55)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0"),
            align="left"
        )
    )
    return fig


def create_smart_money_convergence_gauge(smart_money_score: float, insider_ratio: float) -> go.Figure:
    """
    Renders an AAA dual-bar/bullet gauge showing Smart-Money 13F Accumulation Pressure
    and Insider Open-Market Buy Intensity side-by-side.
    """
    sm_color = "#10B981" if smart_money_score >= 65 else "#FF6B00" if smart_money_score >= 45 else "#F43F5E"
    in_color = "#FB923C" if insider_ratio >= 65 else "#10B981" if insider_ratio >= 45 else "#F43F5E"

    fig = go.Figure()

    # Gauge 1: Smart-Money 13F Accumulation
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=smart_money_score,
        domain={'x': [0.03, 0.48], 'y': [0.12, 0.90]},
        title={'text': "<b>13F WHALE DELTA</b><br><span style='font-size:10px;color:#94A3B8'>3 Power Sectors Inflow</span>", 'font': {'size': 13, 'color': '#E2E8F0', 'family': 'Plus Jakarta Sans'}},
        number={'suffix': "/100", 'font': {'size': 24, 'family': 'JetBrains Mono', 'color': sm_color}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "rgba(255,255,255,0.12)", 'tickfont': {'color': '#94A3B8', 'size': 9}},
            'bar': {'color': sm_color, 'thickness': 0.28},
            'bgcolor': "rgba(12, 15, 22, 0.72)",
            'borderwidth': 1,
            'bordercolor': "rgba(255, 255, 255, 0.08)",
            'steps': [
                {'range': [0, 45], 'color': 'rgba(244, 63, 94, 0.14)'},
                {'range': [45, 70], 'color': 'rgba(255, 107, 0, 0.14)'},
                {'range': [70, 100], 'color': 'rgba(16, 185, 129, 0.20)'}
            ],
            'threshold': {'line': {'color': sm_color, 'width': 3}, 'thickness': 0.75, 'value': smart_money_score}
        }
    ))

    # Gauge 2: Insider P-Code Buy Clusters
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=insider_ratio,
        domain={'x': [0.52, 0.97], 'y': [0.12, 0.90]},
        title={'text': "<b>INSIDER P-CODE CLUSTER</b><br><span style='font-size:10px;color:#94A3B8'>C-Suite Open-Market Ratio</span>", 'font': {'size': 13, 'color': '#E2E8F0', 'family': 'Plus Jakarta Sans'}},
        number={'suffix': "/100", 'font': {'size': 24, 'family': 'JetBrains Mono', 'color': in_color}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "rgba(255,255,255,0.12)", 'tickfont': {'color': '#94A3B8', 'size': 9}},
            'bar': {'color': in_color, 'thickness': 0.28},
            'bgcolor': "rgba(12, 15, 22, 0.72)",
            'borderwidth': 1,
            'bordercolor': "rgba(255, 255, 255, 0.08)",
            'steps': [
                {'range': [0, 45], 'color': 'rgba(244, 63, 94, 0.14)'},
                {'range': [45, 70], 'color': 'rgba(251, 146, 60, 0.12)'},
                {'range': [70, 100], 'color': 'rgba(255, 107, 0, 0.22)'}
            ],
            'threshold': {'line': {'color': in_color, 'width': 3}, 'thickness': 0.75, 'value': insider_ratio}
        }
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=180,
        margin=dict(l=15, r=15, t=35, b=15),
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#CBD5E1")
    )
    return fig


def create_smart_money_gestation_chart(stealth_gems: List[Dict[str, Any]]) -> go.Figure:
    """
    Renders an AAA Scatter Matrix of Unknown Companies Solving Big Problems:
    Market Cap ($M) vs Insider/13F Conviction Score with Dollar Volume sizing.
    """
    if not stealth_gems:
        return go.Figure()

    symbols = [g["symbol"] for g in stealth_gems]
    mcaps = [max(10.0, g["market_cap"] / 1_000_000.0) if g.get("market_cap", 0) > 0 else 500.0 for g in stealth_gems]
    convictions = [g["cluster_conviction"] for g in stealth_gems]
    dollars = [max(20000.0, g.get("total_dollars", 50000.0)) for g in stealth_gems]
    sizes = [min(36, max(14, int((d ** 0.35) * 1.8))) for d in dollars]
    colors = ["#FF6B00" if g.get("c_suite_count", 0) > 0 else "#10B981" for g in stealth_gems]

    hover_texts = [
        f"<b>{g['symbol']} &bull; {g.get('name', '')}</b><br>"
        f"Market Cap: <b>{g.get('market_cap_str', 'N/A')}</b> | Price: <b>${g.get('price', 0):.2f}</b> ({g.get('change_pct', 0):+.2f}%)<br>"
        f"Cluster Conviction: <b>{g['cluster_conviction']}/100</b> ({g.get('signal_tag', '')})<br>"
        f"Total Capital Deployed: <b>${g.get('total_dollars', 0):,.0f}</b> across {g.get('trade_count', 1)} trades<br>"
        f"Key Insiders: {', '.join(g.get('insiders', []))}<br>"
        f"Filing Date: {g.get('latest_filing', '')}"
        for g in stealth_gems
    ]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=mcaps,
        y=convictions,
        mode="markers+text",
        text=symbols,
        textposition="top center",
        textfont=dict(family="JetBrains Mono, monospace", size=11, color="#E2E8F0"),
        marker=dict(
            size=sizes,
            color=colors,
            opacity=0.88,
            line=dict(color="rgba(226, 232, 240, 0.72)", width=1.2)
        ),
        hovertext=hover_texts,
        hoverinfo="text"
    ))

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(12, 15, 22, 0.42)',
        height=260,
        margin=dict(l=45, r=20, t=25, b=35),
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#CBD5E1"),
        xaxis=dict(
            title=dict(text="Market Capitalization ($ Millions)", font=dict(color="#94A3B8", size=11, family="Plus Jakarta Sans")),
            type="log",
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94A3B8", size=10, family="JetBrains Mono")
        ),
        yaxis=dict(
            title=dict(text="Gestation & Cluster Conviction", font=dict(color="#94A3B8", size=11, family="Plus Jakarta Sans")),
            range=[40, 105],
            showgrid=True,
            gridcolor="rgba(255, 255, 255, 0.05)",
            tickfont=dict(color="#94A3B8", size=10, family="JetBrains Mono")
        ),
        hoverlabel=dict(
            bgcolor="rgba(13, 16, 23, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.65)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0"),
            align="left"
        )
    )
    return fig


def create_macro_regime_radar_chart(radar_axes: Dict[str, Any], regime_label: str = "MACRO REGIME") -> go.Figure:
    """
    Renders the AAA 6-Axis Macro Hexagon Radar Chart (The Macro Spider).
    Visualizes the 6 fundamental cross-asset market forces normalized to 0-100:
      1. Credit & Liquidity Appetite (HYG/LQD + BTC)
      2. Duration & Rates Stability (10Y Yield Calmness / TLT Bid)
      3. Tape Breadth & Volume (RSP-QQQ Spread + SPY RVOL)
      4. Inflation & Commodity Equilibrium (Inverted Oil & Dollar Stress)
      5. World Events & News Sentiment (FMP Real-Time News NLP + VIX)
      6. Smart-Money & Early Gestation (13F Elite Whale Inflows + Insider P-Code Buys)
    """
    categories = [
        "Credit & Liquidity<br>Appetite",
        "Duration & Rates<br>Stability",
        "Tape Breadth &<br>Volume Confirmation",
        "Inflation & Energy<br>Equilibrium",
        "World Events &<br>Risk Runway",
        "Smart-Money &<br>Gestation Inflows"
    ]

    c_liq = float(radar_axes.get("credit_liquidity_score", 50.0))
    d_sta = float(radar_axes.get("duration_stability_score", 50.0))
    t_bre = float(radar_axes.get("tape_breadth_score", 50.0))
    e_inf = float(radar_axes.get("energy_inflation_score", 50.0))
    w_eve = float(radar_axes.get("world_events_score", 50.0))
    s_mon = float(radar_axes.get("smart_money_score", 50.0))

    values = [c_liq, d_sta, t_bre, e_inf, w_eve, s_mon]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    avg_score = float(sum(values) / len(values))
    if avg_score >= 58.0:
        line_col = "#10B981"
        fill_col = "rgba(16, 185, 129, 0.20)"
        badge_text = "EXPANSIONARY TAILWIND"
    elif avg_score <= 43.0:
        line_col = "#F43F5E"
        fill_col = "rgba(244, 63, 94, 0.20)"
        badge_text = "DEFENSIVE CONTRACTION"
    else:
        line_col = "#FF6B00"
        fill_col = "rgba(255, 107, 0, 0.18)"
        badge_text = "ROTATIONAL BIFURCATION"

    fig = go.Figure()

    def _pt_col(v: float) -> str:
        return "#10B981" if v >= 58.0 else ("#F43F5E" if v <= 42.0 else "#FB923C")

    pt_colors_closed = [_pt_col(v) for v in values_closed]

    # Red Stress Boundary (42) & Equilibrium Ring (50) & Green Tailwind Ring (58)
    fig.add_trace(go.Scatterpolar(
        r=[42] * len(categories_closed),
        theta=categories_closed,
        mode="lines",
        showlegend=False,
        line=dict(color="rgba(244, 63, 94, 0.34)", width=1.0, dash="dot"),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[50] * len(categories_closed),
        theta=categories_closed,
        mode="lines",
        name="Equilibrium (50)",
        line=dict(color="rgba(226, 232, 240, 0.26)", width=1.4, dash="dot"),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[58] * len(categories_closed),
        theta=categories_closed,
        mode="lines",
        showlegend=False,
        line=dict(color="rgba(16, 185, 129, 0.34)", width=1.0, dash="dot"),
        hoverinfo="skip"
    ))

    # Live Macro Polygon with Per-Vertex Red/Neutral/Green Coloring
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        mode="lines+markers",
        name=f"Live Macro ({avg_score:.1f}/100)",
        line=dict(color=line_col, width=2.8),
        fillcolor=fill_col,
        marker=dict(
            size=9,
            color=pt_colors_closed,
            symbol="circle",
            line=dict(width=1.8, color="#06070A")
        ),
        hoverinfo="text",
        hovertext=[
            f"<b>{cat.replace('<br>', ' ')}</b>: <b>{val:.1f} / 100</b><br>"
            f"Zone: <b>{'GREEN TAILWIND' if val >= 58 else 'RED HEADWIND' if val <= 42 else 'NEUTRAL BUFFER'}</b>"
            for cat, val in zip(categories_closed, values_closed)
        ]
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(12, 15, 22, 0.42)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 50, 75],
                ticktext=["25", "50", "75"],
                tickfont=dict(color="#64748B", size=9, family="JetBrains Mono"),
                gridcolor="rgba(255, 255, 255, 0.05)",
                linecolor="rgba(255, 255, 255, 0.10)"
            ),
            angularaxis=dict(
                tickfont=dict(color="#CBD5E1", size=10, family="Plus Jakarta Sans, sans-serif"),
                gridcolor="rgba(255, 255, 255, 0.05)",
                linecolor="rgba(255, 255, 255, 0.12)",
                direction="clockwise"
            )
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#CBD5E1"),
        height=360,
        margin=dict(l=45, r=45, t=30, b=55),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            font=dict(color="#94A3B8", size=10, family="Plus Jakarta Sans")
        ),
        hoverlabel=dict(
            bgcolor="rgba(13, 16, 23, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.55)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0")
        )
    )
    return fig


def create_macro_economic_7pillar_spider(econ_data: Dict[str, Any]) -> go.Figure:
    """
    Renders the Large 7-Axis Overall US Macro-Economic Regime Spider Graph (0-100 Logistic Buffered):
      1. Manufacturing (ISM & Output)
      2. Retail Sales (Consumer Spend)
      3. Jobless Claims (Labor Resilience)
      4. JOLTS Openings (Hiring Demand)
      5. Treasuries & Bond Auctions
      6. Michigan Sentiment & Inflation Exp.
      7. Fed Chair Powell & FOMC Speeches
    Features concentric Red (0-42), Neutral (42-58), and Green (58-100) regime zones and
    individually color-coded vertex markers with direct 0-100 score callouts.
    """
    pillars = econ_data.get("pillars", [])
    if not pillars:
        return go.Figure()

    categories = [p["label"] for p in pillars]
    values = [float(p["score"]) for p in pillars]
    prior_values = [float(p.get("prior_score", p["score"])) for p in pillars]
    pt_colors = [p["color"] for p in pillars]

    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]
    prior_values_closed = prior_values + [prior_values[0]]
    pt_colors_closed = pt_colors + [pt_colors[0]]
    pillars_closed = pillars + [pillars[0]]

    overall_score = float(econ_data.get("overall_score", sum(values) / max(1, len(values))))
    overall_prior = float(econ_data.get("overall_prior_score", sum(prior_values) / max(1, len(prior_values))))
    if overall_score >= 58.0:
        poly_line = "#10B981"
        poly_fill = "rgba(16, 185, 129, 0.20)"
    elif overall_score <= 42.0:
        poly_line = "#F43F5E"
        poly_fill = "rgba(244, 63, 94, 0.20)"
    else:
        poly_line = "#FF6B00"
        poly_fill = "rgba(255, 107, 0, 0.18)"

    fig = go.Figure()

    # 1. Concentric Regime Zone Background Bands (Outer Green 58-100, Middle Neutral 42-58, Inner Red 0-42)
    fig.add_trace(go.Scatterpolar(
        r=[100] * len(categories_closed),
        theta=categories_closed,
        fill="toself",
        mode="lines",
        showlegend=False,
        fillcolor="rgba(16, 185, 129, 0.06)",
        line=dict(color="rgba(16, 185, 129, 0.24)", width=1.0),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[58] * len(categories_closed),
        theta=categories_closed,
        fill="toself",
        mode="lines",
        showlegend=False,
        fillcolor="rgba(12, 15, 22, 0.86)",
        line=dict(color="rgba(16, 185, 129, 0.42)", width=1.3, dash="dash"),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[58] * len(categories_closed),
        theta=categories_closed,
        fill="toself",
        mode="lines",
        showlegend=False,
        fillcolor="rgba(251, 146, 60, 0.08)",
        line=dict(color="rgba(0,0,0,0)", width=0),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[42] * len(categories_closed),
        theta=categories_closed,
        fill="toself",
        mode="lines",
        showlegend=False,
        fillcolor="rgba(12, 15, 22, 0.88)",
        line=dict(color="rgba(244, 63, 94, 0.48)", width=1.3, dash="dash"),
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[42] * len(categories_closed),
        theta=categories_closed,
        fill="toself",
        mode="lines",
        showlegend=False,
        fillcolor="rgba(244, 63, 94, 0.10)",
        line=dict(color="rgba(0,0,0,0)", width=0),
        hoverinfo="skip"
    ))

    # 2. Equilibrium 50 Baseline Ring
    fig.add_trace(go.Scatterpolar(
        r=[50] * len(categories_closed),
        theta=categories_closed,
        mode="lines",
        name="Equilibrium (50)",
        line=dict(color="rgba(226, 232, 240, 0.28)", width=1.5, dash="dot"),
        hoverinfo="skip"
    ))

    # 2B. Prior-Cycle Ghost Polygon (1M / Prior Release Baseline Contour for Rate-of-Change Visibility)
    fig.add_trace(go.Scatterpolar(
        r=prior_values_closed,
        theta=categories_closed,
        fill="toself",
        mode="lines+markers",
        name=f"Prior Release Baseline ({overall_prior:.1f}/100)",
        line=dict(color="rgba(148, 163, 184, 0.58)", width=1.8, dash="dashdot"),
        fillcolor="rgba(148, 163, 184, 0.05)",
        marker=dict(size=6, color="rgba(148, 163, 184, 0.68)", symbol="diamond"),
        hoverinfo="skip"
    ))

    # 3. Primary 7-Pillar Buffered Macro Polygon & Color-Coded Zone Vertices
    hover_texts = [
        f"<b>{p['short_label']}</b> — <b style='color:{p['color']};'>{p['score']:.1f} / 100 ({p['zone']})</b><br>"
        f"Cycle Impulse: <b style='color:{p.get('delta_color', '#94A3B8')};'>{p.get('delta_badge', '● 0.0')} pts</b> (Prior Baseline: {float(p.get('prior_score', p['score'])):.1f})<br>"
        f"Regime: <b>{p['status']}</b><br>"
        f"Latest Print: {p['latest_str']}<br>"
        f"Surprise / Trend: {p['surprise_str']}<br>"
        f"{p['proxy_str']}<br>"
        f"Next Release: <b>{p['next_str']}</b>"
        for p in pillars_closed
    ]
    text_labels = [
        f"{p['score']:.0f} ({float(p.get('delta_score', 0.0)):+.0f})" if abs(float(p.get("delta_score", 0.0))) >= 1.0 else f"{p['score']:.0f}"
        for p in pillars
    ] + [""]

    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill="toself",
        mode="lines+markers+text",
        name=f"Overall Macro Composite ({overall_score:.1f}/100)",
        line=dict(color=poly_line, width=3.2),
        fillcolor=poly_fill,
        marker=dict(
            size=14,
            color=pt_colors_closed,
            symbol="circle",
            line=dict(width=2.6, color="#06070A")
        ),
        text=text_labels,
        textposition="top center",
        textfont=dict(family="JetBrains Mono, monospace", size=11, color="#E2E8F0"),
        hoverinfo="text",
        hovertext=hover_texts
    ))

    # 4. Explicit Color-Zone Legend Keys (Green / Neutral / Red)
    for z_name, z_col in [
        ("Green Tailwind (58–100)", "#10B981"),
        ("Neutral Buffer (42–58)", "#FB923C"),
        ("Red Headwind (0–42)", "#F43F5E")
    ]:
        fig.add_trace(go.Scatterpolar(
            r=[None],
            theta=[categories[0]],
            mode="markers",
            name=z_name,
            marker=dict(size=10, color=z_col, line=dict(width=1.5, color="#06070A")),
            hoverinfo="skip"
        ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(12, 15, 22, 0.48)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[25, 42, 50, 58, 75, 100],
                ticktext=["25", "42", "50", "58", "75", "100"],
                tickfont=dict(color="#94A3B8", size=9, family="JetBrains Mono, monospace"),
                gridcolor="rgba(255, 255, 255, 0.05)",
                linecolor="rgba(255, 255, 255, 0.10)",
                angle=90
            ),
            angularaxis=dict(
                tickfont=dict(color="#CBD5E1", size=11.5, family="Plus Jakarta Sans, sans-serif"),
                gridcolor="rgba(255, 255, 255, 0.05)",
                linecolor="rgba(255, 255, 255, 0.14)",
                direction="clockwise",
                rotation=90
            )
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#CBD5E1"),
        height=540,
        margin=dict(l=82, r=82, t=42, b=120),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.16,
            xanchor="center",
            x=0.5,
            font=dict(color="#CBD5E1", size=10.5, family="Plus Jakarta Sans, sans-serif"),
            bgcolor="rgba(13, 16, 23, 0.78)",
            bordercolor="rgba(255, 255, 255, 0.08)",
            borderwidth=1
        ),
        hoverlabel=dict(
            bgcolor="rgba(13, 16, 23, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.65)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0"),
            align="left"
        )
    )
    return fig


def create_empirical_excursion_profile_chart(ticker: str, metrics: Dict[str, Any]) -> go.Figure:
    """
    5-Year Conditional 5-Day Excursion & Tail-Risk Profile (MFE vs. Net Close vs. MAE):
    Plots the actual walk-forward distribution of 5-day Maximum Favorable Excursion (Upside),
    5-day Net Close Return, and 5-day Maximum Adverse Excursion (Downside) across all
    historical analogs where the ticker traded at a similar Dual-Coordinate Z-score.
    """
    curr_p = float(metrics.get("price", 100.0) or 100.0)
    tgt_p = float(metrics.get("target_price", curr_p * 1.05) or curr_p * 1.05)
    inv_p = float(metrics.get("invalidation_price", curr_p * 0.96) or curr_p * 0.96)
    tgt_pct = ((tgt_p - curr_p) / curr_p) * 100.0 if curr_p > 0 else 4.0
    stp_pct = ((inv_p - curr_p) / curr_p) * 100.0 if curr_p > 0 else -3.5

    med_up = float(metrics.get("expected_up_basis_pct", 4.5))
    p25_up = float(metrics.get("p25_up_pct", round(med_up * 0.55, 2)))
    p75_up = float(metrics.get("p75_up_pct", metrics.get("p75_basis_pct", round(med_up * 1.45, 2))))
    p90_up = float(metrics.get("p90_up_pct", round(p75_up * 1.30, 2)))

    med_dn = float(metrics.get("expected_down_basis_pct", -3.2))
    p25_dn = float(metrics.get("p25_dn_pct", round(med_dn * 0.55, 2)))
    p75_dn = float(metrics.get("p75_dn_pct", round(med_dn * 1.40, 2)))
    p90_dn = float(metrics.get("p90_dn_pct", round(p75_dn * 1.28, 2)))

    med_cl = float(metrics.get("med_close_pct", round((med_up + med_dn) * 0.55, 2)))
    p25_cl = float(metrics.get("p25_close_pct", round(med_dn * 0.45, 2)))
    p75_cl = float(metrics.get("p75_close_pct", round(med_up * 0.72, 2)))

    sample_n = int(metrics.get("empirical_sample_n", 45))
    win_rate = float(metrics.get("empirical_win_rate_pct", 60.0))

    categories = [
        "5D Downside MAE<br><span style='font-size:10px;color:#94A3B8;'>(Adverse Tail Risk)</span>",
        "5D Net Close<br><span style='font-size:10px;color:#94A3B8;'>(Day-5 Realized)</span>",
        "5D Upside MFE<br><span style='font-size:10px;color:#94A3B8;'>(Max Peak Snap)</span>"
    ]

    fig = go.Figure()

    # 1. Outer 10th-90th Percentile Whiskers
    fig.add_trace(go.Scatter(
        x=[p90_dn, p25_cl * 1.35, 0.0],
        y=categories,
        mode="lines",
        line=dict(color="rgba(255,255,255,0)", width=0),
        showlegend=False,
        hoverinfo="skip"
    ))

    # Draw horizontal range bars for IQR (25th to 75th percentile) and Tail Whiskers
    bar_specs = [
        (categories[0], p90_dn, p75_dn, med_dn, p25_dn, "#F43F5E", "rgba(244, 63, 94, 0.25)", "Downside Excursion (MAE)"),
        (categories[1], p25_cl * 1.4, p25_cl, med_cl, p75_cl, "#FF6B00", "rgba(255, 107, 0, 0.24)", "5-Day Net Close"),
        (categories[2], p25_up * 0.6, p25_up, med_up, p75_up, "#10B981", "rgba(16, 185, 129, 0.25)", "Upside Excursion (MFE)")
    ]
    tail_ends = [p90_dn, p75_cl * 1.35, p90_up]

    for idx, (cat, w_low, q25, med, q75, col_hex, fill_rgba, label_name) in enumerate(bar_specs):
        w_high = tail_ends[idx] if idx > 0 else q25
        w_start = w_low if idx == 0 else q25 * 0.65
        # Whisker line
        fig.add_trace(go.Scatter(
            x=[w_start, w_high],
            y=[cat, cat],
            mode="lines",
            line=dict(color=col_hex, width=2, dash="dot"),
            showlegend=False,
            hoverinfo="skip"
        ))
        # IQR Box (Q25 to Q75)
        span_iqr = q75 - q25
        fig.add_trace(go.Bar(
            x=[span_iqr],
            y=[cat],
            base=[q25],
            orientation="h",
            width=0.42,
            marker=dict(color=fill_rgba, line=dict(color=col_hex, width=1.8)),
            name=f"{label_name} IQR",
            showlegend=False,
            hovertemplate=(
                f"<b>{ticker} — {label_name}</b> (N={sample_n} analogs)<br>"
                f"Median: <b>{med:+.2f}%</b> (${curr_p * (1 + med/100):.2f})<br>"
                f"IQR (25%–75%): <b>{q25:+.2f}%</b> to <b>{q75:+.2f}%</b><br>"
                f"90th Tail Stretch: <b>{tail_ends[idx]:+.2f}%</b><extra></extra>"
            )
        ))
        # Median Diamond Marker + Direct Label
        fig.add_trace(go.Scatter(
            x=[med],
            y=[cat],
            mode="markers+text",
            marker=dict(size=11, color=col_hex, symbol="diamond", line=dict(width=1.5, color="#06070A")),
            text=[f"<b>{med:+.1f}%</b>"],
            textposition="top center",
            textfont=dict(size=10, color="#E2E8F0", family="JetBrains Mono"),
            showlegend=False,
            hoverinfo="skip"
        ))

    # Zero reference line
    fig.add_vline(x=0.0, line_width=1.2, line_dash="solid", line_color="rgba(226, 232, 240, 0.22)")

    # Target & Hard Stop vertical lines
    fig.add_vline(
        x=tgt_pct,
        line_width=1.8,
        line_dash="dash",
        line_color="#10B981",
        annotation_text=f"Target ({tgt_pct:+.1f}%)",
        annotation_position="top right",
        annotation_font=dict(size=9.5, color="#10B981", family="JetBrains Mono")
    )
    fig.add_vline(
        x=stp_pct,
        line_width=1.8,
        line_dash="dash",
        line_color="#F43F5E",
        annotation_text=f"Stop ({stp_pct:+.1f}%)",
        annotation_position="top left",
        annotation_font=dict(size=9.5, color="#F43F5E", family="JetBrains Mono")
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#CBD5E1"),
        height=235,
        margin=dict(l=135, r=24, t=26, b=32),
        xaxis=dict(
            title=dict(text=f"5-Day Forward Excursion % Across {sample_n} Historical Z-Analogs ({win_rate:.0f}% Win Rate)", font=dict(size=10, color="#94A3B8")),
            ticksuffix="%",
            tickfont=dict(size=10, color="#CBD5E1", family="JetBrains Mono"),
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False
        ),
        yaxis=dict(
            tickfont=dict(size=10.5, color="#CBD5E1", family="Plus Jakarta Sans"),
            gridcolor="rgba(255,255,255,0.03)"
        ),
        hoverlabel=dict(
            bgcolor="rgba(13, 16, 23, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.55)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0")
        )
    )
    return fig


def create_schwab_payoff_curve_chart(
    symbol: str,
    spot_price: float,
    strike: float,
    opt_type: str,
    limit_price: float,
    qty: int,
    dte: int,
    iv: float,
    target_price: float,
    stop_price: float,
    strategy: str = "SINGLE_LEG",
    short_strike: Optional[float] = None,
) -> go.Figure:
    """
    Schwab / thinkorswim-style Multi-Horizon Option P&L & Time-Decay Curve:
    Supports both SINGLE_LEG and VERTICAL_DEBIT_SPREAD (long `strike`, short `short_strike`)
    with dynamic Spot-Vol Skew leverage across:
      1. 1-5D Swing Horizon
      2. Mid-Cycle (DTE / 2)
      3. Expiration (0 DTE Intrinsic)
    """
    s0 = max(1.0, float(spot_price))
    k = max(0.5, float(strike))
    prem = max(0.01, float(limit_price))
    contracts = max(1, int(qty))
    sigma = float(iv) / 100.0 if float(iv) > 3.0 else max(0.15, float(iv))
    r = 0.0425
    is_call = (str(opt_type).upper() == "CALL")
    is_spread = (
        str(strategy).upper() in ("VERTICAL_DEBIT_SPREAD", "DEBIT_SPREAD", "SPREAD")
        and short_strike is not None
        and float(short_strike) > 0.0
        and abs(float(short_strike) - k) >= 0.25
    )
    k2 = float(short_strike) if is_spread else 0.0

    total_debit = contracts * prem * 100.0 + contracts * (1.30 if is_spread else 0.65)

    bounds_pts = [s0 * 0.82, s0 * 1.18, k * 0.85, k * 1.15, float(stop_price) * 0.95, float(target_price) * 1.05]
    if is_spread:
        bounds_pts.extend([k2 * 0.92, k2 * 1.08])
    low_bound = min(bounds_pts)
    high_bound = max(bounds_pts)
    s_grid = np.linspace(max(0.5, low_bound), high_bound, 90)
    # Spot-vol leverage: rallies slightly compress IV, selloffs elevate IV
    sigma_grid = np.clip(sigma * (1.0 - 0.35 * ((s_grid - s0) / s0)), 0.08, 2.50)

    t_entry = max(1, dte) / 365.0
    t_swing = max(1, dte - 4) / 365.0
    t_half = max(1, dte // 2) / 365.0

    _v_erf = np.vectorize(math.erf)

    def _vec_bs(s_arr: np.ndarray, k_leg: float, t_exp: float, sig_arr: Any) -> np.ndarray:
        sqrt_t = math.sqrt(t_exp)
        d1 = (np.log(s_arr / k_leg) + (r + 0.5 * (sig_arr ** 2)) * t_exp) / (sig_arr * sqrt_t)
        d2 = d1 - sig_arr * sqrt_t
        cdf_d1 = 0.5 * (1.0 + _v_erf(d1 / math.sqrt(2.0)))
        cdf_d2 = 0.5 * (1.0 + _v_erf(d2 / math.sqrt(2.0)))
        if is_call:
            return s_arr * cdf_d1 - k_leg * math.exp(-r * t_exp) * cdf_d2
        else:
            return k_leg * math.exp(-r * t_exp) * (1.0 - cdf_d2) - s_arr * (1.0 - cdf_d1)

    if is_spread:
        spread_width = abs(k2 - k)
        bs0_long = float(_vec_bs(np.array([s0]), k, t_entry, np.array([sigma]))[0])
        bs0_short = float(_vec_bs(np.array([s0]), k2, t_entry, np.array([sigma]))[0])
        bs0_net = max(0.03, bs0_long - bs0_short)
        scale = float(np.clip(prem / bs0_net, 0.70, 1.45))

        intr_l = np.maximum(0.0, s_grid - k) if is_call else np.maximum(0.0, k - s_grid)
        intr_s = np.maximum(0.0, s_grid - k2) if is_call else np.maximum(0.0, k2 - s_grid)
        intrinsic_grid = np.clip(intr_l - intr_s, 0.0, spread_width)
        swing_net = (_vec_bs(s_grid, k, t_swing, sigma_grid) - _vec_bs(s_grid, k2, t_swing, sigma_grid)) * scale
        half_net = (_vec_bs(s_grid, k, t_half, sigma_grid) - _vec_bs(s_grid, k2, t_half, sigma_grid)) * scale
        swing_grid = np.clip(swing_net, 0.0, spread_width)
        half_grid = np.clip(half_net, 0.0, spread_width)
    else:
        bs0 = float(_vec_bs(np.array([s0]), k, t_entry, np.array([sigma]))[0])
        scale = float(np.clip(prem / bs0, 0.70, 1.45)) if bs0 > 0.03 else 1.0
        intrinsic_grid = np.maximum(0.0, s_grid - k) if is_call else np.maximum(0.0, k - s_grid)
        swing_grid = np.maximum(intrinsic_grid, _vec_bs(s_grid, k, t_swing, sigma_grid) * scale)
        half_grid = np.maximum(intrinsic_grid, _vec_bs(s_grid, k, t_half, sigma_grid) * scale)

    pnl_swing = (swing_grid * contracts * 100.0) - total_debit
    pnl_half = (half_grid * contracts * 100.0) - total_debit
    pnl_exp = (intrinsic_grid * contracts * 100.0) - total_debit

    fig = go.Figure()

    # Zero Breakeven Horizontal Line
    fig.add_hline(y=0.0, line_width=1.3, line_dash="solid", line_color="rgba(255,255,255,0.25)")

    # 1. Expiration Curve (0 DTE)
    fig.add_trace(go.Scatter(
        x=s_grid,
        y=pnl_exp,
        mode="lines",
        name="At Expiration (0 DTE Intrinsic)",
        line=dict(color="rgba(148, 163, 184, 0.65)", width=1.8, dash="dot"),
        hovertemplate="Underlying: <b>$%{x:.2f}</b><br>Expiration P&L: <b>$%{y:,.2f}</b><extra></extra>"
    ))

    # 2. Half-Life Curve (DTE / 2)
    fig.add_trace(go.Scatter(
        x=s_grid,
        y=pnl_half,
        mode="lines",
        name=f"Mid-Cycle ({max(1, dte // 2)} DTE Left)",
        line=dict(color="#FB923C", width=2.0, dash="dash"),
        hovertemplate="Underlying: <b>$%{x:.2f}</b><br>Mid-Cycle P&L: <b>$%{y:,.2f}</b><extra></extra>"
    ))

    # 3. Primary 1-5D Swing Target Curve (T+4d / DTE-4)
    fig.add_trace(go.Scatter(
        x=s_grid,
        y=pnl_swing,
        mode="lines",
        name=f"1–5D Swing Horizon ({max(1, dte - 4)} DTE Left)",
        line=dict(color="#FF6B00", width=3.0),
        fill="tozeroy",
        fillcolor="rgba(255, 107, 0, 0.10)",
        hovertemplate="Underlying: <b>$%{x:.2f}</b><br>1–5D Swing P&L: <b>$%{y:,.2f}</b><extra></extra>"
    ))

    # Vertical reference lines: Spot, Target, Stop
    fig.add_vline(
        x=s0,
        line_width=1.5,
        line_dash="dot",
        line_color="#E2E8F0",
        annotation_text=f"Spot ${s0:.2f}",
        annotation_position="top",
        annotation_font=dict(size=9.5, color="#E2E8F0", family="JetBrains Mono")
    )
    fig.add_vline(
        x=float(target_price),
        line_width=1.8,
        line_dash="dash",
        line_color="#10B981",
        annotation_text=f"Target ${float(target_price):.2f}",
        annotation_position="top right",
        annotation_font=dict(size=9.5, color="#10B981", family="JetBrains Mono")
    )
    fig.add_vline(
        x=float(stop_price),
        line_width=1.8,
        line_dash="dash",
        line_color="#F43F5E",
        annotation_text=f"Stop ${float(stop_price):.2f}",
        annotation_position="top left",
        annotation_font=dict(size=9.5, color="#F43F5E", family="JetBrains Mono")
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#CBD5E1"),
        height=270,
        margin=dict(l=55, r=24, t=28, b=42),
        xaxis=dict(
            title=dict(text=f"{symbol} Underlying Stock Price ($)", font=dict(size=10, color="#94A3B8")),
            tickprefix="$",
            tickfont=dict(size=10, color="#CBD5E1", family="JetBrains Mono"),
            gridcolor="rgba(255,255,255,0.05)"
        ),
        yaxis=dict(
            title=dict(text="Net Position P&L ($)", font=dict(size=10, color="#94A3B8")),
            tickprefix="$",
            tickfont=dict(size=10, color="#CBD5E1", family="JetBrains Mono"),
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=9.5, color="#CBD5E1", family="Plus Jakarta Sans")
        ),
        hoverlabel=dict(
            bgcolor="rgba(13, 16, 23, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.55)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0")
        )
    )
    return fig


def _format_shares_count(n: float) -> str:
    if n >= 1e9:
        return f"{n / 1e9:.2f}B"
    elif n >= 1e6:
        return f"{n / 1e6:.1f}M"
    elif n >= 1e3:
        return f"{n / 1e3:.0f}K"
    elif n > 0:
        return f"{n:,.0f}"
    return "N/A"


def create_float_topology_card_html(symbol: str, float_data: Dict[str, Any]) -> str:
    """
    Renders AAA Concept 1: Institutional Float Topology & Loan Pressure HUD.
    Displays:
      1. Segmented Institutional vs Retail vs Insider Capital Stack
      2. Short Float % & Days-to-Cover (DTC) Squeeze Indicator
      3. 4-Column high-density micro-metric grid (Short Float, DTC, Borrowed Shares, Institutional Control)
      4. Asymmetric Collar Put Strategy Rationale Box
    """
    sym = (symbol or "").strip().upper()
    if not float_data or not float_data.get("has_data", False):
        return (
            f'<div class="float-topology-card" style="opacity: 0.88;">'
            f'<div class="float-topology-hdr">'
            f'<div class="float-topology-title">'
            f'<i class="fa-solid fa-chart-pie" style="color: #FF6B00;"></i>'
            f'<span>EQUITY FLOAT TOPOLOGY & LOAN PRESSURE</span>'
            f'<span style="color: #64748B; font-size: 0.70rem;">&bull; {sym}</span>'
            f'</div>'
            f'<span class="squeeze-hazard-pill squeeze-hazard-low">'
            f'<i class="fa-solid fa-circle-check"></i> BROAD BASKET / UNTRACKED FLOAT'
            f'</span></div>'
            f'<div style="font-size: 0.75rem; color: #94A3B8; padding: 4px 0;">'
            f'Float loan statistics are not reported or not applicable for broad index / ETF vehicles. Standard mean-reversion metrics apply.'
            f'</div></div>'
        )

    has_true_short = bool(float_data.get("has_true_short_interest", False))
    short_pct = float(float_data.get("short_pct", 0.0) or 0.0)
    dtc = float(float_data.get("days_to_cover", 0.0) or 0.0)
    shares_short = float(float_data.get("shares_short", 0.0) or 0.0)
    float_shares = float(float_data.get("float_shares", 0.0) or 0.0)
    shares_out = float(float_data.get("shares_outstanding", 0.0) or 0.0)
    inst_pct = float(float_data.get("inst_pct", 0.0) or 0.0)
    insider_pct = float(float_data.get("insider_pct", 0.0) or 0.0)
    retail_pct = float(float_data.get("retail_float_pct", 0.0) or 0.0)
    free_float_pct = float(float_data.get("free_float_pct", 100.0) or 100.0)
    inst_lockup_pct = float(float_data.get("inst_lockup_pct", round(max(0.0, 100.0 - free_float_pct), 1)) or 0.0)
    pc_13f = float(float_data.get("inst_put_call_ratio", 1.0) or 1.0)
    hedge_regime = str(float_data.get("inst_hedge_regime", "BALANCED 13F HEDGE"))
    short_mom = float(float_data.get("short_mom_pct", 0.0) or 0.0)
    hazard_level = str(float_data.get("hazard_level", "LOW")).upper()
    hazard_badge = str(float_data.get("hazard_badge", "STABLE FLOAT DYNAMICS"))
    collar_advice = str(float_data.get("collar_advice", "Standard 30-45 DTE options playbook applies."))

    # Hazard pill class & icon
    if hazard_level == "EXTREME":
        hazard_class = "squeeze-hazard-extreme"
        hazard_icon = '<i class="fa-solid fa-triangle-exclamation" style="animation: pulse 1.5s infinite;"></i>'
    elif hazard_level == "ELEVATED":
        hazard_class = "squeeze-hazard-elevated"
        hazard_icon = '<i class="fa-solid fa-triangle-exclamation"></i>'
    elif hazard_level == "MODERATE":
        hazard_class = "squeeze-hazard-moderate"
        hazard_icon = '<i class="fa-solid fa-arrows-split-up-and-left"></i>'
    else:
        hazard_class = "squeeze-hazard-low"
        hazard_icon = '<i class="fa-solid fa-circle-check"></i>'

    # Compute segmented bar widths
    tot_pct = max(1.0, inst_pct + retail_pct + insider_pct)
    w_inst = max(3.0, (inst_pct / tot_pct) * 100.0)
    w_insider = max(2.0, (insider_pct / tot_pct) * 100.0) if insider_pct > 0 else 0.0
    w_retail = max(3.0, 100.0 - w_inst - w_insider)

    short_meter_col = "#F43F5E" if hazard_level == "EXTREME" else ("#FF6B00" if hazard_level == "ELEVATED" else ("#FB923C" if hazard_level == "MODERATE" else "#10B981"))
    mom_sign = "+" if short_mom >= 0 else ""
    mom_col = "#F43F5E" if short_mom >= 5.0 else ("#10B981" if short_mom <= -5.0 else "#94A3B8")

    sh_short_str = _format_shares_count(shares_short)
    sh_float_str = _format_shares_count(float_shares)
    sh_out_str = _format_shares_count(shares_out)

    dtc_col = "#F43F5E" if dtc >= 5.0 else ("#FF6B00" if dtc >= 3.8 else ("#FB923C" if dtc >= 2.5 else "#10B981"))
    dtc_status = "CRITICAL COIL (>5d)" if dtc >= 5.0 else ("ELEVATED COIL (>3.8d)" if dtc >= 3.8 else "NORMAL LIQUIDITY")
    pc_col = "#F43F5E" if pc_13f >= 1.25 else ("#10B981" if pc_13f <= 0.72 else "#38BDF8")

    insider_legend_html = f'<span class="float-legend-item"><span class="float-legend-dot" style="background: #64748B;"></span><span>Insiders: <b style="color: #CBD5E1; font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">{insider_pct:.1f}%</b></span></span>' if insider_pct > 0 else ''
    insider_seg_html = f'<div class="float-bar-seg" style="width: {w_insider:.1f}%; background: #475569;" title="Insiders: {insider_pct:.1f}%"></div>' if w_insider > 0 else ''

    hdr_right_label = (
        f'<span>Short Float Borrow Pressure: <b style="color: {short_meter_col}; font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">{short_pct:.2f}%</b></span>'
        if has_true_short
        else f'<span>13F Institutional Put/Call Hedge: <b style="color: {pc_col}; font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">{pc_13f:.2f}x ({hedge_regime})</b></span>'
    )
    legend_right_html = (
        f'<span>Loan Float: <b style="font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">{short_pct:.2f}%</b> of Float ({sh_short_str} shs)</span>'
        if has_true_short
        else f'<span>Free Float: <b style="font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">{free_float_pct:.1f}%</b> (Lockup {inst_lockup_pct:.1f}%)</span>'
    )

    if has_true_short:
        tiles_html = (
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-arrow-down-short-wide" style="color: {short_meter_col};"></i> Short Float %</div>'
            f'<div class="float-metric-val" style="color: {short_meter_col}; font-variant-numeric: tabular-nums;">{short_pct:.2f}%</div>'
            f'<div class="float-metric-sub">MoM: <span style="color: {mom_col}; font-weight: 700;">{mom_sign}{short_mom:.1f}%</span> vs prior mo</div>'
            f'</div>'
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-clock-rotate-left" style="color: {dtc_col};"></i> Days-To-Cover (DTC)</div>'
            f'<div class="float-metric-val" style="color: {dtc_col}; font-variant-numeric: tabular-nums;">{dtc:.1f} <span style="font-size: 0.80rem; color: #94A3B8;">Days</span></div>'
            f'<div class="float-metric-sub"><span style="color: {dtc_col}; font-weight: 700;">{dtc_status}</span></div>'
            f'</div>'
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-vault" style="color: #FB923C;"></i> Shares Short vs Float</div>'
            f'<div class="float-metric-val" style="color: #E2E8F0; font-variant-numeric: tabular-nums;">{sh_short_str}</div>'
            f'<div class="float-metric-sub">Tradable Float: <b style="color: #CBD5E1;">{sh_float_str}</b></div>'
            f'</div>'
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-scale-balanced" style="color: #10B981;"></i> Inst Long vs Short</div>'
            f'<div class="float-metric-val" style="color: #10B981; font-variant-numeric: tabular-nums;">{round(inst_pct / max(0.1, short_pct), 1):.1f}x</div>'
            f'<div class="float-metric-sub">{"Whales Dominate Tape" if inst_pct >= 50 else "Balanced Order Book"}</div>'
            f'</div>'
        )
    else:
        tiles_html = (
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-shield-halved" style="color: {pc_col};"></i> 13F Put/Call Hedge</div>'
            f'<div class="float-metric-val" style="color: {pc_col}; font-variant-numeric: tabular-nums;">{pc_13f:.2f}x</div>'
            f'<div class="float-metric-sub"><span style="color: {pc_col}; font-weight: 700;">{hedge_regime}</span></div>'
            f'</div>'
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-layer-group" style="color: #38BDF8;"></i> Free Float %</div>'
            f'<div class="float-metric-val" style="color: #E2E8F0; font-variant-numeric: tabular-nums;">{free_float_pct:.1f}%</div>'
            f'<div class="float-metric-sub">Tradable: <b style="color: #CBD5E1;">{sh_float_str}</b></div>'
            f'</div>'
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-lock" style="color: #FB923C;"></i> Float Lockup %</div>'
            f'<div class="float-metric-val" style="color: #FB923C; font-variant-numeric: tabular-nums;">{inst_lockup_pct:.1f}%</div>'
            f'<div class="float-metric-sub">Outstanding: <b style="color: #CBD5E1;">{sh_out_str}</b></div>'
            f'</div>'
            f'<div class="float-metric-tile">'
            f'<div class="float-metric-lbl"><i class="fa-solid fa-building-columns" style="color: #10B981;"></i> 13F Inst Control</div>'
            f'<div class="float-metric-val" style="color: #10B981; font-variant-numeric: tabular-nums;">{inst_pct:.1f}%</div>'
            f'<div class="float-metric-sub">{"Institutions Dominate" if inst_pct >= 50 else "Mixed Ownership"}</div>'
            f'</div>'
        )

    return (
        f'<div class="float-topology-card">'
        f'<div class="float-topology-hdr">'
        f'<div class="float-topology-title">'
        f'<i class="fa-solid fa-chart-pie" style="color: #FF6B00;"></i>'
        f'<span>EQUITY FLOAT TOPOLOGY &amp; 13F HEDGE PRESSURE</span>'
        f'<span style="font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums; font-size: 0.72rem; color: #CBD5E1; background: rgba(255,255,255,0.05); padding: 2px 7px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);">{sym}</span>'
        f'<span style="font-size: 0.70rem; color: #64748B; font-weight: 500; font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">Float: {sh_float_str} shs &bull; Out: {sh_out_str}</span>'
        f'</div>'
        f'<div class="squeeze-hazard-pill {hazard_class}">{hazard_icon} <span>{hazard_badge}</span></div>'
        f'</div>'
        f'<div style="margin-bottom: 6px;">'
        f'<div style="display: flex; justify-content: space-between; font-size: 0.67rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">'
        f'<span>Float Capital Stack (Ownership Distribution)</span>'
        f'{hdr_right_label}'
        f'</div>'
        f'<div class="float-bar-track">'
        f'<div class="float-bar-seg" style="width: {w_inst:.1f}%; background: linear-gradient(90deg, #EA580C 0%, #FF6B00 100%);" title="Institutional Long: {inst_pct:.1f}%"></div>'
        f'<div class="float-bar-seg" style="width: {w_retail:.1f}%; background: linear-gradient(90deg, #475569 0%, #94A3B8 100%);" title="Public / Retail Float: {retail_pct:.1f}%"></div>'
        f'{insider_seg_html}'
        f'</div></div>'
        f'<div class="float-legend-row">'
        f'<div style="display: flex; gap: 14px; flex-wrap: wrap; align-items: center;">'
        f'<span class="float-legend-item"><span class="float-legend-dot" style="background: #FF6B00;"></span><span>Institutions Long: <b style="color: #E2E8F0; font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">{inst_pct:.1f}%</b></span></span>'
        f'<span class="float-legend-item"><span class="float-legend-dot" style="background: #94A3B8;"></span><span>Public / Retail: <b style="color: #E2E8F0; font-family: \'JetBrains Mono\', monospace; font-variant-numeric: tabular-nums;">{retail_pct:.1f}%</b></span></span>'
        f'{insider_legend_html}'
        f'</div>'
        f'<div style="display: flex; align-items: center; gap: 6px;">'
        f'<span class="float-legend-item" style="color: {short_meter_col}; font-weight: 700;">'
        f'<i class="fa-solid fa-fire" style="font-size: 0.70rem;"></i>'
        f'{legend_right_html}'
        f'</span></div></div>'
        f'<div class="float-grid-4">'
        f'{tiles_html}'
        f'</div>'
        f'<div class="float-collar-banner">'
        f'<div style="font-size: 1.1rem; color: #FF6B00; flex-shrink: 0;">'
        f'<i class="fa-solid fa-shield-halved"></i></div>'
        f'<div><b style="color: #FB923C; font-weight: 800; letter-spacing: 0.02em;">COLLAR PUT &amp; DERIVATIVES PRESCRIPTION:</b>'
        f'<span style="color: #E2E8F0; margin-left: 4px;">{collar_advice}</span></div>'
        f'</div></div>'
    )

