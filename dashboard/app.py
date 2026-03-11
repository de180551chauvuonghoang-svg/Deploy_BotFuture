import streamlit as st
import pandas as pd
import time
import os
import sys
import plotly.graph_objects as go
import io
import warnings
from datetime import datetime
import pandas as pd

# Silence annoying pandas warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
pd.set_option('future.no_silent_downcasting', True)

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from core.exchange import ExchangeHandler

st.set_page_config(page_title="Trading Bot Dashboard", layout="wide", page_icon="📊")

# Initialize Session State
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = Config.TRADING_PAIRS[0]

# Initialize Exchange
@st.cache_resource
def get_exchange():
    return ExchangeHandler()

exchange = get_exchange()

# Optimized Data Fetching (Fast Cache)
@st.cache_data(ttl=30)
def fetch_ohlcv_cached(symbol, timeframe, limit=200):
    return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

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

# 1. Real-time Metrics and Positions Fragment
@st.fragment(run_every=5) # Real-time feel every 5 seconds
def show_realtime_data():
    positions = exchange.fetch_positions(Config.TRADING_PAIRS)
    balance = exchange.get_balance()
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    col_stat1.metric("Account Balance", f"{balance:,.2f} USDT")
    col_stat2.metric("Active Positions", len(positions))
    
    total_upnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions)
    col_stat3.metric("Unrealized PnL", f"{total_upnl:,.2f} USDT", delta_color="normal")
    col_stat4.metric("Status", "🟢 Running" if exchange.dry_run or exchange.exchange.api_key else "🔴 Error")

    st.header("⚡ Active Trading Positions")
    
    if positions:
        for pos in positions:
            side = pos['side'].upper()
            color = "#2ebd85" if side == "LONG" else "#f6465d"
            upnl = float(pos.get('unrealizedPnl', 0))
            margin = float(pos.get('initialMargin', 0))
            roi = (upnl / margin * 100) if margin > 0 else 0
            leverage = pos.get('leverage', '10')
            
            st.markdown(f"""
            <div style="border-left: 5px solid {color}; padding: 15px; border-radius: 5px; margin-bottom: 5px; background-color: rgba(255,255,255,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 20px; font-weight: bold; color: {color};">{pos['symbol']}</span>
                        <span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px; margin-left: 10px;">{side} {leverage}x</span>
                    </div>
                    <div style="text-align: right;">
                        <p style="margin: 0; color: #848e9c; font-size: 14px;">Unrealized PnL (USDT)</p>
                        <p style="margin: 0; font-size: 20px; font-weight: bold; color: {'#2ebd85' if upnl >= 0 else '#f6465d'};">
                            {upnl:+.2f} ({roi:+.2f}%)
                        </p>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 15px;">
                    <div>
                        <p style="margin: 0; color: #848e9c; font-size: 13px;">Size</p>
                        <p style="margin: 0; font-weight: 500;">{pos['contracts']}</p>
                    </div>
                    <div>
                        <p style="margin: 0; color: #848e9c; font-size: 13px;">Entry Price</p>
                        <p style="margin: 0; font-weight: 500;">{float(pos['entryPrice']):,.4f}</p>
                    </div>
                    <div>
                        <p style="margin: 0; color: #848e9c; font-size: 13px;">Target TP1</p>
                        <p style="margin: 0; font-weight: 500; color: #2ebd85;">{float(pos.get('tp1', 0)):,.4f}</p>
                    </div>
                    <div>
                        <p style="margin: 0; color: #848e9c; font-size: 13px;">Stop Loss</p>
                        <p style="margin: 0; font-weight: 500; color: #f6465d;">{float(pos.get('sl', 0)):,.4f}</p>
                    </div>
                    <div>
                        <p style="margin: 0; color: #848e9c; font-size: 13px;">Mark Price</p>
                        <p style="margin: 0; font-weight: 500;">{float(pos.get('markPrice', pos['entryPrice'])):,.4f}</p>
                    </div>
                    <div>
                        <p style="margin: 0; color: #848e9c; font-size: 13px;">Margin</p>
                        <p style="margin: 0; font-weight: 500;">{margin:,.2f} USDT</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 1. Row for Chart Action
            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn1:
                # Using latest streamlit width parameter if applicable, or keeping use_container_width=True
                if st.button(f"📈 SHOW CHART: {pos['symbol']}", key=f"btn_chart_{pos['symbol']}", use_container_width=True):
                    st.session_state.selected_symbol = pos['symbol']
                    st.session_state.selector_global = pos['symbol']
                    st.rerun()
            
            with col_btn2:
                # 🛑 MANUAL CLOSE BUTTON
                if st.button(f"✖️ CLOSE", key=f"btn_close_{pos['symbol']}", use_container_width=True, type="secondary", help=f"Tất toán lệnh {pos['symbol']} ngay lập tức"):
                    with st.spinner(f"Closing {pos['symbol']}..."):
                        try:
                            # Determine reverse side
                            rev_side = 'sell' if side == 'LONG' else 'buy'
                            amt = abs(float(pos['contracts']))
                            
                            # Execute close order
                            res = exchange.create_order(pos['symbol'], rev_side, amt)
                            
                            if res and res.get('status') == 'closed' or res.get('id'):
                                st.toast(f"✅ Đã đóng lệnh {pos['symbol']} thành công!", icon='🚀')
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"❌ Không thể đóng lệnh {pos['symbol']}")
                        except Exception as e:
                            st.error(f"Error closing position: {e}")
    else:
        st.info("No active positions currently. Waiting for SMC triggers...")

@st.fragment(run_every=90) # Less frequent scanner
def show_scanner():
    st.header("📡 Market Scanner (SMC Setups)")
    st.info("Scanner updates every 90 seconds to save bandwidth.")
    
    all_signals = []
    scan_progress = st.progress(0, text="Scanning markets...")
    balance_local = exchange.get_balance()
    
    for i, symbol in enumerate(Config.TRADING_PAIRS):
        scan_progress.progress((i + 1) / len(Config.TRADING_PAIRS), text=f"Analyzing {symbol}...")
        try:
            df_15m_all = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
            df_1h_all = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=200)
            df_4h_all = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=200)
            
            from strategy.smc_strategy import SMCStrategy
            strategy = SMCStrategy()
            sig_data_all = strategy.generate_signal(symbol, exchange, df_4h_all, df_1h_all, df_15m_all, balance=balance_local)
            conf_local = sig_data_all.get("confluences", {})
            
            all_signals.append({
                "Symbol": symbol,
                "Signal": sig_data_all['signal'],
                "Price": sig_data_all.get('entry', 0.0),
                "Score": conf_local.get('score', 0.0),
                "Regime": conf_local.get('regime', 'N/A'),
                "Reason": sig_data_all.get('reason', 'N/A')
            })
        except: continue

    scan_progress.empty()
    
    if all_signals:
        sig_df = pd.DataFrame(all_signals)
        def color_signal(row):
            if row['Signal'] == 'LONG': return ['background-color: rgba(46, 189, 133, 0.2)']*len(row)
            if row['Signal'] == 'SHORT': return ['background-color: rgba(246, 70, 93, 0.2)']*len(row)
            return ['']*len(row)
            
        st.table(sig_df.style.apply(color_signal, axis=1).format({"Price": "{:,.4f}", "Score": "{:.1f}"}))

# Execute top section
show_realtime_data()

# Selection for the global focus (Chart + Signals)
selected_symbol = st.selectbox(
    "🔍 Select Trading Pair to Focus",
    Config.TRADING_PAIRS,
    key="selector_global"
)

# Sync state
st.session_state.selected_symbol = selected_symbol

# Global data for non-fragment sections
balance = exchange.get_balance()
positions = exchange.fetch_positions(Config.TRADING_PAIRS)

from strategy.smc_strategy import SMCStrategy
strategy = SMCStrategy()

# 2. Tabs
tab1, tab2 = st.tabs(["🎯 Market Hub", "🏦 Account Manager"])

with tab1:
    # 3. Focus Section (Chart & SMC)
    with st.status(f"� Preparing Analysis for {selected_symbol}...", expanded=True) as status:
        st.write("� Fetching real-time market data...")
        # Use Cached fetching for speed
        df_15m = fetch_ohlcv_cached(selected_symbol, timeframe='15m', limit=200)
        df_1h = fetch_ohlcv_cached(selected_symbol, timeframe='1h', limit=200)
        df_4h = fetch_ohlcv_cached(selected_symbol, timeframe='4h', limit=200)
        
        st.write("🧠 Analyzing SMC structures (OB/FVG/Bias)...")
        sig_data = strategy.generate_signal(selected_symbol, exchange, df_4h, df_1h, df_15m, balance=balance)

        st.write("📊 Finalizing market chart...")
        if sig_data and "confluences" in sig_data:
            conf = sig_data["confluences"]
            # These will render inside the status if we don't move them, so we just finish status first
        
        status.update(label=f"✅ {selected_symbol} Analysis Ready", state="complete", expanded=False)

    # Render main content outside the status so it's clean
    if sig_data and "confluences" in sig_data:
        conf = sig_data["confluences"]
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bias", conf['bias'])
        m2.metric("Regime", conf['regime'])
        m3.metric("OB/FVG Hit", "✅" if conf['ob_hit'] or conf['fvg_hit'] else "❌")
        m4.metric("SMC Score", f"{conf['score']:.1f}")
        st.progress(min(conf['score'] / 10.0, 1.0))

    if df_15m is not None and not df_15m.empty:
        # ⚡ CRITICAL: Ensure all numeric types and no NaNs for Plotly browser rendering
        df_plot = df_15m.copy()
        for col in ['open', 'high', 'low', 'close']:
            df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
        df_plot.dropna(subset=['open', 'high', 'low', 'close'], inplace=True)
        
        if not df_plot.empty:
            # 🛡️ Robust Timezone Handling: Check if index is DatetimeIndex before accessing .tz
            if isinstance(df_plot.index, pd.DatetimeIndex):
                x_data = df_plot.index.tz_localize(None) if df_plot.index.tz is not None else df_plot.index
            else:
                # Fallback: If it's a RangeIndex (e.g. from old cache), try to convert if 'timestamp' exists
                if 'timestamp' in df_plot.columns:
                    df_plot['timestamp'] = pd.to_datetime(df_plot['timestamp'])
                    df_plot.set_index('timestamp', inplace=True)
                    x_data = df_plot.index.tz_localize(None) if df_plot.index.tz is not None else df_plot.index
                else:
                    x_data = df_plot.index
            
            fig = go.Figure(data=[go.Candlestick(
                x=x_data,
                open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'],
                name="Market Data"
            )])

            curr_pos = next((p for p in positions if p['symbol'] == selected_symbol), None)
            if curr_pos:
                try:
                    entry_px = float(curr_pos['entryPrice'])
                    side = curr_pos['side'].upper()
                    color = "#2ebd85" if side in ["LONG", "BUY"] else "#f6465d"
                    
                    # Entry horizontal line
                    fig.add_hline(y=entry_px, line_dash="dash", line_color=color, annotation_text=f"ENTRY ({side})")
                    
                    entry_time = curr_pos.get('entryTime')
                    if entry_time:
                        # Normalize to UTC and then to naive for plotting consistency
                        entry_dt = pd.to_datetime(entry_time, utc=True).tz_localize(None)
                        
                        # Only plot annotation if it's within a 24h window of current data to avoid X-axis stretching
                        if entry_dt > df_plot.index[0].tz_localize(None) - pd.Timedelta(hours=24):
                            fig.add_annotation(
                                x=entry_dt, y=entry_px,
                                text=f"ENTRY @ {entry_px:,.4f}", showarrow=True, arrowhead=7, 
                                ax=0, ay=-40 if side in ["LONG", "BUY"] else 40,
                                bgcolor=color, font=dict(color="white")
                            )
                except Exception as e:
                    st.warning(f"Could not plot entry markers: {e}")
    
            fig.update_layout(
                template="plotly_dark", 
                xaxis_rangeslider_visible=False, 
                height=500, 
                margin=dict(l=10, r=10, t=10, b=10),
                uirevision='keep' # Keep zoom level on refresh
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error(f"⚠️ No valid candles to display for {selected_symbol}")
    else:
        st.error(f"⚠️ Could not fetch data for {selected_symbol}")

    st.divider()
    show_scanner()

with tab2:
    st.header("🏦 Financial Management")
    col_bal1, col_bal2, col_bal3 = st.columns(3)
    col_bal1.metric("Wallet Balance", f"{balance:,.2f} USDT")
    total_upnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions)
    col_bal2.metric("Total Unrealized PnL", f"{total_upnl:,.2f} USDT")
    equity = balance + total_upnl
    col_bal3.metric("Total Equity", f"{equity:,.2f} USDT")

    st.write("---")
    st.subheader("🚀 Active Positions Stats (Real-time)")
    if positions:
        pos_df = pd.DataFrame(positions)
        # Calculate some health metrics
        avg_roi = sum((float(p.get('unrealizedPnl', 0)) / float(p.get('initialMargin', 1)) * 100) for p in positions) / len(positions)
        total_margin = sum(float(p.get('initialMargin', 0)) for p in positions)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Avg. Unrealized ROI", f"{avg_roi:+.2f}%")
        m2.metric("Total Margin Busy", f"{total_margin:,.2f} USDT")
        m3.metric("Health Factor", "🟢 SAFE" if total_margin < balance * 0.5 else "🟡 CAUTION" if total_margin < balance * 0.8 else "🔴 DANGER")
    else:
        st.info("No active positions to display real-time stats.")

    if positions:
        st.subheader("📊 Portfolio Allocation")
        pie_df = pd.DataFrame(positions)
        fig_pie = go.Figure(data=[go.Pie(labels=pie_df['symbol'], values=pie_df['initialMargin'].astype(float), hole=.3)])
        fig_pie.update_layout(template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    st.subheader("📊 Closed Trade Reports (Excel Export)")
    
    # Load history safely
    if hasattr(exchange, '_load_trade_history'):
        history = exchange._load_trade_history()
    else:
        # Fallback if cache is stale
        import json
        history_file = "data/trade_history.json"
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
    
    if history:
        hist_df = pd.DataFrame(history)
        hist_df['entryTime'] = pd.to_datetime(hist_df['entryTime']).dt.tz_localize(None)
        hist_df['exitTime'] = pd.to_datetime(hist_df['exitTime']).dt.tz_localize(None)
        
        # Summary Stats
        total_trades = len(hist_df)
        winning_trades = len(hist_df[hist_df['pnl'] > 0])
        win_rate = (winning_trades / total_trades) * 100
        total_pnl = hist_df['pnl'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Trades", total_trades)
        c2.metric("Win Rate", f"{win_rate:.2f}%")
        c3.metric("Total Net Profit", f"{total_pnl:.2f} USDT", 
                  delta=f"{total_pnl:.2f}", delta_color="normal" if total_pnl >= 0 else "inverse")
        
        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            hist_df.to_excel(writer, index=False, sheet_name='TradeHistory')
            # Add summary sheet
            summary_data = {
                "Metric": ["Total Trades", "Winning Trades", "Win Rate (%)", "Total PnL (USDT)", "Avg ROI (%)"],
                "Value": [total_trades, winning_trades, f"{win_rate:.2f}%", f"{total_pnl:.2f}", f"{hist_df['roi'].mean():.2f}%"]
            }
            pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
        
        excel_data = output.getvalue()
        
        st.download_button(
            label="📄 DOWNLOAD PROFESSIONAL FINANCIAL REPORT (EXCEL)",
            data=excel_data,
            file_name=f"Trading_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
        st.write("---")
        st.subheader("🕒 Recent Closed Trades (History)")
        st.dataframe(hist_df.sort_values('exitTime', ascending=False).head(10), use_container_width=True)
    else:
        st.warning("📥 **No Trade History Recorded Yet.**")
        st.info("""
            **Tại sao tôi chưa thấy báo cáo tài chính?**
            - Báo cáo này chỉ ghi nhận các lệnh đã **ĐÓNG** (Realized PnL).
            - Hiện tại bạn đang có lệnh đang **CHẠY** (Active), dữ liệu của chúng nằm ở tab chính hoặc phần 'Active Positions Stats' phía trên.
            - Ngay sau khi bot chốt lời (TP) hoặc cắt lỗ (SL) lệnh đầu tiên, nút Export Excel sẽ xuất hiện tại đây.
        """)

# 6. Logs
@st.fragment(run_every=15)
def show_logs():
    st.header("📜 Recent Activity")
    if os.path.exists(Config.LOG_FILE):
        with open(Config.LOG_FILE, 'r') as f:
            lines = f.readlines()[-15:]
            log_text = "".join(reversed(lines))
            st.code(log_text)

show_logs()
