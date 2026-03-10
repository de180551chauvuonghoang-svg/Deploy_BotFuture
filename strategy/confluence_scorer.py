import pandas as pd
import pandas_ta as ta

class ConfluenceScorer:
    """
    Scores the quality of each trade setup from 0 to 10.0 based on confluence rules.
    """
    def __init__(self, ema_fast=21, ema_slow=50, rsi_period=14):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period

    def score(self, df_15m: pd.DataFrame, df_1h: pd.DataFrame, bias: str, ob_zone: dict = None, fvg_zone: dict = None) -> float:
        """
        Calculates the quality score of a potential trade.
        """
        score = 0.0
        curr = df_15m.iloc[-1]
        prev = df_15m.iloc[-2]
        
        # 1. HTF Alignment (+2.0)
        is_long = (bias == "LONG_ONLY")
        is_short = (bias == "SHORT_ONLY")
        score += 2.0 if (is_long or is_short) else 0.0
        
        # 2. OB/FVG Zone (+1.5 each)
        if ob_zone: score += 1.5
        if fvg_zone: score += 1.5
        
        # 3. RSI Confirmation (+1.0)
        if 'rsi' in df_15m.columns:
            rsi = df_15m['rsi'].iloc[-1]
        else:
            rsi = ta.rsi(df_15m['close'], length=self.rsi_period).iloc[-1]
            
        if is_long and rsi < 40: score += 1.0 # RSI oversold/neutral for Long
        elif is_short and rsi > 60: score += 1.0 # RSI overbought/neutral for Short
        
        # 4. Volume Spike (+1.0)
        vol_ema = ta.ema(df_15m['volume'], length=20).iloc[-1]
        if curr['volume'] > vol_ema * 1.2:
            score += 1.0
            
        # 5. Confirmation Candle Pattern (+1.0)
        body = (curr['close'] - curr['open'])
        prev_body = (prev['close'] - prev['open'])
        # Engulfing check
        if is_long and body > 0 and abs(body) > abs(prev_body): score += 1.0
        elif is_short and body < 0 and abs(body) > abs(prev_body): score += 1.0
        
        # 6. EMA Alignment on 1H (+0.5)
        if 'ema_21' in df_1h.columns and 'ema_50' in df_1h.columns:
            ema_fast = df_1h['ema_21'].iloc[-1]
            ema_slow = df_1h['ema_50'].iloc[-1]
        else:
            ema_fast = ta.ema(df_1h['close'], length=self.ema_fast).iloc[-1]
            ema_slow = ta.ema(df_1h['close'], length=self.ema_slow).iloc[-1]
        if is_long and ema_fast > ema_slow: score += 0.5
        elif is_short and ema_fast < ema_slow: score += 0.5
        
        # 7. Round Number / S&R nearby (+0.5)
        # Simply check if price is close to round numbers (ending in 00 or 50)
        if round(curr['close'] * 100) % 50 == 0:
            score += 0.5
            
        return min(score, 10.0)
