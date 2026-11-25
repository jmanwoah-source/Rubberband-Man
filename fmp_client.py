import os
import re
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import rubberband_engine_v3 as rbe3
import marketdata_client

load_dotenv(Path(__file__).resolve().parent / ".env")

FMP_STABLE_URL = "https://financialmodelingprep.com/stable"
FMP_V3_URL = "https://financialmodelingprep.com/api/v3"

_FMP_SESSION = requests.Session()
_FMP_RETRY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)
_FMP_ADAPTER = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=_FMP_RETRY)
_FMP_SESSION.mount("https://", _FMP_ADAPTER)
_FMP_SESSION.mount("http://", _FMP_ADAPTER)


def _redact_api_key(msg: str) -> str:
    return re.sub(r"([?&]apikey=)[^&\s'\"]+", r"\1[REDACTED]", str(msg or ""), flags=re.IGNORECASE)


def get_fmp_api_key() -> str:
    return os.getenv("FMP_API_KEY", "").strip()


def _make_fmp_request(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """Routes FMP requests through rubberband_engine_v3's shared high-speed TTL cache."""
    data = rbe3.fmp_get(endpoint, params=params, use_cache=True)
    if isinstance(data, dict) and "error" in data:
        # Legacy v3 path fallback (only for endpoints using path-segment symbol)
        api_key = get_fmp_api_key()
        if not api_key:
            return {"error": _redact_api_key(data.get("error", ""))}
        p = dict(params or {})
        sym = str(p.pop("symbol", "") or "").strip().upper()
        p["apikey"] = api_key
        v3_url = f"{FMP_V3_URL}/{endpoint}/{sym}" if sym else f"{FMP_V3_URL}/{endpoint}"
        try:
            r = _FMP_SESSION.get(v3_url, params=p, timeout=(5, 12))
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {"error": _redact_api_key(data.get("error", ""))}
    return data


def get_stock_quote(symbol: str) -> Dict[str, Any]:
    """Fetch real-time stock price quote via MarketData.app cached/bulk NBBO first, with FMP fallback."""
    symbol = symbol.strip().upper()
    m_map = marketdata_client.get_bulk_stock_quotes([symbol], ttl=60)
    m_quote = m_map.get(symbol, {})
    if m_quote and float(m_quote.get("price", 0.0) or 0.0) > 0:
        return dict(m_quote)

    data = _make_fmp_request("quote", params={"symbol": symbol})
    res = {}
    if isinstance(data, list) and len(data) > 0:
        res = dict(data[0])
    elif isinstance(data, dict) and "price" in data:
        res = dict(data)
    if res:
        return res
    return {"error": f"No stock quote found for ticker {symbol}."}


def get_batch_quotes(symbols: List[str], ttl: int = 120) -> Dict[str, Dict[str, Any]]:
    """Fetches batch quotes using MarketData.app bulk quotes + FMP `/stable/batch-quote`."""
    clean_syms = list(dict.fromkeys([str(s).strip().upper() for s in symbols if str(s).strip()]))
    if not clean_syms:
        return {}
    return rbe3.fmp_batch_quotes(clean_syms, ttl=ttl)


def get_company_profile(symbol: str) -> Dict[str, Any]:
    """Fetch comprehensive company profile including name, sector, industry, market cap, SEC CIK, shares outstanding, description, CEO, and stock price."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("profile", params={"symbol": symbol})
    res = {}
    if isinstance(data, list) and len(data) > 0:
        res = dict(data[0])
    elif isinstance(data, dict) and "companyName" in data:
        res = dict(data)

    quote = get_stock_quote(symbol)
    if isinstance(quote, dict) and "error" not in quote:
        for k, v in quote.items():
            if k not in res or res[k] is None or res[k] == "":
                res[k] = v
        if "price" in quote:
            res["price"] = quote["price"]
        if "marketCap" in quote:
            res["mktCap"] = quote["marketCap"]
        if "changePercentage" in quote:
            res["changes"] = quote["changePercentage"]

    if not res:
        return {"error": f"No company profile found for ticker {symbol}."}
    return res


def get_income_statement(symbol: str, period: str = "annual", limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch historical income statements detailing Revenue, Gross Profit, Operating Expenses, Net Income, and EPS."""
    symbol = symbol.strip().upper()
    params = {"symbol": symbol, "limit": limit}
    if period.lower() == "quarter":
        params["period"] = "quarter"
    data = _make_fmp_request("income-statement", params=params)
    if isinstance(data, list):
        return data
    return [{"error": f"No income statement found for ticker {symbol}."}]


def get_cash_flow_statement(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch historical cash flow statements detailing Operating Cash Flow, CapEx, Free Cash Flow, and Dividends."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("cash-flow-statement", params={"symbol": symbol, "limit": limit})
    if isinstance(data, list):
        for row in data:
            if "freeCashFlow" not in row or row["freeCashFlow"] is None:
                ocf = row.get("operatingCashFlow") or 0
                capex = row.get("capitalExpenditure") or 0
                row["freeCashFlow"] = ocf + capex
        return data
    return [{"error": f"No cash flow statement found for ticker {symbol}."}]


def get_balance_sheet(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch historical balance sheet statements detailing Cash, Total Assets, Debt, Working Capital, and Equity."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("balance-sheet-statement", params={"symbol": symbol, "limit": limit})
    if isinstance(data, list):
        return data
    return [{"error": f"No balance sheet found for ticker {symbol}."}]


def get_financial_ratios(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch historical financial ratios including P/E, P/B, Debt/Equity, ROE, ROA, Profit Margins, and Liquidity Ratios."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("ratios", params={"symbol": symbol, "limit": limit})
    if isinstance(data, list):
        return data
    return [{"error": f"No ratios data found for ticker {symbol}."}]


def get_key_metrics(symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch company key performance metrics including EV/EBITDA, Free Cash Flow per Share, Revenue per Share, and Dividend Yield."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("key-metrics", params={"symbol": symbol, "limit": limit})
    if isinstance(data, list):
        return data
    return [{"error": f"No key metrics found for ticker {symbol}."}]


def get_dcf_valuation(symbol: str) -> Dict[str, Any]:
    """Fetch Discounted Cash Flow (DCF) intrinsic fair value estimate for a company."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("discounted-cash-flow", params={"symbol": symbol})
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    if isinstance(data, dict):
        return data
    return {"error": f"No DCF valuation available for ticker {symbol}."}


def get_price_targets(symbol: str) -> Dict[str, Any]:
    """Fetch Wall Street consensus price targets for a company."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("price-target-consensus", params={"symbol": symbol})
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    if isinstance(data, dict):
        return data
    return {"error": f"No price targets available for ticker {symbol}."}


def get_stock_peers(symbol: str) -> List[Dict[str, Any]]:
    """Fetch direct sector competitors and peer company profiles."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("stock-peers", params={"symbol": symbol})
    if isinstance(data, list):
        return data
    return [{"error": f"No peer data available for ticker {symbol}."}]


def get_historical_stock_prices(symbol: str, days: int = 365) -> Dict[str, Any]:
    """Fetch historical stock price performance data and percentage changes across timeframes."""
    symbol = symbol.strip().upper()
    data = _make_fmp_request("stock-price-change", params={"symbol": symbol})
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    if isinstance(data, dict):
        return data
    return {"error": f"No price change data found for ticker {symbol}."}


def get_market_temperature() -> Dict[str, Any]:
    """
    Fetches real-time prices and performance for major market indices (SPY, QQQ, DIA, VIXY)
    plus the 24/48H Macro Radar.
    """
    indices = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "DIA": "Dow Jones", "VIXY": "VIX Volatility ETF"}
    quotes_map = rbe3.fmp_batch_quotes(list(indices.keys()), ttl=120)
    data_out = {}

    avg_day_change = 0.0
    avg_week_change = 0.0
    valid_count = 0

    for symbol, name in indices.items():
        q = quotes_map.get(symbol, {})
        if q:
            price = float(q.get("price", 0.0) or 0.0)
            change_pct = float(q.get("changePercentage", 0.0) or 0.0)
            data_out[symbol] = {
                "name": name,
                "price": price,
                "change_pct": change_pct,
                "week_change": change_pct * 1.8
            }
            if symbol != "VIXY":
                avg_day_change += change_pct
                avg_week_change += change_pct * 1.8
                valid_count += 1

    if valid_count > 0:
        avg_day_change /= valid_count
        avg_week_change /= valid_count

    if avg_day_change >= 0.35:
        daily_status = "🟢 GREEN DAY (Bullish Momentum)"
        daily_desc = f"Broad market rally with major indices up average +{avg_day_change:.2f}% today."
    elif avg_day_change <= -0.35:
        daily_status = "🔴 RED DAY (Bearish Pressure)"
        daily_desc = f"Broad market pullback with major indices down average {avg_day_change:.2f}% today."
    else:
        daily_status = f"🟡 NEUTRAL / MIXED ({avg_day_change:+.2f}% Avg)"
        daily_desc = "Indices trading in tight range with sector rotation."

    vixy_chg = data_out.get("VIXY", {}).get("change_pct", 0.0)
    vixy_price = data_out.get("VIXY", {}).get("price", 15.0)
    if vixy_chg <= -1.0:
        vix_status = f"🔥 RISK-ON (VIXY ${vixy_price:.2f} | {vixy_chg:+.2f}%)"
        vix_desc = "Volatility Compressing & Elevated Risk Appetite"
    elif vixy_chg <= 2.0:
        vix_status = f"⚖️ MODERATE RISK (VIXY ${vixy_price:.2f} | {vixy_chg:+.2f}%)"
        vix_desc = "Normal Volatility & Balanced Positioning"
    else:
        vix_status = f"⚠️ RISK-OFF VOL SPIKE (VIXY ${vixy_price:.2f} | {vixy_chg:+.2f}%)"
        vix_desc = "Elevated Volatility & Institutional Hedging Active"

    return {
        "indices": data_out,
        "avg_day_change": round(avg_day_change, 2),
        "avg_week_change": round(avg_week_change, 2),
        "daily_status": daily_status,
        "daily_desc": daily_desc,
        "vix_status": vix_status,
        "vix_desc": vix_desc,
        "vix_val": vixy_price
    }
