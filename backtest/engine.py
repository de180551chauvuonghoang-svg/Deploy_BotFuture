import pandas as pd
import numpy as np
import pandas_ta as ta
from config.config import Config
from strategy.base import SniperTrendStrategy

class Backtester:
    def __init__(self, strategy, initial_capital=10000):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.fee = 0.0006 # 0.06% taker fee

    def run(self, df):
        df = df.copy()
        # Precompute indicators
        self.strategy.generate_signals(df) 
        
        # Simulating...
        for i in range(21, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # This is a simplified backtest
            # Real backtests should handle SL/TP per bar
            signal_data = self.strategy.generate_signals(df.iloc[:i+1])
            if not signal_data: continue
            
            signal = signal_data['signal']
            price = signal_data['price']
            
            # Simple logic: Enter on signal, exit on reversal
            if not self.positions:
                if signal != 0:
                    self.positions.append({
                        'side': 'long' if signal == 1 else 'short',
                        'entry_price': price,
                        'entry_time': current_row['timestamp']
                    })
            else:
                pos = self.positions[0]
                if (pos['side'] == 'long' and signal == -1) or \
                   (pos['side'] == 'short' and signal == 1):
                    # Close trade
                    exit_price = price
                    pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price'] if pos['side'] == 'long' \
                              else (pos['entry_price'] - exit_price) / pos['entry_price']
                    
                    pnl_usdt = self.capital * Config.POSITION_SIZE_PCT * pnl_pct * Config.LEVERAGE
                    pnl_usdt -= (self.capital * Config.POSITION_SIZE_PCT * self.fee * 2) # fees
                    
                    self.capital += pnl_usdt
                    self.trades.append({
                        'entry_time': pos['entry_time'],
                        'exit_time': current_row['timestamp'],
                        'pnl': pnl_usdt,
                        'pnl_pct': pnl_pct
                    })
                    self.positions = []

        return self.report()

    def report(self):
        if not self.trades:
            return "No trades executed."
            
        tdf = pd.DataFrame(self.trades)
        total_pnl = tdf['pnl'].sum()
        win_rate = (tdf['pnl'] > 0).mean() * 100
        max_drawdown = self.calculate_max_drawdown(tdf)
        
        report = f"""
--- Backtest Report ---
Initial Capital: {self.initial_capital}
Final Capital: {self.capital:.2f}
Total PnL: {total_pnl:.2f}
Win Rate: {win_rate:.2f}%
Total Trades: {len(tdf)}
Max Drawdown: {max_drawdown:.2f}%
        """
        return report

    def calculate_max_drawdown(self, tdf):
        equity_curve = tdf['pnl'].cumsum() + self.initial_capital
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        return abs(drawdown.min()) * 100
