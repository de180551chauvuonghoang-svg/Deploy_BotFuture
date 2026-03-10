import pandas as pd

def find_fvg(df: pd.DataFrame, lookback: int = 100) -> list[dict]:
    """
    Identifies Fair Value Gaps (FVG) or Imbalance zones.
    Vectorized for performance.
    """
    if df is None or len(df) < 3: return []
    
    df_mini = df.tail(lookback + 2).copy()
    
    # Bullish FVG: high[i-1] < low[i+1]
    df_mini['is_bull_fvg'] = df_mini['high'].shift(1) < df_mini['low'].shift(-1)
    
    # Bearish FVG: low[i-1] > high[i+1]
    df_mini['is_bear_fvg'] = df_mini['low'].shift(1) > df_mini['high'].shift(-1)
    
    bull_indices = df_mini[df_mini['is_bull_fvg']].index
    bear_indices = df_mini[df_mini['is_bear_fvg']].index
    
    fvgs = []
    
    for idx in bull_indices:
        loc = df.index.get_loc(idx)
        if loc > 0 and loc < len(df) - 1:
            fvgs.append({
                "top": df['low'].iloc[loc+1],
                "bottom": df['high'].iloc[loc-1],
                "type": "BULLISH",
                "timestamp": idx,
                "midpoint": (df['low'].iloc[loc+1] + df['high'].iloc[loc-1]) / 2
            })
            
    for idx in bear_indices:
        loc = df.index.get_loc(idx)
        if loc > 0 and loc < len(df) - 1:
            fvgs.append({
                "top": df['low'].iloc[loc-1],
                "bottom": df['high'].iloc[loc+1],
                "type": "BEARISH",
                "timestamp": idx,
                "midpoint": (df['low'].iloc[loc-1] + df['high'].iloc[loc+1]) / 2
            })
            
    # Filter active ones
    active = []
    for fvg in fvgs:
        try:
            start_loc = df.index.get_loc(fvg['timestamp'])
            df_after = df.iloc[start_loc + 1:]
            
            if fvg['type'] == "BULLISH":
                is_filled = (df_after['close'] < fvg['bottom']).any()
            else:
                is_filled = (df_after['close'] > fvg['top']).any()
                
            if not is_filled:
                active.append(fvg)
        except:
            continue
            
    return active[-5:]

def price_in_fvg(current_price, fvg_list):
    for fvg in fvg_list:
        if fvg['bottom'] <= current_price <= fvg['top']:
            return fvg
    return None
