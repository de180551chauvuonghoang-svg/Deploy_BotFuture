import pandas as pd

class FairValueGapDetector:
    """
    Detects Bullish and Bearish Fair Value Gaps (FVG) or imbalance zones.
    """
    def __init__(self, body_threshold=1.5):
        self.body_threshold = body_threshold

    def _calculate_gap(self, df: pd.DataFrame, i: int) -> dict:
        """
        Calculates gaps using candle[i-1] high and candle[i+1] low.
        """
        # Bullish FVG check
        if df['high'].iloc[i-1] < df['low'].iloc[i+1]:
            return {
                "high": df['low'].iloc[i+1],
                "low": df['high'].iloc[i-1],
                "midpoint": (df['low'].iloc[i+1] + df['high'].iloc[i-1]) / 2,
                "type": "BULLISH",
                "timestamp": df.index[i]
            }
        
        # Bearish FVG check
        if df['low'].iloc[i-1] > df['high'].iloc[i+1]:
            return {
                "high": df['low'].iloc[i-1],
                "low": df['high'].iloc[i+1],
                "midpoint": (df['low'].iloc[i-1] + df['high'].iloc[i+1]) / 2,
                "type": "BEARISH",
                "timestamp": df.index[i]
            }
            
        return None

    def detect(self, df: pd.DataFrame, lookback: int = 200) -> dict:
        """
        Identifies active FVGs that have not been filled.
        Optimization: Only looks back at the last 'lookback' candles.
        """
        if df is None or len(df) < 3:
            return {"bullish": [], "bearish": []}

        # Determine start index based on lookback
        start_scan = max(1, len(df) - lookback)
        
        all_fvgs = []
        for i in range(start_scan, len(df) - 1):
            gap = self._calculate_gap(df, i)
            if gap:
                all_fvgs.append(gap)
                
        # Filter active ones (not filled)
        active_bullish = []
        active_bearish = []
        
        for gap in all_fvgs:
            is_filled = False
            start_idx = df.index.get_loc(gap['timestamp']) + 1
            
            # Check only recent candles for filling
            for j in range(start_idx, len(df)):
                px_high = df['high'].iloc[j]
                px_low = df['low'].iloc[j]
                px_close = df['close'].iloc[j]
                
                if (gap['type'] == "BULLISH" and px_close < gap['low']) or \
                   (gap['type'] == "BEARISH" and px_close > gap['high']):
                    is_filled = True
                    break
                    
            if not is_filled:
                if gap['type'] == "BULLISH": active_bullish.append(gap)
                else: active_bearish.append(gap)
                
        return {
            "bullish": active_bullish,
            "bearish": active_bearish
        }
