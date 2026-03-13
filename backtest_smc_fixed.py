#!/usr/bin/env python3
"""
Fixed Advanced SMC Strategy Backtest - Direct Cache Loading
Loads data from existing cache files without exchange handler
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import warnings
from datetime import datetime
from pathlib import Path

from backtest.engine import Backtester
from strategy.smc_strategy import SMCStrategy
from config.config import Config
from core.logger import logger

warnings.filterwarnings('ignore')
os.environ['IS_BACKTEST'] = 'true'

# Configuration
CACHE_DIR = "data/cache"
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'AVAX/USDT']
days = 800
initial_capital = 1300
config = Config()

def load_from_cache(symbol, timeframe):
    """Load data from cache file."""
    safe_symbol = symbol.replace("/", "_")
    cache_file = f"{CACHE_DIR}/{safe_symbol}_{timeframe}_{days}d.csv"
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col='timestamp', parse_dates=True)
        df = df.sort_index()
        return df
    except Exception as e:
        logger.error(f"Error loading {cache_file}: {e}")
        return None

print("=" * 80)
print("[BACKTEST] ADVANCED SMC STRATEGY")
print(f"   Periods: {days} days")
print(f"   Symbols: {len(symbols)}")
print(f"   Initial Capital: ${initial_capital:,.2f}")
print("=" * 80)
print()

strategy = SMCStrategy(name="AdvancedSMC")
all_trades = []
symbol_results = {}

for idx, symbol in enumerate(symbols, 1):
    print(f"[{idx:2d}/{len(symbols)}] Backtesting {symbol:15} ...", end=" ", flush=True)
    
    try:
        # Load data from cache
        df_15m = load_from_cache(symbol, '15m')
        df_1h = load_from_cache(symbol, '1h')
        df_4h = load_from_cache(symbol, '4h')
        
        if df_15m is None or df_1h is None or df_4h is None:
            print("[!] Cache missing")
            continue
        
        if len(df_15m) < 100 or len(df_1h) < 100 or len(df_4h) < 100:
            print("[!] Insufficient data")
            continue
        
        # Run backtest
        backtester = Backtester(strategy, initial_capital=initial_capital)
        report = backtester.run(df_15m=df_15m, df_1h=df_1h, df_4h=df_4h)
        
        # Get trade log from backtester
        trades = backtester.trade_log
        if trades:
            symbol_results[symbol] = {
                'trades': len(trades),
                'total_pnl': sum([t.get('pnl', 0) for t in trades]),
                'wins': len([t for t in trades if t.get('pnl', 0) > 0]),
            }
            all_trades.extend(trades)
            print(f"[OK] {len(trades)} trades, PnL: ${symbol_results[symbol]['total_pnl']:.2f}")
        else:
            print("[!] No trades")
            
    except Exception as e:
        print(f"[ERROR] {str(e)[:50]}")
        logger.error(f"Error backtesting {symbol}: {e}")
        continue

print()
print("=" * 80)
print("[RESULTS] ADVANCED SMC STRATEGY")
print("=" * 80)

if all_trades:
    total_trades = len(all_trades)
    total_pnl = sum([t.get('pnl', 0) for t in all_trades])
    total_wins = len([t for t in all_trades if t.get('pnl', 0) > 0])
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    roi = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
    
    print(f"Total Trades:     {total_trades}")
    print(f"Total Wins:       {total_wins}")
    print(f"Win Rate:         {win_rate:.2f}%")
    print(f"Total PnL:        ${total_pnl:,.2f}")
    print(f"ROI:              {roi:.2f}%")
    print()
    print("By Symbol:")
    for symbol in symbols:
        if symbol in symbol_results:
            r = symbol_results[symbol]
            print(f"  {symbol:15} {r['trades']:4d} trades, PnL: ${r['total_pnl']:10,.2f}, Win rate: {r['wins']/max(1,r['trades'])*100:.1f}%")
else:
    print("[!] No trades executed")

print()
print("[COMPLETE] Backtest completed!")
