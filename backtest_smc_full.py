#!/usr/bin/env python3
"""
Full SMC Backtest - Exact Bot Configuration
23 pairs, $1,300 capital, 800 days historical data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import warnings
import time
from datetime import datetime
from pathlib import Path

from backtest.engine import Backtester
from strategy.smc_strategy import SMCStrategy
from config.config import Config
from core.logger import logger

warnings.filterwarnings('ignore')
os.environ['IS_BACKTEST'] = 'true'

# Configuration - EXACT BOT SETTINGS
CACHE_DIR = "data/cache"
symbols = Config.TRADING_PAIRS  # 23 pairs từ config
days = 800  # Full 800 days
initial_capital = 1300  # $1,300 như yêu cầu
config = Config()

print("=" * 80)
print("[BACKTEST] FULL SMC STRATEGY - EXACT BOT CONFIG")
print(f"   Periods: {days} days")
print(f"   Symbols: {len(symbols)}")
print(f"   Initial Capital: ${initial_capital:,.2f}")
print(f"   Pairs: {', '.join(symbols[:5])}... (23 total)")
print("=" * 80)
print()

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

strategy = SMCStrategy(name="AdvancedSMC")
all_trades = []
symbol_results = {}
total_skipped = 0
start_time = time.time()

for idx, symbol in enumerate(symbols, 1):
    elapsed = time.time() - start_time
    print(f"[{idx:2d}/{len(symbols)}] {symbol:15} | Elapsed: {elapsed:6.1f}s ...", end=" ", flush=True)
    
    try:
        # Load data from cache
        df_15m = load_from_cache(symbol, '15m')
        df_1h = load_from_cache(symbol, '1h')
        df_4h = load_from_cache(symbol, '4h')
        
        if df_15m is None or df_1h is None or df_4h is None:
            print("[SKIP] Cache missing")
            total_skipped += 1
            continue
        
        if len(df_15m) < 100 or len(df_1h) < 100 or len(df_4h) < 100:
            print(f"[SKIP] Insufficient data")
            total_skipped += 1
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
            sr = symbol_results[symbol]
            wr = (sr['wins'] / sr['trades'] * 100) if sr['trades'] > 0 else 0
            print(f"[OK] {sr['trades']:3d} trades | Win: {wr:5.1f}% | PnL: ${sr['total_pnl']:10,.2f}")
        else:
            print("[OK] 0 trades generated")
            
    except KeyboardInterrupt:
        print("[INTERRUPTED]")
        break
    except Exception as e:
        print(f"[ERROR] {str(e)[:40]}")
        logger.error(f"Error backtesting {symbol}: {e}")
        total_skipped += 1
        continue

elapsed_total = time.time() - start_time
print()
print("=" * 80)
print("[RESULTS] FULL SMC BACKTEST - 23 PAIRS SUMMARY")
print("=" * 80)

if all_trades:
    total_trades = len(all_trades)
    total_pnl = sum([t.get('pnl', 0) for t in all_trades])
    total_wins = len([t for t in all_trades if t.get('pnl', 0) > 0])
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    roi = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
    
    print(f"Total Trades:     {total_trades}")
    print(f"Winning Trades:   {total_wins}")
    print(f"Losing Trades:    {total_trades - total_wins}")
    print(f"Win Rate:         {win_rate:.2f}%")
    print(f"Total PnL:        ${total_pnl:,.2f}")
    print(f"ROI:              {roi:.2f}%")
    print(f"Execution Time:   {elapsed_total:.1f}s")
    print()
    print("By Symbol (Top 10 by trades):")
    print("-" * 80)
    
    # Sort by trade count
    sorted_symbols = sorted(symbol_results.items(), key=lambda x: x[1]['trades'], reverse=True)
    for symbol, data in sorted_symbols[:10]:
        wr = (data['wins']/max(1, data['trades'])*100)
        print(f"  {symbol:15} {data['trades']:4d} trades | Win: {wr:5.1f}% | PnL: ${data['total_pnl']:10,.2f}")
    
    print()
    print(f"Total symbols with trades: {len(symbol_results)}")
    print(f"Total symbols processed:   {len(symbols)}")
    print(f"Symbols skipped:           {total_skipped}")
else:
    print("[!] No trades executed across all 23 symbols")

print()
print("[COMPLETE] Full backtest completed!")
print(f"Total execution time: {elapsed_total:.1f} seconds ({elapsed_total/60:.1f} minutes)")
