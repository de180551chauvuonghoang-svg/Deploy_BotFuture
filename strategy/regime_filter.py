import pandas as pd
import pandas_ta as ta
import numpy as np

def get_regime(df_1h: pd.DataFrame) -> str:
    """
    Detects the current market condition (TRENDING, RANGING, HIGH_VOLATILITY, SQUEEZE, or AVOID).
    - TRENDING: ADX > 25 and price moving.
    - RANGING: ADX < 20.
    - HIGH_VOLATILITY: ATR > 1.8x its 20-period average.
    - SQUEEZE: Bollinger Band Width < 20th percentile.
    """
    if df_1h is None or len(df_1h) < 30:
        return "AVOID"

    # 1. ADX(14) - Trend Strength
    if 'adx' in df_1h.columns:
        adx = df_1h['adx'].iloc[-1]
    else:
        adx_df = ta.adx(df_1h['high'], df_1h['low'], df_1h['close'], length=14)
        adx = adx_df.iloc[-1, 0]
    
    # 2. ATR(14) - Volatility
    if 'atr' in df_1h.columns:
        atr_now = df_1h['atr'].iloc[-1]
        atr_sma = df_1h['atr'].rolling(window=20).mean().iloc[-1]
    else:
        atr = ta.atr(df_1h['high'], df_1h['low'], df_1h['close'], length=14)
        atr_now = atr.iloc[-1]
        atr_sma = atr.rolling(window=20).mean().iloc[-1]
    
    # 3. Bollinger Band Width
    if 'bbw' in df_1h.columns:
        bbw_now = df_1h['bbw'].iloc[-1]
        bbw_20th = df_1h['bbw'].rolling(window=100).quantile(0.2).iloc[-1]
    else:
        bb = ta.bbands(df_1h['close'], length=20, std=2)
        bb_width = (bb.iloc[:, 2] - bb.iloc[:, 0]) / bb.iloc[:, 1]
        bbw_now = bb_width.iloc[-1]
        bbw_20th = bb_width.rolling(window=100).quantile(0.2).iloc[-1]

    # --- REGIME LOGIC ---
    if atr_now > 2.0 * atr_sma: # Increased threshold for extreme volatility
        return "HIGH_VOLATILITY"
    
    if bbw_now < bbw_20th:
        return "SQUEEZE"
        
    if adx > 20: # Lowered threshold to 20 for trending
        return "TRENDING"
    
    # If not trending or special volatile condition, it's RANGING
    return "RANGING"
