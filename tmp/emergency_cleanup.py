import sys
import os
sys.path.append(os.getcwd())

from core.exchange import ExchangeHandler
from core.logger import logger

def emergency_cleanup():
    ex = ExchangeHandler()
    print("🆘 ĐANG THỰC HIỆN DỌN DẸP KHẨN CẤP...")
    
    positions = ex.exchange.fetch_positions()
    managed = [p for p in positions if float(p['contracts']) > 0]
    
    if not managed:
        print("✅ Không có vị thế nào đang mở.")
        return

    for p in managed:
        symbol = p['symbol']
        amount = abs(float(p['contracts']))
        side = p['side'] # exchange side
        
        # Close side is opposite
        close_side = 'sell' if float(p['contracts']) > 0 else 'buy'
        
        print(f"🔥 Đóng vị thế {symbol} | Size: {amount}")
        try:
            # Using market order to exit immediately
            res = ex.exchange.create_order(symbol, 'market', close_side, amount)
            print(f"✅ Đã đóng {symbol} thành công.")
            
            # Clean up metadata
            all_meta = ex._load_dry_positions()
            updated_meta = [m for m in all_meta if ex._normalize_symbol(m['symbol']) != ex._normalize_symbol(symbol)]
            ex._save_dry_positions(updated_meta)
            
        except Exception as e:
            print(f"❌ Lỗi khi đóng {symbol}: {e}")

if __name__ == "__main__":
    emergency_cleanup()
