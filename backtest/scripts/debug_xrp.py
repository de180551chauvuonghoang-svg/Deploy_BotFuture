import ccxt
import pandas as pd
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from core.exchange import ExchangeHandler

def debug_xrp():
    print("--- XRP DEBUG START ---")
    exchange = ExchangeHandler()
    symbol = "XRP/USDT"
    
    print(f"Fetching OHLCV for {symbol}...")
    df = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=10)
    
    if df is None:
        print("❌ Error: df is None")
        return
        
    print(f"Success! Rows: {len(df)}")
    print(f"Index type: {type(df.index)}")
    print("Columns types:")
    print(df.dtypes)
    print("\nSample Rows:")
    print(df.head())
    print("\n--- XRP DEBUG END ---")

if __name__ == "__main__":
    debug_xrp()
