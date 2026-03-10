import pandas as pd
import numpy as np
import pandas_ta as ta
from config.config import Config
from risk.adaptive_risk import AdaptiveRiskManager

class Backtester:
    """
    Advanced Backtester for SMC Strategy.
    Simulates trades with SL/TP, commissions, and multi-timeframe confluence.
    """
    def __init__(self, strategy, initial_capital=10000):
        self.strategy = strategy
        self.risk_manager = AdaptiveRiskManager(base_risk=0.01) # 1% risk
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = []
        self.trades = []
        self.fee = 0.0006 # 0.06% taker fee

    def run(self, df_15m, df_1h, df_4h):
        """
        Runs backtest by iterating through 15m candles and checking HTF bias.
        """
        print(f"Pre-calculating indicators for speed...")
        # 15m Indicators
        adx_df = ta.adx(df_15m['high'], df_15m['low'], df_15m['close'])
        df_15m['adx'] = adx_df.iloc[:, 0]
        df_15m['atr'] = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'])
        df_15m['rsi'] = ta.rsi(df_15m['close'])
        
        # 1h Indicators
        df_1h['ema_21'] = ta.ema(df_1h['close'], length=21)
        df_1h['ema_50'] = ta.ema(df_1h['close'], length=50)
        
        # 4h Indicators
        df_4h['ema_200'] = ta.ema(df_4h['close'], length=200)
        
        print(f"Running backtest on {len(df_15m)} units of 15m data...")
        
        # Align timeframes (very simplified alignment for backtest)
        for i in range(50, len(df_15m)):
            curr_time = df_15m.index[i]
            
            # 1. Get current slices of higher timeframes
            slice_15m = df_15m.iloc[:i+1]
            slice_1h = df_1h[df_1h.index <= curr_time]
            slice_4h = df_4h[df_4h.index <= curr_time]
            
            if len(slice_1h) < 20 or len(slice_4h) < 20: continue
            
            current_row = df_15m.iloc[i]
            
            # 2. Check current position status (SL/TP)
            if self.positions:
                pos = self.positions[0]
                is_closed = self._check_exit(current_row, pos)
                if is_closed:
                    self.positions = []
                    continue # One action per candle
            
            # 3. Generate Signal
            if not self.positions:
                signal_data = self.strategy.generate_signals(slice_15m, slice_4h, slice_1h)
                
                if signal_data and signal_data['signal'] != 0:
                    self._open_position(signal_data, slice_15m)

        return self.report()

    def _open_position(self, signal_data, df_15m):
        price = signal_data['price']
        side = 1 if signal_data['signal'] == 1 else -1
        
        # Calculate Risk and SL/TP
        risk_data = self.risk_manager.calculate_trade_risk(
            self.capital, df_15m, price, side=side
        )
        
        if risk_data['size'] <= 0: return

        self.positions.append({
            'side': 'long' if side == 1 else 'short',
            'side_int': side,
            'entry_price': price,
            'entry_time': df_15m.index[-1],
            'sl': risk_data['sl'],
            'tp1': risk_data['tp1'],
            'tp2': risk_data['tp2'],
            'size': risk_data['size'],
            'score': signal_data.get('score', 0)
        })

    def _check_exit(self, row, pos):
        curr_price_high = row['high']
        curr_price_low = row['low']
        curr_price_close = row['close']
        
        exit_price = None
        exit_reason = ""
        
        # 1. Check Stop Loss
        if pos['side'] == 'long':
            if curr_price_low <= pos['sl']:
                exit_price = pos['sl']
                exit_reason = "STOP_LOSS"
            elif curr_price_high >= pos['tp1']:
                # Simplified: close full position at TP1 for backtest clarity
                exit_price = pos['tp1']
                exit_reason = "TAKE_PROFIT_1"
        else: # Short
            if curr_price_high >= pos['sl']:
                exit_price = pos['sl']
                exit_reason = "STOP_LOSS"
            elif curr_price_low <= pos['tp1']:
                exit_price = pos['tp1']
                exit_reason = "TAKE_PROFIT_1"
                
        if exit_price:
            self._close_trade(pos, exit_price, row.name, exit_reason)
            return True
        return False

    def _close_trade(self, pos, exit_price, exit_time, reason):
        pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price'] if pos['side'] == 'long' \
                  else (pos['entry_price'] - exit_price) / pos['entry_price']
        
        # Net PnL after fees
        pnl_usdt = (pos['size'] * exit_price * pnl_pct)
        fees = (pos['size'] * pos['entry_price'] * self.fee) + (pos['size'] * exit_price * self.fee)
        pnl_usdt -= fees
        
        self.capital += pnl_usdt
        self.trades.append({
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'pnl': pnl_usdt,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'score': pos['score']
        })

    def report(self):
        if not self.trades:
            return "No trades executed."
            
        tdf = pd.DataFrame(self.trades)
        total_pnl = tdf['pnl'].sum()
        win_rate = (tdf['pnl'] > 0).mean() * 100
        
        # Profit Factor
        gross_profit = tdf[tdf['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(tdf[tdf['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        
        max_drawdown = self.calculate_max_drawdown(tdf)
        
        report = f"""
==================================================
           ADVANCED SMC BACKTEST REPORT
==================================================
Initial Capital:  {self.initial_capital:.2f} USDT
Final Capital:    {self.capital:.2f} USDT
Total PnL:        {total_pnl:.2f} USDT ({((self.capital/self.initial_capital)-1)*100:.2f}%)
Win Rate:         {win_rate:.2f}%
Profit Factor:    {profit_factor:.2f}
Total Trades:     {len(tdf)}
Max Drawdown:     {max_drawdown:.2f}%
==================================================
        """
        return report

    def calculate_max_drawdown(self, tdf):
        equity_curve = tdf['pnl'].cumsum() + self.initial_capital
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        return abs(drawdown.min()) * 100
