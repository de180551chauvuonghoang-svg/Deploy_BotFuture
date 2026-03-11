import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import ccxt
from datetime import datetime

st.title("XRP PLOT DEBUG")

exchange = ccxt.binance({'options': {'defaultType': 'future'}})
ohlcv = exchange.fetch_ohlcv('XRP/USDT', '15m', limit=50)

df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

st.write("Data Sample:")
st.dataframe(df.head())

st.write("Attempting Plotly...")
try:
    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close']
    )])
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig)
    st.success("Plotly Rendered successfully.")
except Exception as e:
    st.error(f"Plotly error: {e}")
