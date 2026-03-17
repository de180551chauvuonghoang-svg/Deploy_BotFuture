import sys
import os
import pandas as pd
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import TradingEngine
from core.logger import logger
from config.config import Config
from strategy.smc_strategy import SMCStrategy

def test_strategy_analysis():
    """
    Phân tích chiến thuật SMC hiện tại trên môi trường Testnet.
    Sẽ in ra các vùng Order Block, FVG và Structure cho các cặp tiền hàng đầu.
    """
    print("="*60)
    print("🔍 PHÂN TÍCH CHIẾN THUẬT SMC (TESTNET ENVIRONMENT)")
    print("="*60)
    
    engine = TradingEngine()
    strategy = SMCStrategy()
    
    test_pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"]
    
    for symbol in test_pairs:
        print(f"\n📊 Đang phân tích {symbol}...")
        data = engine._fetch_multi_tf_data(symbol)
        if not data:
            print(f"❌ Không thể lấy dữ liệu cho {symbol}")
            continue
            
        df_15m, df_1h, df_4h = data
        
        # Chạy logic chiến thuật
        # Chúng ta gọi trực tiếp để lấy signal_data chi tiết
        signal_data = strategy.generate_signal(symbol, engine.exchange, df_4h, df_1h, df_15m)
        
        if signal_data:
            conf = signal_data.get('confluences', {})
            print(f"  > Cấu trúc (Bias): {conf.get('bias', 'N/A')}")
            print(f"  > Regime: {conf.get('regime', 'N/A')}")
            print(f"  > SMC Score: {conf.get('score', 0):.1f}")
            print(f"  > Tín hiệu hiện tại: {signal_data.get('signal', 'NONE')}")
            print(f"  > Lý do: {signal_data.get('reason', 'N/A')}")
            
            if signal_data.get('signal') != 'NONE':
                print(f"  🚀 TIỀM NĂNG: Entry {signal_data['entry']:.2f}")
            else:
                print(f"  ⏳ Chờ đợi: Chưa đạt đủ điều kiện hội tụ (Score cần > {Config.MIN_SCORE_THRESHOLD})")
        else:
            print(f"  ❌ Không có dữ liệu phân tích cho {symbol}")

    print("\n" + "="*60)
    print("💡 Gợi ý: Nếu bạn muốn ép bot vào lệnh ngay để test logic SL/TP/Trailing,")
    print("   hãy sử dụng script 'tools/force_test_order.py'.")
    print("="*60)

if __name__ == "__main__":
    test_strategy_analysis()
