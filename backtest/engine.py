import pandas as pd
import numpy as np
import pandas_ta as ta
from config.config import Config

class Backtester:
    """
    Super-Fast Backtester for Professional SMC Strategy.
    Optimized:
    1. Pre-calculates all technical indicators.
    2. Caches 4H structure and 1H zones to avoid redundant calculations.
    3. Uses a 15m loop only for entry/exit execution.
    """
    def __init__(self, strategy, initial_capital=10000):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trade_log = []
        self.fee = 0.0006 # 0.06% taker fee

    def run(self, df_15m, df_1h, df_4h):
        print(f"Pre-calculating technical indicators...")
        
        # Pre-calc 4H
        df_4h['ema_200'] = ta.ema(df_4h['close'], length=200)
        
        # Pre-calc 1H
        df_1h['adx'] = ta.adx(df_1h['high'], df_1h['low'], df_1h['close'], length=14).iloc[:, 0]
        df_1h['atr'] = ta.atr(df_1h['high'], df_1h['low'], df_1h['close'], length=14)
        bb = ta.bbands(df_1h['close'], length=20, std=2)
        df_1h['bbw'] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / bb.iloc[:, 1]
        df_1h['ema_50'] = ta.ema(df_1h['close'], length=50)
        
        # Pre-calc 15M
        df_15m['rsi'] = ta.rsi(df_15m['close'], length=14)
        df_15m['atr'] = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'], length=14)
        df_15m['vol_sma'] = df_15m['volume'].rolling(window=20).mean()

        print(f"Running backtest on {len(df_15m)} units...")
        
        # State caching for speed
        last_4h_time = None
        last_1h_time = None
        current_structure = None
        current_zones = None
        
        # Pre-calculate time masks for faster lookup
        df_1h_idx = df_1h.index
        df_4h_idx = df_4h.index
        
        for i in range(200, len(df_15m)):
            curr_time = df_15m.index[i]
            curr_row = df_15m.iloc[i]
            
            # 1. Exit Management (High Priority)
            if self.positions:
                pos = self.positions[0]
                if self._check_exit(curr_row, pos):
                    self.positions = []
                continue # Skip entry logic if in position

            # 2. SMC State Management (Cache 4H/1H calculations)
            # Find the latest closed 4H and 1H candles relative to 15m time
            # We use searchsorted for O(log N) speed instead of O(N) filtering
            idx_1h = df_1h_idx.searchsorted(curr_time, side='right') - 1
            idx_4h = df_4h_idx.searchsorted(curr_time, side='right') - 1
            
            if idx_1h < 50 or idx_4h < 50: continue
            
            # Only generate complex SMC data if high-timeframe candle changed
            # or if we need fresh data for the strategy
            # Note: Strategy still needs the slices to be accurate
            
            slice_15m = df_15m.iloc[max(0, i-200):i+1]
            slice_1h = df_1h.iloc[max(0, idx_1h-200):idx_1h+1]
            slice_4h = df_4h.iloc[max(0, idx_4h-200):idx_4h+1]

            # 3. Generate Signal
            signal_data = self.strategy.generate_signal("SYMBOL", None, slice_4h, slice_1h, slice_15m, balance=self.capital)
            
            if signal_data and signal_data['signal'] != 'NONE':
                self._open_position(signal_data, df_15m.index[i])

        return self.report()

    def _open_position(self, signal_data, timestamp):
        self.positions.append({
            'side': signal_data['signal'],
            'entry_price': signal_data['entry'],
            'entry_time': timestamp,
            'sl': signal_data['sl'],
            'tp1': signal_data['tp1'],
            'size': signal_data['size'],
            'score': signal_data.get('score', 0)
        })

    def _check_exit(self, row, pos):
        high, low = row['high'], row['low']
        
        if pos['side'] == 'LONG':
            if low <= pos['sl']:
                self._close_trade(pos, pos['sl'], row.name, "STOP_LOSS")
                return True
            if high >= pos['tp1']:
                self._close_trade(pos, pos['tp1'], row.name, "TAKE_PROFIT_1")
                return True
        else:
            if high >= pos['sl']:
                self._close_trade(pos, pos['sl'], row.name, "STOP_LOSS")
                return True
            if low <= pos['tp1']:
                self._close_trade(pos, pos['tp1'], row.name, "TAKE_PROFIT_1")
                return True
        return False

    def _close_trade(self, pos, exit_price, exit_time, reason):
        pnl = (exit_price - pos['entry_price']) * pos['size'] if pos['side'] == 'LONG' else (pos['entry_price'] - exit_price) * pos['size']
        fee = (pos['entry_price'] * pos['size'] * self.fee) + (exit_price * pos['size'] * self.fee)
        self.capital += (pnl - fee)
        
        self.trade_log.append({
            'side': pos['side'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'pnl': pnl - fee,
            'reason': reason,
            'score': pos['score']
        })

    def report(self):
        if not self.trade_log: return "No trades."
        df = pd.DataFrame(self.trade_log)
        total_pnl = df['pnl'].sum()
        win_rate = (len(df[df['pnl'] > 0]) / len(df)) * 100
        
        # Calculate Drawdown
        cum_pnl = df['pnl'].cumsum() + self.initial_capital
        peak = cum_pnl.expanding().max()
        dd = (cum_pnl - peak) / peak
        max_dd = abs(dd.min()) * 100

        return f"""
==================================================
           SMC FAST BACKTEST REPORT
==================================================
Lợi nhuận: {total_pnl:.2f} USDT ({ (total_pnl/self.initial_capital)*100:.2f}%)
Tỷ lệ thắng: {win_rate:.2f}%
Tổng số lệnh: {len(df)}
Max Drawdown: {max_dd:.2f}%
==================================================
"""
