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
        # Only block if regime is strictly AVOID
        if regime == "AVOID" and balance < 1000: # Example logic: stop if balance low, else trade
            return {"signal": "NONE", "reason": "Market regime: AVOID"}

        # 2. Macro Structure (4H bias)
        structure_4h = detect_structure(df_4h, lookback=200) # Increased lookback
        bias = structure_4h["bias"]
        if bias == "NONE" and regime != "TRENDING":
             return {"signal": "NONE", "reason": "No clear structure bias"}
        
        # If trend is strong, we can infer bias from price vs EMA200 even if fractals missing
        if bias == "NONE":
            ema200 = df_4h['ema_200'].iloc[-1] if 'ema_200' in df_4h.columns else curr_px
            bias = "LONG" if df_4h['close'].iloc[-1] > ema200 else "SHORT"

        # 3. Key Zones (OB & FVG on 1H)
        ob_list = find_bullish_ob(df_1h) if bias == "LONG" else find_bearish_ob(df_1h)
        fvg_list = find_fvg(df_1h)
        
        # 4. Entry Triggers (15M)
        sweep = detect_liquidity_sweep(df_15m)
        curr_px = df_15m['close'].iloc[-1]
        
        # 5. Check confluence
        ob_hit = price_in_ob_zone(curr_px, ob_list)
        fvg_hit = price_in_fvg(curr_px, fvg_list)
        
        if not (ob_hit or fvg_hit):
            return {"signal": "NONE", "reason": "Price not in OB or FVG zone"}

        # 6. Scoring
        score = score_setup(bias, regime, ob_hit, fvg_hit, sweep, df_15m, df_1h)
        
        if score < 3.5:
            return {"signal": "NONE", "reason": f"Low confluence score: {score:.1f}"}

        # 7. Risk Calculation
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
            "size": risk_data["size"],
            "score": score,
            "reason": f"SMC {bias} Setup | Regime: {regime} | Score: {score:.1f}"
        }
