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
            "ob_hit_top": ob_hit['top'] if ob_hit else None,
            "ob_hit_bottom": ob_hit['bottom'] if ob_hit else None,
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

        # 6. Entry Price Optimization (AI Dynamic Entry)
        ob_mid = (ob_hit['top'] + ob_hit['bottom']) / 2 if ob_hit else curr_px
        
        if Config.USE_AI_DYNAMIC_ENTRY:
             # Scale aggressiveness based on AI confidence (0.8 to 1.0)
             # Higher confidence = push entry closer to market price to ensure fill
             dynamic_agg = Config.ENTRY_AGGRESSIVENESS * ((ai_confidence - 0.7) / 0.3)
             dynamic_agg = max(0.1, min(0.9, dynamic_agg))
             
             # Calculate weighted entry: (1-agg)*OB_Mid + (agg)*Current_Price
             entry_px = (ob_mid * (1 - dynamic_agg)) + (curr_px * dynamic_agg)
             
             # Safeguard: Ensure entry is still within or very near the OB/FVG zone
             if ob_hit:
                 entry_px = max(ob_hit['bottom'], min(ob_hit['top'], entry_px))
        else:
             entry_px = ob_mid
        
        # 6.2 Distance Filter: Skip if price is already too far gone (Market Chase Prevention)
        dist_to_market = abs(entry_px - curr_px) / curr_px
        if dist_to_market > Config.MAX_ENTRY_DISTANCE_PCT:
             return {"signal": "NONE", "reason": f"Market too far ({dist_to_market:.1%}) from ideal SMC zone", "confluences": confluences}
            
        # 6. AI Confidence Filter (NEW - Moved up for Dynamic TP)
        ai_confidence = 1.0
        confluences['ai_confidence'] = ai_confidence
        
        try:
            from ai.inference import ai_engine
            
            # Prepare features for AI
            rsi_15m = df_15m['rsi'].iloc[-1] if 'rsi' in df_15m.columns else 50
            vol_sma = df_15m['vol_sma'].iloc[-1] if 'vol_sma' in df_15m.columns else df_15m['volume'].rolling(20).mean().iloc[-1]
            vol_ratio = df_15m['volume'].iloc[-1] / vol_sma if vol_sma > 0 else 1.0
            
            ema200_h4 = df_4h['ema_200'].iloc[-1] if 'ema_200' in df_4h.columns else df_4h['close'].iloc[-1]
            dist_ema200 = (df_4h['close'].iloc[-1] - ema200_h4) / ema200_h4 if ema200_h4 > 0 else 0
            
            sl_est_dist = abs(entry_px - low_15m) / entry_px # Rough estimate for AI features
            tp_est_dist = sl_est_dist * Config.TP1_RR
            
            features = {
                'score': score,
                'rsi_15m': rsi_15m,
                'vol_ratio_15m': vol_ratio,
                'dist_ema200_h4': dist_ema200,
                'sl_dist_pct': sl_est_dist,
                'tp_dist_pct': tp_est_dist,
                'rr': Config.TP1_RR,
                'body_ratio': 0.5, # Default
                'vol_24h_usdt': (df_15m['volume'] * df_15m['close']).rolling(window=96).sum().iloc[-1],
                'side': 1 if bias == 'LONG' else 0
            }
            
            ai_confidence = ai_engine.get_confidence(features)
            confluences['ai_confidence'] = ai_confidence
            
            if ai_confidence < Config.AI_CONFIDENCE_THRESHOLD:
                return {"signal": "NONE", "reason": f"AI Confidence {ai_confidence:.1%} below threshold ({Config.AI_CONFIDENCE_THRESHOLD:.0%})", "confluences": confluences}
        except Exception as e:
            print(f"⚠️ AI Inference skipped: {e}")

        # 7. Risk Calculation (Now with AI awareness and Market Limits)
        atr_15m_all = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'])
        atr_15m = atr_15m_all.iloc[-1]
        
        # 🎯 NEW: Fetch Max Qty limit from exchange
        max_qty = 0
        try:
            limits = exchange.get_market_limits(symbol)
            max_qty = limits.get('maxQty', 0)
        except: pass
            
        risk_data = calculate_smart_sl_tp(bias, entry_px, ob_hit, atr_15m, balance, score, ai_confidence, max_qty)
        
        if not risk_data:
            return {"signal": "NONE", "reason": "Risk distance too large", "confluences": confluences}

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

    def check_early_exit(self, symbol, side, df_15m, df_1h, p_info) -> tuple:
        """
        🛡️ AI REVERSAL SHIELD: Analyzes if an active trade should be closed early 
        to avoid a full Stop Loss hit during market reversals.
        Returns: (should_exit, reason)
        """
        if df_15m is None or len(df_15m) < 10: return False, ""
        
        curr_price = df_15m['close'].iloc[-1]
        prev_price = df_15m['close'].iloc[-2]
        side = side.upper()
        
        # 1. EMERGENCE OF OPPOSITE STRUCTURE (CHoCH)
        # Using 15m for faster reaction
        struct_15m = detect_structure(df_15m, lookback=50)
        # If we are LONG and signal is SHORT (Bias flipped), exit.
        if (side == 'LONG' and struct_15m['bias'] == 'SHORT') or \
           (side == 'SHORT' and struct_15m['bias'] == 'LONG'):
            return True, f"🛡️ AI Shield: CHoCH Reversal detected on 15m ({struct_15m.get('reason', 'Bias Break')})"

        # 2. MOMENTUM REVERSAL (V-Top/Bottom) 
        # Check for large counter-trend candle (1.8x ATR) 
        import pandas_ta as ta
        atr_all = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'])
        atr = atr_all.iloc[-1] if atr_all is not None else 0
        candle_size = abs(df_15m['close'].iloc[-1] - df_15m['open'].iloc[-1])
        
        is_bearish_impulse = (side == 'LONG' and curr_price < prev_price and candle_size > 1.8 * atr)
        is_bullish_impulse = (side == 'SHORT' and curr_price > prev_price and candle_size > 1.8 * atr)
        
        if (is_bearish_impulse or is_bullish_impulse) and atr > 0:
            return True, "🛡️ AI Shield: Extreme Counter-Momentum Impulse detected."

        # 3. REGIME DEGRADATION NEAR SL
        # If price is within 20% of SL distance and regime becomes AVOID
        sl_val = float(p_info.get('sl', 0))
        if sl_val > 0:
            dist_to_sl = abs(curr_price - sl_val)
            entry_to_sl = abs(p_info['entry'] - sl_val)
            # If we've already lost 80% of the way to SL
            if dist_to_sl < 0.2 * entry_to_sl:
                regime_h1 = get_regime(df_1h)
                if regime_h1 == "AVOID":
                    return True, "🛡️ AI Shield: Market Regime degraded to AVOID while near SL."

        # 4. ORDER BLOCK VIOLATION (Support/Resistance Failure)
        # If price closes beyond the original entry OB zone, the setup logic is invalidated.
        ob_top = p_info.get('ob_top')
        ob_bot = p_info.get('ob_bottom')
        if ob_top is not None and ob_bot is not None:
            if side == 'LONG' and curr_price < ob_bot:
                return True, "🛡️ AI Shield: Support OB Zone violated (Price closed below OB)."
            if side == 'SHORT' and curr_price > ob_top:
                return True, "🛡️ AI Shield: Resistance OB Zone violated (Price closed above OB)."

        return False, ""
