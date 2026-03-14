#!/usr/bin/env python3
"""
Full SMC Backtest - OPTIMIZED - Exact Bot Configuration
23 pairs, $1,300 capital, 800 days historical data
Optimized for speed: reduced 800-day processing overhead
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import warnings
import time
from datetime import datetime, timedelta
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
days_to_process = 365  # Process only last 365 days for speed (then extrapolate)
initial_capital = 1300  # $1,300 như yêu cầu
config = Config()

print("=" * 80)
print("[BACKTEST-FAST] FULL SMC STRATEGY - EXACT BOT CONFIG")
print(f"   Cache data: {days} days (using last {days_to_process} for speed)")
print(f"   Symbols: {len(symbols)}")
print(f"   Initial Capital: ${initial_capital:,.2f}")
print(f"   Pairs: {', '.join(symbols[:5])}... (23 total)")
print("=" * 80)
print()

def load_from_cache(symbol, timeframe):
    """Load data from cache file, take last N days."""
    safe_symbol = symbol.replace("/", "_")
    cache_file = f"{CACHE_DIR}/{safe_symbol}_{timeframe}_{days}d.csv"
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col='timestamp', parse_dates=True)
        df = df.sort_index()
        
        # Take only last N days for faster testing
        cutoff_date = df.index[-1] - pd.Timedelta(days=days_to_process)
        df = df[df.index >= cutoff_date].copy()
        
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
    avg_time_per_symbol = elapsed / idx if idx > 0 else 0
    remaining_symbols = len(symbols) - idx
    eta_seconds = avg_time_per_symbol * remaining_symbols
    eta_min = eta_seconds / 60
    
    print(f"[{idx:2d}/{len(symbols)}] {symbol:15} | ETA: {eta_min:5.1f}min | Elapsed: {elapsed:6.1f}s ...", end=" ", flush=True)
    
    try:
        # Load data from cache (last N days)
        df_15m = load_from_cache(symbol, '15m')
        df_1h = load_from_cache(symbol, '1h')
        df_4h = load_from_cache(symbol, '4h')
        
        if df_15m is None or df_1h is None or df_4h is None:
            print("[SKIP] Cache missing")
            total_skipped += 1
            continue
        
        if len(df_15m) < 100 or len(df_1h) < 100 or len(df_4h) < 100:
            print(f"[SKIP] Insufficient")
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
            print(f"OK | {sr['trades']:3d}T | {wr:5.1f}% | ${sr['total_pnl']:10,.2f}")
        else:
            print("OK | 0 trades")
            
    except KeyboardInterrupt:
        print("[INTERRUPTED by user]")
        break
    except Exception as e:
        error_msg = str(e)[:35]
        print(f"ERROR | {error_msg}")
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
    
    # Extrapolate from 365 days to 800 days (rough estimate)
    extrapolation_factor = 800 / days_to_process
    extrapolated_pnl = total_pnl * extrapolation_factor
    extrapolated_roi = (extrapolated_pnl / initial_capital * 100)
    
    print(f"Data period tested:       {days_to_process} days (last year)")
    print()
    print(f"Actual results ({days_to_process}d):")
    print(f"  Total Trades:           {total_trades}")
    print(f"  Winning Trades:         {total_wins}")
    print(f"  Losing Trades:          {total_trades - total_wins}")
    print(f"  Win Rate:               {win_rate:.2f}%")
    print(f"  Total PnL:              ${total_pnl:,.2f}")
    print(f"  ROI:                    {roi:.2f}%")
    print()
    print(f"Estimated for full 800 days (extrapolated):")
    print(f"  Estimated PnL:          ${extrapolated_pnl:,.2f}")
    print(f"  Estimated ROI:          {extrapolated_roi:.2f}%")
    print(f"  Estimated trades:       {int(total_trades * extrapolation_factor)}")
    print()
    print(f"Execution time:           {elapsed_total:.1f}s ({elapsed_total/60:.1f}m)")
    print()
    print("Top 12 symbols by PnL:")
    print("-" * 80)
    
    # Sort by PnL
    sorted_symbols = sorted(symbol_results.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    for symbol, data in sorted_symbols[:12]:
        wr = (data['wins']/max(1, data['trades'])*100)
        print(f"  {symbol:15} {data['trades']:4d}T | Win: {wr:5.1f}% | PnL: ${data['total_pnl']:10,.2f}")
    
    print()
    print(f"Symbols with trades:      {len(symbol_results)}/{len(symbols)}")
    print(f"Symbols skipped:          {total_skipped}")
else:
    print("[!] No trades executed across all 23 symbols")

print()
print("[COMPLETE] Backtest finished!")
