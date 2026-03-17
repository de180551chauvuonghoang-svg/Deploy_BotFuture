import sys
import os
import pandas as pd
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import TradingEngine
from core.logger import logger
from config.config import Config

def test_automated_order():
    """
    Script để test quy trình vào lệnh tự động của bot.
    Nó sẽ tạo một tín hiệu giả lập và ép bot thực hiện vào lệnh.
    """
    logger.info("="*50)
    logger.info("🚀 BẮT ĐẦU TEST QUY TRÌNH VÀO LỆNH TỰ ĐỘNG")
    logger.info("="*50)
    
    # Khởi tạo engine
    engine = TradingEngine()
    
    # Kích hoạt test chuỗi TP Chuyên nghiệp (BTC/USDT)
    symbol = "BTC/USDT"
    
    ticker = engine.exchange.fetch_ticker(symbol)
    if not ticker: return
    price = ticker['last']
    
    # Kích thước 0.01 BTC ~ $750 (TP1 33% ~ $250 -> Đủ hạn mức sàn)
    signal_data = {
        'symbol': symbol,
        'signal': 'LONG',
        'entry': price,
        'sl': price * 0.99,
        'tp1': price * 1.01,
        'tp2': price * 1.02,
        'tp3': price * 1.03,
        'size': 0.01,
        'reason': 'PROFESSIONAL TP SEQUENCE TEST',
        'confluences': {'score': 10.0}
    }
    
    logger.info(f"Kích hoạt lệnh test cho {symbol} tại giá {price}")
    logger.info(f"SL: {signal_data['sl']:.2f} | TP1: {signal_data['tp1']:.2f}")
    
    # Ép bot vào lệnh
    try:
        engine.open_position(symbol, signal_data)
        logger.info("="*50)
        logger.info("✅ LỆNH TEST ĐÃ ĐƯỢC GỬI ĐI!")
        logger.info("Hãy kiểm tra:")
        logger.info("1. Discord: Thông báo vào lệnh mới.")
        logger.info("2. Dashboard: Vị thế mới xuất hiện trong danh sách.")
        logger.info("3. Terminal: Log chi tiết quá trình vào lệnh.")
        logger.info("="*50)
    except Exception as e:
        logger.error(f"❌ Lỗi khi thực hiện lệnh test: {e}")

if __name__ == "__main__":
    test_automated_order()
