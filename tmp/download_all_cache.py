import sys
import os
sys.path.append(os.getcwd())

import ccxt
import time
from backtest.data import fetch_historical_data
from config.config import Config
from core.logger import logger

def download_everything():
    symbols = Config.TRADING_PAIRS
    # Normalize symbols: trailing space, etc.
    symbols = [s.strip() for s in symbols if s.strip()]
    
    timeframes = ['15m', '1h', '4h']
    days_to_fetch = 180
    
    # Use Testnet if configured, but for history usually Mainnet is better/more stable
    # However, let's stick to the handler's exchange logic or just use Mainnet for data.
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    print(f"🚀 STARTING BULK DOWNLOAD: {len(symbols)} Symbols x {len(timeframes)} Timeframes")
    print(f"   Target: {days_to_fetch} Days")
    print("="*60)
    
    for i, symbol in enumerate(symbols):
        print(f"\n[{i+1}/{len(symbols)}] Processing {symbol}...")
        for tf in timeframes:
            try:
                fetch_historical_data(exchange, symbol, tf, days=days_to_fetch)
            except Exception as e:
                print(f"   ❌ Error {symbol} ({tf}): {e}")
                
    print("\n" + "="*60)
    print("✅ BULK DOWNLOAD COMPLETE!")

if __name__ == "__main__":
    download_everything()
