# Luxury Stocks Dashboard

An interactive Streamlit dashboard that analyses whether luxury stocks (LVMH, Hermès, Kering) outperform the broader S&P 500 market. 

---

## Features

- **Normalized price performance** — tracks cumulative returns from a common base of 100
- **Rolling volatility** — annualized volatility over a configurable window (10–90 days)
- **Risk vs. Return scatter** — plots each asset in annualized volatility / return space
- **Full metrics table** — total return, annualized return & volatility, Sharpe ratio, best/worst day
- **Maximum drawdown** — peak-to-trough analysis via a collapsible panel
- **Interactive controls** — custom date range and rolling-window slider in the sidebar
- **Live data** — prices fetched on demand from Yahoo Finance via `yfinance`, cached for 1 hour

---

## Project Structure

```
├── app.py                        # Main Streamlit application
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## Requirements

| Package | Minimum version |
|---------|----------------|
| Python  | 3.10+          |
| streamlit | 1.32        |
| yfinance  | 0.2         |
| pandas    | 2.0         |
| numpy     | 1.24        |
| plotly    | 5.18        |
| matplotlib | 3.7        |

---

## Setup & Installation

**1. Clone or download the project**

```bash
git clone <repo-url>
cd luxury-stock-dashboard
```

**2. Create and activate a virtual environment** *(recommended)*

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the App

```bash
streamlit run app.py
```

Streamlit will open the dashboard automatically in your default browser at `http://localhost:8501`.

---

## Usage

| Control | Location | Description |
|---------|----------|-------------|
| **Start / End date** | Sidebar | Select the analysis period (any range from 2010 to today) |
| **Volatility window** | Sidebar | Number of trading days used for the rolling volatility calculation (default: 30) |
| **Worst Drawdown Periods** | Main panel | Click to expand the maximum drawdown table |

> **Note:** European stocks (LVMH, Hermès, Kering) are priced in **EUR**; the S&P 500 is in **USD**. Currency effects are **not** adjusted. The Sharpe Ratio uses a simplified risk-free rate of 0%.

---

## Data Source

Prices are downloaded from **Yahoo Finance** using the `yfinance` library. Results are cached for **1 hour** to avoid excessive API requests.

| Ticker | Name | Exchange |
|--------|------|----------|
| `MC.PA` | LVMH Moët Hennessy Louis Vuitton | Euronext Paris |
| `RMS.PA` | Hermès International | Euronext Paris |
| `KER.PA` | Kering | Euronext Paris |
| `^GSPC` | S&P 500 Index | — |
