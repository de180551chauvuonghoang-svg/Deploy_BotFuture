import os
import sys
import pandas as pd
import time
from datetime import datetime, timedelta
import pandas_ta as ta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import Config
from core.exchange import ExchangeHandler
from strategy.smc_strategy import SMCStrategy

def format_time(minutes):
    if minutes < 60:
        return f"{int(minutes)}m"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h {m}m"

def predict_signals():
    print("="*60)
    print(f"🚀 SMC SIGNAL PREDICTOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    exchange = ExchangeHandler()
    strategy = SMCStrategy()
    
    results = []
    
    for symbol in Config.TRADING_PAIRS:
        try:
            # Fetch data (cached if possible)
            df_15m = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
            df_1h = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=200)
            df_4h = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=200)
            
            if df_15m is None or df_1h is None or df_4h is None:
                continue
                
            # Current price and ATR
            curr_px = df_15m['close'].iloc[-1]
            atr_15m = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'], length=14).iloc[-1]
            avg_candle_pct = (atr_15m / curr_px) * 100
            
            # Use strategy logic to get zones and bias
            # We bypass the full signal to get the underlying structure
            from strategy.structure import detect_structure
            from strategy.regime_filter import get_regime
            from strategy.order_blocks import find_bullish_ob, find_bearish_ob
            from strategy.fvg import find_fvg
            
            structure = detect_structure(df_4h, lookback=400)
            bias = structure['bias']
            regime = get_regime(df_1h)
            
            # Find closest zones
            zones = []
            if bias == "LONG":
                obs = find_bullish_ob(df_1h, lookback=200)
                fvgs = find_fvg(df_1h, lookback=200)
                # For long, we care about zones BELOW price
                for z in obs + fvgs:
                    if z['top'] < curr_px:
                        dist_pct = abs(curr_px - z['top']) / curr_px * 100
                        zones.append({'type': 'OB' if 'bottom' in z else 'FVG', 'dist': dist_pct, 'target': z['top']})
            elif bias == "SHORT":
                obs = find_bearish_ob(df_1h, lookback=200)
                fvgs = find_fvg(df_1h, lookback=200)
                # For short, we care about zones ABOVE price
                for z in obs + fvgs:
                    if z['bottom'] > curr_px:
                        dist_pct = abs(z['bottom'] - curr_px) / curr_px * 100
                        zones.append({'type': 'OB' if 'bottom' in z else 'FVG', 'dist': dist_pct, 'target': z['bottom']})
            
            # Sort zones by distance
            zones.sort(key=lambda x: x['dist'])
            
            # Estimation logic
            min_dist = zones[0]['dist'] if zones else 999
            
            # Score (for quality check)
            sig_data = strategy.generate_signal(symbol, exchange, df_4h, df_1h, df_15m)
            score = sig_data.get('confluences', {}).get('score', 0)
            
            # Determine sentiment and ETA
            if bias == "NONE":
                sentiment = "💤 NO BIAS"
                eta_min = -1
                status = "Chờ cấu trúc 4H hình thành."
            elif regime == "AVOID":
                sentiment = "⚠️ VOLATILE"
                eta_min = -1
                status = "Thị trường quá biến động, rủi ro cao."
            elif sig_data['signal'] != "NONE":
                sentiment = "🔥 TRIGGERED"
                eta_min = 0
                status = "Lệnh đang mở hoặc giá đang trong vùng Entry!"
            elif min_dist < 0.2:
                sentiment = "🚀 IMMINENT"
                eta_min = (min_dist / avg_candle_pct) * 15 # Approx in 15m intervals
                status = f"Giá cực sát vùng {zones[0]['type']}. Sẵn sàng vào lệnh."
            elif min_dist < 0.8 and score > 5:
                sentiment = "👀 WATCHING"
                # ETA: Usually takes 4-8 candles to bridge 0.5-0.8% distance
                eta_min = (min_dist / avg_candle_pct) * 15 * 1.5
                status = f"Đang chờ hồi về {zones[0]['type']}. Setup chất lượng cao."
            else:
                sentiment = "⏳ DEVELOPING"
                eta_min = (min_dist / avg_candle_pct) * 15 * 2.5
                status = "Đang trong quá trình hình thành cấu trúc."

            results.append({
                'symbol': symbol,
                'bias': bias,
                'score': score,
                'dist': min_dist,
                'eta': eta_min,
                'sentiment': sentiment,
                'status': status
            })
            
        except Exception as e:
            # print(f"Error analyzing {symbol}: {e}")
            continue

    # Sort results by ETA
    results.sort(key=lambda x: x['eta'] if x['eta'] >= 0 else 9999)

    print(f"{'SYMBOL':<12} | {'BIAS':<6} | {'SCORE':<5} | {'DIST %':<7} | {'SENTIMENT':<12} | {'ETA':<8}")
    print("-" * 60)
    for r in results:
        eta_str = format_time(r['eta']) if r['eta'] > 0 else "---" if r['eta'] < 0 else "NOW"
        print(f"{r['symbol']:<12} | {r['bias']:<6} | {r['score']:<5.1f} | {r['dist']:<7.2f} | {r['sentiment']:<12} | {eta_str:<8}")
        print(f"   └─ Status: {r['status']}")
    
    print("\n" + "="*60)
    print("💡 Lưu ý: Đây là dự báo dựa trên vận tốc nến trung bình (ATR).")
    print("   Thị trường có thể đảo chiều hoặc đi ngang bất cứ lúc nào.")
    print("="*60)

if __name__ == "__main__":
    predict_signals()
