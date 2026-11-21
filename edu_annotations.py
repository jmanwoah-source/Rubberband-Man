"""
Progressive Educational Annotations ("Learn Mode": Beginner -> Intermediate -> Desk Pro)
========================================================================================
Renders compact, closed-by-default Obsidian frosted-glass <details> drawers anchored to
live screen telemetry so users learning options, macro, and microstructure can build real
desk intuition without cluttering the terminal or triggering Streamlit reruns.
"""
from __future__ import annotations

import hashlib
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

    if topic_key == "scanner_matrix":
        sec = str(ctx.get("sector", "Semiconductors"))
        top_sym = str(ctx.get("top_symbol", "NVDA"))
        ev_pct = _num(ctx, "net_ev_pct", 4.2)
        win_pct = _num(ctx, "win_rate_pct", 60.0)
        n_ana = int(round(_num(ctx, "sample_n", 40)))
        vrp = _num(ctx, "vrp_pts", 2.0)
        pref_sp = bool(ctx.get("prefer_spread", False))
        live = f"{_esc(sec)} · #{_esc(top_sym)} · 5D EV {ev_pct:+.1f}% · Hit {win_pct:.0f}% (n={n_ana}) · VRP {vrp:+.1f}v"
        beg = (
            "Each row ranks a stock in this sector from <b>#1 down</b>. Higher <b>Conviction (-200..+200)</b> + a positive <b>5D EV%</b> and "
            "<b>Hit Rate %</b> means history and today's options market agree on a clean 1–5 day bounce (CALL) or fade (PUT)."
        )
        inter = (
            f"<b>{_esc(top_sym)}</b> posts a <b>{win_pct:.0f}% 5Y win rate (n={n_ana} similar stretches)</b> and <b>{ev_pct:+.1f}% net EV</b>. "
            f"<b>VRP ({vrp:+.1f}v)</b> shows whether options cost more than recent stock movement — suggesting <b>{'Vertical Spread' if pref_sp else 'Naked Single-Leg'}</b>."
        )
        pro = (
            "Each row screens orthogonalized -200..+200 scores against OPRA bid-ask spread friction, 5Y CRR repricing over empirical q10..q90 closes, and binary earnings gates. "
            "VRP &ge; +6.5v triggers spread structure substitution to immunize long-gamma entries against post-event Vega compression."
        )
        thumb = "Skip weak scores below &plusmn;35 or crowded negative-EV rows; concentrate on top-3 ranked names in a constructive sector."
        return ("Reading the Scanner Rows & Net EV", live, beg, inter, pro, thumb)

    if topic_key == "trade_ticket":
        sym = str(ctx.get("symbol", "NVDA"))
        delta_v = _num(ctx, "delta", 0.52)
        mid_v = _num(ctx, "mid_price", 3.50)
        tgt_p = _num(ctx, "target_price", 105.0)
        stp_p = _num(ctx, "stop_price", 96.0)
        kelly = _num(ctx, "quarter_kelly_pct", 2.5)
        spr = _num(ctx, "spread_pct", 3.5)
        live = f"{_esc(sym)} · Δ {delta_v:+.2f} · Mid ${mid_v:.2f} · Target ${tgt_p:.2f} · Stop ${stp_p:.2f} · ¼-Kelly {kelly:.1f}%"
        beg = (
            "Your <b>Trade Ticket</b> gives all four numbers before you risk a dollar: what contract to buy (<b>Strike &amp; DTE</b>), "
            "what price to bid (<b>Mid Limit</b>), where to take profit (<b>+1&sigma; Target</b>), and where you admit you are wrong (<b>Hard Stop</b>)."
        )
        inter = (
            f"On <b>{_esc(sym)}</b>, <b>Delta {delta_v:+.2f}</b> gives stock-like speed while paying <b>{spr:.1f}% bid-ask spread</b>. "
            f"Exit into <b>${tgt_p:.2f}</b> on the rubberband snapback, or cut immediately if shares close below <b>${stp_p:.2f}</b>; <b>¼-Kelly ({kelly:.1f}%)</b> caps account size."
        )
        pro = (
            "Mid-limit execution targets inside-NBBO fills so entry slippage stays below 0.5x spread friction. "
            "Hard Stock Invalidation marks 2&times; ATR/VWMA structural breakdown where the mean-reversion O-U hypothesis flips to momentum trend risk."
        )
        thumb = "Never move your Hard Invalidation stop lower mid-trade; respect ¼-Kelly sizing so a single stop-out stays routine."
        return ("Trade Ticket: Mid Limit, +1σ Target & Hard Stop", live, beg, inter, pro, thumb)

    if topic_key == "trade_anatomy":
        sym = str(ctx.get("symbol", "NVDA"))
        spot = _num(ctx, "spot", 100.0)
        vwma = _num(ctx, "vwma20", spot)
        strike = _num(ctx, "strike", spot)
        be_p = _num(ctx, "breakeven", spot)
        tgt = _num(ctx, "target_price", spot * 1.05)
        stp = _num(ctx, "stop_price", spot * 0.95)
        cw = _num(ctx, "call_wall", 0.0)
        pw = _num(ctx, "put_wall", 0.0)
        gflip = _num(ctx, "gamma_flip", 0.0)
        cw_txt = f" · Call Wall ${cw:.2f}" if cw > 0 else ""
        pw_txt = f" · Put Wall ${pw:.2f}" if pw > 0 else ""
        gf_txt = f" · γ-Flip ${gflip:.2f}" if gflip > 0 else ""
        live = f"{_esc(sym)} · Stop ${stp:.2f} · Spot ${spot:.2f} · BE ${be_p:.2f} · Target ${tgt:.2f}{cw_txt}{gf_txt}"
        beg = (
            "This horizontal map puts <b>every key stock price on one ruler</b>: the <b>blue shaded cloud</b> shows where 5 years of history says the stock usually lands in 5 days, "
            "while markers show your <b>Hard Stop</b>, <b>Today's Price</b>, <b>Option Strike</b>, <b>Breakeven</b>, and <b>Profit Target</b>."
        )
        inter = (
            f"If your <b>Target (${tgt:.2f})</b> and <b>Breakeven (${be_p:.2f})</b> sit comfortably inside the shaded <b>P25–P75 historical core zone</b>, "
            f"history supports the move — if <b>Strike (${strike:.2f})</b> sits beyond <b>P90</b>{cw_txt or pw_txt}, you need a rare tail breakout to get paid."
        )
        pro = (
            "Overlaying empirical 5D quantile corridors (P10–P90 / P25–P75) onto OPRA dealer Put/Call OI walls and Net Gamma Flip exposes structural pin risk: "
            "high Call Wall OI above spot acts as dealer-hedged resistance capping upside MFE into expiration."
        )
        thumb = "Best setups have VWMA-20 and your Target tucked inside the P25–P75 corridor without slamming straight into an opposite dealer wall."
        return ("Reading the Trade Anatomy & Probability Corridor", live, beg, inter, pro, thumb)

    if topic_key == "journal_audit":
        snap_date = str(ctx.get("snapshot_date", "Latest"))
        win_rt = _num(ctx, "win_rate_pct", 60.0)
        avg_ret = _num(ctx, "avg_dir_pct", 1.2)
        avg_roi = _num(ctx, "avg_opt_roi_pct", 8.5)
        n_recs = int(round(_num(ctx, "count", 20)))
        live = f"{_esc(snap_date)} ({n_recs} picks) · Dir Win {win_rt:.0f}% · Avg 5D {avg_ret:+.2f}% · Est Opt ROI {avg_roi:+.1f}%"
        beg = (
            "Every trading morning the scanner locks its Top-5 picks in a permanent notebook so nobody can cherry-pick winners later. "
            "<b>T+5d Dir</b> shows where the stock closed 5 trading days later, and <b>MFE</b> shows the biggest favorable move along the way."
        )
        inter = (
            f"Across <b>{n_recs} audited signals</b> on {_esc(snap_date)}, directional win rate is <b>{win_rt:.0f}%</b> with <b>{avg_ret:+.2f}%</b> average move and <b>{avg_roi:+.1f}% estimated option ROI</b>. "
            "Compare <b>MFE vs Close</b> to learn whether taking partials on Day 2–3 beats holding to Day 5."
        )
        pro = (
            "Forward T+1..T+5 path auditing prevents look-ahead leakage and quantifies MFE-to-Close decay across Volatility Regimes. "
            "Systematic gaps where MFE &gt; Target while T+5d Close fades confirm mean-reversion overshoot exhaustion and calibrate profit-taking triggers."
        )
        thumb = "Judge any signal system by audited out-of-sample T+1..T+5 follow-through and target/stop hit ratio, never by cherry-picked single trades."
        return ("Auditing Top-5 Recommendations (T+5d Dir, MFE & Opt ROI)", live, beg, inter, pro, thumb)

    if topic_key == "mobile_hero":
        sym = str(ctx.get("symbol", "NVDA"))
        z5 = _num(ctx, "z_score_5d", 0.0)
        hl = _num(ctx, "ou_half_life", 4.5)
        s200 = int(round(_num(ctx, "conviction_score_200", 0)))
        cost = _num(ctx, "contract_cost", 350.0)
        be_p = _num(ctx, "breakeven", 100.0)
        live = f"{_esc(sym)} · {s200:+d} · Z {z5:+.2f}σ · τ½ {hl:.1f}d · BE ${be_p:.2f} · Risk ${cost:.0f}"
        beg = (
            "This Hero Card summarizes one high-conviction option setup in plain numbers: <b>Conviction</b> gives direction &amp; strength, "
            "<b>Risk</b> is the max dollars one contract can lose, and <b>BE</b> is the stock price needed at expiration to break even."
        )
        inter = (
            f"<b>{_esc(sym)}</b> shows <b>Dual Z {z5:+.2f}&sigma;</b> with a <b>{hl:.1f}-day Half-Life</b>. "
            f"Check that your <b>Max Risk (${cost:.0f}/ct)</b> fits a tiny slice of your account before tapping Simulate."
        )
        pro = (
            "Hero contract selection picks the liquid 30/45 DTE High-Delta (0.45–0.65Δ) cycle filtered by 5D binary shield clearance, "
            "balancing gamma responsiveness per dollar of Theta against empirical 5Y Bayesian hit probability."
        )
        thumb = "Always confirm 5D binary rings, Dual Z, and Max Risk $/ct on the card before staging a practice order."
        return ("Quick Guide: Hero Contract & 1-Tap Risk Check", live, beg, inter, pro, thumb)

    return None


