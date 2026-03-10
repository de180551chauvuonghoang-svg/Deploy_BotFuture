import pandas as pd
import pandas_ta as ta
from strategy.base_strategy import BaseStrategy
from strategy.market_regime import MarketRegimeDetector
from strategy.structure_analyzer import MarketStructureAnalyzer
from strategy.order_block import OrderBlockDetector
from strategy.fair_value_gap import FairValueGapDetector
from strategy.confluence_scorer import ConfluenceScorer

class SignalGenerator(BaseStrategy):
    """
    Master signal engine that aggregates market regime, structure, order blocks, 
    FVGs, and scoring into a single signal.
    """
    def __init__(self, name="AdvancedSMC"):
        super().__init__(name=name)
        self.regime_detector = MarketRegimeDetector()
        self.structure_analyzer = MarketStructureAnalyzer()
        self.ob_detector = OrderBlockDetector()
        self.fvg_detector = FairValueGapDetector()
        self.scorer = ConfluenceScorer()

    def generate_signals(self, df_15m: pd.DataFrame, df_4h: pd.DataFrame = None, df_1h: pd.DataFrame = None) -> dict:
        """
        Coordinates all modules to produce a final trade signal with confidence score.
        """
        if df_15m is None or df_4h is None or df_1h is None:
            return {"signal": 0, "reason": "Missing timeframe data"}

        # Optimization: Pre-calculate indicators if not present
        if 'adx' not in df_15m.columns:
            adx_df = ta.adx(df_15m['high'], df_15m['low'], df_15m['close'])
            df_15m['adx'] = adx_df.iloc[:, 0]
        if 'atr' not in df_15m.columns:
            df_15m['atr'] = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'])

        # 1. Market Regime Detection
        regime_data = self.regime_detector.detect(df_15m)
        regime = regime_data['regime']
        if regime == "AVOID":
            return {"signal": 0, "reason": "Market regime: AVOID", "regime": regime}

        # 2. HTF Structure Bias (4H)
        bias_data = self.structure_analyzer.get_bias(df_4h)
        bias = bias_data['bias']
        if bias == "NEUTRAL":
            return {"signal": 0, "reason": f"Bias: {bias} on 4H structure", "regime": regime}

        # 3. Detect OBs & FVGs
        obs = self.ob_detector.detect(df_15m)
        fvgs = self.fvg_detector.detect(df_15m)
        curr_price = df_15m['close'].iloc[-1]
        
        # 4. Check zones for entry
        active_ob = None
        # Check if current price is in an OB zone
        for ob in (obs['bullish'] if bias == "LONG_ONLY" else obs['bearish']):
            if ob['low'] <= curr_price <= ob['high']:
                active_ob = ob
                break
                
        active_fvg = None
        # Check if current price is in an FVG zone
        for fvg in (fvgs['bullish'] if bias == "LONG_ONLY" else fvgs['bearish']):
            if fvg['low'] <= curr_price <= fvg['high']:
                active_fvg = fvg
                break

        # 5. Calculate Setup Score
        score = self.scorer.score(df_15m, df_1h, bias, active_ob, active_fvg)
        
        # 6. Check Signal Logic (Combined conditions)
        signal = 0
        if score >= 4.0 and (active_ob or active_fvg):
            if bias == "LONG_ONLY":
                signal = 1
            elif bias == "SHORT_ONLY":
                signal = -1
                
        # Risk Control based on regime/score
        position_size_multiplier = 1.0
        if regime == "VOLATILE" or (5.0 <= score < 7.0):
            position_size_multiplier = 0.5
        elif regime == "AVOID" or score < 5.0:
            signal = 0

        return {
            "signal": signal,
            "score": score,
            "regime": regime,
            "bias": bias,
            "price": curr_price,
            "position_multiplier": position_size_multiplier,
            "timestamp": df_15m.index[-1]
        }
