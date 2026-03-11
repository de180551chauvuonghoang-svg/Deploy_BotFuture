import ccxt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import warnings
import os
import time
from backtest.data import fetch_historical_data
from strategy.smc_strategy import SMCStrategy
from datetime import datetime
import numpy as np

warnings.filterwarnings('ignore')
os.environ['IS_BACKTEST'] = 'true'

class PortfolioBacktester:
    def __init__(self, symbols, strategy, initial_capital=10000):
        self.symbols = symbols
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.active_positions = [] # List of dicts
        self.trade_history = []
        self.fee = 0.0006 # 0.06% taker fee

    def run(self, data_map, days):
        """
        data_map: { 'BTC/USDT': { '15m': df, '1h': df, '4h': df }, ... }
        """
        print(f"\n--- STARTING PORTFOLIO BACKTEST (Shared Wallet: {self.initial_capital} USDT) ---")
        
        # Optimization: Pre-calculate indicators for all dataframes
        print("Pre-calculating indicators for speedup...")
        import pandas_ta as ta
        for symbol in self.symbols:
            d = data_map[symbol]
            # 4H EMA
            d['4h']['ema_200'] = ta.ema(d['4h']['close'], length=200)
            # 1H Indicators
            d['1h']['atr'] = ta.atr(d['1h']['high'], d['1h']['low'], d['1h']['close'], length=14)
            d['1h']['ema_50'] = ta.ema(d['1h']['close'], length=50)
            # 15M Indicators
            d['15m']['atr'] = ta.atr(d['15m']['high'], d['15m']['low'], d['15m']['close'], length=14)
            d['15m']['rsi'] = ta.rsi(d['15m']['close'], length=14)

        # 1. Synchronize Timeline
        # Get all 15m timestamps across all symbols
        all_timestamps = set()
        for s in self.symbols:
            all_timestamps.update(data_map[s]['15m'].index)
        
        sorted_timestamps = sorted(list(all_timestamps))
        print(f"Total timeline steps (15m): {len(sorted_timestamps)}")

        # 2. Iterate through time
        count = 0
        for ts in sorted_timestamps:
            count += 1
            if count % 5000 == 0:
                print(f"Processed {count}/{len(sorted_timestamps)} steps...")
            
            # A. Manage Existing Positions (Exit Check)
            remaining_positions = []
            for pos in self.active_positions:
                symbol = pos['symbol']
                df_15m = data_map[symbol]['15m']
                
                if ts in df_15m.index:
                    curr_row = df_15m.loc[ts]
                    if self._check_exit(curr_row, pos):
                        # Position closed
                        continue
                
                remaining_positions.append(pos)
            self.active_positions = remaining_positions

            # B. Check for New Entries
            # We only check for entries if we have capital and space (limit to say 5 max concurrent trades)
            if len(self.active_positions) < 5 and self.balance > (self.initial_capital * 0.05):
                for symbol in self.symbols:
                    # Don't take multiple trades for the same symbol
                    if any(p['symbol'] == symbol for p in self.active_positions):
                        continue
                        
                    data = data_map[symbol]
                    df_15m = data['15m']
                    df_1h = data['1h']
                    df_4h = data['4h']
                    
                    if ts not in df_15m.index: continue
                    
                    # Get slices with enough data for SMC Strategy (min 200+ candles)
                    idx_15m = df_15m.index.get_loc(ts)
                    if idx_15m < 400: continue
                    
                    # HTF context relative to current time
                    idx_1h = df_1h.index.searchsorted(ts, side='right') - 1
                    idx_4h = df_4h.index.searchsorted(ts, side='right') - 1
                    
                    if idx_1h < 400 or idx_4h < 400: continue
                    
                    # We give 400 candles of lookback to each slice to satisfy strategy requirements
                    slice_15m = df_15m.iloc[idx_15m-400 : idx_15m+1]
                    slice_1h = df_1h.iloc[idx_1h-400 : idx_1h+1]
                    slice_4h = df_4h.iloc[idx_4h-400 : idx_4h+1]
                    
                    # Generate signal with shared balance
                    signal = self.strategy.generate_signal(symbol, None, slice_4h, slice_1h, slice_15m, balance=self.balance)
                    
                    if signal and signal['signal'] != 'NONE':
                        self._open_position(symbol, signal, ts)
                        if len(self.active_positions) >= 5: break

        return self.generate_report(days)

    def _open_position(self, symbol, signal, timestamp):
        # Professional Risk Check
        size_usdt = signal['size'] * signal['entry']
        if size_usdt > self.balance * 0.5: # Safety cap: don't use more than 50% equity on one trade
             return

        new_pos = {
            'symbol': symbol,
            'side': signal['signal'],
            'entry_price': signal['entry'],
            'entry_time': timestamp,
            'sl': signal['sl'],
            'tp1': signal['tp1'],
            'tp2': signal['tp2'],
            'tp3': signal['tp3'],
            'size': signal['size'],
            'initial_size': signal['size'],
            'tp1_hit': False,
            'tp2_hit': False
        }
        self.active_positions.append(new_pos)

    def _check_exit(self, row, pos):
        high, low = row['high'], row['low']
        
        # TP1
        if not pos['tp1_hit']:
            if (pos['side'] == 'LONG' and high >= pos['tp1']) or (pos['side'] == 'SHORT' and low <= pos['tp1']):
                pos['tp1_hit'] = True
                self._close_partial(pos, pos['tp1'], row.name, "TP1_33%", pos['initial_size'] * 0.33)
                pos['size'] -= (pos['initial_size'] * 0.33)
                pos['sl'] = pos['entry_price'] # Break-even

        # TP2
        elif not pos['tp2_hit']:
            if (pos['side'] == 'LONG' and high >= pos['tp2']) or (pos['side'] == 'SHORT' and low <= pos['tp2']):
                pos['tp2_hit'] = True
                self._close_partial(pos, pos['tp2'], row.name, "TP2_33%", pos['initial_size'] * 0.33)
                pos['size'] -= (pos['initial_size'] * 0.33)
                pos['sl'] = pos['tp1'] # Lock profit

        # TP3 / Full Target
        elif pos['tp2_hit']:
            if (pos['side'] == 'LONG' and high >= pos['tp3']) or (pos['side'] == 'SHORT' and low <= pos['tp3']):
                self._close_partial(pos, pos['tp3'], row.name, "TP3_FULL", pos['size'])
                return True

        # SL Check
        if (pos['side'] == 'LONG' and low <= pos['sl']) or (pos['side'] == 'SHORT' and high >= pos['sl']):
            reason = "STOP_LOSS" if not pos['tp1_hit'] else "BE_STOP"
            self._close_partial(pos, pos['sl'], row.name, reason, pos['size'])
            return True
            
        return False

    def _close_partial(self, pos, exit_price, exit_time, reason, size):
        if size <= 0: return
        pnl = (exit_price - pos['entry_price']) * size if pos['side'] == 'LONG' else (pos['entry_price'] - exit_price) * size
        fee = (pos['entry_price'] * size * self.fee) + (exit_price * size * self.fee)
        self.balance += (pnl - fee)
        
        self.trade_history.append({
            'symbol': pos['symbol'],
            'side': pos['side'],
            'entry': pos['entry_price'],
            'exit': exit_price,
            'pnl': pnl - fee,
            'reason': reason,
            'time': exit_time
        })

    def generate_report(self, days):
        if not self.trade_history: return "No trades executed."
        df = pd.DataFrame(self.trade_history)
        total_pnl = self.balance - self.initial_capital
        roi = (total_pnl / self.initial_capital) * 100
        win_rate = (len(df[df['pnl'] > 0]) / len(df)) * 100
        
        # Portfolio Max Drawdown
        cum_bal = df['pnl'].cumsum() + self.initial_capital
        peak = cum_bal.expanding().max()
        dd = (cum_bal - peak) / peak
        max_dd = abs(dd.min()) * 100

        report = f"""
# PORTFOLIO REAL-TRADER BACKTEST REPORT
- **Duration**: {days} Days
- **Starting Capital**: {self.initial_capital} USDT
- **Final Balance**: {self.balance:.2f} USDT
- **Net PnL**: {total_pnl:.2f} USDT ({roi:.2f}%)
- **Win Rate**: {win_rate:.2f}%
- **Total Trades**: {len(df)}
- **Portfolio Max Drawdown**: {max_dd:.2f}%
- **Symbols Tested**: {', '.join(self.symbols)}
"""
        with open("REPORT_PORTFOLIO_800_DAYS.md", "w", encoding='utf-8') as f:
            f.write(report)
        return report

def main():
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'AVAX/USDT']
    days = 800
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    strategy = SMCStrategy()
    
    print("Loading all historical data for portfolio test...")
    data_map = {}
    valid_symbols = []
    
    for s in symbols:
        try:
            print(f"Fetching {s}...")
            m15 = fetch_historical_data(exchange, s, '15m', days=days)
            h1 = fetch_historical_data(exchange, s, '1h', days=days)
            h4 = fetch_historical_data(exchange, s, '4h', days=days)
            
            if m15 is not None and h1 is not None and h4 is not None:
                data_map[s] = {
                    '15m': m15,
                    '1h': h1,
                    '4h': h4
                }
                valid_symbols.append(s)
            else:
                print(f"Skipping {s} due to missing data.")
        except Exception as e:
            print(f"Error fetching {s}: {e}")

    if not valid_symbols:
        print("No valid symbols fetched. Exiting.")
        return

    backtester = PortfolioBacktester(valid_symbols, strategy, initial_capital=10000)
    report = backtester.run(data_map, days)
    print(report)

if __name__ == "__main__":
    main()
