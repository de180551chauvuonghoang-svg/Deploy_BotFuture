#!/usr/bin/env python3
"""
Quick SMC Backtest - Simplified for speed testing
Tests only the last 30 days of data per symbol to verify strategy works
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
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']  # Reduced to 4 for speed
days = 800
days_to_test = 60  # Test only last 60 days for speed
initial_capital = 1300
config = Config()

def load_from_cache(symbol, timeframe):
    """Load data from cache file and slice last N days."""
    safe_symbol = symbol.replace("/", "_")
    cache_file = f"{CACHE_DIR}/{safe_symbol}_{timeframe}_{days}d.csv"
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col='timestamp', parse_dates=True)
        df = df.sort_index()
        
        # Take only last N days for faster testing
        cutoff_date = df.index[-1] - pd.Timedelta(days=days_to_test)
        df = df[df.index >= cutoff_date].copy()
        
        return df
    except Exception as e:
        logger.error(f"Error loading {cache_file}: {e}")
        return None

print("=" * 80)
print("[BACKTEST] QUICK SMC STRATEGY TEST")
print(f"   Testing last: {days_to_test} days")
print(f"   Symbols: {len(symbols)}")
print(f"   Initial Capital: ${initial_capital:,.2f}")
print("=" * 80)
print()

strategy = SMCStrategy(name="AdvancedSMC")
all_trades = []
symbol_results = {}
total_failed = 0

for idx, symbol in enumerate(symbols, 1):
    print(f"[{idx:2d}/{len(symbols)}] Testing {symbol:15} ...", end=" ", flush=True)
    
    try:
        # Load data from cache (last N days)
        df_15m = load_from_cache(symbol, '15m')
        df_1h = load_from_cache(symbol, '1h')
        df_4h = load_from_cache(symbol, '4h')
        
        if df_15m is None or df_1h is None or df_4h is None:
            print("[!] Cache missing")
            total_failed += 1
            continue
        
        if len(df_15m) < 100 or len(df_1h) < 100 or len(df_4h) < 100:
            print(f"[!] Insufficient data (15m:{len(df_15m)} 1h:{len(df_1h)} 4h:{len(df_4h)})")
            total_failed += 1
            continue
        
        print(f"Data loaded ({len(df_15m)} bars) ...", end=" ", flush=True)
        
        # Run backtest
        backtester = Backtester(strategy, initial_capital=initial_capital)
        report = backtester.run(df_15m=df_15m, df_1h=df_1h, df_4h=df_4h)
        print(f"Done!", flush=True)
        
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
            win_pct = (sr['wins'] / sr['trades'] * 100) if sr['trades'] > 0 else 0
            print(f"        --> {sr['trades']} trades | Win rate: {win_pct:.1f}% | PnL: ${sr['total_pnl']:.2f}")
        else:
            print(f"        --> No trades generated (strategy didn't trigger)")
            
    except KeyboardInterrupt:
        print("[INTERRUPTED]")
        break
    except Exception as e:
        print(f"[ERROR] {str(e)[:40]}")
        logger.error(f"Error backtesting {symbol}: {e}")
        total_failed += 1
        continue

print()
print("=" * 80)
print("[RESULTS] SMC BACKTEST SUMMARY")
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
    print()
    print("By Symbol:")
    for symbol in symbols:
        if symbol in symbol_results:
            r = symbol_results[symbol]
            wr = (r['wins']/max(1,r['trades'])*100)
            print(f"  {symbol:15} {r['trades']:3d} trades | Win: {wr:5.1f}% | PnL: ${r['total_pnl']:10,.2f}")
    print()
    print(f"Symbols failed:   {total_failed}")
else:
    print("[!] No trades executed across all symbols")
    print(f"Symbols failed:   {total_failed}")

print()
print("[COMPLETE] Fast backtest completed!")
