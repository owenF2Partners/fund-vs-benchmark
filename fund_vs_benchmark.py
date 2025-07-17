import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np

# Set page config to wide
st.set_page_config(layout="wide")

st.title("Mutual Fund vs Benchmark Dashboard")

# Load CSV
df = pd.read_csv("FundsAndBenchmarks.csv")

# Sidebar: Fund selector
fund_ticker = st.selectbox(
    "Select Mutual Fund Ticker",
    df["Ticker"].unique()
)

# Get fund details
row = df[df["Ticker"] == fund_ticker].iloc[0]
benchmark_ticker = row["Benchmark Ticker"]
fund_name = row["Name"]
benchmark_name = row["New Benchmark Name"]

st.markdown(f"""
### {fund_name} ({fund_ticker})  
Benchmark: **{benchmark_name} ({benchmark_ticker})**
""")

# Time horizon selector
horizon = st.selectbox(
    "Select Time Horizon",
    options=["YTD", "1Y", "3Y", "5Y"],
    index=0
)

today = pd.Timestamp.today()
if horizon == "YTD":
    start = pd.Timestamp(year=today.year, month=1, day=1)
elif horizon == "1Y":
    start = today - pd.DateOffset(years=1)
elif horizon == "3Y":
    start = today - pd.DateOffset(years=3)
elif horizon == "5Y":
    start = today - pd.DateOffset(years=5)
else:
    start = pd.Timestamp(year=today.year, month=1, day=1)

end = today

st.write(f"Fetching data from {start.date()} to {end.date()}...")

tickers = [fund_ticker, benchmark_ticker]
data = yf.download(tickers, start=start, end=end)

if data.empty:
    st.error("No data was retrieved. Please check the tickers and try again.")
    st.stop()

# Always use 'Close'
if isinstance(data.columns, pd.MultiIndex):
    price_data = data["Close"].copy()
else:
    price_data = data.copy()
    price_data.columns = tickers[:1]  # fallback

price_data = price_data.ffill().dropna()

# Verify both tickers present
available_tickers = price_data.columns.tolist()
missing = [t for t in tickers if t not in available_tickers]
if missing:
    st.error(f"Data for the following tickers could not be retrieved: {', '.join(missing)}")
    st.stop()

# Calculate actual % return
start_prices = price_data.iloc[0]
end_prices = price_data.iloc[-1]
returns = ((end_prices - start_prices) / start_prices * 100).round(2)

# Rename indexes to fund name / benchmark
returns.index = [fund_name if t == fund_ticker else "Benchmark" for t in returns.index]

# Normalize for chart
norm_data = price_data / start_prices * 100

# Performance snapshot
st.subheader("Performance Snapshot")

col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div style="text-align: center; font-size: 24px; font-weight: bold; color: #1f77b4;">
    {fund_name} ({fund_ticker})  
    <br>
    {returns[fund_name]}%
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style="text-align: center; font-size: 24px; font-weight: bold; color: #1f77b4;">
    Benchmark ({benchmark_ticker})  
    <br>
    {returns['Benchmark']}%
    </div>
    """, unsafe_allow_html=True)

# Melt for plotting
df_melted = norm_data.reset_index().melt(id_vars="Date", var_name="Ticker", value_name="Normalized Price")

fig = px.line(
    df_melted,
    x="Date",
    y="Normalized Price",
    color="Ticker",
    title=f"{fund_name} ({fund_ticker}) vs {benchmark_name} ({benchmark_ticker}) - {horizon}",
    labels={"Normalized Price": "Normalized Value (Start = 100)"}
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# RISK METRICS
# ---------------------------

# Compute risk metrics for the fund
fund_prices = price_data[fund_ticker]
daily_returns = fund_prices.pct_change().dropna()

# Annualized volatility
volatility = daily_returns.std() * np.sqrt(252) * 100

# Max Drawdown
cum_returns = (1 + daily_returns).cumprod()
cum_max = cum_returns.cummax()
drawdowns = (cum_returns - cum_max) / cum_max
max_drawdown = drawdowns.min() * 100

# Historical 1-day 95% Value at Risk (VaR)
VaR_95 = np.percentile(daily_returns, 5) * 100

# Show snapshot
st.subheader("Risk Profile Snapshot (Mutual Fund Only)")

risk_cols = st.columns(3)

risk_cols[0].markdown(f"""
<div style="text-align:center; font-size:20px; font-weight:bold;">
Volatility<br><span style="color:#2c7be5;">{volatility:.2f}%</span>
</div>
""", unsafe_allow_html=True)

risk_cols[1].markdown(f"""
<div style="text-align:center; font-size:20px; font-weight:bold;">
Max Drawdown<br><span style="color:#e53e3e;">{max_drawdown:.2f}%</span>
</div>
""", unsafe_allow_html=True)

risk_cols[2].markdown(f"""
<div style="text-align:center; font-size:20px; font-weight:bold;">
95% Daily VaR<br><span style="color:#f0ad4e;">{VaR_95:.2f}%</span>
</div>
""", unsafe_allow_html=True)
