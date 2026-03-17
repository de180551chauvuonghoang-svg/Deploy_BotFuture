import sys
import os
import time
sys.path.append(os.getcwd())

from core.exchange import ExchangeHandler

def chunk_close_melania():
    ex = ExchangeHandler()
    symbol = "MELANIA/USDT:USDT"
    target_amount = 250866.06
    chunk_size = 5000.0 # Thử size nhỏ hơn nữa
    
    print(f"🆘 Đang đóng MELANIA chi tiết từng phần (Size: {target_amount})...")
    
    # Clean up meta anyway
    all_meta = ex._load_dry_positions()
    updated_meta = [m for m in all_meta if "MELANIA" not in m['symbol']]
    ex._save_dry_positions(updated_meta)

    # Thử gọi API để lấy MAX SIZE nếu có thể
    try:
        markets = ex.exchange.load_markets()
        market = markets.get(symbol)
        if market:
            limits = market.get('limits', {})
            print(f"DEBUG: Limits: {limits}")
    except: pass

    remaining = target_amount
    while remaining > 0:
        batch = min(remaining, chunk_size)
        try:
            ex.exchange.create_order(symbol, 'market', 'sell', batch)
            remaining -= batch
            print(f"✅ Chốt {batch}. Còn lại: {remaining:.2f}")
        except Exception as e:
            if "Quantity greater than max quantity" in str(e):
                chunk_size /= 2
                print(f"⚠️ Giảm chunk size xuống {chunk_size}...")
                if chunk_size < 1: break
            else:
                print(f"❌ Lỗi khác: {e}")
                break

    print("✅ Hoàn tất dọn dẹp MELANIA.")

if __name__ == "__main__":
    chunk_close_melania()
