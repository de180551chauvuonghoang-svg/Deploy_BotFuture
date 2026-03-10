import pandas as pd

def detect_liquidity_sweep(df: pd.DataFrame) -> dict:
    """
    Detects if price swept liquidity at recent highs/lows.
    Lookback 20 bars for previous high/low.
    """
    if df is None or len(df) < 30:
        return {"swept": False, "direction": None}

    lookback = 20
    prev_df = df.iloc[-lookback-1:-1]
    
    prev_high = prev_df['high'].max()
    prev_low = prev_df['low'].min()
    
    curr = df.iloc[-1]
    
    # BULLISH SWEEP: Price breaks below low then closes above it
    is_bull_sweep = curr['low'] < prev_low and curr['close'] > prev_low
    
    # BEARISH SWEEP: Price breaks above high then closes below it
    is_bear_sweep = curr['high'] > prev_high and curr['close'] < prev_high
    
    if is_bull_sweep:
        return {"swept": True, "direction": "bull", "level": prev_low}
    if is_bear_sweep:
        return {"swept": True, "direction": "bear", "level": prev_high}
        
    return {"swept": False, "direction": None}
