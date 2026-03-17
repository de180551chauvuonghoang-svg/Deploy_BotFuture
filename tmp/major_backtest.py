import sys
import os
sys.path.append(os.getcwd())

import pandas as pd
from backtest.engine import Backtester
from strategy.smc_strategy import SMCStrategy
from config.config import Config
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Use current config
# AI_CONFIDENCE_THRESHOLD = 0.80
# MIN_SCORE_THRESHOLD = 8.5

MAJOR_PAIRS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'NEAR/USDT', 'LTC/USDT', 'XRP/USDT', 'DOGE/USDT', 'BNB/USDT', 'LINK/USDT', 'FIL/USDT']
CACHE_DIR = "data/cache"
DAYS_TO_TEST = 30 # Super fast 30-day "AI Pulse Check"

def load_data(symbol, timeframe):
    safe_symbol = symbol.replace("/", "_")
    found = None
    for d in [360, 180, 90]:
        f = f"{CACHE_DIR}/{safe_symbol}_{timeframe}_{d}d.csv"
        if os.path.exists(f):
            found = f
            break
    if not found: return None
    df = pd.read_csv(found, index_col='timestamp', parse_dates=True)
    df = df.sort_index()
    cutoff_date = df.index[-1] - pd.Timedelta(days=DAYS_TO_TEST)
    return df[df.index >= cutoff_date]

strategy = SMCStrategy(name="Aggressive_AI_SMC")
all_trades = []
initial_capital = 1300

print(f"--- BACKTEST: TOP 10 MAJORS | Period: {DAYS_TO_TEST} Days | AI: {Config.AI_CONFIDENCE_THRESHOLD:.0%} | Score: {Config.MIN_SCORE_THRESHOLD} ---")

for symbol in MAJOR_PAIRS:
    df_15m = load_data(symbol, '15m')
    df_1h = load_data(symbol, '1h')
    df_4h = load_data(symbol, '4h')
    
    if df_15m is None or df_1h is None or df_4h is None:
        print(f"Skipping {symbol} (Missing Cache)")
        continue
        
    print(f"Processing {symbol} ({len(df_15m)} rows)...")
    bt = Backtester(strategy, initial_capital=initial_capital)
    bt.run(df_15m, df_1h, df_4h)
    all_trades.extend(bt.trade_log)

if not all_trades:
    print("\n[!] NO TRADES FOUND with current strict filters (Score 8.5 + AI 80%).")
    print("Lowering Score Threshold to 7.0 for a comparative test...")
    Config.MIN_SCORE_THRESHOLD = 7.0
    for symbol in MAJOR_PAIRS:
        df_15m = load_data(symbol, '15m')
        df_1h = load_data(symbol, '1h')
        df_4h = load_data(symbol, '4h')
        if df_15m is None or df_1h is None or df_4h is None: continue
        bt = Backtester(strategy, initial_capital=initial_capital)
        bt.run(df_15m, df_1h, df_4h)
        all_trades.extend(bt.trade_log)

if all_trades:
    df = pd.DataFrame(all_trades)
    pnl = df['pnl'].sum()
    wr = (len(df[df['pnl'] > 0]) / len(df)) * 100
    print(f"\nFinal Report (Majors):")
    print(f"  Trades: {len(df)}")
    print(f"  Net PnL: ${pnl:.2f}")
    print(f"  Win Rate: {wr:.2f}%")
    print(f"  ROI: {(pnl/initial_capital)*100:.2f}%")
else:
    print("\nStill no trades even at Score 8.0. The strategy is extremely selective.")
