import pandas as pd
import pandas_ta as ta

class MarketStructureAnalyzer:
    """
    Analyzes Market Structure (HH/HL/LH/LL) on the 4H timeframe to establish
    a macro bias (Bullish/Bearish/Neutral).
    """
    def __init__(self, ema_period=200, window=2):
        self.ema_period = ema_period
        self.window = window

    def _find_swing_points(self, df: pd.DataFrame, lookback: int = 300):
        """
        Find Swing Highs and Swing Lows.
        Optimization: Only look at recent 'lookback' candles.
        """
        highs = []
        lows = []
        
        start_idx = max(self.window, len(df) - lookback)
        for i in range(start_idx, len(df) - self.window):
            # Swing High: Highest high in the window
            is_sh = True
            for j in range(1, self.window + 1):
                if df['high'].iloc[i] <= df['high'].iloc[i - j] or df['high'].iloc[i] <= df['high'].iloc[i + j]:
                    is_sh = False
                    break
            if is_sh:
                highs.append((df.index[i], df['high'].iloc[i]))
            
            # Swing Low: Lowest low in the window
            is_sl = True
            for j in range(1, self.window + 1):
                if df['low'].iloc[i] >= df['low'].iloc[i - j] or df['low'].iloc[i] >= df['low'].iloc[i + j]:
                    is_sl = False
                    break
            if is_sl:
                lows.append((df.index[i], df['low'].iloc[i]))
        
        return highs, lows

    def get_bias(self, df_4h: pd.DataFrame) -> dict:
        """
        Determines the current bias (LONG_ONLY, SHORT_ONLY, NEUTRAL) based on 4H structure.
        """
        if df_4h is None or len(df_4h) < self.ema_period:
            return {"bias": "NEUTRAL", "reason": "Insufficient 4H data"}

        # 1. Indicator Check (EMA 200)
        if 'ema_200' in df_4h.columns:
            ema_200 = df_4h['ema_200'].iloc[-1]
        else:
            ema_200 = ta.ema(df_4h['close'], length=self.ema_period).iloc[-1]
        curr_price = df_4h['close'].iloc[-1]
        
        # 2. Structure Check
        highs, lows = self._find_swing_points(df_4h)
        
        # Need at least 3 swing points to determine trend direction
        if len(highs) < 3 or len(lows) < 3:
            return {"bias": "NEUTRAL", "reason": "Insufficient swing points"}
            
        last_highs = [h[1] for h in highs[-3:]]
        last_lows = [l[1] for l in lows[-3:]]
        
        is_bullish = (last_highs[2] > last_highs[1] > last_highs[0] and 
                      last_lows[2] > last_lows[1] > last_lows[0] and
                      curr_price > ema_200)
                      
        is_bearish = (last_highs[2] < last_highs[1] < last_highs[0] and 
                      last_lows[2] < last_lows[1] < last_lows[0] and
                      curr_price < ema_200)
        
        bias = "NEUTRAL"
        if is_bullish:
            bias = "LONG_ONLY"
        elif is_bearish:
            bias = "SHORT_ONLY"
            
        return {
            "bias": bias,
            "ema_200": ema_200,
            "last_highs": last_highs,
            "last_lows": last_lows
        }
