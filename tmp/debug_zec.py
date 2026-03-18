import json
import os
from core.exchange import ExchangeHandler
from config.config import Config

def debug_zec_tp():
    ex = ExchangeHandler()
    symbol = "ZEC/USDT"
    
    # 1. Fetch current price
    ticker = ex.fetch_ticker(symbol)
    cur_price = ticker['last']
    
    # 2. Load position data
    pos_file = "data/dry_run_positions.json"
    with open(pos_file, 'r') as f:
        positions = json.load(f)
    
    zec_pos = next((p for p in positions if p['symbol'] == symbol), None)
    
    if not zec_pos:
        print("ZEC position not found in dry_run_positions.json")
        return
        
    tp1 = float(zec_pos.get('tp1', 0))
    tp1_done = zec_pos.get('tp1_done', False)
    
    print(f"--- Debug ZEC TP1 ---")
    print(f"Current Price (Ticker): {cur_price}")
    print(f"Target TP1: {tp1}")
    print(f"TP1 Done Status: {tp1_done}")
    
    is_tp1 = cur_price >= tp1
    print(f"Condition (cur_price >= tp1): {is_tp1}")
    
    if is_tp1 and not tp1_done:
        print("🚨 TRIGGER SHOULD HAVE FIRED!")
        # Check size/notional
        contracts = abs(float(zec_pos['contracts']))
        close_amt = contracts * 0.33
        notional = close_amt * cur_price
        min_notional = 100.0 if Config.USE_TESTNET else 10.0
        print(f"Close Amount (33%): {close_amt}")
        print(f"Notional: {notional}")
        print(f"Min Notional Required: {min_notional}")
        if notional < min_notional:
            print("❌ REASON: Notional too small for Testnet close.")
    else:
        print("✅ Condition for TP1 not met (either price too low or already done).")

if __name__ == "__main__":
    debug_zec_tp()
