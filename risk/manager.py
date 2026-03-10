from config.config import Config
from core.logger import logger

class RiskManager:
    def __init__(self, exchange_handler):
        self.exchange = exchange_handler
        self.daily_pnl = 0
        self.initial_balance = 0

    def calculate_position_size(self, symbol, entry_price, balance):
        """
        Calculates position size based on % of account and leverage.
        """
        try:
            # Risk amount in USDT
            risk_amount = balance * Config.POSITION_SIZE_PCT
            
            # Since this is futures, position size = (Balance * Leverage * %) / Price
            position_value = (balance * Config.LEVERAGE * Config.POSITION_SIZE_PCT)
            contracts = position_value / entry_price
            
            return contracts
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def check_emergency_stop(self, current_balance):
        if self.initial_balance == 0:
            self.initial_balance = current_balance
            return False
            
        drawdown = (self.initial_balance - current_balance) / self.initial_balance
        if drawdown >= Config.MAX_DRAWDOWN_PCT:
            logger.critical(f"EMERGENCY: Max drawdown {drawdown*100:.2f}% reached. Stopping bot.")
            return True
        return False

    def get_sl_tp(self, side, entry_price, atr=None):
        """
        ATR-based or Fixed % SL/TP
        """
        sl_pct = Config.STOP_LOSS_PCT
        tp_pct = Config.TAKE_PROFIT_PCT
        
        if side == 'buy':
            sl = entry_price * (1 - sl_pct)
            tp = entry_price * (1 + tp_pct)
        else:
            sl = entry_price * (1 + sl_pct)
            tp = entry_price * (1 - tp_pct)
            
        return sl, tp
