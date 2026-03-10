import pandas as pd
import pandas_ta as ta

def calculate_smart_sl_tp(side, entry, ob, atr_val, account_balance, score):
    """
    Calculates dynamic SL/TP and position size based on SMC zones.
    """
    # 1. Stop Loss Placement
    if ob:
        # Buffer SL with ATR to avoid liquidity sweeps (0.5x ATR)
        sl_buffer = 0.5 * atr_val
        if side == "LONG":
            sl = ob['bottom'] - sl_buffer
        else:
            sl = ob['top'] + sl_buffer
    else:
        # Fallback to ATR
        sl = entry - (atr_val * 2.5) if side == "LONG" else entry + (atr_val * 2.5)

    # Constraints
    sl_dist_pct = abs(entry - sl) / entry
    if sl_dist_pct < 0.003: # Min 0.3%
        sl = entry * (1 - 0.003) if side == "LONG" else entry * (1 + 0.003)
    elif sl_dist_pct > 0.04: # Increased Max 4.0%
        return None 

    sl_dist = abs(entry - sl)

    # 2. Position Sizing
    risk_pct = 0.005 # Default 0.5%
    if score >= 8.0: risk_pct = 0.015
    elif score >= 7.0: risk_pct = 0.010
    
    risk_amount = account_balance * risk_pct
    position_size = risk_amount / sl_dist if sl_dist > 0 else 0

    # 3. Take Profit (Multi-level)
    tp1 = entry + (sl_dist * 1.5) if side == "LONG" else entry - (sl_dist * 1.5)
    tp2 = entry + (sl_dist * 2.5) if side == "LONG" else entry - (sl_dist * 2.5)
    
    return {
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "size": position_size,
        "risk_pct": risk_pct
    }

def update_dynamic_exit(curr_px, entry, current_sl, side, atr_val, tp1_hit):
    """
    Implements Breakeven and Trailing rules.
    """
    sl_dist = abs(entry - current_sl)
    
    # 1. Breakeven Rule (at TP1 or +1.5R)
    if tp1_hit:
        if (side == "LONG" and current_sl < entry) or (side == "SHORT" and current_sl > entry):
            return entry * (1 + 0.001) if side == "LONG" else entry * (1 - 0.001)

    # 2. Trail after +2.5R
    pnl_dist = abs(curr_px - entry)
    if pnl_dist > (sl_dist * 2.5):
        new_sl = curr_px - atr_val if side == "LONG" else curr_px + atr_val
        if side == "LONG": return max(current_sl, new_sl)
        else: return min(current_sl, new_sl)
        
    return current_sl
