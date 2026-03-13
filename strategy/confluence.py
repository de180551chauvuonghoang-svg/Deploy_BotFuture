import pandas as pd
import pandas_ta as ta

def score_setup(bias, regime, ob_hit, fvg_hit, 
                liquidity_data, df_15m, df_1h) -> float:
    """
    Scoring system for SMC setups (max 10.0).
    Optimized for backtest speed.
    """
    score = 0.0
    
    # 1. Structure (+2.5 total)
    if (bias == "LONG" and ob_hit and ob_hit['type'] == "BULLISH") or \
       (bias == "SHORT" and ob_hit and ob_hit['type'] == "BEARISH"):
        score += 2.0
    
    # Check 1H structure alignment (+0.5)
    curr_1h = df_1h['close'].iloc[-1]
    if 'ema_50' in df_1h.columns:
        ema_1h = df_1h['ema_50'].iloc[-1]
    else:
        ema_1h = ta.ema(df_1h['close'], length=50).iloc[-1]
        
    if (bias == "LONG" and curr_1h > ema_1h) or (bias == "SHORT" and curr_1h < ema_1h):
        score += 0.5

    # 2. Key Zone (+3.5 total)
    if ob_hit: score += 2.0
    if fvg_hit: score += 1.5
    if ob_hit and fvg_hit: 
        score += 0.5 
    
    # Round number nearby (+0.5)
    curr_px = df_15m['close'].iloc[-1]
    if round(curr_px * 100) % 50 == 0:
        score += 0.5

    # 3. Liquidity (+2.0)
    if liquidity_data['swept']:
        if (bias == "LONG" and liquidity_data['direction'] == "bull") or \
           (bias == "SHORT" and liquidity_data['direction'] == "bear"):
            score += 2.0

    # 4. Momentum (+1.5 total)
    if 'rsi' in df_15m.columns:
        rsi = df_15m['rsi'].iloc[-1]
    else:
        rsi = ta.rsi(df_15m['close'], length=14).iloc[-1]
        
    if (bias == "LONG" and rsi < 35) or (bias == "SHORT" and rsi > 65):
        score += 1.0
        
    if 'vol_sma' in df_15m.columns:
        vol_avg = df_15m['vol_sma'].iloc[-1]
    else:
        vol_avg = df_15m['volume'].rolling(window=20).mean().iloc[-1]
        
    if df_15m['volume'].iloc[-1] > 1.5 * vol_avg:
        score += 0.5

    # 5. Confirmation Pattern (+1.0)
    curr = df_15m.iloc[-1]
    prev = df_15m.iloc[-2]
    is_bull_engulf = curr['close'] > prev['open'] and curr['open'] < prev['close'] and curr['close'] > curr['open']
    is_bear_engulf = curr['close'] < prev['open'] and curr['open'] > prev['close'] and curr['close'] < curr['open']
    
    if (bias == "LONG" and is_bull_engulf) or (bias == "SHORT" and is_bear_engulf):
        score += 1.5

    return min(score, 10.0)
