from backtest.engine import Backtester
from backtest.data import fetch_historical_data
from strategy.base import SniperTrendStrategy
from core.exchange import ExchangeHandler
from config.config import Config
import pandas as pd
import os

def main():
    symbol = 'BTC/USDT'
    timeframe = '1h'
    days = 360
    
    print(f"--- 360-Day Backtest for {symbol} ({timeframe}) ---")
    
    # 1. Load Data
    import ccxt
    public_exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    df = fetch_historical_data(public_exchange, symbol, timeframe, days=days)
    
    if df is None or df.empty:
        print("Failed to fetch data. Public exchange OHLCV failed.")
        return
        
    # 2. Initialize Strategy & Backtester
    strategy = SniperTrendStrategy()
    backtester = Backtester(strategy, initial_capital=10000)
    
    # 3. Run
    report = backtester.run(df)
    
    print(report)
    
    # 4. Save to a log file for README update
    with open('backtest_results.txt', 'w') as f:
        f.write(report)

if __name__ == "__main__":
    main()
