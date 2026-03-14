import os
import sys
import pandas as pd
import warnings

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from core.exchange import ExchangeHandler
from strategy.smc_strategy import SMCStrategy
from strategy.structure import detect_structure

warnings.filterwarnings('ignore')

def main():
    try:
        exchange = ExchangeHandler()
        strategy = SMCStrategy()
        balance = exchange.get_balance()
        
        print("=== DỰ ĐOÁN TÍN HIỆU SMC (TRẠNG THÁI HIỆN TẠI) ===")
        for symbol in Config.TRADING_PAIRS:
            df_15m = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=500)
            df_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=500)
            df_4h = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=500)
            
            if df_15m is None or df_1h is None or df_4h is None:
                print(f"{symbol}: Lỗi khi lấy dữ liệu")
                continue
                
            sig_data = strategy.generate_signal(symbol, exchange, df_4h, df_1h, df_15m, balance=balance)
            
            # Fetch zones manually for display
            from strategy.order_blocks import find_bullish_ob, find_bearish_ob
            from strategy.fvg import find_fvg
            
            structure_4h = detect_structure(df_4h, lookback=400)
            bias = structure_4h["bias"]
            
            ob_list = (find_bullish_ob(df_1h, lookback=200) if bias == "LONG" 
                      else find_bearish_ob(df_1h, lookback=200)) if bias != "NONE" else []
            fvg_list = find_fvg(df_1h, lookback=200)
            
            if "confluences" in sig_data:
                conf = sig_data["confluences"]
                score = conf.get("score", 0.0)
                reason = sig_data.get("reason", "")
                
                print(f"\n🔹 [{symbol}] Xu hướng 4H: {bias} | Điểm chất lượng: {score:.1f}/10")
                
                if bias != "NONE":
                    if ob_list:
                        nearest_ob = ob_list[0]
                        print(f"   📍 Vùng Order Block (1H): {nearest_ob['bottom']:.2f} - {nearest_ob['top']:.2f}")
                    if fvg_list:
                        # Find nearest FVG to current price
                        curr_px = df_15m['close'].iloc[-1]
                        nearest_fvg = min(fvg_list, key=lambda x: abs(x['bottom'] - curr_px))
                        print(f"   📍 Vùng FVG (1H): {nearest_fvg['bottom']:.2f} - {nearest_fvg['top']:.2f}")

                    if not (conf.get("ob_hit") or conf.get("fvg_hit")):
                        curr_px = df_15m['close'].iloc[-1]
                        print(f"   ⏳ Dự đoán: Giá hiện tại ({curr_px:.2f}) chưa chạm vùng. Cần {'GIẢM' if bias == 'LONG' else 'TĂNG'} về các vùng trên để kích hoạt lệnh.")
                    elif score < 6.0:
                        print(f"   🔍 Dự đoán: Giá ĐÃ CHẠM vùng. Đang chờ xác nhận Momentum/Liquidity (Điểm hiện tại: {score:.1f}).")
                    else:
                        print("   🚀 Dự đoán: TÍN HIỆU MẠNH! Đủ điều kiện vào lệnh.")
                else:
                    print(f"   ⚪ Trạng thái: {reason}")
                
    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == '__main__':
    main()
