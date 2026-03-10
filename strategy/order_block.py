import pandas as pd
import pandas_ta as ta

class OrderBlockDetector:
    """
    Detects Bullish and Bearish Order Blocks (OBs) based on market structure and
    strong impulse candle patterns.
    """
    def __init__(self, impulse_period=3, body_multiplier=1.5, avg_body_period=20):
        self.impulse_period = impulse_period
        self.body_multiplier = body_multiplier
        self.avg_body_period = avg_body_period

    def detect(self, df: pd.DataFrame, lookback: int = 200) -> dict:
        """
        Finds all active Bullish and Bearish Order Blocks.
        Optimization: Only scan the last 'lookback' candles.
        """
        if df is None or len(df) < self.avg_body_period:
            return {"bullish": [], "bearish": []}

        # Calculate candle body sizes
        df['body'] = (df['close'] - df['open']).abs()
        avg_body = df['body'].rolling(window=self.avg_body_period).mean()
        
        bullish_obs = []
        bearish_obs = []
        
        # Determine start index based on lookback
        start_idx = max(self.avg_body_period, len(df) - lookback)
        
        for i in range(start_idx, len(df) - self.impulse_period):
            is_bullish_impulse = True
            is_bearish_impulse = True
            
            # Check for impulse: 3+ candles in the same direction with strong body
            for j in range(self.impulse_period):
                if df['close'].iloc[i+j] <= df['open'].iloc[i+j] or df['body'].iloc[i+j] < avg_body.iloc[i+j] * self.body_multiplier:
                    is_bullish_impulse = False
                if df['close'].iloc[i+j] >= df['open'].iloc[i+j] or df['body'].iloc[i+j] < avg_body.iloc[i+j] * self.body_multiplier:
                    is_bearish_impulse = False
            
            # 1. Bullish Order Block (Last RED candle before strong bullish impulse)
            if is_bullish_impulse and i > 0:
                last_red = df.iloc[i-1]
                if last_red['close'] < last_red['open']:
                    ob = {
                        "high": last_red['high'],
                        "low": last_red['low'],
                        "timestamp": last_red.name,
                        "tested_count": 0,
                        "type": "BULLISH"
                    }
                    bullish_obs.append(ob)
                    
            # 2. Bearish Order Block (Last GREEN candle before strong bearish impulse)
            if is_bearish_impulse and i > 0:
                last_green = df.iloc[i-1]
                if last_green['close'] > last_green['open']:
                    ob = {
                        "high": last_green['high'],
                        "low": last_green['low'],
                        "timestamp": last_green.name,
                        "tested_count": 0,
                        "type": "BEARISH"
                    }
                    bearish_obs.append(ob)

        return {
            "bullish": self._filter_active(df, bullish_obs),
            "bearish": self._filter_active(df, bearish_obs)
        }

    def _filter_active(self, df: pd.DataFrame, obs: list):
        """
        Filters out OBs that have been re-entered more than once or fully cleared.
        """
        active_obs = []
        curr_price = df['close'].iloc[-1]
        
        for ob in obs:
            tested_count = 0
            is_cleared = False
            
            # Analyze price action after OB creation
            start_idx = df.index.get_loc(ob['timestamp']) + 1
            for j in range(start_idx, len(df)):
                px_high = df['high'].iloc[j]
                px_low = df['low'].iloc[j]
                px_close = df['close'].iloc[j]
                
                # If price re-enters the OB zone
                if px_low <= ob['high'] and px_high >= ob['low']:
                    tested_count += 1
                
                # If price closes completely through the OB low/high (Break of Structure)
                if (ob['type'] == "BULLISH" and px_close < ob['low']) or \
                   (ob['type'] == "BEARISH" and px_close > ob['high']):
                    is_cleared = True
                    break
            
            if not is_cleared and tested_count < 2:
                ob['tested_count'] = tested_count
                active_obs.append(ob)
                
        return active_obs
