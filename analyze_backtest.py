import pandas as pd
import numpy as np
from datetime import datetime

# Load both backtest trades CSVs
print("=" * 80)
print("DETAILED BACKTEST ANALYSIS REPORT")
print("=" * 80)
print()

# 1. STANDARD STRATEGY ANALYSIS
print("1️⃣  STANDARD STRATEGY (backtest_trades.csv)")
print("-" * 80)
try:
    df = pd.read_csv(r'backtest_trades.csv')
    
    total_trades = len(df)
    winning_trades = len(df[df['pnl'] > 0])
    losing_trades = len(df[df['pnl'] < 0])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = df['pnl'].sum()
    avg_pnl = df['pnl'].mean()
    max_profit = df['pnl'].max()
    max_loss = df['pnl'].min()
    
    print(f"📊 GLOBAL STATISTICS:")
    print(f"   • Total Trades: {total_trades}")
    print(f"   • Winning Trades: {winning_trades} ({win_rate:.2f}%)")
    print(f"   • Losing Trades: {losing_trades} ({100-win_rate:.2f}%)")
    print()
    print(f"💰 PnL STATISTICS:")
    print(f"   • Total PnL: {total_pnl:.2f} USDT")
    print(f"   • Average PnL per Trade: {avg_pnl:.2f} USDT")
    print(f"   • Best Trade: +{max_profit:.2f} USDT")
    print(f"   • Worst Trade: {max_loss:.2f} USDT")
    print()
    
    # Exit reason breakdown
    print(f"🎯 EXIT REASONS:")
    reason_counts = df['reason'].value_counts()
    for reason, count in reason_counts.items():
        pnl_for_reason = df[df['reason'] == reason]['pnl'].sum()
        win_rate_reason = (len(df[(df['reason'] == reason) & (df['pnl'] > 0)]) / count * 100) if count > 0 else 0
        print(f"   • {reason:15} : {count:3} trades | PnL: {pnl_for_reason:10.2f} USDT | Win%: {win_rate_reason:6.2f}%")
    print()
    
    # Symbol breakdown
    print(f"📈 SYMBOL BREAKDOWN (Ranked by PnL):")
    print()
    symbol_pnl = df.groupby('symbol')['pnl'].sum().sort_values(ascending=False)
    for i, symbol in enumerate(symbol_pnl.index, 1):
        symbol_df = df[df['symbol'] == symbol]
        sym_trades = len(symbol_df)
        sym_pnl = symbol_df['pnl'].sum()
        sym_win = len(symbol_df[symbol_df['pnl'] > 0])
        sym_win_rate = (sym_win / sym_trades * 100) if sym_trades > 0 else 0
        print(f"   {i:2}. {symbol:12} | Trades: {sym_trades:3} | PnL: {sym_pnl:10.2f} USDT | Win%: {sym_win_rate:6.2f}% | Avg/Trade: {sym_pnl/sym_trades:6.2f}")
    
    print()
    print()
    
except Exception as e:
    print(f"❌ Error analyzing standard strategy: {e}")
    print()

