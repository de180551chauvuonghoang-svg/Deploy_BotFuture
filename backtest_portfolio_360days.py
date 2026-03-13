#!/usr/bin/env python3
"""
Full Portfolio Backtest - 23 Pairs, 360 Days, Detailed Report
Advanced SMC Strategy - Current Bot Configuration
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

# Configuration - EXACT BOT SETTINGS
CACHE_DIR = "data/cache"
symbols = Config.TRADING_PAIRS  # 23 pairs
days_available = 800
days_to_test = 360  # Full year
initial_capital = 1300

print("=" * 90)
print("[BACKTEST] FULL PORTFOLIO - 23 PAIRS x 360 DAYS")
print(f"   Strategy: Advanced SMC")
print(f"   Pairs: {len(symbols)}")
print(f"   Period: {days_to_test} days")
print(f"   Capital: ${initial_capital:,.2f}")
print("=" * 90)
print()

def load_from_cache(symbol, timeframe):
    safe_symbol = symbol.replace("/", "_")
    cache_file = f"{CACHE_DIR}/{safe_symbol}_{timeframe}_{days_available}d.csv"
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        df = pd.read_csv(cache_file, index_col='timestamp', parse_dates=True)
        df = df.sort_index()
        cutoff_date = df.index[-1] - pd.Timedelta(days=days_to_test)
        df = df[df.index >= cutoff_date].copy()
        return df if len(df) > 0 else None
    except Exception as e:
        logger.error(f"Error loading {cache_file}: {e}")
        return None

strategy = SMCStrategy(name="AdvancedSMC")
all_trades = []
symbol_results = {}
symbol_errors = {}
start_time = time.time()

for idx, symbol in enumerate(symbols, 1):
    elapsed = time.time() - start_time
    if idx > 1:
        avg_time = elapsed / (idx - 1)
        eta = avg_time * (len(symbols) - idx) / 60
    else:
        eta = 0
    
    print(f"[{idx:2d}/{len(symbols)}] {symbol:15} ETA: {eta:6.1f}m | Elapsed: {elapsed:7.1f}s", end=" | ", flush=True)
    
    try:
        df_15m = load_from_cache(symbol, '15m')
        df_1h = load_from_cache(symbol, '1h')
        df_4h = load_from_cache(symbol, '4h')
        
        if not all([df_15m is not None, df_1h is not None, df_4h is not None]):
            print("SKIP[cache missing]")
            symbol_errors[symbol] = "Cache data missing"
            continue
        
        if not all([len(df) > 100 for df in [df_15m, df_1h, df_4h]]):
            print(f"SKIP[insufficient data]")
            symbol_errors[symbol] = "Insufficient data points"
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
                'win_rate': (wins / len(trades) * 100) if len(trades) > 0 else 0,
            }
            all_trades.extend(trades)
            wr = symbol_results[symbol]['win_rate']
            print(f"OK[{len(trades):3d}T | WR:{wr:5.1f}% | ${pnl:10.2f}]")
        else:
            print(f"OK[0 trades]")
            symbol_results[symbol] = {
                'trades': 0,
                'total_pnl': 0,
                'wins': 0,
                'win_rate': 0,
            }
            
    except KeyboardInterrupt:
        print("INTERRUPTED BY USER")
        break
    except Exception as e:
        error_msg = str(e)[:40]
        print(f"ERROR[{error_msg}]")
        symbol_errors[symbol] = error_msg
        continue

total_time = time.time() - start_time

print()
print("=" * 90)
print("[RESULTS] 23-PAIR PORTFOLIO BACKTEST - DETAILED ANALYSIS")
print("=" * 90)
print()

if all_trades:
    total_trades = len(all_trades)
    total_pnl = sum([t.get('pnl', 0) for t in all_trades])
    wins = len([t for t in all_trades if t.get('pnl', 0) > 0])
    losses = len([t for t in all_trades if t.get('pnl', 0) < 0])
    wr = (wins / total_trades * 100)
    roi = (total_pnl / initial_capital * 100)
    
    # Calculate additional metrics
    df_trades = pd.DataFrame(all_trades)
    avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if len(df_trades[df_trades['pnl'] > 0]) > 0 else 0
    avg_loss = df_trades[df_trades['pnl'] < 0]['pnl'].mean() if len(df_trades[df_trades['pnl'] < 0]) > 0 else 0
    max_win = df_trades['pnl'].max()
    max_loss = df_trades['pnl'].min()
    
    # Profit factor
    gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
    gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Drawdown
    cum_pnl = df_trades['pnl'].cumsum() + initial_capital
    peak = cum_pnl.expanding().max()
    dd = (cum_pnl - peak) / peak * 100
    max_dd = dd.min()
    
    # Monthly performance (rough estimate)
    df_trades['date'] = pd.to_datetime(df_trades['time'])
    monthly = df_trades.groupby(df_trades['date'].dt.to_period('M'))['pnl'].sum()
    avg_monthly_pnl = monthly.mean() if len(monthly) > 0 else 0
    positive_months = len(monthly[monthly > 0])
    total_months = len(monthly)
    
    print("[PORTFOLIO SUMMARY]")
    print(f"  Period Tested:          {days_to_test} days ({total_months} months)")
    print(f"  Initial Capital:        ${initial_capital:,.2f}")
    print(f"  Final Equity:           ${cum_pnl.iloc[-1]:,.2f}")
    print(f"  Total Gain:             ${total_pnl:,.2f}")
    print()
    
    print("[TRADE STATISTICS]")
    print(f"  Total Trades:           {total_trades}")
    print(f"  Winning Trades:         {wins} ({wr:.2f}%)")
    print(f"  Losing Trades:          {losses} ({100-wr:.2f}%)")
    print(f"  Avg Trade PnL:          ${total_pnl/total_trades:.2f}")
    print(f"  Avg Win:                ${avg_win:.2f}")
    print(f"  Avg Loss:               ${avg_loss:.2f}")
    print(f"  Max Win:                ${max_win:.2f}")
    print(f"  Max Loss:               ${max_loss:.2f}")
    print()
    
    print("[PERFORMANCE METRICS]")
    print(f"  ROI:                    {roi:.2f}%")
    print(f"  Monthly Avg PnL:        ${avg_monthly_pnl:.2f}")
    print(f"  Positive Months:        {positive_months}/{total_months}")
    print(f"  Win/Loss Ratio:         {profit_factor:.2f}x")
    print(f"  Max Drawdown:           {max_dd:.2f}%")
    print()
    
    print("[TOP 15 PERFORMERS BY PnL]")
    print("-" * 90)
    sorted_sym = sorted(symbol_results.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    for i, (sym, data) in enumerate(sorted_sym[:15], 1):
        if data['trades'] > 0:
            print(f"  {i:2d}. {sym:15} {data['trades']:4d}T | WR:{data['win_rate']:5.1f}% | PnL:${data['total_pnl']:10,.2f}")
    
    print()
    print("[BOTTOM 15 PERFORMERS BY PnL]")
    print("-" * 90)
    for i, (sym, data) in enumerate(sorted_sym[-15:], 1):
        if data['trades'] > 0:
            print(f"  {i:2d}. {sym:15} {data['trades']:4d}T | WR:{data['win_rate']:5.1f}% | PnL:${data['total_pnl']:10,.2f}")
        else:
            print(f"  {i:2d}. {sym:15} No trades")
    
    print()
    print("[SYMBOL STATISTICS]")
    print(f"  Symbols with Trades:    {len([s for s in symbol_results.values() if s['trades'] > 0])}/{len(symbol_results)}")
    print(f"  Symbols with Errors:    {len(symbol_errors)}")
    print(f"  Avg Trades/Symbol:      {total_trades / len([s for s in symbol_results.values() if s['trades'] > 0]):.1f}")
    
    if symbol_errors:
        print()
        print("[SYMBOLS WITH ERRORS]")
        for sym, error in symbol_errors.items():
            print(f"  {sym:15} - {error}")
    
    print()
    print("[EXECUTION INFO]")
    print(f"  Total Time:             {total_time:.1f}s ({total_time/60:.1f}m)")
    print(f"  Speed:                  {total_trades/total_time:.1f} trades/sec")
    
else:
    print("[!] No trades executed")

print()
print("=" * 90)

# Generate detailed markdown report
report_path = f"BACKTEST_REPORT_360DAYS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
print(f"[GENERATING] Detailed report to {report_path}...")

with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"# Advanced SMC Strategy Backtest Report\n")
    f.write(f"## 23 Pairs | 360 Days | ${initial_capital:,.2f} Capital\n\n")
    f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    if all_trades:
        f.write(f"### Executive Summary\n")
        f.write(f"- **Total Trades:** {total_trades}\n")
        f.write(f"- **Win Rate:** {wr:.2f}%\n")
        f.write(f"- **Total PnL:** ${total_pnl:,.2f}\n")
        f.write(f"- **ROI:** {roi:.2f}%\n")
        f.write(f"- **Max Drawdown:** {max_dd:.2f}%\n")
        f.write(f"- **Profit Factor:** {profit_factor:.2f}x\n\n")
        
        f.write(f"### Top 10 Symbols\n")
        f.write(f"| Rank | Symbol | Trades | Win Rate | PnL | Avg/Trade |\n")
        f.write(f"|------|--------|--------|----------|-----|----------|\n")
        for i, (sym, data) in enumerate(sorted_sym[:10], 1):
            if data['trades'] > 0:
                avg_pnl = data['total_pnl'] / data['trades']
                f.write(f"| {i} | {sym} | {data['trades']} | {data['win_rate']:.1f}% | ${data['total_pnl']:.2f} | ${avg_pnl:.2f} |\n")
        
        f.write(f"\n### Monthly Performance\n")
        for period, pnl in monthly.items():
            f.write(f"- **{period}:** ${pnl:.2f}\n")
    
    f.write(f"\n### Configuration\n")
    f.write(f"- Strategy: Advanced SMC (Multi-timeframe: 4H/1H/15M)\n")
    f.write(f"- Score Threshold: 8.5/10.0\n")
    f.write(f"- Position Size: 2%\n")
    f.write(f"- Leverage: 5x\n")
    f.write(f"- Backtest Period: {days_to_test} days\n\n")
    
    f.write(f"### Notes\n")
    f.write(f"- Backtest uses local cache data (no API calls)\n")
    f.write(f"- Assumes perfect fills (no slippage)\n")
    f.write(f"- Fee model: 0.06% per side (realistic Binance)\n")

print(f"[COMPLETE] Report saved to {report_path}")
print()
