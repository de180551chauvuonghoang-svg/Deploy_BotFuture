import pandas as pd
import pandas_ta as ta
import numpy as np

def detect_structure(df: pd.DataFrame, lookback: int = 100) -> dict:
    """
    Detects market structure (HH/HL/LH/LL) using fractal logic.
    Vectorized for performance during backtesting.
    """
    if df is None or len(df) < 20:
        return {"bias": "NONE"}

    # 1. Identify Bias using EMA200
    if 'ema_200' in df.columns:
        ema200 = df['ema_200'].iloc[-1]
    else:
        ema200 = ta.ema(df['close'], length=200).iloc[-1]
    curr_price = df['close'].iloc[-1]

    # 2. Identify Fractals (Vectorized)
    # A fractal is a point higher/lower than 2 neighbors on each side
    df_fractal = df.tail(lookback).copy()
    
    # Swing Highs
    df_fractal['is_sh'] = (df_fractal['high'] > df_fractal['high'].shift(1)) & \
                          (df_fractal['high'] > df_fractal['high'].shift(2)) & \
                          (df_fractal['high'] > df_fractal['high'].shift(-1)) & \
                          (df_fractal['high'] > df_fractal['high'].shift(-2))
    
    # Swing Lows
    df_fractal['is_sl'] = (df_fractal['low'] < df_fractal['low'].shift(1)) & \
                          (df_fractal['low'] < df_fractal['low'].shift(2)) & \
                          (df_fractal['low'] < df_fractal['low'].shift(-1)) & \
                          (df_fractal['low'] < df_fractal['low'].shift(-2))
    
    sh_list = df_fractal[df_fractal['is_sh']]['high'].tolist()
    sl_list = df_fractal[df_fractal['is_sl']]['low'].tolist()

    if len(sh_list) < 2 or len(sl_list) < 2:
        return {"bias": "NONE"}

    last_sh = sh_list[-1]
    last_sl = sl_list[-1]
    prev_sh = sh_list[-2]
    prev_sl = sl_list[-2]

    bias = "NONE"
    
    # BULLISH BOS: High broken
    if curr_price > last_sh:
        bias = "LONG"
    # BEARISH BOS: Low broken
    elif curr_price < last_sl:
        bias = "SHORT"
    # Continuation bias
    elif curr_price > ema200 and last_sh > prev_sh:
        bias = "LONG"
    elif curr_price < ema200 and last_sl < prev_sl:
        bias = "SHORT"
    
    return {
        "bias": bias,
        "last_swing_high": last_sh,
        "last_swing_low": last_sl
    }
