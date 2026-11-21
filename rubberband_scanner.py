"""
Autonomous Rubberband Divergence CLI & Scheduled Scanner (v3.5)
Runs Dual-Coordinate Kinetic Engine -> FMP Pro Solvency Audit -> Qwen 3.8 / Gemini 2.5 Trade Arbiter.
Supports scheduled runs, headless signal logging to signals/today.md, and direct terminal inspection.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import rubberband_engine as rbe_eng
import rubberband_arbiter as rba

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

WATCHLIST = [
    "MPWR", "ON", "MCHP", "ALGM", "CRUS", "AMBA", "WOLF", "RMBS",
    "VRT", "SMCI", "ALAB", "COHR", "CIEN", "CRDO", "PSTG",
    "TER", "SYM", "CGNX", "PATH", "ZBRA",
    "OKLO", "SMR", "CCJ", "BWXT", "LEU", "CEG", "VST"
]
BENCHMARK = "SMH"


def run_scan(z_threshold: float = 1.65, log_to_file: bool = True):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Rubberband v3.5 Scanner...")

    # Pre-warm batch quotes
    rbe_eng.fmp_batch_quotes(WATCHLIST + ["SMH", "BOTZ", "URA", "XLU"])
    qualifying_candidates = []

    for ticker in WATCHLIST:
        sys.stdout.write(f"Analyzing {ticker}...")
        sys.stdout.flush()

        dd = rbe_eng.get_due_diligence_candidate(ticker, benchmark_symbol=BENCHMARK)
        if not dd:
            print(" [No Data]")
            continue

        metrics = dd["metrics"]
        fund = dd["fundamentals"]
        bp = dd["blueprint"]
        news = rbe_eng.get_recent_news(ticker, limit=3)

        entry = {
            "ticker": ticker,
            "metrics": metrics,
            "fundamentals": fund,
            "blueprint": bp,
            "news": news,
            "profile": {"companyName": dd["company_name"], "description": dd["description"]}
        }

        z = metrics["z_score_5d"]
        conv_200 = int(bp.get("conviction_score_200", metrics.get("conviction_score_200", 0)) or 0)
        rec_dte = int(bp.get("recommended_dte", metrics.get("recommended_dte", 30)) or 30)
        is_trig = (
            not metrics.get("is_bad_data", False)
            and int(metrics.get("days_to_earnings", 45) or 45) > 15
            and (abs(z) >= z_threshold or "COILED" in metrics["state"])
            and metrics["action"] in ["BUY CALL", "BUY PUT"]
        )
        status = "[TRIGGER]" if is_trig else "[NORMAL]"
        print(
            f" Eff Z: {z:+.2f}σ (Abs: {metrics['z_abs']:+.2f}σ) | Half-Life: {metrics['ou_half_life']:.1f}d | "
            f"Conv200: {conv_200:+d} ({rec_dte}D) | Quality: {fund['fund_score']:.0f}/100 | Action: {metrics['action']} | R:R: {metrics['rr_ratio']:.2f}:1 | {status}"
        )

        if is_trig:
            qualifying_candidates.append(entry)

    qualifying_candidates.sort(
        key=lambda x: x["blueprint"].get("conviction_abs_200", x["blueprint"].get("composite_score", 0)),
        reverse=True,
    )
    print(f"\nScan completed. Found {len(qualifying_candidates)} high-conviction 1-5D setups.\n")

    output_lines = [
        f"# 🏹 Rubberband Man v3.5 Divergence & Kinetic Radar - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Trigger Threshold:** ±{z_threshold}σ Dual-Coordinate Stretch or Coiled Spring | **Active Universe:** Sub-$200B MktCap\n",
        "---"
    ]

    for candidate in qualifying_candidates[:6]:
        ticker = candidate["ticker"]
        m = candidate["metrics"]
        f = candidate["fundamentals"]
        bp = candidate["blueprint"]
        c200 = int(bp.get("conviction_score_200", m.get("conviction_score_200", 0)) or 0)
        ctier = bp.get("conviction_tier", m.get("conviction_tier", "WATCH / DEVELOPING"))
        rec_dte = int(bp.get("recommended_dte", m.get("recommended_dte", 30)) or 30)
        print(f"Generating Outright Call/Put Card for {ticker}...")
        thesis = rba.generate_options_thesis(candidate, "Core Universe", m.get("sub_benchmark", BENCHMARK))
        print(thesis)
        print("-" * 60)

        output_lines.append(f"## {ticker} {m['playbook_type']} (${m['price']:.2f})")
        output_lines.append(f"- **Conviction Score (-200..+200):** `{c200:+d}` (`{ctier}` | Prescribed Horizon: `{rec_dte} DTE`)")
        output_lines.append(f"- **Effective Stretch Z-Score:** `{m['z_score_5d']:+.2f}σ` (Abs VWMA Z: `{m['z_abs']:+.2f}σ` | Rel Factor Z: `{m['z_rel_5d']:+.2f}σ`)")
        output_lines.append(f"- **O-U Snap Half-Life:** `{m['ou_half_life']:.1f} Days` | **Hurst H:** `{m['hurst']:.2f}` | **RVOL:** `{m.get('rvol', 1.0)}x`")
        output_lines.append(f"- **FMP Pro Quality Score:** `{f['fund_score']:.0f}/100` (Altman Z: `{f['altman_z']}` | Piotroski: `{f['piotroski_score']}/9`)")
        output_lines.append(f"- **Directional Target:** `{m['action']}` ({rec_dte} DTE Strike: `${m['recommended_strike']:.2f}` | 1–5D Target: `${m['target_price']:.2f}` | Stop: `${m['invalidation_price']:.2f}` | R:R: `{m['rr_ratio']:.2f}:1`)\n")
        output_lines.append(thesis)
        output_lines.append("\n---\n")

    if log_to_file:
        sig_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signals")
        os.makedirs(sig_dir, exist_ok=True)
        file_path = os.path.join(sig_dir, "today.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"\n✅ Signals successfully logged to: {os.path.abspath(file_path)}")


if __name__ == "__main__":
    threshold = 1.65
    if len(sys.argv) > 1:
        try:
            threshold = float(sys.argv[1])
        except ValueError:
            threshold = 1.65
    run_scan(z_threshold=threshold, log_to_file=True)
