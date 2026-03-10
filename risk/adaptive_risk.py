import pandas as pd
import pandas_ta as ta

class AdaptiveRiskManager:
    """
    Implements advanced risk management: adaptive position sizing, 
    OB-based Stop Loss, and multi-TP logic.
    """
    def __init__(self, base_risk=0.01, min_sl=0.005, max_sl=0.025, buffer=0.0015):
        self.base_risk = base_risk
        self.min_sl = min_sl
        self.max_sl = max_sl
        self.buffer = buffer

    def calculate_trade_risk(self, account_equity: float, df_15m: pd.DataFrame, entry_price: float, ob_zone: dict = None, side: int = 1) -> dict:
        """
        Calculates position size and SL/TP levels based on OB/ATR volatility.
        """
        # 1. Volatility-Adjusted Risk %
        atr = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'], length=14)
        atr_now = atr.iloc[-1]
        atr_avg = atr.rolling(window=20).mean().iloc[-1]
        
        current_risk_pct = self.base_risk
        if atr_now > 1.5 * atr_avg:
            current_risk_pct = self.base_risk * 0.5 # High Volatility, reduce risk
        elif atr_now < 0.7 * atr_avg:
            current_risk_pct = self.base_risk * 1.5 # Low Volatility, tighter risk
            
        # 2. Stop Loss Calculation (Based on OB/ATR)
        if ob_zone:
            if side == 1:
                sl_price = ob_zone['low'] * (1 - self.buffer)
            else:
                sl_price = ob_zone['high'] * (1 + self.buffer)
        else:
            # Fallback to ATR for SL
            sl_price = entry_price - (atr_now * 2) if side == 1 else entry_price + (atr_now * 2)

        # 3. Distance constraints
        sl_dist = abs(entry_price - sl_price) / entry_price
        if sl_dist < self.min_sl:
            sl_price = entry_price * (1 - self.min_sl) if side == 1 else entry_price * (1 + self.min_sl)
        elif sl_dist > self.max_sl:
            sl_price = entry_price * (1 - self.max_sl) if side == 1 else entry_price * (1 + self.max_sl)
            
        sl_dist = abs(entry_price - sl_price)
        
        # 4. Position Sizing
        if sl_dist > 0:
            position_size = (account_equity * current_risk_pct) / sl_dist
        else:
            position_size = 0
            
        # 5. Take Profit (Multi-stage)
        tp1_price = entry_price + (sl_dist * 1.5) if side == 1 else entry_price - (sl_dist * 1.5)
        tp2_price = entry_price + (sl_dist * 2.5) if side == 1 else entry_price - (sl_dist * 2.5)
        
        return {
            "sl": sl_price,
            "tp1": tp1_price,
            "tp2": tp2_price,
            "size": position_size,
            "risk_pct": current_risk_pct,
            "sl_pct": sl_dist / entry_price
        }

    def check_dynamic_trailing(self, current_price: float, entry_price: float, current_sl: float, side: int, atr: float) -> float:
        """
        Implements Breakeven and Drifting Stop Loss rule.
        - Move to BE at +1R
        - Trail by 0.5 ATR at +2R
        """
        pnl_dist = abs(current_price - entry_price)
        sl_dist = abs(entry_price - current_sl)
        
        if sl_dist == 0: return current_sl
        
        # 1. Breakeven rule (+1R)
        if pnl_dist >= sl_dist:
            if (side == 1 and current_sl < entry_price) or (side == -1 and current_sl > entry_price):
                return entry_price
        
        # 2. Trail rule (+2R)
        if pnl_dist >= 2 * sl_dist:
            new_sl = current_price - (atr * 0.5) if side == 1 else current_price + (atr * 0.5)
            # Ensure trail only moves in one direction
            if side == 1:
                return max(current_sl, new_sl)
            else:
                return min(current_sl, new_sl)
                
        return current_sl
