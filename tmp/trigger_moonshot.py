import sys
import os
sys.path.append(os.getcwd())

from core.engine import TradingEngine
from core.logger import logger

def demo_moonshot_logic():
    engine = TradingEngine()
    print("🌙 KÍCH HOẠT CHUỖI TP2 -> TP3 -> MOONSHOT CHO ETH/USDT...")
    
    positions = engine.exchange.fetch_positions()
    eth_pos = None
    for p in positions:
        if "ETH" in p['symbol']:
            eth_pos = p
            break
            
    if not eth_pos:
        print("❌ Không thấy vị thế ETH trên sàn.")
        return

    symbol = eth_pos['symbol']
    # Giả lập trạng thái đã qua TP1
    eth_pos['tp1_done'] = True
    eth_pos['tp2_done'] = False # Để trigger TP2 ngay
    eth_pos['tp2'] = 1000.0   # Target ảo để khớp ngay
    eth_pos['tp3'] = 1010.0
    eth_pos['side'] = 'LONG'
    eth_pos['entry'] = 2343.68
    eth_pos['tp1'] = 2200.0   # Mức giá để khóa SL tại đây
    
    print(f"🚀 BƯỚC 1: Kích hoạt TP2 (Chốt 50% còn lại, khóa SL tại TP1)...")
    engine.process_symbol(symbol, None, eth_pos)
    
    # Đợi 1 chút để metadata cập nhật
    eth_pos['tp2_done'] = True
    eth_pos['tp3_done'] = False
    print(f"🚀 BƯỚC 2: Kích hoạt TP3 & MOONSHOT (Giữ 17% cuối, Trail cực chặt)...")
    engine.process_symbol(symbol, None, eth_pos)
    
    print("✅ HOÀN TẤT MÔ PHỎNG. Hãy kiểm tra Dashboard để thấy vị thế ETH đã 'gồng lãi' Moonshot!")

if __name__ == "__main__":
    demo_moonshot_logic()
