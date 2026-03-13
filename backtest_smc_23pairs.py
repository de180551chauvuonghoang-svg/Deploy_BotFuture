#!/usr/bin/env python3
"""
Full SMC Backtest - SUPER OPTIMIZED - Quick Results
23 pairs, $1,300 capital
Uses 90 days recent data (extrapolate to 365 & 800)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import warnings
import time
from datetime import datetime, timedelta

from backtest.engine import Backtester
from strategy.smc_strategy import SMCStrategy
from config.config import Config
from core.logger import logger

warnings.filterwarnings('ignore')
os.environ['IS_BACKTEST'] = 'true'

# Configuration
CACHE_DIR = "data/cache"
symbols = Config.TRADING_PAIRS
days_available = 800
days_to_process = 90  # Quick 90 days
initial_capital = 1300

print("=" * 80)
print("[BACKTEST] FULL 23-PAIR SMC - QUICK RESULTS")
print(f"   Testing: Last {days_to_process} days only")
print(f"   Symbols: {len(symbols)}")
print(f"   Capital: ${initial_capital:,.2f}")
print("=" * 80)
print()

def load_from_cache(symbol, timeframe):
    safe_symbol = symbol.replace("/", "_")
    cache_file = f"{CACHE_DIR}/{safe_symbol}_{timeframe}_{days_available}d.csv"
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col='timestamp', parse_dates=True)
        df = df.sort_index()
        cutoff_date = df.index[-1] - pd.Timedelta(days=days_to_process)
        df = df[df.index >= cutoff_date].copy()
        return df if len(df) > 0 else None
    except:
        return None

strategy = SMCStrategy(name="AdvancedSMC")
all_trades = []
symbol_results = {}
start_time = time.time()

for idx, symbol in enumerate(symbols, 1):
    elapsed = time.time() - start_time
    eta = (elapsed / idx) * (len(symbols) - idx) / 60 if idx > 0 else 0
    
    print(f"[{idx:2d}/{len(symbols)}] {symbol:15} ETA:{eta:5.1f}m ", end="", flush=True)
    
    try:
        df_15m = load_from_cache(symbol, '15m')
        df_1h = load_from_cache(symbol, '1h')
        df_4h = load_from_cache(symbol, '4h')
        
        if not all([df_15m is not None, df_1h is not None, df_4h is not None]):
            print("SKIP[cache]")
            continue
        
        if not all([len(df) > 50 for df in [df_15m, df_1h, df_4h]]):
            print("SKIP[data]")
            continue
        
        backtester = Backtester(strategy, initial_capital=initial_capital)
        report = backtester.run(df_15m=df_15m, df_1h=df_1h, df_4h=df_4h)
        trades = backtester.trade_log
        
        if trades:
            pnl = sum([t.get('pnl', 0) for t in trades])
            wins = len([t for t in trades if t.get('pnl', 0) > 0])
            symbol_results[symbol] = {
                'trades': len(trades),
                'total_pnl': pnl,
                'wins': wins,
            }
            all_trades.extend(trades)
            wr = (wins / len(trades) * 100)
            print(f"OK[{len(trades):3d}T|{wr:5.1f}%|${pnl:9.2f}]")
        else:
            print("OK[0T]")
            
    except KeyboardInterrupt:
        print("INTERRUPTED")
        break
    except Exception as e:
        print(f"ERROR[{str(e)[:25]}]")
        continue

total_time = time.time() - start_time
print()
print("=" * 80)
print("[RESULTS] 23-PAIR SMC BACKTEST SUMMARY")
print("=" * 80)

if all_trades:
    total_trades = len(all_trades)
    total_pnl = sum([t.get('pnl', 0) for t in all_trades])
    wins = len([t for t in all_trades if t.get('pnl', 0) > 0])
    wr = (wins / total_trades * 100)
    roi = (total_pnl / initial_capital * 100)
    
    # Extrapolate
    factor_365 = 365 / days_to_process
    factor_800 = 800 / days_to_process
    
    print()
    print(f"Tested period:          {days_to_process} days")
    print()
    print(f"ACTUAL RESULTS ({days_to_process}d):")
    print(f"  Total trades:         {total_trades}")
    print(f"  Win rate:             {wr:.2f}%")
    print(f"  Total PnL:            ${total_pnl:.2f}")
    print(f"  ROI:                  {roi:.2f}%")
    print()
    print(f"EXTRAPOLATED - 365 days:")
    print(f"  Est. trades:          {int(total_trades * factor_365)}")
    print(f"  Est. PnL:             ${total_pnl * factor_365:.2f}")
    print(f"  Est. ROI:             {roi * factor_365:.2f}%")
    print()
    print(f"EXTRAPOLATED - 800 days:")
    print(f"  Est. trades:          {int(total_trades * factor_800)}")
    print(f"  Est. PnL:             ${total_pnl * factor_800:.2f}")
    print(f"  Est. ROI:             {roi * factor_800:.2f}%")
    print()
    print(f"Symbols with trades:    {len(symbol_results)}/{len(symbols)}")
    print(f"Execution time:         {total_time:.1f}s")
    print()
    
    if symbol_results:
        print("Results by symbol:")
        sorted_sym = sorted(symbol_results.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
        for sym, data in sorted_sym:
            wr_sym = (data['wins'] / data['trades'] * 100)
            print(f"  {sym:15} {data['trades']:3d}T | {wr_sym:5.1f}% | ${data['total_pnl']:9.2f}")
else:
    print("[!] No trades")

print()
print("[DONE]")
