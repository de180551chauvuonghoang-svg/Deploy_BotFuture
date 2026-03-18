import pandas as pd
import pandas_ta as ta

def calculate_smart_sl_tp(side, entry, ob, atr_val, account_balance, score, ai_confidence=1.0, max_qty=0):
    """
    Calculates dynamic SL/TP and position size based on SMC zones and AI Analysis.
    """
    from config.config import Config
    
    # 1. Stop Loss Placement
    if ob:
        # Buffer SL with ATR to avoid liquidity sweeps (0.5x ATR)
        sl_buffer = 0.8 * atr_val
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
    elif sl_dist_pct > 0.08: # Professional cap: 8% (Reduced size will protect us)
        return None 

    sl_dist = abs(entry - sl)

    # 2. Position Sizing (Fixed Risk Per Trade Model)
    # Scale risk from 1.0% to 2.0% based on score
    risk_pct = Config.BASE_RISK_PCT
    if score >= 9.0:
        over_threshold = (score - 8.0) / 2.0 # Scale from 0 to 1
        risk_pct = Config.BASE_RISK_PCT + (over_threshold * (Config.MAX_RISK_PCT - Config.BASE_RISK_PCT))
    
    risk_amount = account_balance * risk_pct
    position_size = risk_amount / sl_dist if sl_dist > 0 else 0

    max_margin_usd = account_balance * 0.10
    max_size_by_margin = (max_margin_usd * Config.LEVERAGE) / entry
    
    if position_size > max_size_by_margin:
        position_size = max_size_by_margin

    # 🎯 NEW: Cap by Exchange Max Quantity Limit
    if max_qty > 0 and position_size > max_qty:
        from core.logger import logger
        logger.warning(f"⚠️ Capping position size by Exchange Max Limit: {position_size:.4f} -> {max_qty:.4f}")
        position_size = max_qty

    # 3. Take Profit (Dynamic Scaling based on AI Win Probability)
    tp1_rr, tp2_rr, tp3_rr = Config.TP1_RR, Config.TP2_RR, Config.TP3_RR
    
    if Config.USE_AI_DYNAMIC_TP:
        # AI Logic: 
        # If AI is super confident (90%+), we trust the trend and extend TP.
        # If AI is barely confident (80%), we take quick profit.
        # Base multiplier centered at AI 85%
        ai_mult = (ai_confidence - 0.70) / 0.15 # 0.85 -> 1.0, 0.95 -> 1.66
        ai_mult = max(0.8, min(1.5, ai_mult))   # Clamp between 80% and 150% of base TP
        
        tp1_rr *= ai_mult
        tp2_rr *= ai_mult
        tp3_rr *= ai_mult

    tp1 = entry + (sl_dist * tp1_rr) if side == "LONG" else entry - (sl_dist * tp1_rr)
    tp2 = entry + (sl_dist * tp2_rr) if side == "LONG" else entry - (sl_dist * tp2_rr)
    tp3 = entry + (sl_dist * tp3_rr) if side == "LONG" else entry - (sl_dist * tp3_rr)
    
    return {
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "size": position_size,
        "risk_pct": risk_pct
    }

def update_dynamic_exit(curr_px, entry, current_sl, side, atr_val, p_info):
    """
    Implements aggressive Breakeven and Trailing rules to protect positive PnL.
    """
    tp1_hit = p_info.get('tp1_done', False)
    tp2_hit = p_info.get('tp2_done', False)
    tp3_hit = p_info.get('tp3_done', False)
    
    # 1. TP1 Hit: Move SL to Hard Breakeven (Exact Entry)
    if tp1_hit and not tp2_hit:
        # 1. Base Security: Always at least Entry (Hard BE)
        new_sl = entry
        
        tp1_price = float(p_info.get('tp1', entry))
        tp2_price = float(p_info.get('tp2', entry))
        total_dist = abs(tp2_price - tp1_price)
        current_progress = abs(curr_px - tp1_price)
        progress_pct = current_progress / total_dist if total_dist > 0 else 0

        # 2. Dynamic Sniper Trailing (The "Hay hơn" part)
        if progress_pct > 0.5:
            # Nếu vượt 50% quãng đường, bắt đầu bám sát bằng ATR
            # Càng gần TP2, khoảng cách càng hẹp (Từ 1.5x ATR nén xuống còn 0.7x ATR)
            compression_factor = 1.5 - (progress_pct * 0.8) # Giảm dần khoảng cách
            trail_dist = atr_val * max(0.7, compression_factor) 
            
            if side == "LONG":
                target_sl = curr_px - trail_dist
                # SL chỉ có tiến, không có lùi. Tối thiểu phải là TP1 khi đã qua 50%
                new_sl = max(tp1_price, target_sl)
            else:
                target_sl = curr_px + trail_dist
                new_sl = min(tp1_price, target_sl)
            
        if side == "LONG": current_sl = max(current_sl, new_sl)
        else: current_sl = min(current_sl, new_sl)

    # 2. TP2 Hit: Lock profit at TP1 and start ATR Trailing
    if tp2_hit and not tp3_hit:
        tp1_price = float(p_info.get('tp1', entry))
        new_sl = tp1_price
        
        trail_dist = atr_val * 1.5
        if side == "LONG":
            target_sl = curr_px - trail_dist
            new_sl = max(new_sl, target_sl)
        else:
            target_sl = curr_px + trail_dist
            new_sl = min(new_sl, target_sl)
            
        current_sl = new_sl

    # 3. Moonshot Stage (After TP3): Extremely Tight trailing to catch parabolic moves
    if tp3_hit:
        # Move SL to TP2 baseline as minimum
        tp2_price = float(p_info.get('tp2', entry))
        new_sl = tp2_price
        
        # Super Tight Trailing: 1.0x ATR from current price to lock parabolic gains
        trail_dist = atr_val * 1.0
        if side == "LONG":
            target_sl = curr_px - trail_dist
            new_sl = max(new_sl, target_sl)
        else:
            target_sl = curr_px + trail_dist
            new_sl = min(new_sl, target_sl)
            
        current_sl = new_sl
            
    return current_sl
