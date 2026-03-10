import time
from config.config import Config
from core.exchange import ExchangeHandler
from core.logger import logger
from strategy.base import SniperTrendStrategy
from risk.manager import RiskManager
from utils.notifications import notify_trade_opened, notify_trade_closed

class TradingEngine:
    def __init__(self):
        self.exchange = ExchangeHandler()
        self.strategy = SniperTrendStrategy()
        self.risk = RiskManager(self.exchange)
        self.active_positions = {} # symbol -> position info

    def run_cycle(self):
        try:
            logger.info("--- Starting Trading Cycle ---")
            
            # 1. Update balance & Check Emergency Stop
            balance = self.exchange.get_balance()
            if self.risk.check_emergency_stop(balance):
                return False
                
            # 2. Iterate through symbols
            for symbol in Config.TRADING_PAIRS:
                self.process_symbol(symbol, balance)
                
            logger.info("--- Cycle Complete ---")
            return True
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            return True

    def process_symbol(self, symbol, balance):
        # 1. Fetch Data
        df = self.exchange.fetch_ohlcv(symbol, timeframe=Config.TIMEFRAME)
        if df is None: return

        # 2. Generate Signal
        signal_data = self.strategy.generate_signals(df)
        if not signal_data: return
        
        signal = signal_data['signal']
        current_price = signal_data['price']
        
        # 3. Check existing positions
        positions = self.exchange.fetch_positions([symbol])
        has_position = len(positions) > 0
        
        if not has_position:
            if signal != 0:
                self.open_position(symbol, signal, current_price, balance, signal_data.get('atr'))
        else:
            # Logic for closing or trailing stop
            pos = positions[0]
            side = 'long' if float(pos['contracts']) > 0 else 'short'
            
            # Simple exit: if signal reverses
            if (side == 'long' and signal == -1) or (side == 'short' and signal == 1):
                self.close_position(symbol, "Signal Reversal")

    def open_position(self, symbol, signal, price, balance, atr):
        side = 'buy' if signal == 1 else 'sell'
        amount = self.risk.calculate_position_size(symbol, price, balance)
        
        if amount <= 0:
            logger.warning(f"Calculated amount for {symbol} is 0. Skipping.")
            return

        # Set Leverage first
        self.exchange.set_leverage(symbol, Config.LEVERAGE)
        
        order = self.exchange.create_order(symbol, side, amount)
        if order:
            sl, tp = self.risk.get_sl_tp(side, price, atr)
            # In a real production bot, you'd also place SL/TP orders here
            # For this MVP, we'll track them in the engine or use CCXT params if supported
            logger.info(f"Opened {side} position on {symbol} at {price}. SL: {sl}, TP: {tp}")
            notify_trade_opened(symbol, side, price, amount, sl, tp)

    def close_position(self, symbol, reason):
        positions = self.exchange.fetch_positions([symbol])
        if not positions: return
        
        pos = positions[0]
        side = 'sell' if float(pos['contracts']) > 0 else 'buy'
        amount = abs(float(pos['contracts']))
        
        order = self.exchange.create_order(symbol, side, amount)
        if order:
            logger.info(f"Closed position on {symbol}. Reason: {reason}")
            # Calculate PnL (simplification)
            notify_trade_closed(symbol, 0, reason) # PnL calculation needs tracking entry price

    def start(self):
        logger.info("Bot started...")
        while True:
            success = self.run_cycle()
            if not success: break
            
            # Wait for next candle or a fixed interval
            time.sleep(60) # Check every minute
