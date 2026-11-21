import os
import re
import json
import time
import functools
from typing import List, Dict, Any, Tuple, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

import fmp_client
import rubberband_engine as rbe
import intel_bus_bridge as ibb
import llm_router

load_dotenv()

SYSTEM_INSTRUCTION = """
You are the Chief Quantitative & Financial Analysis AI running on an ASUS GX10 Supercomputer (powered by Qwen 3.8 & Google Gemini 3.5 Flash Lite), operating hand-in-hand with the Karpathy Research Wiki for 'Rubberband Man'.
Your mission is to identify high-conviction 1-to-5 day explosive stock moves (up or down) using 30-to-45 DTE aggressive Out-Of-The-Money (OTM) Calls and Puts across 4 core universes:
1. Semiconductors (SMH)
2. AI Infrastructure (SMH)
3. Robotics & Automation (BOTZ)
4. Nuclear & Next-Gen Energy (URA / XLU — strictly non-oil nuclear SMRs, uranium enrichment, & grid power)

Rules & Capabilities:
1. ARBITRARY TICKER LOOKUP & PEER SCANNING:
   You have full permission to query ANY stock ticker symbol via your tools:
   - `get_rubberband_metrics(symbol="OKLO", benchmark="URA")`
   - `get_24_48h_macro_radar()`
   - `get_stock_quote(symbol="NNE")`
   - `get_stock_peers(symbol="MPWR")`
   - `get_company_profile(symbol="SMR")`
   - `get_financial_ratios(symbol="CCJ")`

2. DUAL-COORDINATE ELASTICITY, O-U HALF-LIFE & KARPATHY WIKI MOAT SYNTHESIS:
   Always evaluate:
   - Dual-Coordinate Effective Z-Score (62% Absolute VWMA-20/ATR-14 Stretch + 38% Relative Factor Residual)
   - Ornstein-Uhlenbeck Mean-Reversion Half-Life (τ_1/2 in days, targeting 1.5–5.5 day fast snappers) & Hurst Exponent (H)
   - 2nd-Derivative Velocity Hook (Δ²Z) & 4-Hour Close Location Value (CLV)
   - Real FMP Pro Altman Z-Score, Piotroski F-Score (0–9), 3Y Revenue Growth, and Verified Days to Earnings
   - Karpathy Research Wiki Technological Moat / Material Breakthrough / Whale Sympathy Lag
   - Greater Market 6-Pillar 24/48H Forecast (Bonds TLT/10Y, Credit Stress HYG/LQD, Crude Oil, Gold, Silver, Bitcoin)

3. MANDATORY $1,000 SIMULATED 30-45 DTE TRADE DEPLOYMENT & ASYMMETRIC R:R:
   Whenever you recommend, audit, or discuss an options trade on ANY ticker, always conclude with a concrete ~$1,000 simulated 30–45 DTE position matrix showing:
   - Direction (CALL or PUT), Target Strike, Moneyness (% OTM), and Delta
   - Contracts & Capital Allocated (~$1,000)
   - 1–5 Day Target Profit ($ and % ROI) at the VWMA/ATR target price
   - Disciplined Stop-Loss ($ and % drawdown) at the hard invalidation price
   - Final Skew-Adjusted Risk-to-Reward Ratio (e.g., "3.8 : 1 R:R")
"""


