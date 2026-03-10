import pandas as pd
import pandas_ta as ta
from strategy.regime_filter import get_regime
from strategy.structure import detect_structure
from strategy.order_blocks import find_bullish_ob, find_bearish_ob, price_in_ob_zone
from strategy.fvg import find_fvg, price_in_fvg
from strategy.liquidity import detect_liquidity_sweep
from strategy.confluence import score_setup
from risk.smart_risk import calculate_smart_sl_tp

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
        if regime == "AVOID":
            return {"signal": "NONE", "reason": "Market regime: AVOID"}

        # 2. Macro Structure (4H bias - NO FALLBACK)
        structure_4h = detect_structure(df_4h, lookback=400)
        bias = structure_4h["bias"]
        if bias == "NONE":
            return {"signal": "NONE", "reason": "No clear 4H structure bias"}

        # 3. Key Zones (OB & FVG)
        ob_list = find_bullish_ob(df_1h, lookback=200) if bias == "LONG" else find_bearish_ob(df_1h, lookback=200)
        fvg_list = find_fvg(df_1h, lookback=200)
        
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
        
        if not (ob_hit or fvg_hit):
            return {"signal": "NONE", "reason": "No 1H zone touch"}

        # 5. Scoring (Floor: 6.0 - High Quality)
        sweep = detect_liquidity_sweep(df_15m)
        score = score_setup(bias, regime, ob_hit, fvg_hit, sweep, df_15m, df_1h)
        
        if score < 6.0:
            return {"signal": "NONE", "reason": f"Quality score {score:.1f} too low"}

        # 6. Risk Calculation
        atr_15m = ta.atr(df_15m['high'], df_15m['low'], df_15m['close']).iloc[-1]
        risk_data = calculate_smart_sl_tp(bias, curr_px, ob_hit, atr_15m, balance, score)
        
        if not risk_data:
            return {"signal": "NONE", "reason": "Risk distance too large"}

        return {
            "signal": bias,
            "entry": curr_px,
            "sl": risk_data["sl"],
            "tp1": risk_data["tp1"],
            "tp2": risk_data["tp2"],
            "tp3": risk_data["tp3"], # Added TP3
            "size": risk_data["size"],
            "score": score,
            "reason": f"SMC {bias} Setup | Regime: {regime} | Score: {score:.1f}"
        }
