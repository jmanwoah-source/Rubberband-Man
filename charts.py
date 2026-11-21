import os
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(12, 15, 22, 0.42)",
    font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1", size=12),
    margin=dict(l=40, r=40, t=50, b=40),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        bgcolor="rgba(12, 15, 22, 0.72)",
        bordercolor="rgba(255, 255, 255, 0.08)",
        borderwidth=1,
        font=dict(color="#E2E8F0", size=11)
    ),
    hoverlabel=dict(
        bgcolor="rgba(10, 12, 18, 0.96)",
        bordercolor="rgba(255, 107, 0, 0.48)",
        font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0")
    ),
    hovermode="x unified"
)

def fetch_daily_price_history(symbol: str, range_str: str = "1y") -> Optional[pd.DataFrame]:
    """
    100% FMP Ultra Implementation:
    Fetches daily OHLCV historical price data directly from FMP stable historical-price-eod/full
    and computes SMA, Bollinger Bands, and RSI(14).
    """
    import os
    symbol = symbol.strip().upper()
    fmp_key = os.getenv("FMP_API_KEY", "").strip()
    if not fmp_key:
        return None

    url = f"https://financialmodelingprep.com/stable/historical-price-eod/full"
    try:
        r = requests.get(url, params={"symbol": symbol, "apikey": fmp_key}, timeout=12)
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return None

        df = pd.DataFrame(data)
        if "date" not in df.columns or "close" not in df.columns:
            return None
            
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        
        # Ensure numerical types
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["close"])
        
        if df.empty:
            return None
            
        # Simple Moving Averages
        df["sma20"] = df["close"].rolling(window=20, min_periods=1).mean()
        df["sma50"] = df["close"].rolling(window=50, min_periods=1).mean()
        
        # Bollinger Bands (20-day, 2 StdDev)
        df["std20"] = df["close"].rolling(window=20, min_periods=1).std().fillna(0)
        df["upper_band"] = df["sma20"] + (df["std20"] * 2)
        df["lower_band"] = df["sma20"] - (df["std20"] * 2)
        
        # RSI (14-period Relative Strength Index)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / (loss.replace(0, np.nan))
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50)

        # Filter dataset based on selected timeframe after indicator calculation
        range_key = range_str.lower().strip()
        last_date = df["date"].max()

        if range_key in ["1m", "1mo"]:
            cutoff = last_date - pd.Timedelta(days=30)
            df = df[df["date"] >= cutoff]
        elif range_key in ["3m", "3mo"]:
            cutoff = last_date - pd.Timedelta(days=90)
            df = df[df["date"] >= cutoff]
        elif range_key in ["6m", "6mo"]:
            cutoff = last_date - pd.Timedelta(days=180)
            df = df[df["date"] >= cutoff]
        elif range_key in ["1y", "1yr"]:
            cutoff = last_date - pd.Timedelta(days=365)
            df = df[df["date"] >= cutoff]
        elif range_key == "ytd":
            cutoff = pd.Timestamp(year=last_date.year, month=1, day=1)
            df = df[df["date"] >= cutoff]
            
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"Error fetching daily price history: {e}")
        return None


