from backtest.engine import Backtester
from backtest.data import fetch_historical_data
from strategy.signal_generator import SignalGenerator
from core.exchange import ExchangeHandler
from config.config import Config
import pandas as pd
import os
import ccxt

def main():
    symbol = 'BTC/USDT'
    days = 90 
    
    print(f"--- Advanced SMC Backtest for {symbol} ---")
    
    # 1. Initialize Public Exchange
    public_exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    
    # 2. Load Data for Multiple Timeframes
    print("Fetching 15m data...")
    df_15m = fetch_historical_data(public_exchange, symbol, '15m', days=days)
    
    print("Fetching 1h data...")
    df_1h = fetch_historical_data(public_exchange, symbol, '1h', days=days)
    
    print("Fetching 4h data...")
    df_4h = fetch_historical_data(public_exchange, symbol, '4h', days=days)
    
    if df_15m is None or df_1h is None or df_4h is None:
        print("Failed to fetch multi-timeframe data.")
        return
        
    # 3. Initialize Strategy & Backtester
    strategy = SignalGenerator(name="AdvancedSMC")
    backtester = Backtester(strategy, initial_capital=10000)
    
    # 4. Run Backtest
    report = backtester.run(df_15m, df_1h, df_4h)
    
    print(report)
    
    # 5. Save Results
    with open('backtest_results_smc.txt', 'w') as f:
        f.write(report)
    print("Results saved to backtest_results_smc.txt")

if __name__ == "__main__":
    main()
