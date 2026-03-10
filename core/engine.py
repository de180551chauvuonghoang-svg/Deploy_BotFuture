import time
import pandas as pd
from config.config import Config
from core.exchange import ExchangeHandler
from core.logger import logger
from strategy.signal_generator import SignalGenerator
from risk.adaptive_risk import AdaptiveRiskManager
from utils.notifications import notify_trade_opened, notify_trade_closed

class TradingEngine:
    """
    Core Trading Engine for managing cycles, signals, and risk.
    Upgraded for multi-timeframe SMC strategy.
    """
    def __init__(self):
        self.exchange = ExchangeHandler()
        self.strategy = SignalGenerator(name="AdvancedSMC")
        self.risk_manager = AdaptiveRiskManager(base_risk=Config.POSITION_SIZE_PCT)
        self.active_positions = {} # symbol -> position info

    def run_cycle(self):
        try:
            logger.info("--- Starting Advanced SMC Cycle ---")
            
            # 1. Update balance
            balance_info = self.exchange.get_balance()
            equity = balance_info.get('total', 0)
            
            # 2. Iterate through symbols
            for symbol in Config.TRADING_PAIRS:
                self.process_symbol(symbol, equity)
                
            logger.info("--- Cycle Complete ---")
            return True
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return True

    def _fetch_multi_tf_data(self, symbol):
        """
        Fetches OHLCV data for multiple timeframes required by the strategy.
        """
        try:
            df_15m = self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df_1h = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            df_4h = self.exchange.fetch_ohlcv(symbol, timeframe='4h', limit=100)
            
            if df_15m is None or df_1h is None or df_4h is None:
                return None
            return df_15m, df_1h, df_4h
        except Exception as e:
            logger.error(f"Error fetching multi-TF data for {symbol}: {e}")
            return None

    def process_symbol(self, symbol, equity):
        # 1. Fetch Multi-Timeframe Data
        data = self._fetch_multi_tf_data(symbol)
        if not data: return
        df_15m, df_1h, df_4h = data

        # 2. Generate Signal using SMC Logic
        signal_data = self.strategy.generate_signals(df_15m, df_4h, df_1h)
        if not signal_data: return
        
        signal = signal_data['signal']
        curr_price = signal_data['price']
        
        # 3. Check existing positions
        positions = self.exchange.fetch_positions([symbol])
        has_position = len(positions) > 0
        
        if not has_position:
            # If a valid setup is detected
            if signal != 0:
                self.open_position(symbol, signal_data, equity)
        else:
            # Dynamic Risk Management: Check for Trailing SL / Breakeven
            pos = positions[0]
            side_int = 1 if float(pos['contracts']) > 0 else -1
            
            # For simplicity, we assume we track the SL in self.active_positions
            # In a real bot, we'd fetch actual SL orders from the exchange
            if symbol in self.active_positions:
                pos_info = self.active_positions[symbol]
                atr = ta.atr(df_15m['high'], df_15m['low'], df_15m['close']).iloc[-1]
                
                new_sl = self.risk_manager.check_dynamic_trailing(
                    curr_price, 
                    pos_info['entry'], 
                    pos_info['sl'], 
                    side_int, 
                    atr
                )
                
                if new_sl != pos_info['sl']:
                    logger.info(f"Updating SL for {symbol} to {new_sl} (Trailing/BE)")
                    pos_info['sl'] = new_sl
                    # Here you would call exchange.update_order(sl_order_id, price=new_sl)

            # Signal reversal exit
            side = 'long' if side_int == 1 else 'short'
            if (side == 'long' and signal == -1) or (side == 'short' and signal == 1):
                self.close_position(symbol, "Signal Reversal")

    def open_position(self, symbol, signal_data, equity):
        side = 'buy' if signal_data['signal'] == 1 else 'sell'
        price = signal_data['price']
        
        # Calculate Risk and Position Size
        risk_data = self.risk_manager.calculate_trade_risk(
            equity, signal_data.get('df_15m'), price, side=(1 if side == 'buy' else -1)
        )
        
        amount = risk_data['size']
        if amount <= 0: return

        # Set Leverage
        self.exchange.set_leverage(symbol, Config.LEVERAGE)
        
        logger.info(f"Opening {side} position on {symbol} | Score: {signal_data['score']}")
        order = self.exchange.create_order(symbol, side, amount)
        
        if order:
            self.active_positions[symbol] = {
                'entry': price,
                'sl': risk_data['sl'],
                'tp1': risk_data['tp1'],
                'tp2': risk_data['tp2']
            }
            logger.info(f"SMC Position Opened: {symbol} at {price}. SL: {risk_data['sl']:.2f}, TP1: {risk_data['tp1']:.2f}")
            notify_trade_opened(symbol, side, price, amount, risk_data['sl'], risk_data['tp1'])

    def close_position(self, symbol, reason):
        positions = self.exchange.fetch_positions([symbol])
        if not positions: return
        
        pos = positions[0]
        side = 'sell' if float(pos['contracts']) > 0 else 'buy'
        amount = abs(float(pos['contracts']))
        
        order = self.exchange.create_order(symbol, side, amount)
        if order:
            logger.info(f"SMC Closed: {symbol}. Reason: {reason}")
            if symbol in self.active_positions: del self.active_positions[symbol]
            notify_trade_closed(symbol, 0, reason)

    def start(self):
        logger.info("Advanced SMC Bot started in Monitoring Mode...")
        while True:
            success = self.run_cycle()
            if not success: break
            time.sleep(60)