def get_rubberband_metrics(symbol: str, benchmark: str = "SMH") -> Dict[str, Any]:
    """
    Computes complete v3.5 Rubberband Man institutional metrics for any stock ticker:
    Dual-Coordinate Effective Z-Score, VWMA-20 Equilibrium, O-U Half-Life (days), Hurst Exponent,
    Real Altman Z & Piotroski F-Score, Days to Earnings, 30-45 DTE Strike, and $1,000 trade simulation.
    """
    sym = symbol.strip().upper()
    bench = rbe.normalize_benchmark(benchmark)
    dd = rbe.get_due_diligence_candidate(sym, benchmark_symbol=bench)
    if not dd:
        return {"error": f"Insufficient historical data to compute elasticity for {sym} vs {bench}."}
    m = dd["metrics"]
    f = dd["fundamentals"]
    bp = dd["blueprint"]
    return {
        "symbol": sym,
        "benchmark": dd.get("benchmark", bench),
        "price": m["price"],
        "beta": m["beta"],
        "effective_z_score": m["z_score_5d"],
        "z_abs_vwma": m.get("z_abs"),
        "z_rel_5d": m.get("z_rel_5d"),
        "ou_half_life_days": m.get("ou_half_life"),
        "hurst_exponent": m.get("hurst"),
        "statistical_regime": m.get("statistical_regime"),
        "playbook_type": m.get("playbook_type"),
        "velocity_status": m.get("velocity_status", "N/A"),
        "delta_z_1d": m.get("delta_z_1d", 0.0),
        "delta_z_3d": m.get("delta_z_3d", 0.0),
        "clv_4h_1d": m.get("clv", 0.0),
        "rvol": m.get("rvol", 1.0),
        "recommended_action": m["action"],
        "move_potential_score": bp.get("composite_score"),
        "target_strike": m["recommended_strike"],
        "otm_pct": m.get("otm_pct"),
        "estimated_delta": m.get("estimated_delta"),
        "vwma20_equilibrium": m.get("vwma20", m["sma20"]),
        "target_price_1_5d": m.get("target_price"),
        "invalidation_stop": m.get("invalidation_price"),
        "sma50": m.get("sma50"),
        "sma200": m.get("sma200"),
        "days_to_earnings": m.get("days_to_earnings"),
        "earnings_date": m.get("earnings_date"),
        "quality_score": f.get("fund_score"),
        "altman_z": f.get("altman_z"),
        "piotroski_score": f.get("piotroski_score"),
        "rev_growth_3y_pct": f.get("rev_growth_3y_pct"),
        "risk_reward_ratio": m.get("rr_ratio", 2.0),
        "simulated_1k_trade": m.get("sim_1k", {})
    }


def get_24_48h_macro_radar() -> Dict[str, Any]:
    """
    Retrieves the live 6-Pillar Greater Market Radar (Bonds TLT/10Y, Credit Stress HYG/LQD,
    Crude Oil, Gold GLD, Silver SLV, Bitcoin BTCUSD) and the 24/48-Hour US Stock Market Direction Forecast.
    """
    return rbe.get_24_48h_market_direction_radar()


FMP_TOOLS = [
    fmp_client.get_company_profile,
    fmp_client.get_income_statement,
    fmp_client.get_cash_flow_statement,
    fmp_client.get_balance_sheet,
    fmp_client.get_financial_ratios,
    fmp_client.get_key_metrics,
    fmp_client.get_dcf_valuation,
    fmp_client.get_price_targets,
    fmp_client.get_stock_peers,
    fmp_client.get_stock_quote,
    fmp_client.get_historical_stock_prices,
    fmp_client.get_market_temperature,
    get_rubberband_metrics,
    get_24_48h_macro_radar,
]


def get_gemini_client() -> Tuple[Optional[Any], str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None, "GEMINI_API_KEY is not set. Please set it in your .env file or sidebar."
    try:
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=45000))
        return client, ""
    except Exception as e:
        return None, f"Failed to initialize Gemini Client: {str(e)}"


