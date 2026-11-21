"""
Rubberband Man - ASUS GX10 Qwen 3.8 & Gemini 2.5 Qualitative Arbiter
Synthesizes Dual-Coordinate Kinetic Elasticity (VWMA-20, ATR-14, O-U Half-Life, Hurst H),
FMP Pro Institutional Solvency (Real Altman Z-Score, Piotroski F-Score, Earnings Countdown),
6-Pillar 24/48H Macro Radar, and Karpathy Research Wiki Moat Intelligence into decisive
30-45 DTE Aggressive CALL or PUT Execution Blueprints.
"""

import os
import sys
from dotenv import load_dotenv
import rubberband_engine as rbe
import intel_bus_bridge as ibb
import llm_router

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()


def generate_options_thesis(candidate: dict, sector_name: str, benchmark_symbol: str, mode: str = "thesis") -> str:
    """
    Invokes the active AI Engine (ASUS GX10 Local Qwen 3.8 or Cloud Google Gemini 2.5)
    with institutional pre-prompts optimized for Qwen 3.8 + Karpathy Research Wiki integration.
    Modes supported:
      - 'thesis': Outright 30-45 DTE Call/Put Verdict + 1-5 Day Kinetic Edge + $1,000 Matrix
      - 'karpathy_moat': Karpathy Wiki Technological Moat, Material Breakthrough & Whale Bottleneck Audit
      - 'red_team': Adversarial failure-mode stress-test (Steel-man the opposing case)
      - 'catalyst': Deterministic Earnings Countdown, Macro 24/48H Alignment & IV Skew Defense
      - 'confluence': Multi-timeframe VWMA-20 / 50-DMA / 200-DMA & Hurst Regime Confluence
    """
    ticker = candidate["ticker"].upper()
    metrics = candidate["metrics"]
    fund = candidate["fundamentals"]
    news = candidate.get("news", [])
    profile = candidate.get("profile", {})

    # Check if ticker has a live Karpathy Research Wiki dossier on the GX10 Intel Bus
    intel_signals = ibb.read_intel_bus_signals()
    wiki_record = next((s for s in intel_signals if s.get("symbol") == ticker), None)
    if wiki_record:
        wiki_context = (
            f"- Karpathy Wiki Track: {wiki_record.get('track')} (Wiki Conviction Score: {wiki_record.get('wiki_score')}/100)\n"
            f"- Tier-1 Anchor Whale Customer: {wiki_record.get('parent_whale')}\n"
            f"- ATM Dilution / Shelf Overhang Risk: {wiki_record.get('dilution_risk')}\n"
            f"- Karpathy Wiki Breakthrough / Moat Hook: \"{wiki_record.get('thesis_hook')}\""
        )
    else:
        wiki_context = (
            f"- Company Profile Summary: {profile.get('description', 'US-traded technology & industrial innovator.')}\n"
            f"- Karpathy Wiki Directive: Evaluate {ticker}'s proprietary technological moat, material science breakthrough, or supply-chain bottleneck power."
        )

    # Pull 24/48H Macro Radar summary
    try:
        macro_radar = rbe.get_24_48h_market_direction_radar()
        macro_summary = (
            f"- 24/48H US Market Outlook: {macro_radar.get('signage_short')} ({macro_radar.get('probability_pct')}% Conviction)\n"
            f"- Expected Market Move: {macro_radar.get('expected_move')}\n"
            f"- Desk Directive: {macro_radar.get('options_directive')}"
        )
    except Exception:
        macro_summary = "- 24/48H Macro Outlook: Neutral / Balanced"

    news_text = "\n".join([f"- {n['title']} ({n['publishedDate']}): {n['text']}" for n in news]) if news else "No breaking headlines in the last 72h."

    sim = metrics.get("sim_1k", {})
    sim_contracts = sim.get("contracts", 1)
    sim_invested = sim.get("total_invested", 1000.0)
    sim_prem = sim.get("prem_per_share", 1.50)
    sim_cost_contract = sim.get("cost_per_contract", 150.0)
    sim_gain = sim.get("target_profit", 0.0)
    sim_roi = sim.get("target_roi_pct", 0.0)
    sim_loss = sim.get("stop_loss", 0.0)
    sim_loss_pct = sim.get("stop_loss_pct", 0.0)
    sim_rr = sim.get("sim_rr_ratio", metrics.get("rr_ratio", 2.0))

    vwma20 = metrics.get("vwma20", metrics.get("sma20", 0.0))
    dma50 = metrics.get("sma50") or profile.get("priceAvg50", "N/A")
    dma200 = metrics.get("sma200") or profile.get("priceAvg200", "N/A")
    z_score_val = metrics.get("z_score_5d", metrics.get("z_score", 0.0))
    z_abs_val = metrics.get("z_abs", z_score_val)
    z_rel_val = metrics.get("z_rel_5d", z_score_val)
    ou_hl = metrics.get("ou_half_life", 4.2)
    hurst_val = metrics.get("hurst", 0.45)
    yz_vol = metrics.get("realized_vol_30d", metrics.get("realized_vol", 35.0))
    vol_rank_val = metrics.get("vol_rank", 50.0)
    days_to_earn = metrics.get("days_to_earnings", 45)
    earn_date_str = metrics.get("earnings_date", "Clear (>35d)")
    bp = candidate.get("blueprint", {}) or {}
    conv_200 = int(metrics.get("conviction_score_200", bp.get("conviction_score_200", 0)) or 0)
    conv_tier = str(metrics.get("conviction_tier", bp.get("conviction_tier", "WATCH / DEVELOPING")))
    rec_dte = int(metrics.get("recommended_dte", bp.get("recommended_dte", 30)) or 30)
    dte_rationale = str(metrics.get("dte_rationale", bp.get("dte_rationale", f"Prescribed {rec_dte} DTE horizon.")))
    pillars = metrics.get("conviction_pillars", bp.get("conviction_pillars", {})) or {}

    if mode == "karpathy_moat":
        system_prompt = (
            "You are the Qwen 3.8 Chief Deep-Research Architect on an ASUS GX10 workstation, operating alongside the "
            "Karpathy Research Wiki. Your specialty is connecting deep technological moats, material science breakthroughs, "
            "and Tier-1 hyperscaler bottlenecks to explosive 1-to-5 day options re-pricings."
        )
        prompt = f"""
Conduct a Deep Karpathy Research Wiki Moat & 1-5 Day Catalyst Audit on {ticker} ({profile.get('companyName', ticker)}) in {sector_name} (Factor Benchmark: {benchmark_symbol}):

=== KARPATHY WIKI & ECOSYSTEM INTELLIGENCE ===
{wiki_context}

=== VERIFIED FMP PRO QUANTITATIVE & FUNDAMENTAL TELEMETRY ===
- Live Price: ${metrics.get('price', 0)} | Institutional Equilibrium (VWMA-20): ${vwma20:.2f}
- Dual-Coordinate Stretch: Effective Z = {z_score_val:+.2f}σ (Abs VWMA Z: {z_abs_val:+.2f}σ | Rel Factor Z: {z_rel_val:+.2f}σ)
- Kinetic Playbook: {metrics.get('playbook_type', 'MEAN_REVERSION')} ({metrics.get('velocity_status')})
- O-U Mean-Reversion Half-Life: {ou_hl:.1f} Trading Days | Hurst Exponent H = {hurst_val:.2f} ({metrics.get('statistical_regime')})
- FMP Pro Quality Score: {fund.get('fund_score', 50):.0f}/100 | Real Altman Z: {fund.get('altman_z')} | Piotroski F-Score: {fund.get('piotroski_score')}/9
- Real Revenue Growth: YoY {fund.get('rev_growth_yoy_pct', 0):+.1f}% | 3Y CAGR: {fund.get('rev_growth_3y_pct', 0):+.1f}% | Operating Margin: {fund.get('operating_margin_pct', 0):+.1f}%

=== RECENT HEADLINES ===
{news_text}

Deliver a crisp, high-conviction 4-part Karpathy Moat & Options Synthesis:
1. 🔬 TECHNOLOGICAL MOAT & MATERIAL BREAKTHROUGH: Define {ticker}'s core engineering monopoly, physical bottleneck, or IP moat—or expose if it is a commoditized mirage.
2. 🐋 WHALE SUPPLY-CHAIN LEVERAGE: Explain how capex/demand from Tier-1 whales (NVDA, TSM, MSFT, AMZN, Grid Utilities) transmits into {ticker}'s order book and why the current {z_score_val:+.2f}σ stretch / coil is mispriced.
3. ⚡ 1–5 DAY RE-RATING CATALYST: Why the combination of O-U Half-Life ({ou_hl:.1f}d), RVOL ({metrics.get('rvol')}x), and 4H CLV ({metrics.get('clv'):+.2f}) signals an imminent 1–5 day move to ${metrics.get('target_price', 0):.2f}.
4. 🎯 30–45 DTE CONVEXITY VERDICT: Exact {metrics.get('action')} execution at the ${metrics.get('recommended_strike', 0):.2f} strike ({metrics.get('otm_pct', 0):.1f}% OTM | Δ {metrics.get('estimated_delta', 0.28):+.2f}).
"""

    elif mode == "red_team":
        system_prompt = (
            "You are an objective, Staff-level quantitative risk auditor and adversarial red-team specialist running on the ASUS GX10. "
            "Stress-test trade proposals with rigorous evidence—distinguishing high-probability setups on fortress balance sheets from value traps."
        )
        prompt = f"""
Conduct a rigorous Adversarial Red-Team Audit on this 1-5 Day {metrics.get('action', 'BUY')} proposal for {ticker} ({sector_name}, Benchmark: {benchmark_symbol}):
- Signal: {metrics.get('action', 'BUY')} @ 30–45 DTE Strike ${metrics.get('recommended_strike', 0):.2f} (Live Price: ${metrics.get('price', 0)})
- Institutional VWMA-20 Equilibrium: ${vwma20:.2f} | 1–5D Target: ${metrics.get('target_price', 0):.2f} | Hard Stop: ${metrics.get('invalidation_price', 0):.2f}
- Dual-Coordinate Stretch: Effective Z = {z_score_val:+.2f}σ | O-U Half-Life: {ou_hl:.1f}d | Hurst H = {hurst_val:.2f}
- Multi-Timeframe Trend: 50-DMA: ${dma50} | 200-DMA: ${dma200}
- Kinetic Velocity & Microstructure: {metrics.get('velocity_status')} | 4H/1D CLV: {metrics.get('clv'):+.2f} | RVOL: {metrics.get('rvol')}x
- FMP Pro Solvency: Quality Score {fund.get('fund_score')}/100 | Real Altman Z: {fund.get('altman_z')} | Piotroski: {fund.get('piotroski_score')}/9 | Current Ratio: {fund.get('current_ratio')}x | FCF Yield: {fund.get('fcf_yield_pct')}%
- Upcoming Earnings Countdown: {days_to_earn} days ({earn_date_str})
- Greater Market 24/48H Context:
{macro_summary}

Recent News Headlines:
{news_text}

Deliver your Adversarial Stress-Test in 4 sections:
1. 🚨 ADVERSARIAL THREAT LEVEL: [CRITICAL RISK | ELEVATED RISK | CONTROLLED RISK] (Calibrate honestly using Altman Z {fund.get('altman_z')} and Piotroski {fund.get('piotroski_score')}/9).
2. ⚠️ TOP 3 FAILURE MECHANISMS (NEXT 1–5 DAYS): Specific macro, sector, or microstructure traps that could invalidate the move to ${metrics.get('target_price', 0):.2f}.
3. 📉 KNIFE-CATCH VS. INSTITUTIONAL ABSORPTION AUDIT: Audit CLV ({metrics.get('clv'):+.2f}), RVOL ({metrics.get('rvol')}x), and 200-DMA (${dma200}) positioning.
4. 🛡️ FINAL CAPITAL DEFENSE VERDICT: [DEPLOY FULL $1,000 | SIZE DOWN TO $500 | STAND DOWN] with exact trigger conditions.
"""

    elif mode == "catalyst":
        system_prompt = (
            "You are an elite equity derivatives volatility strategist specializing in 1-5 day event catalysts, FMP earnings calendars, and 30-45 DTE Vega/Vanna skew dynamics."
        )
        prompt = f"""
Audit the DETERMINISTIC EARNINGS COUNTDOWN, 24/48H MACRO ALIGNMENT & IV SKEW RISK for {ticker}:
- Direction: {metrics.get('action', 'BUY')} | 30–45 DTE Strike: ${metrics.get('recommended_strike', 0):.2f} ({metrics.get('otm_pct', 0):.1f}% OTM | Δ {metrics.get('estimated_delta', 0.28):+.2f})
- FMP Pro Verified Earnings Countdown: {days_to_earn} Days Away (Next Date: {earn_date_str} | Binary 7D Warning: {metrics.get('has_binary_earnings_7d', False)})
- Yang-Zhang 30D Realized Volatility: {yz_vol}% | 1-Year Volatility Rank: {vol_rank_val}%
- Options Regime: {metrics.get('options_regime')} ({metrics.get('options_regime_desc')})
- Greater Market 24/48H Forecast:
{macro_summary}

Recent Headlines:
{news_text}

Deliver a Volatility, Earnings & Macro Catalyst Report in 4 sections:
1. 📅 VERIFIED EARNINGS & BINARY EVENT WINDOW: Assess the {days_to_earn}-day earnings runway ({earn_date_str}) and whether pre-earnings IV expansion or post-event IV crush applies.
2. 📉 VEGA / VANNA SKEW DYNAMICS: With 1Y Vol Rank at {vol_rank_val}% and Yang-Zhang Vol at {yz_vol}%, explain how IV will behave over the next 1–5 days as {ticker} moves toward ${metrics.get('target_price', 0):.2f}.
3. 🌐 24/48H CROSS-ASSET MACRO ALIGNMENT: How Bonds, Credit Stress, Oil, Gold, Silver, and BTC impact this trade right now.
4. ⚡ EXECUTION TIMING DIRECTIVE: Immediate entry at market open, wait for 4H CLV hook, or switch to a vertical debit spread?
"""

    elif mode == "confluence":
        system_prompt = (
            "You are a Chief Quantitative Technician specializing in multi-timeframe institutional moving averages, VWMA-20 equilibrium, Ornstein-Uhlenbeck half-life, and Hurst exponent regimes."
        )
        prompt = f"""
Analyze the MULTI-TIMEFRAME TREND & HURST REGIME CONFLUENCE for {ticker} ({sector_name}):
- Current Price: ${metrics.get('price', 0)}
- 20-Day Volume-Weighted Equilibrium (VWMA-20): ${vwma20:.2f} (Effective Z: {z_score_val:+.2f}σ)
- 50-Day Intermediate Trend Line: ${dma50}
- 200-Day Macro Structural Line: ${dma200}
- Ornstein-Uhlenbeck Half-Life: {ou_hl:.1f} Days | Hurst Exponent H: {hurst_val:.2f} ({metrics.get('statistical_regime')})
- Volatility Squeeze Ratio (BB/KC): {metrics.get('squeeze_ratio', 1.0):.2f}x | Beta vs {benchmark_symbol}: {metrics.get('beta', 1.0)}x

Deliver a Multi-Timeframe Confluence Report in 4 sections:
1. 🌊 STRUCTURAL & HURST REGIME: Interpret H = {hurst_val:.2f} and Half-Life = {ou_hl:.1f}d alongside the 50-DMA (${dma50}) and 200-DMA (${dma200}).
2. 📊 VWMA-20 & INSTITUTIONAL COST BASIS: Where current price sits relative to volume-weighted institutional cost basis (${vwma20:.2f}).
3. ⚖️ 1–5 DAY EXPECTANCY MULTIPLIER: Win-rate impact of taking this {metrics.get('action')} in the current structural trend.
4. 🏁 TACTICAL CONFLUENCE VERDICT: High-Probability Institutional Setup or Counter-Trend Knife Catch.
"""

    else:
        # Default 'thesis' mode
        system_prompt = (
            "You are an elite quantitative equity derivatives trader and Chief Financial Strategist running on an ASUS GX10 (Qwen 3.8 + Karpathy Research Wiki). "
            "Synthesize the deterministic math, Karpathy Wiki moat intelligence, and 24/48H macro regime into a decisive 5-part 30-45 DTE options execution card."
        )
        prompt = f"""
Review this detected 1–5 Day Kinetic Options Setup for {ticker} ({profile.get('companyName', ticker)}) in {sector_name} (Factor Benchmark: {benchmark_symbol}):

=== KARPATHY RESEARCH WIKI & MOAT CONTEXT ===
{wiki_context}

=== DETERMINISTIC 1–5 DAY KINETIC & ELASTICITY METRICS ===
- Live Stock Price: ${metrics.get('price', 0)} | Institutional Equilibrium (VWMA-20): ${vwma20:.2f} | ATR(14): ${metrics.get('atr14', 0):.2f}
- Dual-Coordinate Effective Z-Score: {z_score_val:+.2f}σ (Absolute VWMA Stretch: {z_abs_val:+.2f}σ | 5D Beta-Adjusted Residual vs {benchmark_symbol}: {z_rel_val:+.2f}σ)
- Playbook Classification: {metrics.get('playbook_type', 'ELASTIC SNAPBACK')} ({metrics.get('velocity_status')})
- Kinetic Velocity & Hook: 1D ΔZ: {metrics.get('delta_z_1d', 0.0):+.2f}σ | 3D ΔZ: {metrics.get('delta_z_3d', 0.0):+.2f}σ | 2nd-Deriv Curvature (Δ²Z): {metrics.get('accel_z_2d', 0.0):+.2f}σ
- Ornstein-Uhlenbeck Half-Life: {ou_hl:.1f} Trading Days | Hurst Exponent H: {hurst_val:.2f} ({metrics.get('statistical_regime')})
- Intraday Microstructure: 4H/1D CLV: {metrics.get('clv', 0.0):+.2f} | RVOL (NY Paced): {metrics.get('rvol', 1.0)}x | Bull OBV Div: {metrics.get('bull_obv_divergence')}
- Yang-Zhang 30D Volatility: {yz_vol}% | 1Y Vol Rank: {vol_rank_val}% ({metrics.get('options_regime')})
- Verified Earnings Countdown: {days_to_earn} Days ({earn_date_str})

=== VERIFIED FMP PRO FUNDAMENTAL SOLVENCY ===
- Composite Quality Score: {fund.get('fund_score', 50):.0f}/100 ({'PASS' if fund.get('viable') else 'MIRAGE / FRAGILE'})
- Real Altman Z-Score: {fund.get('altman_z', 'N/A')} | Piotroski F-Score: {fund.get('piotroski_score', 'N/A')}/9
- Current Ratio: {fund.get('current_ratio', 'N/A')}x | Debt/Equity: {fund.get('debt_to_equity', 'N/A')}x | FCF Yield: {fund.get('fcf_yield_pct', 0):+.1f}%
- Real Revenue Growth: YoY {fund.get('rev_growth_yoy_pct', 0):+.1f}% | 3Y CAGR: {fund.get('rev_growth_3y_pct', 0):+.1f}% | Operating Margin: {fund.get('operating_margin_pct', 0):+.1f}%

=== GREATER MARKET 24/48H OUTLOOK ===
{macro_summary}

=== RECENT HEADLINES ===
{news_text}

Generate a crisp, authoritative Rubberband Man Execution Card with these 5 sections:
1. 🎯 VERDICT & PLAYBOOK: [{metrics.get('action', 'BUY CALL')} — {metrics.get('playbook_type', 'ELASTIC SNAPBACK')}]
2. 🧲 1–5 DAY KINETIC EDGE & O-U HALF-LIFE MECHANISM: Explain why the Dual-Coordinate Z-Score ({z_score_val:+.2f}σ), Velocity Hook ({metrics.get('velocity_status')}), and Ornstein-Uhlenbeck Half-Life ({ou_hl:.1f}d, H={hurst_val:.2f}) project an imminent 1–5 day move to ${metrics.get('target_price', 0):.2f}.
3. 🔬 KARPATHY MOAT & FMP PRO SOLVENCY SHIELD: Synthesize the company's technological moat/breakthrough with its verified Altman Z ({fund.get('altman_z')}), Piotroski ({fund.get('piotroski_score')}/9), RVOL ({metrics.get('rvol')}x), and {days_to_earn}-day earnings runway.
4. ⚡ {rec_dte} DTE STRIKE, CONVICTION ({conv_200:+d}/200 · {conv_tier}) & CONVEXITY BLUEPRINT:
   - Direction & Expiration: {metrics.get('action')} | {rec_dte} DTE ({rbe.get_target_options_friday(rec_dte)}) — {dte_rationale}
   - Orthogonal 5-Pillar Score: {conv_200:+d}/200 (Elasticity {pillars.get('elasticity_kalman', 0):+.1f}, Kinetic {pillars.get('kinetic_asymmetry', 0):+.1f}, Whale {pillars.get('dealer_whale_flow', 0):+.1f}, Surface {pillars.get('surface_convexity', 0):+.1f}, Regime {pillars.get('regime_solvency', 0):+.1f})
   - Target Strike: ${metrics.get('recommended_strike', 0):.2f} ({metrics.get('otm_pct', 0):.1f}% OTM | Estimated Δ {metrics.get('estimated_delta', 0.50):+.2f})
   - Gamma / Vega Convexity Thesis: Why this {rec_dte} DTE contract maximizes 1–5 day return under Yang-Zhang Vol {yz_vol}% (Vol Rank {vol_rank_val}%).
   - 1–5 Day Underlying Target: ${metrics.get('target_price', 0):.2f} | Hard Invalidation Stop: ${metrics.get('invalidation_price', 0):.2f} ({metrics.get('rr_ratio', 2.0):.1f}:1 Underlying R:R)
5. 💵 $1,000 SIMULATED TRADE DEPLOYMENT & SKEW-ADJUSTED R:R MATRIX:
   - Capital Allocated: ${sim_invested:,.2f} ({sim_contracts} contract(s) @ ~${sim_prem:.2f}/sh = ~${sim_cost_contract:.0f}/contract)
   - Projected 1–5D Profit at ${metrics.get('target_price', 0):.2f}: +${sim_gain:,.2f} (+{sim_roi:.1f}% ROI)
   - Disciplined Stop Loss at ${metrics.get('invalidation_price', 0):.2f}: -${sim_loss:,.2f} (-{sim_loss_pct:.1f}% loss)
   - Final Skew-Adjusted Options Risk/Reward Ratio: {sim_rr:.1f} : 1 Asymmetric Edge
"""

    text, err = llm_router.generate_text(prompt, system_instruction=system_prompt)
    if err:
        return f"⚠️ **AI Compute Notice**: {err}"
    return text
