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
        
        df_1h_idx = df_1h.index
        df_4h_idx = df_4h.index
        
        last_idx_1h = -1
        last_idx_4h = -1
        
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
            idx_1h = df_1h_idx.searchsorted(curr_time, side='right') - 1
            idx_4h = df_4h_idx.searchsorted(curr_time, side='right') - 1
            
            if idx_1h < 50 or idx_4h < 50: continue
            
            # OPTIMIZATION: Only run strategy on 15M candle if it's the start of a 15m period
            # and only if HTF potentially has new data.
            # For backtest speed, many users only check entries on 15m candle close.
            
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
            'tp2': signal_data['tp2'],
            'tp3': signal_data['tp3'],
            'size': signal_data['size'],
            'initial_size': signal_data['size'],
            'score': signal_data.get('score', 0),
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False
        })

    def _check_exit(self, row, pos):
        high, low, cur_price = row['high'], row['low'], row['close']
        atr_val = row.get('atr', 0)
        
        # 0. Dynamic Trailing (ATR-based - MATCHES LIVE)
        if atr_val > 0:
            from risk.smart_risk import update_dynamic_exit
            old_sl = pos['sl']
            p_info = {
                'tp1_done': pos['tp1_hit'],
                'tp2_done': pos['tp2_hit'],
                'tp3_done': pos.get('tp3_hit', False),
                'tp1': pos['tp1'],
                'tp2': pos['tp2'],
                'tp3': pos['tp3']
            }
            new_sl = update_dynamic_exit(cur_price, pos['entry_price'], old_sl, pos['side'], atr_val, p_info)
            if (pos['side'] == 'LONG' and new_sl > old_sl) or (pos['side'] == 'SHORT' and new_sl < old_sl):
                pos['sl'] = new_sl

        # 1. TP1 Check (Close 33%)
        if not pos['tp1_hit']:
            if (pos['side'] == 'LONG' and high >= pos['tp1']) or \
               (pos['side'] == 'SHORT' and low <= pos['tp1']):
                pos['tp1_hit'] = True
                partial_size = pos['initial_size'] * 0.33
                self._close_partial(pos, pos['tp1'], row.name, "TP1_33%", partial_size)
                pos['size'] -= partial_size
                # Trail Stop to Breakeven
                pos['sl'] = pos['entry_price']
                
        # 2. TP2 Check (Close another 33%)
        elif not pos['tp2_hit']:
            if (pos['side'] == 'LONG' and high >= pos['tp2']) or \
               (pos['side'] == 'SHORT' and low <= pos['tp2']):
                pos['tp2_hit'] = True
                partial_size = pos['initial_size'] * 0.33
                self._close_partial(pos, pos['tp2'], row.name, "TP2_33%", partial_size)
                pos['size'] -= partial_size
                # Trail Stop to TP1 to lock in 2R profit
                pos['sl'] = pos['tp1']

        # 3. TP3 Check (Close final part)
        elif pos['tp2_hit'] and not pos['tp3_hit']:
            if (pos['side'] == 'LONG' and high >= pos['tp3']) or \
               (pos['side'] == 'SHORT' and low <= pos['tp3']):
                pos['tp3_hit'] = True
                partial_size = pos['initial_size'] * 0.17 # Close half of rem (Total closed 83%)
                self._close_partial(pos, pos['tp3'], row.name, "TP3_PARTIAL", partial_size)
                pos['size'] -= partial_size
                pos['sl'] = pos['tp2']

        # 4. SL Check
        if (pos['side'] == 'LONG' and low <= pos['sl']) or \
           (pos['side'] == 'SHORT' and high >= pos['sl']):
            reason = "STOP_LOSS"
            if pos['tp1_hit']: reason = "BE_STOP"
            if pos['tp2_hit']: reason = "TP1_TRAIL"
            if pos['tp3_hit']: reason = "TP2_TRAIL"
            self._close_partial(pos, pos['sl'], row.name, reason, pos['size'])
            return True
            
        return False

    def _close_partial(self, pos, exit_price, exit_time, reason, size):
        if size <= 0: return
        pnl = (exit_price - pos['entry_price']) * size if pos['side'] == 'LONG' else (pos['entry_price'] - exit_price) * size
        fee = (pos['entry_price'] * size * self.fee) + (exit_price * size * self.fee)
        self.capital += (pnl - fee)
        
        self.trade_log.append({
            'side': pos['side'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'pnl': pnl - fee,
            'reason': reason,
            'score': pos['score'],
            'time': exit_time
        })

    def report(self):
        if not self.trade_log: return "No trades."
        df = pd.DataFrame(self.trade_log)
        
        # Save to CSV for later analysis
        df.to_csv("backtest_trades_single.csv", index=False)
        
        total_pnl = df['pnl'].sum()
        roi = (total_pnl / self.initial_capital) * 100
        win_rate = (len(df[df['pnl'] > 0]) / len(df)) * 100
        
        # Advanced Statistics
        wins = df[df['pnl'] > 0]
        losses = df[df['pnl'] < 0]
        draws = df[df['pnl'] == 0]
        
        total_wins = len(wins)
        total_losses = len(losses)
        total_draws = len(draws)
        
        gross_profit = wins['pnl'].sum() if not wins.empty else 0
        gross_loss = abs(losses['pnl'].sum()) if not losses.empty else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Calculate Drawdown
        cum_pnl = df['pnl'].cumsum() + self.initial_capital
        peak = cum_pnl.expanding().max()
        dd = (cum_pnl - peak) / peak
        max_dd = abs(dd.min()) * 100

        return f"""
==================================================
           SMC FAST BACKTEST REPORT
==================================================
Lợi nhuận: {total_pnl:.2f} USDT ({roi:.2f}%)
Tỷ lệ thắng: {win_rate:.2f}%
Tổng số lệnh: {len(df)}
--------------------------------------------------
Thắng (Win): {total_wins}
Thua (Loss): {total_losses}
Hòa (Draw):  {total_draws}
Profit Factor: {profit_factor:.2f}
Max Drawdown: {max_dd:.2f}%
==================================================
Trade logs saved to backtest_trades_single.csv
"""
