import streamlit as st
import pandas as pd
import time
import os
import plotly.graph_objects as go
from config.config import Config
from core.exchange import ExchangeHandler

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide", page_icon="📊")

# Initialize Exchange
@st.cache_resource
def get_exchange():
    return ExchangeHandler()

exchange = get_exchange()

# 0. Custom CSS to maximize width
st.markdown("""
<style>
    .main .block-container {
        max-width: 100%;
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    iframe {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Crypto Futures Trading Bot Dashboard")

# Sidebar
st.sidebar.header("⚙️ Configuration")
st.sidebar.info(f"**Exchange:** {Config.EXCHANGE.upper()}")
st.sidebar.info(f"**Mode:** {'Paper Trading (Local)' if exchange.dry_run else 'Live/Sandbox'}")
st.sidebar.info(f"**Timeframe:** {Config.TIMEFRAME}")
st.sidebar.write("---")
st.sidebar.write(f"**Pairs:** {', '.join(Config.TRADING_PAIRS)}")

# 1. Fetch Data
balance = exchange.get_balance()
positions = exchange.fetch_positions(Config.TRADING_PAIRS)

col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
col_stat1.metric("Account Balance", f"{balance:,.2f} USDT")
col_stat2.metric("Active Positions", len(positions))

total_upnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions)
col_stat3.metric("Unrealized PnL", f"{total_upnl:,.2f} USDT", delta_color="normal")
col_stat4.metric("Status", "🟢 Running" if exchange.dry_run or exchange.exchange.api_key else "🔴 Error")

# Selection for the global focus (Chart + Signals)
selected_symbol = st.selectbox(
    "🔍 Select Trading Pair to Focus",
    Config.TRADING_PAIRS,
    index=0
)

# 2. Tabs for better organization
tab1, tab2 = st.tabs(["🎯 Market Hub", "🏦 Account Manager"])

with tab1:
    # 3. Live Signals Section
    st.header("📡 Live Signal Alerts")
    
    # Check for live signals (read from log or separate file)
    # For now, let's display signals based on current market state
    col_sig1, col_sig2, col_sig3 = st.columns(3)
    
    # We fetch current signal for the selected symbol
    df_sig = exchange.fetch_ohlcv(selected_symbol, timeframe=Config.TIMEFRAME, limit=100)
    from strategy.base import SniperTrendStrategy
    strategy = SniperTrendStrategy()
    sig_data = strategy.generate_signals(df_sig)
    
    if sig_data:
        sig_val = sig_data['signal']
        sig_text = "BUY/LONG" if sig_val == 1 else ("SELL/SHORT" if sig_val == -1 else "NEUTRAL")
        sig_color = "green" if sig_val == 1 else ("red" if sig_val == -1 else "gray")
        
        col_sig1.metric("Current Signal", sig_text, delta=None, delta_color="normal")
        col_sig2.metric("Signal Price", f"{sig_data['price']:,.2f}")
        
        # Artificial ROI based on unrealized PnL of current position if exists
        curr_pos = next((p for p in positions if p['symbol'] == selected_symbol), None)
        if curr_pos:
            upnl = float(curr_pos.get('unrealizedPnl', 0))
            # Calculate ROI (Estimated)
            margin = float(curr_pos.get('initialMargin', 1)) or 1
            roi = (upnl / margin) * 100
            col_sig3.metric("Live ROI (%)", f"{roi:,.2f}%", delta=f"{upnl:,.2f} USDT")
        else:
            col_sig3.metric("Live ROI (%)", "N/A - No Position")

    # 4. Open Positions Table
    st.header("🛒 Open Positions")
    if positions:
        pos_df = pd.DataFrame(positions)
        # Calculate ROIs for all positions
        pos_df['ROI (%)'] = (pos_df['unrealizedPnl'].astype(float) / pos_df['initialMargin'].astype(float).replace(0, 1)) * 100
        
        cols = ['symbol', 'side', 'entryPrice', 'contracts', 'unrealizedPnl', 'ROI (%)', 'leverage']
        available_cols = [c for c in cols if c in pos_df.columns]
        st.dataframe(pos_df[available_cols].style.format({'ROI (%)': '{:.2f}%', 'unrealizedPnl': '{:.2f}'}), use_container_width=True)
    else:
        st.info("No active positions currently.")

    # 5. Binance-Style Market Analysis
    st.header("📈 Market Charting")
    tv_symbol = f"BINANCE:{selected_symbol.replace('/', '')}"
    tf_map = {'1m': '1', '5m': '5', '15m': '15', '30m': '30', '1h': '60', '4h': '240', '1d': 'D'}
    tv_interval = tf_map.get(Config.TIMEFRAME, '15')
    chart_height = 700

    tradingview_html = f"""
    <html>
    <body style="margin:0; padding:0; background-color:#0e1117;">
        <div id="tradingview_chart" style="height:{chart_height}px; width:100%;"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({{
          "width": "100%", "height": {chart_height},
          "symbol": "{tv_symbol}", "interval": "{tv_interval}",
          "timezone": "Etc/UTC", "theme": "dark", "style": "1", "locale": "en",
          "enable_publishing": false, "hide_top_toolbar": false, "container_id": "tradingview_chart",
          "studies": ["MASimple@tv-basicstudies", "RSI@tv-basicstudies", "MACD@tv-basicstudies"]
        }});
        </script>
    </body>
    </html>
    """
    st.components.v1.html(tradingview_html, height=chart_height + 20)

with tab2:
    st.header("🏦 Financial Management")
    
    col_bal1, col_bal2, col_bal3 = st.columns(3)
    col_bal1.metric("Wallet Balance", f"{balance:,.2f} USDT")
    
    # Calculate total unrealized
    total_upnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions)
    col_bal2.metric("Total Unrealized PnL", f"{total_upnl:,.2f} USDT")
    
    equity = balance + total_upnl
    col_bal3.metric("Total Equity", f"{equity:,.2f} USDT")

    st.write("---")
    st.subheader("📊 Portfolio Allocation")
    if positions:
        # Create a pie chart of margin allocation
        pie_df = pd.DataFrame(positions)
        fig = go.Figure(data=[go.Pie(labels=pie_df['symbol'], values=pie_df['initialMargin'].astype(float), hole=.3)])
        fig.update_layout(template="plotly_dark", title="Margin Allocation per Symbol")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("💰 Risk Exposure")
        total_margin = sum(float(p.get('initialMargin', 0)) for p in positions)
        margin_usage = (total_margin / balance) * 100 if balance > 0 else 0
        st.progress(min(margin_usage / 100, 1.0), text=f"Margin Usage: {margin_usage:.2f}%")
        if margin_usage > 50:
            st.warning("⚠️ High margin usage detected! Monitor your risks.")
    else:
        st.info("No funds currently allocated to positions.")

# 6. Recent Logs
st.header("📜 Recent Activity")
if os.path.exists(Config.LOG_FILE):
    with open(Config.LOG_FILE, 'r') as f:
        logs = f.readlines()[-15:]
        log_text = "".join(reversed(logs))
        st.code(log_text)

# Auto-refresh
time.sleep(30)
st.rerun()
