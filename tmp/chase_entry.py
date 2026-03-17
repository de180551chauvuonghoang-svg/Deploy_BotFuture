import sys
import os
sys.path.append(os.getcwd())

import json
import time
from core.exchange import ExchangeHandler
from config.config import Config
from risk.smart_risk import calculate_smart_sl_tp
from core.logger import logger

def chase_unfilled_orders():
    ex = ExchangeHandler()
    file_path = "data/dry_run_positions.json"
    
    if not os.path.exists(file_path):
        print("No active positions tracked.")
        return

    with open(file_path, 'r') as f:
        positions = json.load(f)

    # We want to chase: ETH/USDT and LTC/USDT
    target_symbols = ["ETH/USDT", "LTC/USDT"]
    updated_positions = []
    
    print("🚀 CHASING UNFILLED ORDERS TO CURRENT MARKET PRICE...")
    print("=" * 60)

    for pos in positions:
        symbol = pos['symbol']
        if symbol not in target_symbols:
            updated_positions.append(pos)
            continue
            
        try:
            # 1. Cancel existing orders for this symbol
            print(f"🔄 Canceling existing orders for {symbol}...")
            # We cancel by symbol to be safe
            ex.exchange.cancel_all_orders(symbol)
            
            # 2. Get current market price
            ticker = ex.fetch_ticker(symbol)
            current_price = ticker['last']
            print(f"📈 Current Price for {symbol}: {current_price}")
            
            # 3. Adjust entry price (Chase to current)
            # We'll use the current price as the new entry
            new_entry = ex.price_to_precision(symbol, current_price)
            
            # 4. Recalculate TP/SL to maintain Risk/Reward
            # Use same SL to keep risk profile, or adjust it? 
            # Usually keep SL at original technical zone.
            original_sl = float(pos.get('sl'))
            side = pos.get('side', 'LONG').upper()
            
            print(f"⚖️ Recalculating TP/SL for {symbol} (Entry: {new_entry}, SL: {original_sl})...")
            
            # We need ATR or similar for calculate_smart_sl_tp, 
            # but let's just use the RR multipliers from config for simplicity
            sl_dist = abs(new_entry - original_sl)
            
            if side == "LONG":
                new_tp1 = ex.price_to_precision(symbol, new_entry + (sl_dist * Config.TP1_RR * 0.8)) # 0.8 AI mult
                new_tp2 = ex.price_to_precision(symbol, new_entry + (sl_dist * Config.TP2_RR * 0.8))
                new_tp3 = ex.price_to_precision(symbol, new_entry + (sl_dist * Config.TP3_RR * 0.8))
            else:
                new_tp1 = ex.price_to_precision(symbol, new_entry - (sl_dist * Config.TP1_RR * 0.8))
                new_tp2 = ex.price_to_precision(symbol, new_entry - (sl_dist * Config.TP2_RR * 0.8))
                new_tp3 = ex.price_to_precision(symbol, new_entry - (sl_dist * Config.TP3_RR * 0.8))

            # 5. Place NEW matching order
            amount = float(pos['contracts'])
            side_cmd = 'buy' if side == 'LONG' else 'sell'
            
            print(f"🔥 Placing NEW {side} order for {symbol} @ {new_entry}...")
            order = ex.create_order(
                symbol, side_cmd, amount, 
                type='limit', price=new_entry,
                sl=original_sl, tp1=new_tp1, tp2=new_tp2, tp3=new_tp3
            )
            
            # 6. Place NEW Hard SL
            sl_side = 'sell' if side_cmd == 'buy' else 'buy'
            sl_order = ex.place_stop_order(symbol, sl_side, amount, original_sl)
            
            # Update local pos
            pos['entryPrice'] = str(new_entry)
            pos['entry'] = new_entry
            pos['sl'] = original_sl
            pos['tp1'] = new_tp1
            pos['tp2'] = new_tp2
            pos['tp3'] = new_tp3
            pos['sl_order_id'] = sl_order['id'] if sl_order else None
            
            print(f"✅ {symbol} updated and order replaced.")
            updated_positions.append(pos)
            
        except Exception as e:
            print(f"❌ Error chasing {symbol}: {e}")
            updated_positions.append(pos)

    # Save
    with open(file_path, 'w') as f:
        json.dump(updated_positions, f, indent=2)
    
    print("=" * 60)
    print("CHASE OPERATION COMPLETE.")

if __name__ == "__main__":
    chase_unfilled_orders()
