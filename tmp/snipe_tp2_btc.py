import sys
import os
import pandas as pd
sys.path.append(os.getcwd())

from core.engine import TradingEngine
from core.logger import logger
from config.config import Config

def snipe_tp2():
    engine = TradingEngine()
    print("🎯 ĐANG THỰC HIỆN SNIPE TP2 CHO BTC/USDT...")
    
    # Lấy vị thế thực tế từ sàn
    positions = engine.exchange.fetch_positions()
    btc_pos = None
    for p in positions:
        if "BTC" in p['symbol']:
            btc_pos = p
            break
            
    if not btc_pos:
        print("❌ Không thấy vị thế BTC trên sàn.")
        return

    symbol = btc_pos['symbol']
    # Ép trạng thái TP1_done để engine xử lý TP2
    btc_pos['tp1_done'] = True
    btc_pos['tp2_done'] = False
    btc_pos['tp2'] = 10000.0 # Target cực thấp để trigger
    btc_pos['side'] = 'LONG'
    btc_pos['entry'] = float(btc_pos.get('entryPrice', 0))
    btc_pos['tp1'] = btc_pos['entry'] * 1.01
    
    # Gọi trực tiếp hàm xử lý
    print(f"🚀 Kích hoạt logic TP2 cho {symbol}...")
    engine.process_symbol(symbol, None, btc_pos)
    print("✅ Đã thực hiện xong lệnh Snipe. Hãy kiểm tra Dashboard/Discord!")

if __name__ == "__main__":
    snipe_tp2()