def create_price_line_chart(
    symbol: str, 
    df: Optional[pd.DataFrame] = None, 
    chart_type: str = "Line",
    show_bb: bool = False,
    show_rsi: bool = True
) -> go.Figure:
    """Generates a high-precision line/area price chart with Volume & RSI subplots."""
    if df is None or df.empty:
        df = fetch_daily_price_history(symbol, "1y")
        
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No historical price series available.", showarrow=False, font=dict(size=14, color="#94A3B8"))
        fig.update_layout(**PLOT_LAYOUT)
        return fig

    # Determine overall price trend over selected window for dynamic theme coloring
    price_start = df["close"].iloc[0] if len(df) > 0 else 0
    price_end = df["close"].iloc[-1] if len(df) > 0 else 0
    is_positive = price_end >= price_start

    line_color = "#10B981" if is_positive else "#F43F5E"
    fill_color = "rgba(16, 185, 129, 0.12)" if is_positive else "rgba(244, 63, 94, 0.12)"

    # Subplots: Price (65%), Volume (18%), RSI (17%)
    rows = 3 if show_rsi else 2
    row_heights = [0.65, 0.18, 0.17] if show_rsi else [0.75, 0.25]
    
    titles = [f"{symbol.upper()} Price Action ($)", "Trading Volume"]
    if show_rsi:
        titles.append("RSI Oscillator (14 Period)")

    fig = make_subplots(
        rows=rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=titles
    )

    # 1. Bollinger Bands Shaded Channel (Only if explicitly toggled on)
    if show_bb and "upper_band" in df.columns and "lower_band" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["upper_band"],
            name="Upper BB",
            line=dict(color="rgba(255, 107, 0, 0.32)", width=1, dash="dot"),
            showlegend=False
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["lower_band"],
            name="Bollinger Bands (20,2)",
            line=dict(color="rgba(255, 107, 0, 0.32)", width=1, dash="dot"),
            fill="tonexty",
            fillcolor="rgba(255, 107, 0, 0.05)"
        ), row=1, col=1)

    # 2. Main Price Line / Area Trace
    if chart_type == "Area":
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["close"],
            name=f"{symbol.upper()} Price ($)",
            mode="lines",
            line=dict(color=line_color, width=2.8),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Price: <b>$%{y:.2f}</b><extra></extra>"
        ), row=1, col=1)
    elif chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC Price",
            increasing_line_color="#10B981",
            decreasing_line_color="#F43F5E",
            increasing_fillcolor="rgba(16, 185, 129, 0.25)",
            decreasing_fillcolor="rgba(244, 63, 94, 0.25)"
        ), row=1, col=1)
    else:  # Pure Line Graph (Default)
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["close"],
            name=f"{symbol.upper()} Price ($)",
            mode="lines",
            line=dict(color=line_color, width=3.0),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>Price: <b>$%{y:.2f}</b><extra></extra>"
        ), row=1, col=1)

    # 3. Moving Averages Overlay (20 SMA & 50 SMA)
    if "sma20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["sma20"],
            name="20-Day SMA",
            line=dict(color="#FF6B00", width=1.6, dash="dash")
        ), row=1, col=1)
        
    if "sma50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["sma50"],
            name="50-Day SMA",
            line=dict(color="#94A3B8", width=1.5, dash="dot")
        ), row=1, col=1)

    # 4. Volume Bar Subplot (Row 2)
    colors = ["#10B981" if c >= o else "#F43F5E" for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(
        x=df["date"], y=df["volume"],
        name="Volume",
        marker_color=colors,
        opacity=0.6,
        hovertemplate="<b>%{x|%b %d, %Y}</b><br>Volume: <b>%{y:,.0f}</b><extra></extra>"
    ), row=2, col=1)

    # 5. RSI Oscillator Subplot (Row 3, if enabled)
    if show_rsi and "rsi" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["rsi"],
            name="RSI (14)",
            line=dict(color="#FB923C", width=2),
            hovertemplate="<b>%{x|%b %d, %Y}</b><br>RSI: <b>%{y:.1f}</b><extra></extra>"
        ), row=3, col=1)
        
        # 70 Overbought & 30 Oversold Threshold Lines
        fig.add_shape(type="line", x0=df["date"].iloc[0], x1=df["date"].iloc[-1], y0=70, y1=70,
                      line=dict(color="#F43F5E", width=1, dash="dash"), row=3, col=1)
        fig.add_shape(type="line", x0=df["date"].iloc[0], x1=df["date"].iloc[-1], y0=30, y1=30,
                      line=dict(color="#10B981", width=1, dash="dash"), row=3, col=1)

    # Calculate exact date range bounds
    start_date = df["date"].min()
    end_date = df["date"].max()

    # Layout Tuning
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12, 15, 22, 0.42)",
        font=dict(family="Plus Jakarta Sans, JetBrains Mono, sans-serif", color="#CBD5E1", size=12),
        margin=dict(l=40, r=40, t=45, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0,
            bgcolor="rgba(12, 15, 22, 0.72)",
            bordercolor="rgba(255, 255, 255, 0.08)",
            borderwidth=1,
            font=dict(color="#E2E8F0", size=11)
        ),
        xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", showspikes=True, spikemode="across", spikethickness=1, spikecolor="rgba(255, 107, 0, 0.35)", spikedash="dot", rangeslider=dict(visible=False)),
        xaxis2=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", showspikes=True, spikemode="across", spikethickness=1, spikecolor="rgba(255, 107, 0, 0.35)", spikedash="dot"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", title="Price ($)", tickprefix="$"),
        yaxis2=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", title="Volume"),
        hoverlabel=dict(
            bgcolor="rgba(10, 12, 18, 0.96)",
            bordercolor="rgba(255, 107, 0, 0.48)",
            font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#E2E8F0")
        ),
        hovermode="x unified"
    )

    if show_rsi:
        fig.update_layout(
            xaxis3=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", showspikes=True, spikemode="across", spikethickness=1, spikecolor="rgba(255, 107, 0, 0.35)", spikedash="dot"),
            yaxis3=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", title="RSI", range=[0, 100])
        )

    # Explicitly enforce the exact date range for all subplots
    fig.update_xaxes(range=[start_date, end_date], autorange=False)

    return fig

