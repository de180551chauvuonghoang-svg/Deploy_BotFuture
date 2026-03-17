import json
import pandas as pd
from core.exchange import ExchangeHandler
from strategy.smc_strategy import SMCStrategy
import os

def check_current_positions_for_exit():
    ex = ExchangeHandler()
    strategy = SMCStrategy()
    
    pos_file = "data/dry_run_positions.json"
    if not os.path.exists(pos_file):
        print("No active positions.")
        return

    with open(pos_file, 'r') as f:
        positions = json.load(f)
    
    if not positions:
        print("Empty positions list.")
        return

    print(f"🕵️ Analyzing {len(positions)} active positions with AI Reversal Shield...")

    for pos in positions:
        symbol = pos['symbol']
        side = pos['side'].upper()
        print(f"\n--- Checking {symbol} ({side}) ---")
        
        # Fetch MF data
        data = ex.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df_15m = data if data is not None else None
        
        data_h1 = ex.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        df_1h = data_h1 if data_h1 is not None else None
        
        if df_15m is None or df_1h is None:
            print(f"⚠️ Could not fetch data for {symbol}")
            continue
            
        should_exit, reason = strategy.check_early_exit(symbol, side, df_15m, df_1h, pos)
        
        if should_exit:
            print(f"🚨 ALERT: {reason}")
        else:
            print(f"✅ Status OK. No reversal signals for {symbol}.")

if __name__ == "__main__":
    check_current_positions_for_exit()
