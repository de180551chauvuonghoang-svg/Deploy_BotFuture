import pandas as pd
import pandas_ta as ta
from strategy.regime_filter import get_regime
from strategy.structure import detect_structure
from strategy.order_blocks import find_bullish_ob, find_bearish_ob, price_in_ob_zone
from strategy.fvg import find_fvg, price_in_fvg
from strategy.liquidity import detect_liquidity_sweep
from strategy.confluence import score_setup
from risk.smart_risk import calculate_smart_sl_tp
from config.config import Config
from utils.notifications import notify_trade_opened, notify_trade_closed, send_discord_notification

def notify_potential_signal(symbol, bias, score, reason):
    msg = f"🔍 **Potential Signal Alert**\n" \
          f"Symbol: `{symbol}`\n" \
          f"Direction: `{bias}`\n" \
          f"Quality Score: `{score:.1f}/10.0`\n" \
          f"Status: `{reason}`"
    send_discord_notification(msg)

class SMCStrategy:
    """
    Professional Smart Money Concepts (SMC) Strategy.
    Integrates all modules: regime, structure, OBs, FVGs, Liquidity, and Scoring.
    """
    def __init__(self, name="AdvancedSMC"):
        self.name = name

    def generate_signal(self, symbol, exchange, df_4h, df_1h, df_15m, balance=10000) -> dict:
        """
        Processes data from three timeframes to generate a high-conviction SMC signal.
        """
        if df_4h is None or df_1h is None or df_15m is None:
            return {"signal": "NONE", "reason": "Missing multi-TF data"}

        # 1. Market Regime
        regime = get_regime(df_1h)
        
        # 2. Macro Structure (4H bias)
        structure_4h = detect_structure(df_4h, lookback=400)
        bias = structure_4h["bias"]

        # 3. Key Zones (OB & FVG)
        if bias != "NONE":
            ob_list = (find_bullish_ob(df_1h, lookback=200) if bias == "LONG" 
                      else find_bearish_ob(df_1h, lookback=200))
            fvg_list = find_fvg(df_1h, lookback=200)
        else:
            ob_list, fvg_list = [], []
        
        # 4. Entry Check (Zone Touch)
        curr_px = df_15m['close'].iloc[-1]
        high_15m = df_15m['high'].iloc[-1]
        low_15m = df_15m['low'].iloc[-1]
        
        def touched(px_low, px_high, zone_list):
            for z in zone_list:
                if px_low <= z['top'] and px_high >= z['bottom']:
                    return z
            return None

        ob_hit = touched(low_15m, high_15m, ob_list)
        fvg_hit = touched(low_15m, high_15m, fvg_list)
        
        # 5. Scoring
        sweep = detect_liquidity_sweep(df_15m)
        score = score_setup(bias, regime, ob_hit, fvg_hit, sweep, df_15m, df_1h) if bias != "NONE" else 0.0

        confluences = {
            "bias": bias,
            "regime": regime,
            "ob_hit": ob_hit is not None,
            "fvg_hit": fvg_hit is not None,
            "liquidity_sweep": sweep['swept'],
            "score": score
        }

        # Early exit reasons
        if regime == "AVOID":
            return {"signal": "NONE", "reason": "Market regime: AVOID", "confluences": confluences}
        if bias == "NONE":
            return {"signal": "NONE", "reason": "No clear 4H structure bias", "confluences": confluences}
        if not (ob_hit or fvg_hit):
            return {"signal": "NONE", "reason": "Price not in 1H OB/FVG zone", "confluences": confluences}
        if score < Config.MIN_SCORE_THRESHOLD:
            if score >= (Config.MIN_SCORE_THRESHOLD - 0.5):
                # Prediction alert for high-quality setup close to triggering
                notify_potential_signal(symbol, bias, score, f"Prime Setup - Very close to entry trigger (Score {Config.MIN_SCORE_THRESHOLD})")
            return {"signal": "NONE", "reason": f"Quality score {score:.1f} too low (Min: {Config.MIN_SCORE_THRESHOLD})", "confluences": confluences}

        # 6. Risk Calculation
        # ENTRY OPTIMIZATION: Enter at 50% Equilibrium of the OB for higher R/R and Win Rate
        if ob_hit:
            entry_px = (ob_hit['top'] + ob_hit['bottom']) / 2
        else:
            entry_px = curr_px # Fallback for FVG
            
        atr_15m_all = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'])
        atr_15m = atr_15m_all.iloc[-1]
        risk_data = calculate_smart_sl_tp(bias, entry_px, ob_hit, atr_15m, balance, score)
        
        if not risk_data:
            return {"signal": "NONE", "reason": "Risk distance too large", "confluences": confluences}

        # 7. AI Confidence Filter (NEW)
        ai_confidence = 1.0
        try:
            from ai.inference import ai_engine
            
            # Prepare features for AI
            rsi_15m = df_15m['rsi'].iloc[-1] if 'rsi' in df_15m.columns else 50
            vol_sma = df_15m['vol_sma'].iloc[-1] if 'vol_sma' in df_15m.columns else df_15m['volume'].rolling(20).mean().iloc[-1]
            vol_ratio = df_15m['volume'].iloc[-1] / vol_sma if vol_sma > 0 else 1.0
            
            ema200_h4 = df_4h['ema_200'].iloc[-1] if 'ema_200' in df_4h.columns else df_4h['close'].iloc[-1]
            dist_ema200 = (df_4h['close'].iloc[-1] - ema200_h4) / ema200_h4 if ema200_h4 > 0 else 0
            
            sl_dist_pct = abs(entry_px - risk_data['sl']) / entry_px
            tp_dist_pct = abs(risk_data['tp1'] - entry_px) / entry_px
            rr = tp_dist_pct / sl_dist_pct if sl_dist_pct > 0 else 1.0
            
            curr = df_15m.iloc[-1]
            body_ratio = abs(curr['close'] - curr['open']) / (curr['high'] - curr['low']) if (curr['high'] - curr['low']) > 0 else 0
            
            features = {
                'score': score,
                'rsi_15m': rsi_15m,
                'vol_ratio_15m': vol_ratio,
                'dist_ema200_h4': dist_ema200,
                'sl_dist_pct': sl_dist_pct,
                'tp_dist_pct': tp_dist_pct,
                'rr': rr,
                'body_ratio': body_ratio,
                'vol_24h_usdt': (df_15m['volume'] * df_15m['close']).rolling(window=96).sum().iloc[-1],
                'side': 1 if bias == 'LONG' else 0
            }
            
            ai_confidence = ai_engine.get_confidence(features)
            confluences['ai_confidence'] = ai_confidence
            
            if ai_confidence < Config.AI_CONFIDENCE_THRESHOLD:
                return {"signal": "NONE", "reason": f"AI Confidence {ai_confidence:.1%} below threshold ({Config.AI_CONFIDENCE_THRESHOLD:.0%})", "confluences": confluences}
        except Exception as e:
            print(f"⚠️ AI Inference skipped: {e}")

        return {
            "signal": bias,
            "entry": entry_px,
            "sl": risk_data["sl"],
            "tp1": risk_data["tp1"],
            "tp2": risk_data["tp2"],
            "tp3": risk_data["tp3"],
            "size": risk_data["size"],
            "atr": atr_15m,
            "score": score,
            "ai_confidence": ai_confidence,
            "confluences": confluences,
            "reason": f"SMC {bias} | Score: {score:.1f} | AI: {ai_confidence:.1%}"
        }
