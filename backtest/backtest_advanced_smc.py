#!/usr/bin/env python3
"""
Backtest với Advanced SMC Strategy hiện tại
Sử dụng chiến lược từ bot đang chạy
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import warnings
from datetime import datetime
from pathlib import Path

from backtest.data import fetch_historical_data
from backtest.engine import Backtester
from strategy.smc_strategy import SMCStrategy
from config.config import Config
from core.logger import logger
from core.exchange import ExchangeHandler

warnings.filterwarnings('ignore')
os.environ['IS_BACKTEST'] = 'true'

def run_smc_backtest(symbols, days=360, initial_capital=1300):
    """
    Chạy backtest với SMC Strategy cho portfolio
    """
    print("=" * 80)
    print(f"[BACKTEST] ADVANCED SMC STRATEGY")
    print(f"   Ngay: {days} ngay")
    print(f"   Cap tien: {len(symbols)}")
    print(f"   Von: ${initial_capital:,.2f}")
    print("=" * 80)
    print()
    
    exchange = ExchangeHandler()
    strategy = SMCStrategy(name="AdvancedSMC")
    
    all_trades = []
    symbol_results = {}
    total_capital = initial_capital
    
    for idx, symbol in enumerate(symbols, 1):
        print(f"[{idx:2d}/{len(symbols)}] Backtesting {symbol:15} ...", end=" ", flush=True)
        
        try:
            # 1. Fetch data
            df_15m = fetch_historical_data(exchange, symbol, '15m', days=days)
            df_1h = fetch_historical_data(exchange, symbol, '1h', days=days)
            df_4h = fetch_historical_data(exchange, symbol, '4h', days=days)
            
            if df_15m is None or df_1h is None or df_4h is None:
                print("[!] Data incomplete")
                continue
            
            # 2. Run backtest
            backtester = Backtester(strategy, initial_capital=initial_capital)
            backtester.run(df_15m, df_1h, df_4h)
            
            # 3. Collect results
            if backtester.trade_log:
                all_trades.extend(backtester.trade_log)
                
                trades_df = pd.DataFrame(backtester.trade_log)
                pnl = trades_df['pnl'].sum()
                trades_count = len(backtester.trade_log)
                win_rate = (len(trades_df[trades_df['pnl'] > 0]) / trades_count * 100) if trades_count > 0 else 0
                
                symbol_results[symbol] = {
                    'trades': trades_count,
                    'pnl': pnl,
                    'win_rate': win_rate,
                    'final_capital': initial_capital + pnl
                }
                
                print(f"[OK] {trades_count:3d} trades | PnL: ${pnl:10,.2f} | Win%: {win_rate:.1f}%")
                total_capital += pnl
            else:
                print("[W] No trades")
                
        except Exception as e:
            print(f"[E] Error: {str(e)[:40]}")
            continue
    
    print()
    print("=" * 80)
    print("📊 PORTFOLIO RESULTS")
    print("=" * 80)
    print()
    
    if not all_trades:
        print("[!] No trades executed")
        return
    
    # Global stats
    df_all = pd.DataFrame(all_trades)
    total_pnl = df_all['pnl'].sum()
    win_count = len(df_all[df_all['pnl'] > 0])
    total_trades = len(df_all)
    win_rate_global = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    avg_win = df_all[df_all['pnl'] > 0]['pnl'].mean() if win_count > 0 else 0
    avg_loss = df_all[df_all['pnl'] < 0]['pnl'].mean() if (total_trades - win_count) > 0 else 0
    
    profit_factor = abs(df_all[df_all['pnl'] > 0]['pnl'].sum()) / abs(df_all[df_all['pnl'] < 0]['pnl'].sum()) if len(df_all[df_all['pnl'] < 0]) > 0 else 0
    
    print(f"[STATS] GLOBAL STATISTICS:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Win Rate: {win_rate_global:.2f}%")
    print(f"   Total PnL: ${total_pnl:,.2f}")
    print(f"   Avg Win: ${avg_win:,.2f}")
    print(f"   Avg Loss: ${avg_loss:,.2f}")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print()
    
    # Portfolio metrics
    initial_balance = initial_capital
    final_balance = total_capital
    roi = ((final_balance - initial_balance) / initial_balance * 100) if initial_balance > 0 else 0
    
    print(f"[PORTFOLIO] METRICS:")
    print(f"   Starting Capital: ${initial_balance:,.2f}")
    print(f"   Final Balance: ${final_balance:,.2f}")
    print(f"   Total Profit/Loss: ${final_balance - initial_balance:,.2f}")
    print(f"   ROI: {roi:.2f}%")
    print()
    
    # Top symbol
    print(f"[TOP] TOP PERFORMERS:")
    sorted_results = sorted(symbol_results.items(), key=lambda x: x[1]['pnl'], reverse=True)
    for i, (symbol, results) in enumerate(sorted_results[:5], 1):
        print(f"   {i}. {symbol:12} | Trades: {results['trades']:3d} | PnL: ${results['pnl']:10,.2f} | Win%: {results['win_rate']:6.2f}%")
    
    print()
    
    # Bottom symbols
    print(f"[BOTTOM] WORST PERFORMERS:")
    for i, (symbol, results) in enumerate(sorted_results[-5:], 1):
        print(f"   {i}. {symbol:12} | Trades: {results['trades']:3d} | PnL: ${results['pnl']:10,.2f} | Win%: {results['win_rate']:6.2f}%")
    
    print()
    print("=" * 80)
    
    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"backtest/results/ADVANCED_SMC_{days}d_{timestamp}.md"
    
    with open(report_file, 'w') as f:
        f.write(f"# Advanced SMC Backtest Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Duration:** {days} days\n")
        f.write(f"**Symbols:** {len(symbols)}\n")
        f.write(f"**Strategy:** Advanced SMC\n\n")
        
        f.write(f"## Global Statistics\n")
        f.write(f"- Total Trades: {total_trades}\n")
        f.write(f"- Win Rate: {win_rate_global:.2f}%\n")
        f.write(f"- Total PnL: ${total_pnl:,.2f}\n\n")
        
        f.write(f"## Portfolio Results\n")
        f.write(f"- Starting Capital: ${initial_balance:,.2f}\n")
        f.write(f"- Final Balance: ${final_balance:,.2f}\n")
        f.write(f"- ROI: {roi:.2f}%\n\n")
        
        f.write(f"## Symbol Breakdown\n\n")
        f.write(f"| Symbol | Trades | PnL | Win % |\n")
        f.write(f"|--------|--------|-----|-------|\n")
        for symbol, results in sorted_results:
            f.write(f"| {symbol} | {results['trades']} | ${results['pnl']:,.2f} | {results['win_rate']:.2f}% |\n")
    
    print(f"[OK] Report saved: {report_file}")
    print()

if __name__ == "__main__":
    # Use config from bot
    symbols = Config.TRADING_PAIRS[:6]  # Start with first 6 for speed
    days = 360
    initial_capital = 1300
    
    run_smc_backtest(symbols, days=days, initial_capital=initial_capital)
    
    print("\n[COMPLETE] Backtest completed!")