# 2. HARD STOP STRATEGY ANALYSIS
print("2️⃣  HARD STOP STRATEGY (backtest_trades_hardstop.csv)")
print("-" * 80)
try:
    df_hs = pd.read_csv(r'backtest_trades_hardstop.csv')
    
    total_trades_hs = len(df_hs)
    winning_trades_hs = len(df_hs[df_hs['pnl'] > 0])
    losing_trades_hs = len(df_hs[df_hs['pnl'] < 0])
    win_rate_hs = (winning_trades_hs / total_trades_hs * 100) if total_trades_hs > 0 else 0
    
    total_pnl_hs = df_hs['pnl'].sum()
    avg_pnl_hs = df_hs['pnl'].mean()
    max_profit_hs = df_hs['pnl'].max()
    max_loss_hs = df_hs['pnl'].min()
    
    print(f"📊 GLOBAL STATISTICS:")
    print(f"   • Total Trades: {total_trades_hs}")
    print(f"   • Winning Trades: {winning_trades_hs} ({win_rate_hs:.2f}%)")
    print(f"   • Losing Trades: {losing_trades_hs} ({100-win_rate_hs:.2f}%)")
    print()
    print(f"💰 PnL STATISTICS:")
    print(f"   • Total PnL: {total_pnl_hs:.2f} USDT")
    print(f"   • Average PnL per Trade: {avg_pnl_hs:.2f} USDT")
    print(f"   • Best Trade: +{max_profit_hs:.2f} USDT")
    print(f"   • Worst Trade: {max_loss_hs:.2f} USDT")
    print()
    
    # Exit reason breakdown
    print(f"🎯 EXIT REASONS:")
    reason_counts_hs = df_hs['reason'].value_counts()
    for reason, count in reason_counts_hs.items():
        pnl_for_reason = df_hs[df_hs['reason'] == reason]['pnl'].sum()
        win_rate_reason = (len(df_hs[(df_hs['reason'] == reason) & (df_hs['pnl'] > 0)]) / count * 100) if count > 0 else 0
        print(f"   • {reason:15} : {count:3} trades | PnL: {pnl_for_reason:10.2f} USDT | Win%: {win_rate_reason:6.2f}%")
    print()
    
    # Symbol breakdown
    print(f"📈 SYMBOL BREAKDOWN (Ranked by PnL):")
    print()
    symbol_pnl_hs = df_hs.groupby('symbol')['pnl'].sum().sort_values(ascending=False)
    for i, symbol in enumerate(symbol_pnl_hs.index, 1):
        symbol_df_hs = df_hs[df_hs['symbol'] == symbol]
        sym_trades_hs = len(symbol_df_hs)
        sym_pnl_hs = symbol_df_hs['pnl'].sum()
        sym_win_hs = len(symbol_df_hs[symbol_df_hs['pnl'] > 0])
        sym_win_rate_hs = (sym_win_hs / sym_trades_hs * 100) if sym_trades_hs > 0 else 0
        print(f"   {i:2}. {symbol:12} | Trades: {sym_trades_hs:3} | PnL: {sym_pnl_hs:10.2f} USDT | Win%: {sym_win_rate_hs:6.2f}% | Avg/Trade: {sym_pnl_hs/sym_trades_hs:6.2f}")
    
    print()
    print()
    
except Exception as e:
    print(f"❌ Error analyzing hard stop strategy: {e}")
    print()

# 3. COMPARISON
print("3️⃣  STRATEGY COMPARISON")
print("-" * 80)
try:
    print(f"                            | Standard     | Hard Stop    | Difference")
    print(f"{'Total Trades':<28} | {total_trades:<12} | {total_trades_hs:<12} | {total_trades - total_trades_hs:+d}")
    print(f"{'Win Rate':<28} | {win_rate:>11.2f}% | {win_rate_hs:>11.2f}% | {win_rate - win_rate_hs:+.2f}%")
    print(f"{'Total PnL':<28} | ${total_pnl:>10.2f} | ${total_pnl_hs:>10.2f} | ${total_pnl - total_pnl_hs:+.2f}")
    print(f"{'Avg PnL/Trade':<28} | ${avg_pnl:>10.2f} | ${avg_pnl_hs:>10.2f} | ${avg_pnl - avg_pnl_hs:+.2f}")
    print(f"{'Best Trade':<28} | ${max_profit:>10.2f} | ${max_profit_hs:>10.2f} | ${max_profit - max_profit_hs:+.2f}")
    print(f"{'Worst Trade':<28} | ${max_loss:>10.2f} | ${max_loss_hs:>10.2f} | ${max_loss - max_loss_hs:+.2f}")
    print()
except Exception as e:
    print(f"Error in comparison: {e}")

print()
print("=" * 80)
print("END OF REPORT")
print("=" * 80)
