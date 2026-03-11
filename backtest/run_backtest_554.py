import ccxt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import warnings
import os
from concurrent.futures import ProcessPoolExecutor
from backtest.engine import Backtester
from data import fetch_historical_data
from ..strategy.smc_strategy import SMCStrategy

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
        df_1h = fetch_historical_data(exchange, symbol, '1h', days=days)
        df_4h = fetch_historical_data(exchange, symbol, '4h', days=days)
        
        if df_15m is None or df_1h is None or df_4h is None:
            return None

        # 2. Initialize Backtester
        backtester = Backtester(initial_capital=10000, strategy=strategy)
        
        # 3. Run
        backtester.run(df_15m, df_1h, df_4h)
        return backtester.trade_log, backtester.capital
    except Exception as e:
        print(f"Error testing {symbol}: {e}")
        return None

def main():
    # List of coins to test
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'AVAX/USDT']
    days = 554 
    
    print(f"--- PARALLEL SMC BACKTEST START (Symbols: {len(symbols)}) ---")
    print(f"--- Duration: {days} days ---")
    
    all_trades = []
    current_total_capital = 0
    
    # Using ProcessPoolExecutor to use all CPU Cores
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(run_symbol_backtest, s, days): s for s in symbols}
        
        for future in futures:
            symbol = futures[future]
            result = future.result()
            if result:
                trades, final_cap = result
                all_trades.extend(trades)
                current_total_capital += final_cap
                print(f"--- [{symbol}] Finished. Capital: {final_cap:.2f} ---")
            else:
                current_total_capital += 10000
                print(f"--- [{symbol}] Failed or No Data. ---")

    # 4. Global Report
    if not all_trades:
        print("\nNo trades executed across all symbols.")
        return

    df_all = pd.DataFrame(all_trades)
    total_pnl = df_all['pnl'].sum()
    win_rate = (len(df_all[df_all['pnl'] > 0]) / len(df_all)) * 100
    
    report = f"""
==================================================
       PARALLEL SMC MULTI-TOKEN GLOBAL REPORT
==================================================
Test Duration:    {days} Days
Symbols tested:   {len(symbols)}
Total PnL:        {total_pnl:.2f} USDT
Win Rate:         {win_rate:.2f}%
Total Trades:     {len(df_all)}
Final Balance:    {current_total_capital:.2f} USDT
==================================================
    """
    print(report)
    
    with open("backtest_results_554_days.txt", "w") as f:
        f.write(report)
    print("Full results saved to backtest_results_554_days.txt")

if __name__ == "__main__":
    main()
