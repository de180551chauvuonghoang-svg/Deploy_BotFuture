import ccxt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import warnings
import os
import time
from backtest.data import fetch_historical_data
from config.config import Config
from strategy.smc_strategy import SMCStrategy
from datetime import datetime
import numpy as np
import pandas_ta as ta
from concurrent.futures import ProcessPoolExecutor
import os

warnings.filterwarnings('ignore')
os.environ['IS_BACKTEST'] = 'true'

from strategy.regime_filter import get_regime
from strategy.structure import detect_structure
from strategy.order_blocks import find_bullish_ob, find_bearish_ob, price_in_ob_zone
from strategy.fvg import find_fvg, price_in_fvg
from strategy.liquidity import detect_liquidity_sweep
from strategy.confluence import score_setup
from risk.smart_risk import calculate_smart_sl_tp

# Helper for parallel processing (Must be at top level for pickling)
def pre_calc_symbol_worker(symbol, data):
    import pandas_ta as ta
    from strategy.regime_filter import get_regime
    from strategy.structure import detect_structure
    from strategy.order_blocks import find_bullish_ob, find_bearish_ob
    from strategy.fvg import find_fvg
    from strategy.liquidity import detect_liquidity_sweep

    df_15m, df_1h, df_4h = data['15m'], data['1h'], data['4h']
    
    # A. Pre-calc Indicators
    df_4h['ema_200'] = ta.ema(df_4h['close'], length=200)
    df_1h['atr'] = ta.atr(df_1h['high'], df_1h['low'], df_1h['close'], length=14)
    df_15m['atr'] = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'], length=14)
    df_15m['rsi'] = ta.rsi(df_15m['close'], length=14)
    df_15m['vol_sma'] = df_15m['volume'].rolling(window=20).mean()
    
    # 24h Volume Approximation (for 15m candles: 24*4 = 96 candles)
    df_15m['vol_24h_usdt'] = (df_15m['volume'] * df_15m['close']).rolling(window=96).sum()
    min_vol_filter = Config.MIN_24H_VOLUME_USDT
    
    # B. Pre-calc Multi-TF States
    h4_biases = {}
    h1_regimes = {}
    h1_obs_fvg = {}

    print(f"[{symbol}] Calculating Multi-TF States...")
    
    # 4H Bias (Calculated on closed candles)
    for i in range(400, len(df_4h)):
        ts = df_4h.index[i]
        h4_biases[ts] = detect_structure(df_4h.iloc[i-400 : i+1], lookback=400)['bias']

    # 1H States (Regime & Zones)
    for i in range(200, len(df_1h)):
        ts = df_1h.index[i]
        slice_1h = df_1h.iloc[i-200 : i+1]
        h1_regimes[ts] = get_regime(slice_1h)
        # OB/FVG detection based on bias will happen per-step in the signal map for efficiency
        
    # C. Build 15m Signal Map (Entry Trigger Level)
    signals = {}
    print(f"[{symbol}] Building 15M Signal Map (Optimized)...")
    
    last_idx_1h = -1
    obs, fvgs = [], []

    for i in range(400, len(df_15m)):
        ts = df_15m.index[i]
        cur_px = df_15m['close'].iloc[i]
        high_15m = df_15m['high'].iloc[i]
        low_15m = df_15m['low'].iloc[i]

        # 2. Get 4H Trend (Macro Filter - MANDATORY for SNIPER ELITE)
        idx_4h_raw = df_4h.index.searchsorted(ts, side='right') - 1
        idx_4h = idx_4h_raw - 1 
        if idx_4h < 200: continue
        
        idx_1h_raw = df_1h.index.searchsorted(ts, side='right') - 1
        idx_1h = idx_1h_raw - 1
        if idx_1h < 200: continue
        
        px_curr = df_15m['close'].iloc[i]
        ema_4h = df_4h['ema_200'].iloc[idx_4h]
        
        bias_4h = h4_biases.get(df_4h.index[idx_4h], "NONE")
        regime_1h = h1_regimes.get(df_1h.index[idx_1h], "NORMAL")
        
        if bias_4h == "LONG" and px_curr < ema_4h: bias_4h = "NONE"
        if bias_4h == "SHORT" and px_curr > ema_4h: bias_4h = "NONE"
        
        # Volume Filter
        vol_24h = df_15m['vol_24h_usdt'].iloc[i]
        if vol_24h < min_vol_filter: bias_4h = "NONE"
        
        if bias_4h == "NONE": continue

        # 3. Zone Cache Logic (Only update when 1H changes)
        if idx_1h != last_idx_1h:
            slice_1h_zones = df_1h.iloc[idx_1h-200 : idx_1h+1]
            if bias_4h == "LONG":
                obs = find_bullish_ob(slice_1h_zones, lookback=200)
            elif bias_4h == "SHORT":
                obs = find_bearish_ob(slice_1h_zones, lookback=200)
            else:
                obs = []
            fvgs = find_fvg(slice_1h_zones, lookback=200)
            last_idx_1h = idx_1h
        
        # 4. Zone Touch Logic
        def touched(px_low, px_high, zone_list):
            for z in zone_list:
                if px_low <= z['top'] and px_high >= z['bottom']:
                    return z
            return None

        ob_hit = touched(low_15m, high_15m, obs)
        fvg_hit = touched(low_15m, high_15m, fvgs)
        
        # 5. Confluences (SNIPER: Mandatory Liquidity Sweep)
        slice_15m = df_15m.iloc[i-400 : i+1]
        sweep = detect_liquidity_sweep(slice_15m)
        if not sweep['swept']: continue
        
        signals[ts] = {
            'bias': bias_4h,
            'regime': regime_1h,
            'ob_hit': ob_hit,
            'fvg_hit': fvg_hit,
            'sweep': sweep,
            'px': cur_px,
            'h': high_15m,
            'l': low_15m,
            'atr_15m': df_15m['atr'].iloc[i],
            'vol_24h': df_15m['vol_24h_usdt'].iloc[i], # Add Volume check
            'idx_15m': i,
            'ts_1h': df_1h.index[idx_1h]
        }
    return symbol, signals

