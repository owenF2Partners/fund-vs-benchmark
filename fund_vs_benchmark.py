import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

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
    price_data.columns = tickers[:1]  # single ticker fallback

price_data = price_data.ffill().dropna()

# Verify both tickers present
available_tickers = price_data.columns.tolist()
missing = [t for t in tickers if t not in available_tickers]
if missing:
    st.error(f"Data for the following tickers could not be retrieved: {', '.join(missing)}")
    st.stop()

# Normalize
norm_data = price_data / price_data.iloc[0] * 100

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

# Final values
final_vals = norm_data.iloc[-1].round(2)
final_vals.index = [fund_name if t == fund_ticker else "Benchmark" for t in final_vals.index]

perf_table = pd.DataFrame({
    "Name": final_vals.index,
    "Final Value (Start = 100)": final_vals.values
})

# Round to 2 decimal places (again just in case)
perf_table["Final Value (Start = 100)"] = perf_table["Final Value (Start = 100)"].round(2)

# Display styled table (no index, white bold text)
styled_table = (
    perf_table.style
    .format({"Final Value (Start = 100)": "{:.2f}"})
    .set_table_styles(
        [
            {"selector": "th", "props": [("color", "white"), ("font-weight", "bold"), ("background-color", "#333")]},
            {"selector": "td", "props": [("color", "white"), ("font-weight", "bold")]}
        ]
    )
    .hide(axis="index")
    .to_html()
)

st.subheader("Final Value (Indexed to 100 at Start)")
st.markdown(styled_table, unsafe_allow_html=True)