class FinancialAgentSession:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or llm_router.get_gemini_fallback_models()[0]
        self.tool_logs: List[Dict[str, Any]] = []

    def _tool_execution_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tool_name = func.__name__
            entry: Dict[str, Any] = {
                "name": tool_name,
                "args": kwargs if kwargs else (args if args else {}),
                "status": "invoking",
            }
            self.tool_logs.append(entry)
            try:
                result = func(*args, **kwargs)
                entry["status"] = "success"
                entry["result_summary"] = str(result)[:200]
                return result
            except Exception as exc:
                entry["status"] = "error"
                entry["result_summary"] = str(exc)[:200]
                raise
        return wrapper

    def query(self, prompt: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        backend = llm_router.get_active_backend()
        if backend == "local":
            return self._query_local_model(prompt, chat_history)

        client, err = get_gemini_client()
        if not client:
            return {
                "text": f"⚠️ **Configuration Error**: {err}",
                "tool_logs": [],
                "chart_data": None
            }

        self.tool_logs = []
        wrapped_tools = [self._tool_execution_wrapper(fn) for fn in FMP_TOOLS]

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=wrapped_tools,
            temperature=0.2,
        )

        fallback_models = [self.model_name]
        for fallback in llm_router.get_gemini_fallback_models():
            if fallback not in fallback_models:
                fallback_models.append(fallback)

        history_contents = []
        if chat_history:
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                history_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

        last_exception = None
        for model in fallback_models:
            for attempt in range(3):
                self.tool_logs = []
                try:
                    chat = client.chats.create(
                        model=model,
                        config=config,
                        history=history_contents
                    )
                    response = chat.send_message(prompt)
                    response_text = response.text if response.text else "Analysis generated successfully."
                    return {
                        "text": response_text,
                        "tool_logs": self.tool_logs,
                        "chart_data": None
                    }
                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    if any(k in err_str.upper() for k in ["401", "403", "API_KEY_INVALID", "PERMISSION_DENIED"]):
                        return {
                            "text": f"❌ **Gemini Authorization Error**: {err_str[:180]}",
                            "tool_logs": self.tool_logs,
                            "chart_data": None
                        }
                    if any(k in err_str.upper() for k in ["503", "500", "502", "504", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "HIGH DEMAND", "TIMEOUT"]):
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    break

        return {
            "text": f"❌ **Service High Demand**: ({str(last_exception)}). Please retry.",
            "tool_logs": self.tool_logs,
            "chart_data": None
        }

    def _query_local_model(self, prompt: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Executes query against ASUS GX10 Qwen 3.8 model.
        Automatically resolves quantitative FMP Pro, Karpathy Research Wiki, and 24/48H Macro Radar tools.
        """
        self.tool_logs = []

        target_tickers: List[str] = []
        ctx_match = re.search(r"\[Ticker:\s*([A-Za-z]{1,5})\b", prompt)
        if ctx_match:
            target_tickers.append(ctx_match.group(1).upper())

        candidates = re.findall(r'\b[A-Za-z]{1,5}\b', prompt)
        ignore = {
            "CALL", "PUTS", "PUT", "CALLS", "ATM", "OTM", "ITM", "ROI", "DTE",
            "RVOL", "DMA", "RSI", "SMA", "FCF", "USD", "SPY", "QQQ", "BUY", "SELL",
            "THE", "FOR", "AND", "CAN", "WHAT", "SHOW", "GIVE", "WITH", "RISK",
            "BOND", "GOLD", "NEXT", "MOVE", "DAYS", "HIGH", "LOW", "BEST",
            "AI", "US", "ETF", "EPS", "IV", "SEC", "FED", "CPI", "GDP", "GEX",
            "VRP", "SVI", "VIX", "EV", "PNL", "CEO", "CFO", "IPO", "OPEX", "FOMC",
            "IS", "IT", "IN", "ON", "AT", "TO", "OF", "OR", "AS", "BY", "BE", "DO",
            "IF", "NO", "SO", "UP", "MY", "AN", "WE", "HE", "ME", "VS", "WHY", "HOW",
            "A", "I",
        }
        for c in candidates:
            cu = c.upper()
            if c.isupper() and cu not in ignore and cu not in target_tickers:
                target_tickers.append(cu)
        if not target_tickers:
            target_tickers = ["MPWR"]

        context_blocks = []

        # Inject 24/48H Macro Radar summary
        try:
            wrapped_macro = self._tool_execution_wrapper(get_24_48h_macro_radar)
            macro_r = wrapped_macro()
            context_blocks.append(
                f"### 24/48H US Market Direction & 6-Pillar Macro Radar:\n"
                f"- Verdict: {macro_r.get('signage_title')} ({macro_r.get('expected_move')})\n"
                f"- Options Directive: {macro_r.get('options_directive')}"
            )
        except Exception:
            pass

        intel_signals = ibb.read_intel_bus_signals()

        for sym in target_tickers[:3]:
            try:
                wrapped_metrics = self._tool_execution_wrapper(get_rubberband_metrics)
                m = wrapped_metrics(symbol=sym)
                wiki_match = next((s for s in intel_signals if s.get("symbol") == sym), None)
                context_blocks.append(
                    f"### Verified FMP Pro & Karpathy Wiki Dossier for {sym}:\n"
                    f"- Karpathy Wiki Signal: {json.dumps(wiki_match) if wiki_match else 'Standard Universe Ticker'}\n"
                    f"- Institutional Kinetic & Options Telemetry: {json.dumps(m)}"
                )
            except Exception as e:
                context_blocks.append(f"Notice fetching {sym}: {str(e)}")

        augmented_prompt = prompt
        if context_blocks:
            augmented_prompt += "\n\n=== VERIFIED REAL-TIME FMP PRO, KARPATHY WIKI & MACRO DATA ===\n" + "\n\n".join(context_blocks)

        if chat_history:
            history_summary = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in chat_history[-4:]])
            augmented_prompt = f"Previous conversation context:\n{history_summary}\n\nCurrent user request:\n{augmented_prompt}"

        resp_text, err = llm_router.generate_text(augmented_prompt, system_instruction=SYSTEM_INSTRUCTION)
        if err:
            return {
                "text": f"⚠️ **ASUS GX10 Local Model Notice**: {err}\n\nPlease check your local endpoint settings in the sidebar.",
                "tool_logs": self.tool_logs,
                "chart_data": None
            }

        return {
            "text": resp_text,
            "tool_logs": self.tool_logs,
            "chart_data": None
        }


RubberbandAgentSession = FinancialAgentSession
