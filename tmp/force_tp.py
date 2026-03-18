import json
import os
import pandas as pd
from core.exchange import ExchangeHandler
from config.config import Config
from utils.notifications import notify_trade_closed, send_discord_notification
import logging

# Setup logging to be visible
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("force_tp")

def force_zec_tp1():
    ex = ExchangeHandler()
    symbol = "ZEC/USDT"
    
    # 1. Fetch current data
    ticker = ex.fetch_ticker(symbol)
    cur_price = ticker['last']
    
    # 2. Load position
    pos_file = "data/dry_run_positions.json"
    if not os.path.exists(pos_file):
        print("Positions file not found.")
        return
        
    with open(pos_file, 'r') as f:
        positions = json.load(f)
        
    pos = next((p for p in positions if p['symbol'] == symbol), None)
    if not pos:
        print("ZEC position not found.")
        return
        
    if pos.get('tp1_done'):
        print("TP1 already done for ZEC.")
        return

    side = pos['side'].upper()
    contracts = abs(float(pos['contracts']))
    entry = float(pos['entry'])
    tp1 = float(pos['tp1'])
    
    print(f"🚀 FORCING TP1 for {symbol}")
    print(f"Current Price: {cur_price} | TP1: {tp1}")
    
    # Check if price actually met TP1
    if not ((side == 'LONG' and cur_price >= tp1) or (side == 'SHORT' and cur_price <= tp1)):
        print("⚠️ Current price has not reached TP1. Forcing anyway as requested.")

    # 3. Calculate close amount (33%)
    close_amt = contracts * 0.33
    close_amt = ex.amount_to_precision(symbol, close_amt)
    
    # 4. Execute close on exchange
    order_side = 'sell' if side == 'LONG' else 'buy'
    print(f"Executing {order_side} of {close_amt} {symbol}...")
    
    order = ex.create_order(symbol, order_side, close_amt)
    if not order:
        print("❌ Failed to create exchange order.")
        return

    # 5. Update local data
    now_str = pd.Timestamp.now().strftime('%H:%M:%S')
    tp1_usd = (cur_price - entry) * float(close_amt) if side == 'LONG' else (entry - cur_price) * float(close_amt)
    
    pos['tp1_done'] = True
    pos['tp1_time'] = now_str
    pos['tp1_usd'] = round(tp1_usd, 2)
    pos['realizedPnl'] = float(pos.get('realizedPnl', 0)) + tp1_usd
    
    remaining_contracts = contracts - float(close_amt)
    pos['contracts'] = remaining_contracts
    
    # 6. Move SL to BE
    new_sl = ex.price_to_precision(symbol, entry)
    old_sl = pos['sl']
    pos['sl'] = new_sl
    
    # Update SL order on exchange
    if pos.get('sl_order_id'):
        try: ex.cancel_order(symbol, pos['sl_order_id'])
        except: pass
        
    sl_side = 'sell' if side == 'LONG' else 'buy'
    sl_order = ex.place_stop_order(symbol, sl_side, remaining_contracts, new_sl)
    pos['sl_order_id'] = sl_order['id'] if sl_order else None

    # 7. Save metadata
    ex.update_position_metadata(symbol, pos)
    
    print(f"✅ Success! TP1 Secured: +{tp1_usd:.2f} USDT")
    print(f"✅ SL Moved to Entry: {new_sl}")
    
    # 8. Notifications
    notify_trade_closed(symbol, tp1_usd, f"TP1 Forced Reached (+{tp1_usd:.2f} USDT) - HARD BE ACTIVE")
    send_discord_notification(f"🎯 **ZEC/USDT TP1 FORCED**\nProfit: +{tp1_usd:.2f} USDT\nNew SL: {new_sl} (Breakeven)")

if __name__ == "__main__":
    force_zec_tp1()