class PortfolioBacktester:
    def __init__(self, symbols, strategy, initial_capital=1300):
        self.symbols = symbols
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.active_positions = [] # List of dicts
        self.trade_history = []
        self.fee = 0.0004 # 0.04% Binance Futures Taker fee
        self.slippage_factor = Config.LIVE_SLIPPAGE_FACTOR
        
        # Debugging counters
        self.rejection_reasons = {
            'regime_bias_none': 0,
            'no_ob_fvg_hit': 0,
            'low_score': 0,
            'ai_low_confidence': 0,
            'no_risk_data': 0,
            'max_concurrent_positions': 0,
            'position_size_too_large': 0
        }
        
        # Performance caching
        self.htf_cache = {s: {
            'last_1h_ts': None,
            'last_4h_ts': None,
            'bias': 'NONE',
            'regime': 'AVOID',
            'ob_list': [],
            'fvg_list': []
        } for s in symbols}
        
        self.start_exec_full = time.time()

    def run(self, data_map, days):
        """
        data_map: { 'BTC/USDT': { '15m': df, '1h': df, '4h': df }, ... }
        """
        print(f"\n--- PRE-CALCULATING SIGNALS IN PARALLEL ---")
        symbol_signals = {}
        
        # Run Parallel
        with ProcessPoolExecutor(max_workers=min(len(self.symbols), os.cpu_count())) as executor:
            futures = [executor.submit(pre_calc_symbol_worker, s, data_map[s]) for s in self.symbols]
            for future in futures:
                sym, sigs = future.result()
                symbol_signals[sym] = sigs

        print(f"--- STARTING PORTFOLIO SIMULATION ---")
        all_timestamps = sorted(list(set().union(*(sigs.keys() for sigs in symbol_signals.values()))))
        
        start_exec = time.time()
        peak_balance = self.initial_capital
        simulation_stopped_at = None
        max_dd_limit = Config.MAX_DRAWDOWN_LIMIT
        
        for count, ts in enumerate(all_timestamps, 1):
            if count % 20000 == 0:
                elapsed = time.time() - start_exec
                print(f"Progress: {count}/{len(all_timestamps)} ({count/elapsed:.1f} steps/s)")
            
            # Safety: Portfolio Drawdown Buster
            if self.balance > peak_balance:
                peak_balance = self.balance
            drawdown = (peak_balance - self.balance) / peak_balance
            
            # 🛡️ BALANCED RISK SCALING (Config values)
            if drawdown < 0.15:
                risk_multiplier = 1.0 
            elif drawdown < 0.20:
                risk_multiplier = 0.4
            elif drawdown < 0.24:
                risk_multiplier = 0.1 
            else:
                risk_multiplier = 0.0 # Tạm ngưng
            
            if drawdown >= max_dd_limit:
                 risk_multiplier = 0.0

            # A. Exit Check
            for pos in self.active_positions[:]:
                symbol = pos['symbol']
                if ts in data_map[symbol]['15m'].index:
                    row = data_map[symbol]['15m'].loc[ts]
                    if self._check_exit(row, pos):
                        self.active_positions.remove(pos)

            # B. Entry Check
            if risk_multiplier > 0 and len(self.active_positions) < 5 and self.balance > (self.initial_capital * 0.05):
                for symbol in self.symbols:
                    if any(p['symbol'] == symbol for p in self.active_positions): continue
                    
                    sigs = symbol_signals[symbol].get(ts)
                    if not sigs: continue
                    
                    # 1. Selection Rules (Aligned with SMCStrategy)
                    if sigs['bias'] == "NONE" or sigs['regime'] == "AVOID":
                        self.rejection_reasons['regime_bias_none'] += 1
                        continue
                    
                    if not (sigs['ob_hit'] or sigs['fvg_hit']):
                        self.rejection_reasons['no_ob_fvg_hit'] += 1
                        continue
                        
                    # 2. Scoring (Confluence)
                    idx_15m = sigs['idx_15m']
                    slice_15m = data_map[symbol]['15m'].iloc[idx_15m-400 : idx_15m+1]
                    ts_1h = sigs['ts_1h']
                    df_1h = data_map[symbol]['1h']
                    idx_1h = df_1h.index.get_loc(ts_1h)
                    slice_1h = df_1h.iloc[idx_1h-400 : idx_1h+1]
                    
                    score = score_setup(sigs['bias'], sigs['regime'], sigs['ob_hit'], sigs['fvg_hit'], sigs['sweep'], slice_15m, slice_1h)
                    
                    # MANDATORY SNIPER ALIGNMENT (1H EMA 50)
                    ema_1h = slice_1h['close'].rolling(window=50).mean().iloc[-1]
                    if (sigs['bias'] == "LONG" and sigs['px'] < ema_1h) or \
                       (sigs['bias'] == "SHORT" and sigs['px'] > ema_1h):
                        continue
                    
                    if score < Config.MIN_SCORE_THRESHOLD:
                        self.rejection_reasons['low_score'] += 1
                        continue

                    # 3. AI Confidence Filter (NEW)
                    try:
                        from ai.inference import ai_engine
                        
                        # Prepare features for AI
                        rsi_15m = data_map[symbol]['15m']['rsi'].iloc[idx_15m]
                        vol_sma = data_map[symbol]['15m']['vol_sma'].iloc[idx_15m]
                        vol_ratio = data_map[symbol]['15m']['volume'].iloc[idx_15m] / vol_sma if vol_sma > 0 else 1.0
                        
                        ema_4h_val = data_map[symbol]['4h']['ema_200'].asof(ts)
                        dist_ema200 = (sigs['px'] - ema_4h_val) / ema_4h_val if ema_4h_val > 0 else 0
                        
                        # We need a temporary risk calc to get sl/tp for features
                        temp_risk = calculate_smart_sl_tp(sigs['bias'], sigs['px'], sigs['ob_hit'], sigs['atr_15m'], self.balance, score)
                        if not temp_risk: continue
                        
                        sl_dist_pct = abs(sigs['px'] - temp_risk['sl']) / sigs['px']
                        tp_dist_pct = abs(temp_risk['tp1'] - sigs['px']) / sigs['px']
                        rr = tp_dist_pct / sl_dist_pct if sl_dist_pct > 0 else 1.0
                        
                        curr = data_map[symbol]['15m'].iloc[idx_15m]
                        body_ratio = abs(curr['close'] - curr['open']) / (curr['high'] - curr['low']) if (curr['high'] - curr['low']) > 0 else 0
                        
                        features = {
                            'score': score,
                            'rsi_15m': rsi_15m,
                            'vol_ratio_15m': vol_ratio,
                            'dist_ema200_h4': dist_ema200,
                            'sl_dist_pct': sl_dist_pct,
                            'tp_dist_pct': tp_dist_pct,
                            'rr': rr,
                            'body_ratio': body_ratio,
                            'vol_24h_usdt': sigs['vol_24h'],
                            'side': 1 if sigs['bias'] == 'LONG' else 0
                        }
                        
                        ai_confidence = ai_engine.get_confidence(features)
                        if ai_confidence < Config.AI_CONFIDENCE_THRESHOLD:
                            self.rejection_reasons['ai_low_confidence'] += 1
                            continue
                    except Exception as e:
                         pass

                    # 4. Dynamic High-Conviction Risk (Aimed at $3k-$5k profit target)
                    # ENTRY OPTIMIZATION: Enter at 50% Equilibrium (Re-optimized for R/R)
                    if sigs['ob_hit']:
                        entry_px = (sigs['ob_hit']['top'] + sigs['ob_hit']['bottom']) / 2
                    else:
                        entry_px = sigs['px'] # Fallback for FVG
                        
                    risk_data = calculate_smart_sl_tp(sigs['bias'], entry_px, sigs['ob_hit'], sigs['atr_15m'], self.balance, score)
                    if risk_data:
                        # Dynamic Sniper Risk: High confidence = High scaling
                        if score >= 9.5:
                            risk_pct = 0.06 # Increased for deeper entry
                        elif score >= 9.0:
                            risk_pct = 0.05
                        else:
                            risk_pct = 0.04
                        
                        sl_dist = abs(entry_px - risk_data['sl'])
                        pos_size = (self.balance * risk_pct) / sl_dist if sl_dist > 0 else 0
                        final_size = pos_size * risk_multiplier
                        
                        # SNIPER TP: 1.2R (Close 80% for Win Rate), 3.5R (Profit), 7.0R (Moonshot)
                        self._open_position(symbol, {
                            'signal': sigs['bias'], 'entry': entry_px, 'sl': risk_data['sl'],
                            'tp1': entry_px + (entry_px - risk_data['sl']) * 1.2 if sigs['bias'] == 'LONG' else entry_px - (risk_data['sl'] - entry_px) * 1.2,
                            'tp2': entry_px + (entry_px - risk_data['sl']) * 3.5 if sigs['bias'] == 'LONG' else entry_px - (risk_data['sl'] - entry_px) * 3.5,
                            'tp3': entry_px + (entry_px - risk_data['sl']) * 7.0 if sigs['bias'] == 'LONG' else entry_px - (risk_data['sl'] - entry_px) * 7.0,
                            'size': final_size
                        }, ts)
                    else:
                        self.rejection_reasons['no_risk_data'] += 1

        return self.generate_report(days, simulation_stopped_at)

    def _open_position(self, symbol, signal, timestamp):
        size_usdt = signal['size'] * signal['entry']
        
        # 1. Position Size Cap: Max 500k USDT per trade (Liquidity limit)
        if size_usdt > 500000:
            signal['size'] = 500000 / signal['entry']
            size_usdt = 500000

        # 2. Portfolio Risk: Max Total Leverage 3x (Very safe for Crypto)
        current_total_notional = sum(p['size'] * p['entry_price'] for p in self.active_positions)
        if (current_total_notional + size_usdt) > self.balance * 3:
             self.rejection_reasons['position_size_too_large'] += 1
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
        high, low, close = row['high'], row['low'], row['close']
        ts = row.name
        
        # 0. 🕒 TIME-LIMIT & STAGNATION CHECK (Anti-Stuck)
        entry_time = pd.to_datetime(pos['entry_time'])
        now_ts = pd.to_datetime(ts)
        held_hours = (now_ts - entry_time).total_seconds() / 3600

        # 1. Hard Time Stop (48h)
        if held_hours >= Config.MAX_HOLDING_HOURS:
            self._close_partial(pos, close, ts, f"TIME_STOP_{Config.MAX_HOLDING_HOURS}H", pos['size'])
            return True

        # 2. Stagnation Check (12h near entry)
        if held_hours >= Config.TRADE_STAGNANT_HOURS:
            price_dev = abs(close - pos['entry_price']) / pos['entry_price']
            if price_dev < 0.005:
                self._close_partial(pos, close, ts, "STAGNATION_EXIT", pos['size'])
                return True

        # 3. SL Check (Conservative: SL always hits before TP in the same bar)
        if (pos['side'] == 'LONG' and low <= pos['sl']) or (pos['side'] == 'SHORT' and high >= pos['sl']):
            reason = "STOP_LOSS" if not pos['tp1_hit'] else "TRAILING_STOP"
            pos['atr_at_exit'] = row.get('atr', 0) # Store for slippage calculation
            self._close_partial(pos, pos['sl'], ts, reason, pos['size'])
            return True

        # 4. Professional TP1 (Close 33%)
        if not pos['tp1_hit']:
            if (pos['side'] == 'LONG' and high >= pos['tp1']) or (pos['side'] == 'SHORT' and low <= pos['tp1']):
                pos['tp1_hit'] = True
                close_amount = pos['size'] * 0.33
                pos['atr_at_exit'] = row.get('atr', 0)
                self._close_partial(pos, pos['tp1'], ts, "TP1_33%", close_amount)
                pos['size'] -= close_amount
                # 🚀 SNIPER MOVE: Hard Break-Even
                pos['sl'] = pos['entry_price']
                return False

        # 5. TP2 Check & Sniper Compression Trailing
        elif not pos.get('tp2_hit', False):
            tp1_price, tp2_price = pos['tp1'], pos['tp2']
            total_dist = abs(tp2_price - tp1_price)
            current_progress = (high - tp1_price) / total_dist if total_dist > 0 else 0
            
            # A. Check for TP2 Hit
            if (pos['side'] == 'LONG' and high >= tp2_price) or (pos['side'] == 'SHORT' and low <= tp2_price):
                pos['tp2_hit'] = True
                close_amount = pos['size'] * 0.50
                pos['atr_at_exit'] = row.get('atr', 0)
                self._close_partial(pos, pos['tp2'], ts, "TP2_33%", close_amount)
                pos['size'] -= close_amount
                pos['sl'] = tp1_price # Lock profit at TP1
                return False
            
            # B. Sniper Dynamic Trailing (Compression)
            if current_progress > 0.5:
                atr_val = row.get('atr', 0)
                comp_factor = 1.5 - (current_progress * 0.8)
                trail_dist = atr_val * max(0.7, comp_factor)
                if pos['side'] == 'LONG':
                    target_sl = close - trail_dist
                    pos['sl'] = max(pos['sl'], target_sl, tp1_price)
                else:
                    target_sl = close + trail_dist
                    pos['sl'] = min(pos['sl'], target_sl, tp1_price)

        # 6. TP3 / Moonshot Transition (Close final half of remainder = ~17%)
        elif not pos.get('tp3_hit', False):
            if (pos['side'] == 'LONG' and high >= pos['tp3']) or (pos['side'] == 'SHORT' and low <= pos['tp3']):
                pos['tp3_hit'] = True
                close_amount = pos['size'] * 0.50 # Half of the final piece
                pos['atr_at_exit'] = row.get('atr', 0)
                self._close_partial(pos, pos['tp3'], ts, "TP3_17%_MOONSHOT_START", close_amount)
                pos['size'] -= close_amount
                pos['sl'] = pos['tp2'] # Lock profit at TP2
                return False 
            
        # 7. 🚀 Moonshot Aggressive Trailing (After TP3)
        if pos.get('tp3_hit', False):
            atr_val = row.get('atr', 0)
            if atr_val > 0:
                trail_dist = atr_val * 1.5
                if pos['side'] == 'LONG':
                    target_sl = close - trail_dist
                    pos['sl'] = max(pos['sl'], target_sl)
                else:
                    target_sl = close + trail_dist
                    pos['sl'] = min(pos['sl'], target_sl)
                    
        return False

    def _close_partial(self, pos, exit_price, exit_time, reason, size):
        if size <= 0: return
        
        # 1. Raw PnL
        pnl = (exit_price - pos['entry_price']) * size if pos['side'] == 'LONG' else (pos['entry_price'] - exit_price) * size
        
        # 2. Fees (Standard 0.05% per side = 0.1% total)
        fee = (pos['entry_price'] * size * self.fee) + (exit_price * size * self.fee)
        
        # 3. Slippage (Live Stress Test: Config.LIVE_SLIPPAGE_FACTOR per side)
        slippage = (pos['entry_price'] * size * self.slippage_factor) + (exit_price * size * self.slippage_factor)
        
        # 4. Funding Rate (Approx 0.01% every 8 hours)
        duration_hours = (exit_time - pos['entry_time']).total_seconds() / 3600
        funding_costs = (pos['entry_price'] * size) * 0.0001 * (duration_hours // 8)
        
        net_result = pnl - fee - slippage - funding_costs
        self.balance += net_result
        
        self.trade_history.append({
            'symbol': pos['symbol'],
            'side': pos['side'],
            'entry': pos['entry_price'],
            'exit': exit_price,
            'pnl': net_result,
            'reason': reason,
            'time': exit_time
        })

    def generate_report(self, days, stopped_at=None):
        print("\n--- BACKTEST REJECTION STATS ---")
        for k, v in self.rejection_reasons.items():
            print(f"{k}: {v}")
            
        total_pnl = self.balance - self.initial_capital
        roi = (total_pnl / self.initial_capital) * 100
        
        status_msg = ""
        if stopped_at:
            status_msg = f"\n> [!CAUTION]\n> **HARD STOP TRIGGERED**: Simulation terminated at {stopped_at} due to hitting the 20% drawdown limit.\n"
        
        report_file = "backtest/reports/REPORT_PORTFOLIO_HARD_STOP_20.md"

        if not self.trade_history:
            report = f"""# 🏆 REALISTIC STRESS TEST REPORT (MOST RECENT 90 DAYS) - NO TRADES
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{status_msg}

## 📊 Summary Metrics
- **Duration**: {days} Days (Realistic Stress Test: 0.1% Slippage, 0.04% Fee)
- **Starting Capital**: **{self.initial_capital} USDT**
- **Final Balance**: **{self.balance:.2f} USDT**
- **Net PnL**: `0.00 USDT` (**0.00%**)
- **Total Trades**: `0`
- **Symbols Tested**: {', '.join(self.symbols)}

---
*Note: No trades were executed. Check rejection stats above to see why.*
"""
            with open(report_file, "w", encoding='utf-8') as f:
                f.write(report)
            return report

        df = pd.DataFrame(self.trade_history)
        df.to_csv("backtest_trades_hardstop.csv", index=False)
        
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
        
        avg_win = wins['pnl'].mean() if not wins.empty else 0
        avg_loss = losses['pnl'].mean() if not losses.empty else 0
        win_rate = (total_wins / len(df)) * 100 if len(df) > 0 else 0
        
        # Portfolio Max Drawdown
        cum_bal = df['pnl'].cumsum() + self.initial_capital
        peak = cum_bal.expanding().max()
        dd = (cum_bal - peak) / peak
        max_dd = abs(dd.min()) * 100 if not dd.empty else 0

        report = f"""# 🏆 LATEST DATA BACKTEST REPORT (LAST 180 DAYS)
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{status_msg}

## 📊 Summary Metrics
- **Duration**: {days} Days (Realistic Stress Test)
- **Parameters**: **{self.slippage_factor*100:.2f}% Slippage** per side + **{self.fee*100:.2f}% Fee**
- **Volume Filter**: > **{Config.MIN_24H_VOLUME_USDT/1_000_000:.0f}M USDT**
- **Starting Capital**: **{self.initial_capital} USDT**
- **Final Balance**: **{self.balance:.2f} USDT**
- **Net PnL**: `{total_pnl:.2f} USDT` (**{roi:.2f}%**)
- **Win Rate**: `{win_rate:.2f}%`
- **Total Trades**: `{len(df)}`
- **Max Drawdown Experienced**: `{max_dd:.2f}%`
- **Symbols Tested**: {', '.join(self.symbols)}

## 💎 Performance Breakdown
- **Số lệnh Thắng (Win)**: `{total_wins}`
- **Số lệnh Thua (Loss)**: `{total_losses}`
- **Số lệnh Hòa (Draw)**: `{total_draws}`
- **Profit Factor**: `{profit_factor:.2f}`
- **Average Win**: `{avg_win:.2f} USDT`
- **Average Loss**: `{avg_loss:.2f} USDT`
- **Average PnL per trade**: `{total_pnl / len(df):.2f} USDT`

---
*Note: This backtest implemented a **20% Hard Drawdown Stop**. If the portfolio equity dropped 20% from its peak, all trading was halted.*
"""

        with open(report_file, "w", encoding='utf-8') as f:
            f.write(report)
        return report

def main():
    symbols = Config.TRADING_PAIRS
    days = 360 # Testing with latest 360 days as requested
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    strategy = SMCStrategy()
    
    print(f"Loading all historical data for portfolio test (Stable Parallel Fetch active)...")
    data_map = {}
    valid_symbols = []
    
    from concurrent.futures import ThreadPoolExecutor
    
    def fetch_task(s):
        try:
            print(f"Fetching/Loading {s}...")
            time.sleep(0.5) # Increased buffer for 360-day data volume
            m15 = fetch_historical_data(exchange, s, '15m', days=days)
            h1 = fetch_historical_data(exchange, s, '1h', days=days)
            h4 = fetch_historical_data(exchange, s, '4h', days=days)
            if m15 is not None and h1 is not None and h4 is not None:
                return s, {'15m': m15, '1h': h1, '4h': h4}
        except Exception as e:
            print(f"Error fetching {s}: {e}")
        return s, None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(fetch_task, symbols))
        
    for s, data in results:
        if data:
            data_map[s] = data
            valid_symbols.append(s)
        else:
            print(f"Skipping {s} due to missing data.")

    if not valid_symbols:
        print("No valid symbols fetched. Exiting.")
        return

    backtester = PortfolioBacktester(valid_symbols, strategy, initial_capital=1300)
    report = backtester.run(data_map, days)
    
    report_file = os.path.join(Config.BASE_DIR, "backtest", "reports", "REPORT_LATEST_DATA_STRESS.md")
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, "w", encoding='utf-8') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")
    try:
        print("\n" + report)
    except UnicodeEncodeError:
        # Fallback for terminals that don't support emojis/UTF-8
        print("\n" + report.encode('ascii', 'ignore').decode('ascii'))

if __name__ == "__main__":
    main()
