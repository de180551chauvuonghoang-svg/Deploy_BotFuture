import time
from strategy.smc_strategy import SMCStrategy
from core.exchange import ExchangeHandler
from config.config import Config
from core.logger import logger
from risk.smart_risk import update_dynamic_exit
from utils.notifications import notify_trade_opened, notify_trade_closed

class TradingEngine:
    """
    Core Trading Engine for managing cycles, signals, and risk.
    Upgraded for high-professional SMC strategy.
    """
    def __init__(self):
        self.exchange = ExchangeHandler()
        self.strategy = SMCStrategy(name="AdvancedSMC")
        self.active_positions = {} # symbol -> position info

    def run_cycle(self):
        try:
            logger.info("--- Starting Professional SMC Cycle ---")
            
            # 1. Update balance
            equity = self.exchange.get_balance()
            
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
        Fetches OHLCV data for multiple timeframes.
        """
        try:
            df_15m = self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=500)
            df_1h = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=500)
            df_4h = self.exchange.fetch_ohlcv(symbol, timeframe='4h', limit=500)
            
            if df_15m is None or df_1h is None or df_4h is None:
                return None
            return df_15m, df_1h, df_4h
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def process_symbol(self, symbol, equity):
        # 1. Fetch Multi-Timeframe Data
        data = self._fetch_multi_tf_data(symbol)
        if not data: return
        df_15m, df_1h, df_4h = data

        # 2. Generate Signal
        signal_data = self.strategy.generate_signal(symbol, self.exchange, df_4h, df_1h, df_15m, balance=equity)
        if not signal_data: return
        
        signal = signal_data.get('signal', 'NONE')
        curr_price = signal_data.get('entry')
        
        # 3. Check existing positions
        positions = self.exchange.fetch_positions([symbol])
        has_position = len(positions) > 0
        
        if not has_position:
            if signal != 'NONE':
                self.open_position(symbol, signal_data)
        else:
            # 🔄 PROFESSIONAL TP/SL EXECUTION LÓGIC (Sync with Backtest)
            pos = positions[0]
            contracts = abs(float(pos['contracts']))
            if symbol in self.active_positions:
                p_info = self.active_positions[symbol]
                high_15m = df_15m['high'].iloc[-1]
                low_15m = df_15m['low'].iloc[-1]
                curr_px = df_15m['close'].iloc[-1]
                
                side = p_info['side'] # 'LONG' or 'SHORT'
                
                # A. STOP LOSS CHECK
                is_sl = (side == 'LONG' and low_15m <= p_info['sl']) or \
                        (side == 'SHORT' and high_15m >= p_info['sl'])
                if is_sl:
                    self.close_position(symbol, f"SMC Stop Loss Hit @ {p_info['sl']:.4f}")
                    return

                # B. PARTIAL TP1 (33%)
                if not p_info.get('tp1_done'):
                    is_tp1 = (side == 'LONG' and high_15m >= p_info['tp1']) or \
                             (side == 'SHORT' and low_15m <= p_info['tp1'])
                    if is_tp1:
                        close_amt = contracts * 0.33
                        logger.info(f"SMC: TP1 Hit for {symbol}! Closing 33% ({close_amt:.2f})")
                        self.exchange.create_order(symbol, 'sell' if side == 'LONG' else 'buy', close_amt)
                        p_info['tp1_done'] = True
                        p_info['sl'] = p_info['entry'] # Move to Break-even
                        logger.info(f"SMC: Moved SL to Breakeven ({p_info['sl']:.4f})")
                        return

                # C. PARTIAL TP2 (33%)
                if p_info.get('tp1_done') and not p_info.get('tp2_done'):
                    is_tp2 = (side == 'LONG' and high_15m >= p_info['tp2']) or \
                             (side == 'SHORT' and low_15m <= p_info['tp2'])
                    if is_tp2:
                        close_amt = contracts * 0.50 # Half of remaining (approx 33% of original)
                        logger.info(f"SMC: TP2 Hit for {symbol}! Closing 33% ({close_amt:.2f})")
                        self.exchange.create_order(symbol, 'sell' if side == 'LONG' else 'buy', close_amt)
                        p_info['tp2_done'] = True
                        p_info['sl'] = p_info['tp1'] # Lock profit at TP1
                        logger.info(f"SMC: Locked Profit at TP1 ({p_info['sl']:.4f})")
                        return

                # D. FULL TP3 (Final Target)
                if p_info.get('tp2_done'):
                    is_tp3 = (side == 'LONG' and high_15m >= p_info.get('tp3', p_info['tp2'] * 1.05)) or \
                             (side == 'SHORT' and low_15m <= p_info.get('tp3', p_info['tp2'] * 0.95))
                    if is_tp3:
                        self.close_position(symbol, f"SMC Final TP3 Target Hit")
                        return

            # E. REVERSAL CHECK
            side_actual = 'LONG' if float(pos['contracts']) > 0 else 'SHORT'
            if (side_actual == 'LONG' and signal == 'SHORT') or (side_actual == 'SHORT' and signal == 'LONG'):
                self.close_position(symbol, "SMC Signal Reversal")

    def open_position(self, symbol, signal_data):
        side_cmd = 'buy' if signal_data['signal'] == 'LONG' else 'sell'
        price = signal_data['entry']
        amount = signal_data['size']
        
        if amount <= 0: return

        self.exchange.set_leverage(symbol, Config.LEVERAGE)
        
        logger.info(f"ENTRY: {signal_data['reason']}")
        order = self.exchange.create_order(
            symbol, side_cmd, amount, 
            sl=signal_data['sl'], 
            tp1=signal_data['tp1'], 
            tp2=signal_data['tp2']
        )
        
        if order:
            self.active_positions[symbol] = {
                'side': signal_data['signal'],
                'entry': price,
                'sl': signal_data['sl'],
                'tp1': signal_data['tp1'],
                'tp2': signal_data['tp2']
            }
            logger.info(f"SMC Position: {symbol} @ {price} | SL: {signal_data['sl']:.2f}")
            notify_trade_opened(symbol, side_cmd, price, amount, signal_data['sl'], signal_data['tp1'])

    def close_position(self, symbol, reason):
        positions = self.exchange.fetch_positions([symbol])
        if not positions: return
        
        pos = positions[0]
        side_cmd = 'sell' if float(pos['contracts']) > 0 else 'buy'
        amount = abs(float(pos['contracts']))
        
        order = self.exchange.create_order(symbol, side_cmd, amount)
        if order:
            logger.info(f"SMC EXIT: {symbol} - {reason}")
            if symbol in self.active_positions: del self.active_positions[symbol]
            notify_trade_closed(symbol, 0, reason)

    def start(self):
        logger.info("Professional SMC Bot Active...")
        while True:
            self.run_cycle()
            time.sleep(60)