def render_edu_drawer(
    topic_key: str,
    live_ctx: Optional[Dict[str, Any]] = None,
    compact: bool = False,
    align: str = "left",
) -> None:
    """
    Renders a sleek, low-profile obsidian pill (`◈` glyph + clickable L1/L2/L3 tabs inside)
    when Learn Mode is ON. All dynamic strings are escaped via html.escape. Zero JS or reruns.
    """
    if not is_learn_mode():
        return

    built = _build_topic(topic_key, live_ctx or {})
    if not built:
        return
    title, live, beg, inter, pro, thumb = built

    uid = hashlib.sha1(f"{topic_key}|{live}|{align}".encode("utf-8")).hexdigest()[:10]
    grp_name = f"rm-edu-{uid}"
    cls_list = ["rm-edu-drawer", "rm-edu-chip"]
    if compact:
        cls_list.append("rm-edu-compact")
    if align == "right":
        cls_list.append("rm-edu-right")
    cls_str = " ".join(cls_list)

    live_span = "" if compact else f'<span class="rm-edu-live">{live}</span>'

    html_block = "".join(line.strip() for line in f"""
    <div class="rm-edu-wrap{' is-right' if align == 'right' else ''}">
      <details class="{cls_str}">
        <summary>
          <span class="rm-edu-summary-left">
            <span class="rm-edu-glyph" aria-hidden="true">&#9672;</span>
            <span class="rm-edu-title">{_esc(title)}</span>
            <span class="rm-edu-lvl-dots">L1&middot;L2&middot;L3</span>
          </span>
          {live_span}
        </summary>
        <div class="rm-edu-body">
          <div class="rm-edu-tabs-wrap">
            <details class="rm-edu-level is-l1" name="{grp_name}" open>
              <summary><span class="rm-lvl-badge is-beg">L1</span> Plain English</summary>
              <div class="rm-edu-tier-txt">{beg}</div>
            </details>
            <details class="rm-edu-level is-l2" name="{grp_name}">
              <summary><span class="rm-lvl-badge is-int">L2</span> Live Tape</summary>
              <div class="rm-edu-tier-txt">{inter}</div>
            </details>
            <details class="rm-edu-level is-l3" name="{grp_name}">
              <summary><span class="rm-lvl-badge is-pro">L3</span> Desk Pro</summary>
              <div class="rm-edu-tier-txt">{pro}</div>
            </details>
          </div>
          <div class="rm-edu-thumb"><span>💡 Rule of Thumb:</span> {thumb}</div>
        </div>
      </details>
    </div>
    """.splitlines())
    st.markdown(html_block, unsafe_allow_html=True)
