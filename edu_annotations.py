"""
Progressive Educational Annotations ("Learn Mode": Beginner -> Intermediate -> Desk Pro)
========================================================================================
Renders compact, closed-by-default Obsidian frosted-glass <details> drawers anchored to
live screen telemetry so users learning options, macro, and microstructure can build real
desk intuition without cluttering the terminal or triggering Streamlit reruns.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st


def is_learn_mode() -> bool:
    """Return True when progressive educational drawers are enabled."""
    if "learn_mode" not in st.session_state:
        qp_learn = str(st.query_params.get("learn", "") or "").strip().lower()
        if qp_learn in ("0", "false", "off", "no"):
            st.session_state["learn_mode"] = False
        else:
            st.session_state["learn_mode"] = True
    return bool(st.session_state.get("learn_mode", True))


def _esc(val: Any) -> str:
    return _html.escape(str(val if val is not None else ""), quote=True)


def _num(ctx: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        v = ctx.get(key, default)
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _build_topic(topic_key: str, ctx: Dict[str, Any]) -> Optional[Tuple[str, str, str, str, str, str]]:
    """
    Returns (title, live_readout, beginner_html, intermediate_html, pro_html, rule_of_thumb)
    for the requested topic_key using live context telemetry.
    """
    if topic_key == "macro_regime":
        vix_r = _num(ctx, "vix_ratio", 0.94)
        cred_z = _num(ctx, "credit_z", 0.0)
        tnx = _num(ctx, "tnx_yield", 4.25)
        cap = int(round(_num(ctx, "exposure_cap_pct", 100)))
        reg = str(ctx.get("regime_label", "MACRO EQUILIBRIUM"))

        vix_msg = (
            f"<b>{_esc(f'{vix_r:.3f}x')}</b> (<b>Backwardation Stress</b>: near-term panic is higher than 3-month fear — keep sizes small)"
            if vix_r >= 1.0 else
            f"<b>{_esc(f'{vix_r:.3f}x')}</b> (<b>Contango Calm</b>: normal upward-sloping fear curve — friendly for directional buyers)"
        )
        cred_msg = (
            f"Credit Z is <b>{_esc(f'{cred_z:+.2f}σ')}</b> (junk bonds lagging Treasuries — credit tightening)"
            if cred_z < -0.5 else
            f"Credit Z is <b>{_esc(f'{cred_z:+.2f}σ')}</b> (corporate bond risk appetite is calm)"
        )
        live = f"Regime: {_esc(reg)} · Exposure Cap: {cap}% · VIX Term: {vix_r:.3f}x"
        beg = (
            "Before picking any stock, check the <b>weather outside</b>. "
            "<b>VIX Term</b> compares short-term fear (VIX) vs 3-month fear (VIX3M); "
            "<b>10Y Yield</b> is the market's borrowing rate; and <b>Exposure Cap</b> tells you how much of your normal bet size is safe today."
        )
        inter = (
            f"Live check: VIX Term is {vix_msg}. {cred_msg}. "
            f"The 10-Year Treasury at <b>{_esc(f'{tnx:.2f}%')}</b> sets the valuation gravity for high-multiple tech stocks."
        )
        pro = (
            "When VIX/VIX3M &ge; 1.00 (backwardation) and HYG/LQD Credit Z &lt; -0.50&sigma;, dealer correlation spikes toward 1.0, "
            "widening bid-ask spreads and steepening OTM put skew — shifting edge from Naked Calls to defined-risk Vertical Debit Spreads and smaller Exposure Caps."
        )
        thumb = f"Match your sizing to the Exposure Cap ({cap}%) before looking at any single stock chart."
        return ("Macro Weather & Exposure Cap", live, beg, inter, pro, thumb)

    if topic_key == "catalysts_5d":
        b_cnt = int(round(_num(ctx, "binary_event_count_5d", 0)))
        dte = int(round(_num(ctx, "recommended_dte", 35)))
        b_risk = str(ctx.get("binary_risk_level", "MODERATE"))
        bias_s = int(round(_num(ctx, "ai_bias_score", 0)))
        live = f"5D Binary Shield: {_esc(b_risk)} ({b_cnt} events) · AI Skew: {bias_s:+d}/±200 · {dte} DTE"
        beg = (
            "Big scheduled announcements (<b>Fed FOMC, CPI inflation, Jobs NFP, Earnings</b>) act like coin-flips that make option prices temporarily expensive before the news and cheaper right after."
        )
        inter = (
            f"There are <b>{b_cnt} major catalysts</b> in the next 5 trading days (Shield: <b>{_esc(b_risk)}</b>). "
            f"Because option sellers hike prices ahead of known news, owning <b>{dte} DTE</b> (Days to Expiration) protects you from suffering a sudden time/volatility wipeout."
        )
        pro = (
            "Event variance creates localized front-month implied volatility kinks (term-structure backwardation). "
            "Once the event clears, front-month Vega collapses (IV Crush), forcing dealers short puts to buy back delta (+Vanna flow) unless the headline breaks credit or guidance."
        )
        thumb = "Never buy short weekly options (<14 DTE) across high binary risk unless you intentionally want a coin-flip; use 30–45 DTE to ride the post-event drift."
        return ("5-Day Catalyst Rings & IV Crush Shield", live, beg, inter, pro, thumb)

    if topic_key == "elasticity_micro":
        sym = str(ctx.get("symbol", "TICKER"))
        z5 = _num(ctx, "z_score_5d", 0.0)
        beta_k = _num(ctx, "kalman_beta", _num(ctx, "beta", 1.15))
        hl = _num(ctx, "ou_half_life", 5.0)
        h_exp = _num(ctx, "hurst", 0.48)
        clv = _num(ctx, "clv", 0.0)
        rvol = _num(ctx, "rvol", 1.0)
        live = f"{_esc(sym)} · Dual Z {z5:+.2f}σ · Kalman β {beta_k:.2f} · τ½ {hl:.1f}d · Hurst {h_exp:.2f}"
        beg = (
            "Think of a stock price like a <b>rubberband tied to its 20-day volume-weighted average (VWMA-20)</b>. "
            "Negative <b>Dual Z</b> means it stretched down (potential bounce); positive <b>Dual Z</b> means it stretched up (potential pullback)."
        )
        inter = (
            f"<b>{_esc(sym)}</b> sits at <b>{z5:+.2f}&sigma;</b> with a <b>Kalman Beta of {beta_k:.2f}</b> (how fast it moves vs its sector ETF). "
            f"<b>O-U Half-Life ({hl:.1f}d)</b> estimates how many trading days it takes to snap halfway back; "
            f"<b>CLV ({clv:+.2f})</b> &amp; <b>RVOL ({rvol:.2f}x)</b> check whether big buyers are actually stepping in near the close."
        )
        pro = (
            "Dual Z combines Keltner/Bollinger absolute stretch with a 2D state-space Kalman residual vs benchmark. "
            "Hurst H &lt; 0.47 confirms sub-diffusive mean reversion (Elastic Spring), whereas H &gt; 0.54 signals trend persistence where counter-trend fades bleed against momentum."
        )
        thumb = "Wait for the hook: negative Z + rising CLV (&gt; +0.20) on solid RVOL (&gt; 1.1x) separates dip absorption from catching a falling knife."
        return ("Rubberband Elasticity, Kalman Beta & Microstructure", live, beg, inter, pro, thumb)

    if topic_key == "conviction_5pillar":
        s200 = int(round(_num(ctx, "conviction_score_200", 0)))
        tier = str(ctx.get("conviction_tier", "WATCH"))
        syn = bool(ctx.get("synergy_unlocked", False))
        gate = _num(ctx, "regime_gate_mult", 1.0)
        live = f"Score: {s200:+d}/±200 ({_esc(tier)}) · Synergy: {'UNLOCKED' if syn else 'CAPPED'} · Gate {gate:.2f}x"
        beg = (
            "The <b>-200 to +200 score</b> combines 5 independent report cards into one number: "
            "positive scores lean <b>CALL (up)</b>, negative lean <b>PUT (down)</b>, and scores inside <b>-35 to +35</b> mean sit on your hands."
        )
        inter = (
            f"Live reading is <b>{s200:+d} ({_esc(tier)})</b> with a <b>{gate:.2f}x</b> Macro/Solvency gate. "
            "Watch whether all 5 pillars point the same direction — if Flow or Macro fights Elasticity, size down."
        )
        pro = (
            "Five orthogonalized sub-scores (Elasticity [-65..65], Kinetic [-45..45], Whale/Dealer Flow [-40..40], Surface Convexity [-30..30], Regime/Solvency [-20..20]) "
            "pass through a smooth tanh compression unless 4+ pillars align with positive net EV, low spread friction, and &gt;14d earnings clearance (Synergy Ramp)."
        )
        thumb = "Best risk-adjusted entries live at |Score| &ge; 70 (Tactical Edge) and &ge; 110 (High Conviction) with clear earnings runway."
        return ("How the 5-Pillar (-200..+200) Conviction Score Works", live, beg, inter, pro, thumb)

    if topic_key == "options_surface":
        iv = _num(ctx, "opra_iv", 35.0)
        hv = _num(ctx, "hv20", 35.0)
        vrp = iv - hv
        gex = _num(ctx, "net_gex_m", 0.0)
        gflip = _num(ctx, "gamma_flip_strike", 0.0)
        vanna = _num(ctx, "net_vanna_m", 0.0)
        vrent = _num(ctx, "variance_rent_ratio", 1.0)
        prefer_sp = bool(ctx.get("prefer_spread", False))
        live = f"IV {iv:.1f}% vs HV {hv:.1f}% (VRP {vrp:+.1f}v) · Net GEX {gex:+.1f}M · Rent {vrent:.2f}x"
        beg = (
            "<b>Delta (0.45–0.65)</b> acts like owning ~50 shares of stock at a fraction of the cash; "
            "<b>Theta</b> is the daily rent you pay to hold the contract; and <b>IV</b> is whether options are currently priced cheap or expensive."
        )
        inter = (
            f"Options cost <b>{iv:.1f}% IV</b> vs <b>{hv:.1f}% realized movement</b> (VRP <b>{vrp:+.1f} pts</b>). "
            f"<b>Variance Rent ({vrent:.2f}x)</b> &gt; 1.0 means the stock normally moves enough each day to pay its Theta bill. "
            f"Recommended structure right now: <b>{'Vertical Debit Spread (sell a wing to cut cost & IV crush)' if prefer_sp else 'Naked High-Delta Single Leg'}</b>."
        )
        pro = (
            f"Dealer Net GEX (<b>{gex:+.1f}M/1%</b>, Flip <b>${gflip:.2f}</b>): positive GEX suppresses realized vol via dealer sell-rips/buy-dips hedging; negative GEX accelerates moves. "
            f"Net Vanna (<b>{vanna:+.1f}M/vol</b>) measures forced dealer share buying per 1-vol IV drop, while SVI 25&Delta; skew calibrates directional wing richness."
        )
        thumb = "When IV is much higher than HV (VRP &ge; +8v) or Vol Rank &ge; 72%, favor a Vertical Debit Spread so you aren't overpaying for expensive Vega."
        return ("High-Delta Greeks, GEX/Vanna & Naked vs Spread", live, beg, inter, pro, thumb)

    if topic_key == "fundamentals_float":
        alt_z = _num(ctx, "altman_z", 3.0)
        pio = int(round(_num(ctx, "piotroski_score", 6)))
        sh_pct = _num(ctx, "short_pct", 0.0)
        is_etf = bool(ctx.get("is_etf", False))
        live = "ETF Basket Shield" if is_etf else f"Altman Z {alt_z:.2f} · Piotroski {pio}/9 · Short Float {sh_pct:.1f}%"
        beg = (
            "A cheap stock can stay cheap if the company is running out of cash ('value trap'). "
            "<b>Altman Z</b> checks bankruptcy safety, and <b>Piotroski F-Score (0–9)</b> grades recent financial health."
        )
        inter = (
            "ETFs diversify away single-company bankruptcy/earnings risk across dozens of holdings."
            if is_etf else
            f"<b>Altman Z = {alt_z:.2f}</b> (&gt; 3.0 = Fortress, &lt; 1.8 = Distress zone) and <b>Piotroski = {pio}/9</b> (&ge; 6 = healthy cash flow momentum). "
            f"Short Float ({sh_pct:.1f}%) tracks bearish crowding that can fuel sharp short-covering bounces."
        )
        pro = (
            "Fundamental solvency gates distinguish Track A/B mean-reversion (where institutional buyers step into liquidity vacuums) from Track C structural shorts "
            "burdened by &lt;4 quarters cash runway, ATM equity dilution walls, and negative free-cash-flow yield."
        )
        thumb = "Never buy Calls on an unhedged single-name distress trap (Altman Z &lt; 1.5); strong balance sheets snap back cleanly."
        return ("Solvency Shield (Altman Z, Piotroski & Float)", live, beg, inter, pro, thumb)

    if topic_key == "cross_asset_macro":
        rot = str(ctx.get("rotation_badge", "MACRO ROTATION"))
        sm_score = int(round(_num(ctx, "smart_money_score", 50)))
        live = f"{_esc(rot)} · Smart Money Score {sm_score}/100"
        beg = (
            "Money constantly flows between <b>Risk Assets</b> (Tech, Small Caps, Bitcoin) and <b>Safe Havens</b> (Treasuries TLT, Gold GLD, US Dollar UUP). "
            "The compass shows where big funds are rotating right now."
        )
        inter = (
            f"Rotation reads <b>{_esc(rot)}</b>. Watch the top-left <b>Snapback Ignition</b> quadrant (oversold below 20D VWMA, hooking upward) for fresh Call leaders, "
            f"while <b>Smart Money ({sm_score}/100)</b> blends live volume accumulation, Form 4 insider buys, and 13F institutional filings."
        )
        pro = (
            "Cross-asset factor thrust (Risk Thrust minus Haven Thrust) detects liquidity expansion or offshore USD funding tightening before equity sector dispersion shows up in earnings revisions. "
            "13F QoQ option delta pairs slow quarterly holdings with live dollar-volume-weighted CLV and OPRA unusual sweeps."
        )
        thumb = "When TLT, GLD, and UUP all lead the compass simultaneously, treat equity bounces as tactical trades rather than long holds."
        return ("Cross-Asset Rotation Compass & 13F Smart Money", live, beg, inter, pro, thumb)

    if topic_key == "ev_kelly_backtest":
        ev = _num(ctx, "net_ev_pct", 0.0)
        win = _num(ctx, "bayesian_win_prob_pct", _num(ctx, "empirical_win_rate_pct", 55.0))
        kelly = _num(ctx, "quarter_kelly_pct", 0.0)
        spr = _num(ctx, "spread_friction_pct", 6.0)
        t_st = _num(ctx, "edge_t_stat", 0.0)
        live = f"5D Net EV {ev:+.1f}% · Win Prob {win:.0f}% · ¼-Kelly {kelly:.1f}% · Spread {spr:.1f}%"
        beg = (
            "<b>Expected Value (EV%)</b> estimates your average profit or loss over many similar trades <i>after</i> paying bid-ask spread fees. "
            "<b>Quarter-Kelly (%)</b> tells you what share of your account to risk so a cold streak can't blow you up."
        )
        inter = (
            f"Backtested 5Y analogs show a <b>{win:.0f}% Bayesian win probability</b> and <b>{ev:+.1f}% Net EV</b> after <b>{spr:.1f}%</b> spread slippage, "
            f"prescribing <b>{kelly:.1f}%</b> of equity (def-adjusted t-stat <b>{t_st:.2f}</b>)."
        )
        pro = (
            "Net EV integrates American CRR repricing across 5 empirical 5D close quantiles (q10..q90) with spot-vol leverage beta (-0.40) and VRP mean-reversion, "
            "charging 0.25&times; bid-ask entry+exit slippage. Continuous Quarter-Kelly (0.25 &middot; E[R]/Var[R], capped at 6%) and deflated t-stats prevent overfitting noisy small-N samples."
        )
        thumb = "Demand Net EV &gt; +2.5% and Spread Friction &lt; 15%; if Quarter-Kelly says 0%, pass on the trade — there's always another setup."
        return ("5Y Empirical Excursion, Net EV & Quarter-Kelly Sizing", live, beg, inter, pro, thumb)

    if topic_key == "schwab_ticket":
        sym = str(ctx.get("symbol", "NVDA"))
        strat = str(ctx.get("strategy", "SINGLE_LEG"))
        dte = int(round(_num(ctx, "dte", 35)))
        spr_pct = _num(ctx, "spread_pct", 4.0)
        be_pct = _num(ctx, "be_pct", 0.0)
        theta_d = _num(ctx, "daily_theta", 0.0)
        live = f"{_esc(sym)} · {'Vertical Spread' if 'SPREAD' in strat else 'Single Leg'} · {dte} DTE · Spread {spr_pct:.1f}%"
        beg = (
            "Always trade with a <b>LIMIT</b> order near the <b>Mid price</b> (halfway between Bid and Ask) instead of hitting Market — "
            "and check your <b>Max Risk</b> and <b>Breakeven</b> before clicking Transmit."
        )
        inter = (
            f"Your <b>Breakeven</b> requires {_esc(sym)} to move <b>{be_pct:+.1f}%</b> by expiration, while time decay costs <b>${abs(theta_d):.2f}/day</b>. "
            f"Bid-Ask spread is <b>{spr_pct:.1f}%</b> — bid slightly below Mid first on liquid names to save slippage."
        )
        pro = (
            "Debit Vertical Spreads (Long K1 / Short K2) cap max loss at Net Debit while neutralizing excessive Vega and cutting daily Theta bleed when IV Rank is elevated; "
            "Single-Leg High-Delta (0.45–0.65&Delta;) preserves uncapped convex gamma acceleration in calm contango regimes."
        )
        thumb = "Know both exits before entering: take profits into your 1–5D target zone and cut fast if the Hard Stock Invalidation level breaks."
        return ("Schwab Practice Ticket & Execution Mechanics", live, beg, inter, pro, thumb)

    return None


def render_edu_drawer(topic_key: str, live_ctx: Optional[Dict[str, Any]] = None, compact: bool = False) -> None:
    """
    Renders a sleek, closed-by-default Obsidian <details> educational drawer if Learn Mode is ON.
    All dynamic strings are escaped via html.escape to prevent HTML injection.
    """
    if not is_learn_mode():
        return

    built = _build_topic(topic_key, live_ctx or {})
    if not built:
        return
    title, live, beg, inter, pro, thumb = built

    pad_cls = " rm-edu-compact" if compact else ""
    html_block = "".join(line.strip() for line in f"""
    <details class="rm-edu-drawer{pad_cls}">
      <summary>
        <span class="rm-edu-summary-left">
          <span class="rm-edu-pill">🎓 LEARN</span>
          <span class="rm-edu-title">{_esc(title)}</span>
        </span>
        <span class="rm-edu-live">{live}</span>
      </summary>
      <div class="rm-edu-body">
        <div class="rm-edu-grid">
          <div class="rm-edu-tier">
            <div class="rm-edu-tier-tag is-beg">Level 1 · Plain English</div>
            <div class="rm-edu-tier-txt">{beg}</div>
          </div>
          <div class="rm-edu-tier">
            <div class="rm-edu-tier-tag is-int">Level 2 · Reading Live Tape</div>
            <div class="rm-edu-tier-txt">{inter}</div>
          </div>
          <div class="rm-edu-tier">
            <div class="rm-edu-tier-tag is-pro">Level 3 · Desk Quantitative</div>
            <div class="rm-edu-tier-txt">{pro}</div>
          </div>
        </div>
        <div class="rm-edu-thumb"><span>💡 Rule of Thumb:</span> {thumb}</div>
      </div>
    </details>
    """.splitlines())
    st.markdown(html_block, unsafe_allow_html=True)
