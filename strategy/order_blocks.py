import pandas as pd
import pandas_ta as ta
import numpy as np

def find_bullish_ob(df: pd.DataFrame, lookback: int = 100) -> list[dict]:
    """
    Finds last red candle before a 3-candle bullish impulse.
    """
    if df is None or len(df) < 5: return []
    
    if 'atr' in df.columns:
        atr = df['atr']
    else:
        atr = ta.atr(df['high'], df['low'], df['close'], length=14)
        
    df_mini = df.tail(lookback + 5).copy()
    atr_mini = atr.reindex(df_mini.index)
    
    # Identify Bullish Impulse (3 green candles)
    df_mini['is_green'] = df_mini['close'] > df_mini['open']
    df_mini['move'] = df_mini['close'].shift(-2) - df_mini['open']
    
    # Impulse condition: 3 green + move > 1.5x ATR
    df_mini['is_impulse'] = df_mini['is_green'] & \
                            df_mini['is_green'].shift(-1).fillna(False) & \
                            df_mini['is_green'].shift(-2).fillna(False) & \
                            (df_mini['move'] > 1.5 * atr_mini)
    
    impulse_indices = df_mini[df_mini['is_impulse'] == True].index
    obs = []
    
    for idx in impulse_indices:
        # Get the candle before the impulse start
        try:
            loc = df.index.get_loc(idx)
            if loc > 0:
                last_candle = df.iloc[loc-1]
                if last_candle['close'] < last_candle['open']:
                    obs.append({
                        "top": last_candle['high'],
                        "bottom": last_candle['low'],
                        "timestamp": df.index[loc-1],
                        "type": "BULLISH"
                    })
        except:
            continue
    
    return _filter_valid_obs(df, obs, "BULLISH")

def find_bearish_ob(df: pd.DataFrame, lookback: int = 100) -> list[dict]:
    """
    Finds last green candle before a 3-candle bearish impulse.
    """
    if df is None or len(df) < 5: return []
    
    if 'atr' in df.columns:
        atr = df['atr']
    else:
        atr = ta.atr(df['high'], df['low'], df['close'], length=14)
        
    df_mini = df.tail(lookback + 5).copy()
    atr_mini = atr.reindex(df_mini.index)
    
    df_mini['is_red'] = df_mini['close'] < df_mini['open']
    df_mini['move'] = df_mini['open'] - df_mini['close'].shift(-2)
    
    df_mini['is_impulse'] = df_mini['is_red'] & \
                            df_mini['is_red'].shift(-1).fillna(False) & \
                            df_mini['is_red'].shift(-2).fillna(False) & \
                            (df_mini['move'] > 1.5 * atr_mini)
                            
    impulse_indices = df_mini[df_mini['is_impulse'] == True].index
    obs = []
    
    for idx in impulse_indices:
        try:
            loc = df.index.get_loc(idx)
            if loc > 0:
                last_candle = df.iloc[loc-1]
                if last_candle['close'] > last_candle['open']:
                    obs.append({
                        "top": last_candle['high'],
                        "bottom": last_candle['low'],
                        "timestamp": df.index[loc-1],
                        "type": "BEARISH"
                    })
        except:
            continue
                
    return _filter_valid_obs(df, obs, "BEARISH")

def _filter_valid_obs(df, obs, ob_type):
    valid = []
    if not obs: return []
    
    for ob in obs:
        try:
            start_loc = df.index.get_loc(ob['timestamp'])
            df_after = df.iloc[start_loc + 1:]
            
            if df_after.empty:
                valid.append(ob)
                continue
                
            if ob_type == "BULLISH":
                # Broken if price CLOSES below OB bottom
                broken_mask = df_after['close'] < ob['bottom']
            else:
                # Broken if price CLOSES above OB top
                broken_mask = df_after['close'] > ob['top']
                
            if not broken_mask.any():
                valid.append(ob)
        except:
            continue
            
    return valid[-5:] # Return more OBs for better coverage

def price_in_ob_zone(current_price, ob_list):
    for ob in ob_list:
        if ob['bottom'] <= current_price <= ob['top']:
            return ob
    return None
