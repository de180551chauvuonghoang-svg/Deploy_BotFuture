import sys
import os
sys.path.append(os.getcwd())

from core.exchange import ExchangeHandler
from config.config import Config
from core.logger import logger

def cleanup_duplicate_orders():
    ex = ExchangeHandler()
    print("🧹 ĐANG DỌN DẸP LỆNH TRÙNG LẶP...")
    
    for symbol in Config.TRADING_PAIRS:
        try:
            orders = ex.exchange.fetch_open_orders(symbol)
            if not orders: continue
            
            # Group by type to only clean LIMIT (entry) orders, not STOP
            limit_orders = [o for o in orders if o['type'].upper() == 'LIMIT']
            
            if len(limit_orders) > 1:
                print(f"⚠️ Phát hiện {len(limit_orders)} lệnh LIMIT cho {symbol}. Giữ lại lệnh MỚI NHẤT, hủy các lệnh cũ.")
                # Sort by timestamp
                limit_orders.sort(key=lambda x: x['timestamp'])
                to_cancel = limit_orders[:-1]
                for o in to_cancel:
                     print(f"🔥 Hủy lệnh {o['id']} cho {symbol}")
                     try:
                         ex.exchange.cancel_order(o['id'], symbol)
                     except Exception as e:
                         print(f"❌ Lỗi khi hủy: {e}")
        except Exception as e:
            print(f"❌ Lỗi khi quét {symbol}: {e}")

if __name__ == "__main__":
    cleanup_duplicate_orders()
