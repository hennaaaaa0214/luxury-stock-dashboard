"""
Luxury Stocks Dashboard
=======================
Streamlit app that mirrors the luxury_stocks_analysis notebook
with interactive date selection and Plotly charts.
"""

import time
import warnings
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Luxury Stocks Dashboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Colour palette ─────────────────────────────────────────────────────────────
COLOURS = {
    "LVMH":           "#ebebeb",
    "Hermes":         "#c9935a",
    "Kering":         "#8b0000",
    "Luxury Basket":  "#7b2d8b",
    "S&P 500":        "#2d9b5a",
}

TICKERS = {
    "MC.PA":  "LVMH",
    "RMS.PA": "Hermes",
    "KER.PA": "Kering",
    "^GSPC":  "S&P 500",
}

LUXURY_STOCKS = ["LVMH", "Hermes", "Kering"]
TRADING_DAYS  = 252

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background: linear-gradient(160deg, #0f0f1a 0%, #1a1a2e 100%);
    }
    section[data-testid="stSidebar"] * { color: #e8e8f0 !important; }
    section[data-testid="stSidebar"] .stDateInput label,
    section[data-testid="stSidebar"] .stSlider label { color: #c0c0d8 !important; }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1c1c2e 0%, #16213e 100%);
        border: 1px solid #2d2d4e;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    div[data-testid="metric-container"] label { color: #a0a0c8 !important; font-size: 0.78rem !important; }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #ffffff !important; font-size: 1.4rem !important; font-weight: 700 !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

    /* Section headers */
    h2 {
        color: #c9935a;
        border-bottom: 1px solid #2d2d4e;
        padding-bottom: 6px;
        letter-spacing: 0.02em;
        font-weight: 600;
    }
    h3 {
        color: #e8e8f0;
        font-weight: 500;
        letter-spacing: 0.01em;
    }

    /* Main background */
    .main .block-container { background: #0d0d1a; padding-top: 2rem; }

    /* Expander */
    details summary { color: #c9935a !important; }

    /* DataFrame */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Luxury Stocks")
    st.markdown("*Analyse whether luxury stocks outperform the broader market.*")
    st.markdown("---")

    st.markdown("### Date Range")
    start_date = st.date_input(
        "Start date",
        value=date(2018, 1, 1),
        min_value=date(2010, 1, 1),
        max_value=date.today(),
    )
    end_date = st.date_input(
        "End date",
        value=date(2025, 12, 31),
        min_value=date(2010, 1, 2),
        max_value=date.today(),
    )

    if start_date >= end_date:
        st.error("Start date must be before end date.")
        st.stop()

    st.markdown("---")
    st.markdown("### Rolling Window")
    rolling_window = st.slider("Volatility window (days)", 10, 90, 30, step=5)

    st.markdown("---")
    st.caption(
        "Data sourced from Yahoo Finance via `yfinance`.  \n"
        "Currency effects are **not** adjusted — European stocks trade in EUR, "
        "S&P 500 in USD."
    )

# ── Data fetching ──────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def load_prices(start: str, end: str) -> tuple[pd.DataFrame, list]:
    """Download adjusted close prices one ticker at a time with retries.

    Uses individual yf.Ticker().history() calls (more reliable than yf.download
    for mixed-exchange tickers). yfinance manages its own curl_cffi session.

    Returns
    -------
    (prices_df, failed_names)
        prices_df   : DataFrame of Close prices (columns = friendly names)
        failed_names: list of ticker friendly names that could not be fetched
    """
    frames: list[pd.Series] = []
    failed: list[str] = []

    for symbol, name in TICKERS.items():
        success = False
        for attempt in range(3):
            try:
                tk = yf.Ticker(symbol)
                hist = tk.history(
                    start=start,
                    end=end,
                    auto_adjust=True,
                )
                if not hist.empty:
                    # Normalise timezone-aware index to plain dates
                    series = hist["Close"].copy()
                    series.index = series.index.normalize().tz_localize(None)
                    frames.append(series.rename(name))
                    success = True
                    break
            except Exception:
                pass

            # Exponential back-off before retry
            if attempt < 2:
                time.sleep(2 ** attempt)

        if not success:
            failed.append(name)

    if not frames:
        return pd.DataFrame(), failed

    # Align on a common date index (inner join = only days all markets traded)
    df = pd.concat(frames, axis=1).dropna()
    return df, failed


with st.spinner("Fetching data from Yahoo Finance…"):
    prices, failed_tickers = load_prices(str(start_date), str(end_date))

if failed_tickers:
    st.warning(
        f"Could not load: **{', '.join(failed_tickers)}**. "
        "Charts show only the tickers that loaded. If this persists, "
        "Yahoo Finance may be rate-limiting — wait a moment and refresh."
    )

if prices.empty or len(prices) < 5:
    st.error("No data returned for the selected date range. Try a wider range.")
    st.stop()

# ── Derived data ───────────────────────────────────────────────────────────────
daily_returns = prices.pct_change().dropna()

# Luxury Basket: equal-weight average of whichever luxury stocks loaded
available_luxury = [s for s in LUXURY_STOCKS if s in daily_returns.columns]
if available_luxury:
    daily_returns["Luxury Basket"] = daily_returns[available_luxury].mean(axis=1)

prices_norm = prices / prices.iloc[0] * 100
if "Luxury Basket" in daily_returns.columns:
    prices_norm["Luxury Basket"] = (
        (1 + daily_returns["Luxury Basket"]).cumprod() * 100
    )

rolling_vol = (
    daily_returns.rolling(window=rolling_window).std() * np.sqrt(TRADING_DAYS)
)

# ── Metrics computation ────────────────────────────────────────────────────────
def compute_summary(returns: pd.DataFrame) -> pd.DataFrame:
    n = len(returns)
    summary = pd.DataFrame(index=returns.columns)
    summary["Total Return"]         = (1 + returns).prod() - 1
    summary["Annualized Return"]    = (1 + returns).prod() ** (TRADING_DAYS / n) - 1
    summary["Annualized Volatility"] = returns.std() * np.sqrt(TRADING_DAYS)
    summary["Sharpe Ratio"]         = (
        summary["Annualized Return"] / summary["Annualized Volatility"]
    )  # risk-free rate = 0 (simplified)
    summary["Worst Day"]            = returns.min()
    summary["Best Day"]             = returns.max()
    return summary.sort_values("Total Return", ascending=False)


summary = compute_summary(daily_returns)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#c9935a; font-size:2.2rem; letter-spacing:0.03em; font-weight:700;'>"
    "Luxury Stocks Dashboard</h1>",
    unsafe_allow_html=True,
)
date_str = f"{prices.index[0].date()}  →  {prices.index[-1].date()}"
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(
        f"**Research question:** Are luxury stocks more resilient than the market?  \n"
        f"**Period:** {date_str}  |  **Trading days:** {len(prices):,}"
    )
with col_h2:
    st.markdown(
        f"<div style='text-align:right; color:#888; font-size:0.8rem;'>Data as of {date.today()}</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Metric cards ───────────────────────────────────────────────────────────────
st.markdown("## Performance Summary")

all_cols = ["Hermes", "LVMH", "Kering", "Luxury Basket", "S&P 500"]
metric_cols = st.columns(len(all_cols))

for col_ui, name in zip(metric_cols, all_cols):
    if name not in summary.index:
        continue
    tot   = summary.loc[name, "Total Return"]
    ann   = summary.loc[name, "Annualized Return"]
    vol   = summary.loc[name, "Annualized Volatility"]
    sharpe = summary.loc[name, "Sharpe Ratio"]
    colour = COLOURS.get(name, "#888")
    col_ui.markdown(
        f"<div style='border-left: 4px solid {colour}; padding-left:8px;'>"
        f"<span style='color:{colour}; font-weight:700; font-size:1rem;'>{name}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    col_ui.metric("Total Return",    f"{tot:+.1%}")
    col_ui.metric("Ann. Return",     f"{ann:+.1%}", f"Vol {vol:.1%}")
    col_ui.metric("Sharpe (rf=0)",   f"{sharpe:.2f}")

st.markdown("---")

# ── Chart 1 — Normalised price ─────────────────────────────────────────────────
st.markdown("## Normalized Price Performance")
st.caption("Base = 100 on the first trading day of the selected period.")

fig_price = go.Figure()

plot_cols = ["Hermes", "LVMH", "Kering", "Luxury Basket", "S&P 500"]
line_styles = {
    "Luxury Basket": dict(dash="dash", width=2.5),
    "S&P 500":       dict(dash="dot",  width=2.5),
}

for name in plot_cols:
    if name not in prices_norm.columns:
        continue
    lstyle = line_styles.get(name, dict(width=2))
    fig_price.add_trace(
        go.Scatter(
            x=prices_norm.index,
            y=prices_norm[name],
            name=name,
            line=dict(color=COLOURS[name], **lstyle),
            hovertemplate=f"<b>{name}</b><br>%{{x|%Y-%m-%d}}<br>Index: %{{y:.1f}}<extra></extra>",
        )
    )

fig_price.add_hline(y=100, line_dash="dot", line_color="#444", line_width=1)
fig_price.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0d0d1a",
    plot_bgcolor="#0d0d1a",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis=dict(showgrid=True, gridcolor="#1f1f35"),
    yaxis=dict(showgrid=True, gridcolor="#1f1f35", title="Index (Jan start = 100)"),
    hovermode="x unified",
    height=430,
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig_price, use_container_width=True)

# ── Charts 2 & 3 — Rolling vol + Risk/Return scatter ──────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    st.markdown(f"## {rolling_window}-Day Rolling Volatility")
    fig_vol = go.Figure()
    for name in plot_cols:
        if name not in rolling_vol.columns:
            continue
        lstyle = line_styles.get(name, dict(width=1.8))
        fig_vol.add_trace(
            go.Scatter(
                x=rolling_vol.index,
                y=rolling_vol[name],
                name=name,
                line=dict(color=COLOURS[name], **lstyle),
                hovertemplate=(
                    f"<b>{name}</b><br>%{{x|%Y-%m-%d}}<br>"
                    f"Ann. Vol: %{{y:.1%}}<extra></extra>"
                ),
            )
        )
    fig_vol.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d0d1a",
        plot_bgcolor="#0d0d1a",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor="#1f1f35"),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1f1f35",
            title="Annualized Volatility",
            tickformat=".0%",
        ),
        hovermode="x unified",
        height=370,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_vol, use_container_width=True)

with col_r:
    st.markdown("## Risk vs. Return")
    fig_scatter = go.Figure()
    for name in summary.index:
        colour = COLOURS.get(name, "#888")
        marker_size = 16 if name == "Luxury Basket" else 12
        fig_scatter.add_trace(
            go.Scatter(
                x=[summary.loc[name, "Annualized Volatility"]],
                y=[summary.loc[name, "Annualized Return"]],
                mode="markers+text",
                name=name,
                text=[name],
                textposition="top center",
                textfont=dict(size=10, color=colour),
                marker=dict(
                    color=colour,
                    size=marker_size,
                    line=dict(color="#ffffff", width=1),
                ),
                hovertemplate=(
                    f"<b>{name}</b><br>"
                    f"Ann. Return: %{{y:.1%}}<br>"
                    f"Ann. Volatility: %{{x:.1%}}<extra></extra>"
                ),
            )
        )
    fig_scatter.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d0d1a",
        plot_bgcolor="#0d0d1a",
        showlegend=False,
        xaxis=dict(
            showgrid=True,
            gridcolor="#1f1f35",
            title="Annualized Volatility",
            tickformat=".0%",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1f1f35",
            title="Annualized Return",
            tickformat=".0%",
        ),
        height=370,
        margin=dict(l=0, r=0, t=10, b=30),
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.markdown("---")

# ── Summary table ──────────────────────────────────────────────────────────────
st.markdown("## Full Metrics Table")

display_df = summary.copy()
display_df.index.name = "Asset"

fmt_pct   = lambda v: f"{v:+.2%}"
fmt_ratio = lambda v: f"{v:.3f}"

styled = (
    display_df
    .style
    .format({
        "Total Return":          fmt_pct,
        "Annualized Return":     fmt_pct,
        "Annualized Volatility": fmt_pct,
        "Sharpe Ratio":          fmt_ratio,
        "Worst Day":             fmt_pct,
        "Best Day":              fmt_pct,
    })
    .background_gradient(subset=["Total Return", "Annualized Return"], cmap="RdYlGn")
    .background_gradient(subset=["Annualized Volatility"], cmap="RdYlGn_r")
    .background_gradient(subset=["Sharpe Ratio"], cmap="RdYlGn")
)
st.dataframe(styled, use_container_width=True, height=240)

st.caption(
    "Sharpe Ratio uses a risk-free rate of **0%** (simplified). "
    "European stocks are priced in **EUR**; S&P 500 in **USD** — currency effects are not adjusted."
)

# ── Downturn comparison ────────────────────────────────────────────────────────
with st.expander("Worst Drawdown Periods", expanded=False):
    st.markdown(
        "The table below shows the **maximum drawdown** for each asset "
        "— the largest peak-to-trough decline over the selected period."
    )

    def max_drawdown(price_series: pd.Series) -> float:
        roll_max = price_series.cummax()
        drawdown = price_series / roll_max - 1
        return drawdown.min()

    dd_data = {}
    for name in plot_cols:
        if name == "Luxury Basket":
            series = prices_norm["Luxury Basket"] / 100
        elif name in prices_norm.columns:
            series = prices_norm[name] / 100
        else:
            continue
        dd_data[name] = max_drawdown(series)

    dd_df = pd.DataFrame.from_dict(
        dd_data, orient="index", columns=["Max Drawdown"]
    ).sort_values("Max Drawdown")

    styled_dd = dd_df.style.format({"Max Drawdown": "{:.1%}"}).background_gradient(
        subset=["Max Drawdown"], cmap="RdYlGn"
    )
    st.dataframe(styled_dd, use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#555; font-size:0.78rem;'>"
    "ACC102 Mini Assignment &nbsp;·&nbsp; Data via Yahoo Finance &nbsp;·&nbsp; "
    "For educational purposes only — not investment advice."
    "</div>",
    unsafe_allow_html=True,
)
