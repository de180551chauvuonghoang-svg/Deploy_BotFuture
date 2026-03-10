from strategy.smc_strategy import SMCStrategy
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
        Fetches OHLCV data for multiple timeframes.
        """
        try:
            df_15m = self.exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df_1h = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            df_4h = self.exchange.fetch_ohlcv(symbol, timeframe='4h', limit=200)
            
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
            # Dynamic Management
            pos = positions[0]
            if symbol in self.active_positions:
                pos_info = self.active_positions[symbol]
                import pandas_ta as ta
                atr_15m = ta.atr(df_15m['high'], df_15m['low'], df_15m['close']).iloc[-1]
                
                # Check for TP1 hit to set breakeven (simplified check)
                tp1_hit = (pos_info['side'] == 'LONG' and df_15m['high'].iloc[-1] >= pos_info['tp1']) or \
                          (pos_info['side'] == 'SHORT' and df_15m['low'].iloc[-1] <= pos_info['tp1'])
                
                new_sl = update_dynamic_exit(
                    curr_price, pos_info['entry'], pos_info['sl'], pos_info['side'], atr_15m, tp1_hit
                )
                
                if new_sl != pos_info['sl']:
                    logger.info(f"SMC: Moving SL for {symbol} to {new_sl}")
                    pos_info['sl'] = new_sl

            # Reversal check
            side = 'LONG' if float(pos['contracts']) > 0 else 'SHORT'
            if (side == 'LONG' and signal == 'SHORT') or (side == 'SHORT' and signal == 'LONG'):
                self.close_position(symbol, "SMC Signal Reversal")

    def open_position(self, symbol, signal_data):
        side_cmd = 'buy' if signal_data['signal'] == 'LONG' else 'sell'
        price = signal_data['entry']
        amount = signal_data['size']
        
        if amount <= 0: return

        self.exchange.set_leverage(symbol, Config.LEVERAGE)
        
        logger.info(f"ENTRY: {signal_data['reason']}")
        order = self.exchange.create_order(symbol, side_cmd, amount)
        
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
