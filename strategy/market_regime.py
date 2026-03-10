import pandas as pd
import pandas_ta as ta

class MarketRegimeDetector:
    """
    Detects the current market condition (Trending, Ranging, Volatile, or Avoid)
    using ADX, ATR, and Bollinger Band Width indicators.
    """
    def __init__(self, adx_period=14, atr_period=14, atr_avg_period=20, bb_period=20):
        self.adx_period = adx_period
        self.atr_period = atr_period
        self.atr_avg_period = atr_avg_period
        self.bb_period = bb_period

    def detect(self, df: pd.DataFrame) -> dict:
        """
        Determines the current market regime based on technical indicators.
        Returns a dictionary with the regime type.
        """
        if df is None or len(df) < max(self.adx_period, self.bb_period, self.atr_avg_period):
            return {"regime": "AVOID", "reason": "Insufficient data"}

        # --- Indicator Calculations ---
        # ADX(14) - Trend Strength
        if 'adx' in df.columns:
            adx = df['adx'].iloc[-1]
            adx_prev = df['adx'].iloc[-2]
        else:
            adx_df = ta.adx(df['high'], df['low'], df['close'], length=self.adx_period)
            adx = adx_df.iloc[-1, 0]
            adx_prev = adx_df.iloc[-2, 0]
        
        # ATR(14) - Volatility
        if 'atr' in df.columns:
            atr = df['atr']
        else:
            atr = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)
            
        atr_now = atr.iloc[-1]
        atr_avg = atr.rolling(window=self.atr_avg_period).mean().iloc[-1]
        
        # Bollinger Bands Width - Consolidation vs. Breakout
        bb = ta.bbands(df['close'], length=self.bb_period, std=2)
        bb_width = (bb.iloc[:, 2] - bb.iloc[:, 0]) / bb.iloc[:, 1] # (Upper - Lower) / Middle
        bbw_now = bb_width.iloc[-1]
        bbw_prev = bb_width.iloc[-2]

        # --- Decision Logic ---
        regime = "RANGING" # Default regime
        
        # 1. Volatility Checks (ATR)
        if atr_now > 1.5 * atr_avg:
            regime = "VOLATILE"
        elif atr_now < 0.7 * atr_avg:
            regime = "AVOID" # Too low volatility, avoid fake moves

        # 2. Trend Strength (ADX)
        if regime != "AVOID":
            if adx > 25:
                regime = "TRENDING"
            elif adx < 20:
                regime = "RANGING"
            
            # Sudden ADX Spike usually means news or massive volatility
            if (adx - adx_prev) > 5:
                regime = "VOLATILE"

        # 3. Momentum Check (BBW)
        is_expanding = bbw_now > bbw_prev
        
        return {
            "regime": regime,
            "adx": adx,
            "atr_ratio": atr_now / atr_avg if atr_avg != 0 else 0,
            "bbw_expanding": is_expanding
        }