# Alias for backwards compatibility
create_advanced_candlestick_chart = create_price_line_chart

def create_income_statement_chart(income_data: List[Dict[str, Any]], symbol: str) -> go.Figure:
    """Generates a multi-year breakdown of Revenue, Gross Profit, Operating Income, and Net Income."""
    fig = go.Figure()
    if not income_data or (isinstance(income_data, list) and "error" in income_data[0]):
        return fig
        
    df = pd.DataFrame(income_data)
    if "date" not in df.columns:
        return fig
        
    df["year"] = pd.to_datetime(df["date"]).dt.year.astype(str)
    df = df.sort_values("year")

    for col in ["revenue", "grossProfit", "operatingIncome", "netIncome"]:
        if col in df.columns:
            df[f"{col}_B"] = df[col] / 1e9

    fig.add_trace(go.Bar(
        x=df["year"], y=df.get("revenue_B", [0]*len(df)),
        name="Revenue ($B)",
        marker_color="#FF6B00",
        hovertemplate="<b>FY %{x}</b><br>Revenue: <b>$%{y:.2f}B</b><extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df["year"], y=df.get("grossProfit_B", [0]*len(df)),
        name="Gross Profit ($B)",
        marker_color="#FB923C",
        hovertemplate="<b>FY %{x}</b><br>Gross Profit: <b>$%{y:.2f}B</b><extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df["year"], y=df.get("operatingIncome_B", [0]*len(df)),
        name="Operating Income ($B)",
        marker_color="#64748B",
        hovertemplate="<b>FY %{x}</b><br>Operating Income: <b>$%{y:.2f}B</b><extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df["year"], y=df.get("netIncome_B", [0]*len(df)),
        name="Net Income ($B)",
        mode="lines+markers",
        line=dict(color="#10B981", width=3.5),
        marker=dict(size=9, color="#10B981"),
        hovertemplate="<b>FY %{x}</b><br>Net Income: <b>$%{y:.2f}B</b><extra></extra>"
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        barmode="group",
        xaxis=dict(type="category", title="Fiscal Year", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Amount ($ Billions)", tickprefix="$", ticksuffix="B")
    )
    return fig

def create_cash_flow_chart(cf_data: List[Dict[str, Any]], symbol: str) -> go.Figure:
    """Generates multi-year Cash Flow & Capital Allocation trends (Operating Cash Flow, CapEx, Free Cash Flow)."""
    fig = go.Figure()
    if not cf_data or (isinstance(cf_data, list) and "error" in cf_data[0]):
        return fig
        
    df = pd.DataFrame(cf_data)
    if "date" not in df.columns:
        return fig

    df["year"] = pd.to_datetime(df["date"]).dt.year.astype(str)
    df = df.sort_values("year")

    for col in ["operatingCashFlow", "capitalExpenditure", "freeCashFlow"]:
        if col in df.columns:
            df[f"{col}_B"] = df[col] / 1e9
            
    if "capitalExpenditure_B" in df.columns:
        df["capitalExpenditure_B"] = df["capitalExpenditure_B"].abs()

    fig.add_trace(go.Bar(
        x=df["year"], y=df.get("operatingCashFlow_B", [0]*len(df)),
        name="Operating Cash Flow ($B)",
        marker_color="#FB923C",
        hovertemplate="<b>FY %{x}</b><br>Operating Cash Flow: <b>$%{y:.2f}B</b><extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df["year"], y=df.get("capitalExpenditure_B", [0]*len(df)),
        name="CapEx ($B)",
        marker_color="#F43F5E",
        hovertemplate="<b>FY %{x}</b><br>CapEx: <b>$%{y:.2f}B</b><extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=df["year"], y=df.get("freeCashFlow_B", [0]*len(df)),
        name="Free Cash Flow ($B)",
        mode="lines+markers",
        line=dict(color="#10B981", width=3.5),
        marker=dict(size=9, color="#10B981"),
        hovertemplate="<b>FY %{x}</b><br>Free Cash Flow: <b>$%{y:.2f}B</b><extra></extra>"
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        barmode="group",
        xaxis=dict(type="category", title="Fiscal Year", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Amount ($ Billions)", tickprefix="$", ticksuffix="B")
    )
    return fig

def create_balance_sheet_chart(bs_data: List[Dict[str, Any]], symbol: str) -> go.Figure:
    """Generates Balance Sheet Capital Structure breakdown (Cash vs Debt vs Equity)."""
    fig = go.Figure()
    if not bs_data or (isinstance(bs_data, list) and "error" in bs_data[0]):
        return fig

    df = pd.DataFrame(bs_data)
    if "date" not in df.columns:
        return fig

    df["year"] = pd.to_datetime(df["date"]).dt.year.astype(str)
    df = df.sort_values("year")

    for col in ["cashAndCashEquivalents", "cashAndShortTermInvestments", "totalDebt", "totalStockholdersEquity", "totalAssets"]:
        if col in df.columns:
            df[f"{col}_B"] = df[col] / 1e9

    cash_col = "cashAndShortTermInvestments_B" if "cashAndShortTermInvestments_B" in df.columns else "cashAndCashEquivalents_B"

    fig.add_trace(go.Bar(
        x=df["year"], y=df.get(cash_col, [0]*len(df)),
        name="Cash & Short-Term Inv ($B)",
        marker_color="#10B981",
        hovertemplate="<b>FY %{x}</b><br>Cash & Inv: <b>$%{y:.2f}B</b><extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df["year"], y=df.get("totalDebt_B", [0]*len(df)),
        name="Total Debt ($B)",
        marker_color="#F43F5E",
        hovertemplate="<b>FY %{x}</b><br>Total Debt: <b>$%{y:.2f}B</b><extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df["year"], y=df.get("totalStockholdersEquity_B", [0]*len(df)),
        name="Stockholders Equity ($B)",
        marker_color="#FB923C",
        hovertemplate="<b>FY %{x}</b><br>Stockholders Equity: <b>$%{y:.2f}B</b><extra></extra>"
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        barmode="group",
        xaxis=dict(type="category", title="Fiscal Year", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Amount ($ Billions)", tickprefix="$", ticksuffix="B")
    )
    return fig

def create_target_price_gauge(current_price: float, dcf_val: Optional[Dict[str, Any]], target_val: Optional[Dict[str, Any]], symbol: str) -> go.Figure:
    """Generates DCF Intrinsic Value & Analyst Consensus Price Target comparison chart."""
    fig = go.Figure()
    
    categories = ["Current Price"]
    prices = [current_price]
    colors = ["#64748B"]

    if dcf_val and isinstance(dcf_val, dict) and "dcf" in dcf_val:
        dcf_price = dcf_val["dcf"]
        categories.append("DCF Intrinsic Fair Value")
        prices.append(dcf_price)
        colors.append("#10B981" if dcf_price >= current_price else "#F43F5E")

    if target_val and isinstance(target_val, dict):
        avg_target = target_val.get("lastMonthAvgPriceTarget") or target_val.get("lastQuarterAvgPriceTarget")
        if avg_target:
            categories.append("Wall St Consensus Target")
            prices.append(avg_target)
            colors.append("#FF6B00")

    fig.add_trace(go.Bar(
        x=categories,
        y=prices,
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Target/Price: <b>$%{y:.2f}</b><extra></extra>"
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Price ($ USD)", tickprefix="$")
    )
    return fig

def create_peer_comparison_chart(peers_data: List[Dict[str, Any]], current_symbol: str) -> go.Figure:
    """Generates sector competitor market cap comparison chart."""
    fig = go.Figure()
    if not peers_data or (isinstance(peers_data, list) and "error" in peers_data[0]):
        return fig

    df = pd.DataFrame(peers_data)
    if "symbol" not in df.columns:
        return fig

    df["mktCap_B"] = df.get("mktCap", 0) / 1e9
    df = df.sort_values("mktCap_B", ascending=False).head(8)

    colors = ["#FF6B00" if s == current_symbol.upper() else "#475569" for s in df["symbol"]]

    fig.add_trace(go.Bar(
        x=df["symbol"],
        y=df["mktCap_B"],
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Market Cap: <b>$%{y:.2f}B</b><extra></extra>"
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Market Cap ($ Billions)", tickprefix="$", ticksuffix="B")
    )
    return fig

def create_ratios_chart(ratios_data: List[Dict[str, Any]], symbol: str) -> go.Figure:
    """Generates financial margin and ratio trends over time."""
    fig = go.Figure()
    if not ratios_data or (isinstance(ratios_data, list) and "error" in ratios_data[0]):
        return fig
        
    df = pd.DataFrame(ratios_data)
    if "date" not in df.columns:
        return fig

    df["year"] = pd.to_datetime(df["date"]).dt.year
    df = df.sort_values("year")

    for col in ["grossProfitMargin", "netProfitMargin", "operatingProfitMargin", "returnOnEquity"]:
        if col in df.columns:
            df[f"{col}_pct"] = df[col] * 100

    if "grossProfitMargin_pct" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df["grossProfitMargin_pct"],
            name="Gross Margin %",
            mode="lines+markers",
            line=dict(color="#FF6B00", width=3)
        ))
    if "operatingProfitMargin_pct" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df["operatingProfitMargin_pct"],
            name="Operating Margin %",
            mode="lines+markers",
            line=dict(color="#A78BFA", width=3)
        ))
    if "netProfitMargin_pct" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df["netProfitMargin_pct"],
            name="Net Profit Margin %",
            mode="lines+markers",
            line=dict(color="#10B981", width=3)
        ))
    if "returnOnEquity_pct" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["year"], y=df["returnOnEquity_pct"],
            name="Return on Equity (ROE) %",
            mode="lines+markers",
            line=dict(color="#FB923C", width=3, dash="dash")
        ))

    fig.update_layout(
        **PLOT_LAYOUT,
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Percentage (%)", ticksuffix="%")
    )
    return fig

def create_price_change_chart(change_data: Dict[str, Any], symbol: str) -> go.Figure:
    """Generates a percentage price performance chart across time horizons."""
    fig = go.Figure()
    if not change_data or "error" in change_data:
        return fig

    horizons = ["1D", "5D", "1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]
    values = [change_data.get(h, 0) for h in horizons]
    colors = ["#10B981" if v >= 0 else "#F43F5E" for v in values]

    fig.add_trace(go.Bar(
        x=horizons,
        y=values,
        marker_color=colors,
        hovertemplate="<b>%{x} Horizon</b><br>Return: <b>%{y:+.2f}%</b><extra></extra>"
    ))

    fig.update_layout(
        **PLOT_LAYOUT,
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title="Percentage Change (%)", ticksuffix="%")
    )
    return fig
