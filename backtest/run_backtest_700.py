import ccxt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import warnings
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from backtest.engine import Backtester
from data import fetch_historical_data
from ..strategy.smc_strategy import SMCStrategy
from config.config import Config
from datetime import datetime

warnings.filterwarnings('ignore')
os.environ['IS_BACKTEST'] = 'true'

def run_symbol_backtest(symbol, days):
    """
    Worker function to run backtest for a single symbol.
    """
    try:
        # Each process needs its own exchange instance
        exchange = ccxt.binance({'options': {'defaultType': 'future'}})
        strategy = SMCStrategy()
        
        # 1. Fetch Data (will use cache if available)
        df_15m = fetch_historical_data(exchange, symbol, '15m', days=days)
        df_4h = fetch_historical_data(exchange, symbol, '4h', days=days)
        df_1h = fetch_historical_data(exchange, symbol, '1h', days=days)
        
        if df_15m is None or df_1h is None or df_4h is None:
            return None

        # 2. Initialize Backtester
        backtester = Backtester(initial_capital=10000, strategy=strategy)
        
        # 3. Run
        backtester.run(df_15m, df_1h, df_4h)
        
        # 4. Calculate stats for this specific symbol
        symbol_trades = backtester.trade_log
        if not symbol_trades:
            return {
                'symbol': symbol,
                'trades': [],
                'capital': 10000,
                'pnl': 0,
                'win_rate': 0,
                'total_trades': 0
            }
            
        df_s = pd.DataFrame(symbol_trades)
        pnl = df_s['pnl'].sum()
        win_rate = (len(df_s[df_s['pnl'] > 0]) / len(df_s)) * 100
        
        return {
            'symbol': symbol,
            'trades': symbol_trades,
            'capital': backtester.capital,
            'pnl': pnl,
            'win_rate': win_rate,
            'total_trades': len(df_s)
        }
    except Exception as e:
        print(f"Error testing {symbol}: {e}")
        return None

def main():
    # List of coins to test
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'AVAX/USDT']
    days = 700 
    
    print(f"🚀 --- STARTING 700-DAY SMC BACKTEST COMPARISON ---")
    print(f"Target Symbols: {', '.join(symbols)}")
    
    results = []
    all_global_trades = []
    
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=min(len(symbols), os.cpu_count())) as executor:
        future_to_symbol = {executor.submit(run_symbol_backtest, s, days): s for s in symbols}
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                res = future.result()
                if res:
                    results.append(res)
                    all_global_trades.extend(res['trades'])
                    print(f"✅ [{symbol}] Done. PnL: {res['pnl']:.2f} USDT | WinRate: {res['win_rate']:.2f}%")
                else:
                    print(f"❌ [{symbol}] Failed.")
            except Exception as exc:
                print(f"⚠️ [{symbol}] Generated an exception: {exc}")

    end_time = time.time()
    duration = end_time - start_time

    # 5. Generate Professional Report
    if not results:
        print("No results to report.")
        return

    # Sort results by PnL
    results = sorted(results, key=lambda x: x['pnl'], reverse=True)
    
    total_pnl = sum(r['pnl'] for r in results)
    total_trades = sum(r['total_trades'] for r in results)
    avg_win_rate = sum(r['win_rate'] for r in results) / len(results)
    final_combined_capital = sum(r['capital'] for r in results)

    # Markdown Table Generation
    markdown_report = f"""# 📊 PROFESSIONAL 700-DAY BACKTEST COMPARISON REPORT
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Test Duration: **{days} Days**

## 🏆 Symbol Performance Comparison
| Symbol | Total PnL (USDT) | Win Rate (%) | Total Trades | Final Capital | Performance |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for r in results:
        perf_icon = "🚀" if r['pnl'] > 1000 else "📈" if r['pnl'] > 0 else "📉"
        markdown_report += f"| **{r['symbol']}** | {r['pnl']:.2f} | {r['win_rate']:.2f}% | {r['total_trades']} | {r['capital']:.2f} | {perf_icon} |\n"

    markdown_report += f"""
## 🌍 Global Portfolio Metrics
- **Total Combined PnL**: `{total_pnl:.2f} USDT`
- **Portfolio Win Rate**: `{avg_win_rate:.2f}%`
- **Total Portfolio Trades**: `{total_trades}`
- **Starting Combined Capital**: `{len(symbols) * 10000} USDT`
- **Ending Combined Capital**: `{final_combined_capital:.2f} USDT`
- **Net ROI**: `{(total_pnl / (len(symbols) * 10000)) * 100:.2f}%`

---
*Backtest executed in {duration:.2f} seconds using Parallel ProcessPool.*
"""
    
    # Save to Markdown
    with open("REPORT_BACKTEST_700_DAYS.md", "w", encoding='utf-8') as f:
        f.write(markdown_report)
    
    print(f"\n✅ BACKTEST COMPLETE!")
    print(f"Total Portfolio PnL: {total_pnl:.2f} USDT")
    print(f"Report saved to: REPORT_BACKTEST_700_DAYS.md")

if __name__ == "__main__":
    main()
