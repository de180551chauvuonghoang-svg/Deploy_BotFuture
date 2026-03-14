#!/usr/bin/env python3
"""
Calculate Drawdown Metrics from Backtest Results
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from backtest.engine import Backtester
from strategy.smc_strategy import SMCStrategy
from config.config import Config
from core.logger import logger

# Re-run quick backtest on top 3 pairs to get trade details
CACHE_DIR = "data/cache"
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']  # Top 3 performers
days_available = 800
days_to_process = 90
initial_capital = 1300

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

print("=" * 80)
print("[ANALYSIS] BACKTEST DRAWDOWN CALCULATION")
print("=" * 80)
print()

strategy = SMCStrategy(name="AdvancedSMC")
all_trades = []

for symbol in symbols:
    print(f"Processing {symbol}...", end=" ", flush=True)
    
    df_15m = load_from_cache(symbol, '15m')
    df_1h = load_from_cache(symbol, '1h')
    df_4h = load_from_cache(symbol, '4h')
    
    if not all([df_15m is not None, df_1h is not None, df_4h is not None]):
        print("SKIP")
        continue
    
    backtester = Backtester(strategy, initial_capital=initial_capital)
    report = backtester.run(df_15m=df_15m, df_1h=df_1h, df_4h=df_4h)
    trades = backtester.trade_log
    
    if trades:
        all_trades.extend(trades)
        print(f"OK ({len(trades)} trades)")
    else:
        print("OK (0 trades)")

if not all_trades:
    print("[ERROR] No trades to analyze")
    sys.exit(1)

# Convert to DataFrame
df_trades = pd.DataFrame(all_trades)
df_trades = df_trades.sort_values('time').reset_index(drop=True)

# Calculate cumulative equity
df_trades['cumulative_pnl'] = df_trades['pnl'].cumsum()
df_trades['equity'] = initial_capital + df_trades['cumulative_pnl']

# Calculate running maximum equity
df_trades['running_max'] = df_trades['equity'].expanding().max()

# Calculate drawdown
df_trades['drawdown'] = (df_trades['equity'] - df_trades['running_max']) / df_trades['running_max']
df_trades['drawdown_pct'] = df_trades['drawdown'] * 100
df_trades['drawdown_usd'] = df_trades['equity'] - df_trades['running_max']

# Calculate metrics
max_drawdown_pct = df_trades['drawdown_pct'].min()
max_drawdown_usd = df_trades['drawdown_usd'].min()
max_equity = df_trades['equity'].max()
min_equity = df_trades['equity'].min()
final_equity = df_trades['equity'].iloc[-1]

# Find recovery info
max_dd_idx = df_trades['drawdown_pct'].idxmin()
max_dd_time = df_trades.loc[max_dd_idx, 'time']
max_dd_equity = df_trades.loc[max_dd_idx, 'equity']

# Calculate consecutive losing trades (longest losing streak)
df_trades['win'] = df_trades['pnl'] > 0
losing_streaks = []
current_streak = 0
for win in df_trades['win']:
    if not win:
        current_streak += 1
    else:
        if current_streak > 0:
            losing_streaks.append(current_streak)
        current_streak = 0
if current_streak > 0:
    losing_streaks.append(current_streak)

longest_losing_streak = max(losing_streaks) if losing_streaks else 0

# Calculate profit factor
wins_pnl = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
loss_pnl = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
profit_factor = wins_pnl / loss_pnl if loss_pnl > 0 else float('inf')

print()
print("=" * 80)
print("[RESULTS] DRAWDOWN & RISK METRICS")
print("=" * 80)
print()

print("DRAWDOWN ANALYSIS:")
print("-" * 80)
print(f"Maximum Drawdown:      {max_drawdown_pct:.2f}%")
print(f"Maximum Drawdown USD:  ${max_drawdown_usd:.2f}")
print(f"Max Drawdown Time:     {max_dd_time}")
print(f"Equity at Max DD:      ${max_dd_equity:.2f}")
print()

print("EQUITY STATS:")
print("-" * 80)
print(f"Initial Capital:       ${initial_capital:.2f}")
print(f"Final Equity:          ${final_equity:.2f}")
print(f"Maximum Equity:        ${max_equity:.2f}")
print(f"Minimum Equity:        ${min_equity:.2f}")
print(f"Total Gain:            ${final_equity - initial_capital:.2f}")
print(f"Total Gain %:          {((final_equity - initial_capital) / initial_capital * 100):.2f}%")
print()

print("RISK METRICS:")
print("-" * 80)
print(f"Total Trades:          {len(df_trades)}")
print(f"Winning Trades:        {df_trades['win'].sum()}")
print(f"Losing Trades:         {(~df_trades['win']).sum()}")
print(f"Win Rate:              {(df_trades['win'].sum() / len(df_trades) * 100):.2f}%")
print(f"Longest Losing Streak: {longest_losing_streak} trades")
print(f"Profit Factor:         {profit_factor:.2f}")
print(f"Avg Win:               ${df_trades[df_trades['pnl'] > 0]['pnl'].mean():.2f}")
print(f"Avg Loss:              ${df_trades[df_trades['pnl'] < 0]['pnl'].mean():.2f}")
print()

print("RECOVERY PHASES:")
print("-" * 80)
# Find all major drawdown recovery periods
current_phase_start = 0
equity_curve = df_trades['equity'].values
dd_curve = df_trades['drawdown_pct'].values

phases = []
in_dd = False
dd_start_idx = 0

for i in range(len(dd_curve)):
    is_in_dd = dd_curve[i] < -0.5  # More than 0.5% drawdown
    
    if is_in_dd and not in_dd:
        # Started drawdown
        in_dd = True
        dd_start_idx = i
    elif not is_in_dd and in_dd:
        # Ended drawdown (recovered)
        in_dd = False
        phases.append({
            'start': dd_start_idx,
            'end': i,
            'start_time': df_trades.loc[dd_start_idx, 'time'],
            'end_time': df_trades.loc[i, 'time'],
            'min_dd': df_trades.loc[dd_start_idx:i, 'drawdown_pct'].min(),
            'trades_in_phase': i - dd_start_idx + 1
        })

if phases:
    print(f"Major Drawdown Periods: {len(phases)}")
    for i, phase in enumerate(phases[:3], 1):  # Show top 3 longest
        print(f"  Period {i}:")
        print(f"    Start:       {phase['start_time']}")
        print(f"    End:         {phase['end_time']}")
        print(f"    Min DD:      {phase['min_dd']:.2f}%")
        print(f"    Trades:      {phase['trades_in_phase']}")
else:
    print("No major drawdown periods detected (excellent resilience)")

print()
print("=" * 80)
print("[KEY FINDING]")
print("=" * 80)
print()

if abs(max_drawdown_pct) < 5:
    severity = "MINIMAL"
    recommendation = "Excellent risk profile"
elif abs(max_drawdown_pct) < 10:
    severity = "LOW"
    recommendation = "Good risk management"
elif abs(max_drawdown_pct) < 20:
    severity = "MODERATE"
    recommendation = "Acceptable for crypto, monitor closely"
else:
    severity = "HIGH"
    recommendation = "Consider risk adjustment or investigation"

print(f"Drawdown Severity:     {severity}")
print(f"Assessment:            {recommendation}")
print()
print(f"Profit Factor:         {profit_factor:.2f}x (wins/losses ratio)")
if profit_factor > 2:
    print(f"                       → EXCELLENT (1.5+ is good)")
elif profit_factor > 1.5:
    print(f"                       → GOOD (1.5+ is good)")
elif profit_factor > 1:
    print(f"                       → ACCEPTABLE (>1 means profits > losses)")
else:
    print(f"                       → RISKY (losses exceed profits)")

print()
