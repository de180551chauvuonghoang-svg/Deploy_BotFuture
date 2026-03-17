import sys
import os
sys.path.append(os.getcwd())

import json
import pandas as pd
import pandas_ta as ta
from core.exchange import ExchangeHandler
from strategy.smc_strategy import SMCStrategy
from ai.inference import ai_engine
from risk.smart_risk import calculate_smart_sl_tp
from config.config import Config

def ai_adjust_active_positions():
    ex = ExchangeHandler()
    strategy = SMCStrategy()
    file_path = "data/dry_run_positions.json"
    
    if not os.path.exists(file_path):
        print("No active positions found.")
        return

    with open(file_path, 'r') as f:
        positions = json.load(f)

    updated_positions = []
    
    print("🧠 AI IS ANALYZING ACTIVE TRADES FOR DYNAMIC TP...")
    print("=" * 50)

    for pos in positions:
        symbol = pos['symbol']
        side = pos.get('side', 'LONG').upper()
        
        try:
            # 1. Fetch data for AI analysis
            df_15m = ex.fetch_ohlcv(symbol, '15m', limit=100)
            df_1h = ex.fetch_ohlcv(symbol, '1h', limit=100)
            df_4h = ex.fetch_ohlcv(symbol, '4h', limit=100)
            
            if df_15m is None or df_15m.empty:
                print(f"⚠️ Skipping {symbol}: Missing data")
                updated_positions.append(pos)
                continue

            # 2. Reconstruct features for AI
            # (Matches logic in smc_strategy.py)
            df_15m['rsi'] = ta.rsi(df_15m['close'], length=14)
            df_15m['vol_sma'] = df_15m['volume'].rolling(20).mean()
            df_4h['ema_200'] = ta.ema(df_4h['close'], length=200)
            
            rsi_15m = df_15m['rsi'].iloc[-1]
            vol_ratio = df_15m['volume'].iloc[-1] / df_15m['vol_sma'].iloc[-1] if df_15m['vol_sma'].iloc[-1] > 0 else 1.0
            ema200 = df_4h['ema_200'].iloc[-1]
            dist_ema200 = (df_4h['close'].iloc[-1] - ema200) / ema200 if pd.notna(ema200) and ema200 > 0 else 0
            
            entry_px = float(pos['entryPrice'])
            sl_dist_pct = abs(entry_px - float(pos['sl'])) / entry_px
            
            features = {
                'score': float(pos.get('score', 8.5)),
                'rsi_15m': rsi_15m if not pd.isna(rsi_15m) else 50,
                'vol_ratio_15m': vol_ratio,
                'dist_ema200_h4': dist_ema200,
                'sl_dist_pct': sl_dist_pct,
                'tp_dist_pct': sl_dist_pct * Config.TP1_RR,
                'rr': Config.TP1_RR,
                'body_ratio': 0.5,
                'vol_24h_usdt': (df_15m['volume'] * df_15m['close']).rolling(window=96).sum().iloc[-1],
                'side': 1 if side == 'LONG' else 0
            }
            
            # 3. Get AI Confidence
            conf = ai_engine.get_confidence(features)
            
            # 4. Calculate Dynamic Multiplier
            ai_mult = (conf - 0.70) / 0.15
            ai_mult = max(0.8, min(1.5, ai_mult))
            
            # 5. Apply new TPs
            sl_dist = abs(entry_px - float(pos['sl']))
            tp1_rr = Config.TP1_RR * ai_mult
            tp2_rr = Config.TP2_RR * ai_mult
            tp3_rr = Config.TP3_RR * ai_mult
            
            if side == "LONG":
                pos['tp1'] = round(entry_px + (sl_dist * tp1_rr), 6)
                pos['tp2'] = round(entry_px + (sl_dist * tp2_rr), 6)
                pos['tp3'] = round(entry_px + (sl_dist * tp3_rr), 6)
            else:
                pos['tp1'] = round(entry_px - (sl_dist * tp1_rr), 6)
                pos['tp2'] = round(entry_px - (sl_dist * tp2_rr), 6)
                pos['tp3'] = round(entry_px - (sl_dist * tp3_rr), 6)
            
            print(f"✅ {symbol} (AI Conf: {conf:.1%}) -> Multiplier: {ai_mult:.2f}x")
            print(f"   Target TP1: {pos['tp1']} ({tp1_rr:.2f}R)")
            
            updated_positions.append(pos)
            
        except Exception as e:
            print(f"❌ Error updating {symbol}: {e}")
            updated_positions.append(pos)

    # Save
    with open(file_path, 'w') as f:
        json.dump(updated_positions, f, indent=2)
    
    print("=" * 50)
    print("AI DYNAMIC UPGRADE COMPLETE.")

if __name__ == "__main__":
    ai_adjust_active_positions()
