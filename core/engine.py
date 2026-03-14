import time
import os
import json
import pandas as pd
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
        self._sync_active_positions()

    def _sync_active_positions(self):
        """Re-sync internal memory with persistent storage on startup."""
        try:
            positions = self.exchange.fetch_positions(Config.TRADING_PAIRS)
            for pos in positions:
                sym = pos['symbol']
                self.active_positions[sym] = {
                    'side': pos['side'].upper(),
                    'entry': float(pos['entryPrice']),
                    'entryTime': pos.get('entryTime'), # Add entryTime
                    'sl': float(pos.get('sl', 0)),
                    'tp1': float(pos.get('tp1', 0)),
                    'tp2': float(pos.get('tp2', 0)),
                    'tp3': float(pos.get('tp3', 0)),
                    'tp1_done': pos.get('tp1_done', False),
                    'tp2_done': pos.get('tp2_done', False)
                }
            if self.active_positions:
                logger.info(f"🔄 Đã đồng bộ {len(self.active_positions)} vị thế đang chạy từ bộ nhớ.")
        except Exception as e:
            logger.error(f"Lỗi khi đồng bộ vị thế: {e}")

    def run_cycle(self):
        try:
            logger.info("--- Starting Professional SMC Cycle ---")
            
            # 1. Update balance & Check Global Portfolio Health
            equity = self.exchange.get_balance()
            positions = self.exchange.fetch_positions(Config.TRADING_PAIRS)
            total_margin = sum(float(p.get('initialMargin', 0)) for p in positions)
            total_upnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions)
            available = (equity + total_upnl) - total_margin

            # 🔥 ACTIVE RISK: Emergency Auto-Deleveraging
            # If available balance is negative at all, close the weakest position to free up margin
            if available < 0 and len(positions) > 0:
                logger.warning(f"🚨 PORTFOLIO OVER-LIMIT: Available balance {available:.2f} is negative. Fixing Portfolio Health...")
                # Sort by profit (PnL) and close the one with lowest PnL to free up capital
                sorted_pos = sorted(positions, key=lambda x: float(x.get('unrealizedPnl', 0)))
                target_to_close = sorted_pos[0]['symbol']
                self.close_position(target_to_close, "Capital Preservation (Auto-Deleveraging)")
                # Refresh state after close
                equity = self.exchange.get_balance()
                positions = self.exchange.fetch_positions(Config.TRADING_PAIRS)
                total_margin = sum(float(p.get('initialMargin', 0)) for p in positions)
            
            # 2. Iterate through symbols and collect scan data
            scan_results = []
            
            # GLOBAL MARGIN LIMIT: Don't open new trades if more than 70% of wallet is already locked in margin
            margin_usage_ratio = total_margin / equity if equity > 0 else 1.0
            can_open_new = margin_usage_ratio < 0.70
            
            if not can_open_new:
                 logger.info(f"🛡️ Margin limit reached ({margin_usage_ratio:.1%}). Scanning in View-Only mode.")

            for symbol in Config.TRADING_PAIRS:
                res = self.process_symbol(symbol, equity, can_open_new)
                if res:
                    scan_results.append(res)
            
            # 3. Save shared state for Dashboard sync
            self._save_scan_state(scan_results)
                
            logger.info("--- Cycle Complete ---")
            return True
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return True

    def _save_scan_state(self, scan_results):
        import json
        state_file = os.path.join(Config.DATA_DIR, "market_scanner.json")
        try:
            with open(state_file, 'w') as f:
                json.dump(scan_results, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving scanner state: {e}")

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

    def process_symbol(self, symbol, equity, can_open_new=True):
        # 1. Fetch Multi-Timeframe Data
        data = self._fetch_multi_tf_data(symbol)
        if not data: return
        df_15m, df_1h, df_4h = data

        # 2. Generate Signal
        signal_data = self.strategy.generate_signal(symbol, self.exchange, df_4h, df_1h, df_15m, balance=equity)
        if not signal_data: return
        
        signal = signal_data.get('signal', 'NONE')
        score = signal_data.get('confluences', {}).get('score', 0)
        
        # Verbose scanning log to terminal
        logger.info(f"Scanning {symbol}: Signal={signal} | Score={score:.1f}")

        # 3. Check existing positions
        positions = self.exchange.fetch_positions([symbol])
        has_position = len(positions) > 0
        
        if not has_position:
            if signal != 'NONE':
                if can_open_new:
                    self.open_position(symbol, signal_data)
                else:
                    logger.info(f"⏭️ Skipping {symbol} {signal} signal: Capital Preservation Mode (Margin Limit).")
        else:
            # 🔄 PROFESSIONAL TP/SL EXECUTION (Live/Real-time)
            pos = positions[0]
            contracts = abs(float(pos['contracts']))
            
            # If the bot was restarted, we sync the memory but we need to ensure p_info is available
            if symbol not in self.active_positions:
                 # Reconstruct p_info from the exchange data if it exists
                 self.active_positions[symbol] = {
                    'side': pos['side'].upper(),
                    'entry': float(pos['entryPrice']),
                    'entryTime': pos.get('entryTime'),
                    'sl': float(pos.get('sl', 0)),
                    'tp1': float(pos.get('tp1', 0)),
                    'tp2': float(pos.get('tp2', 0)),
                    'tp3': float(pos.get('tp3', 0)),
                    'tp1_done': pos.get('tp1_done', False),
                    'tp2_done': pos.get('tp2_done', False)
                 }

            p_info = self.active_positions[symbol]
            
            # 🕒 TIME-LIMIT & STAGNATION CHECK (Anti-Stuck)
            if p_info.get('entryTime'):
                try:
                    entry_dt = pd.to_datetime(p_info['entryTime'])
                    now_dt = pd.Timestamp.utcnow()
                    held_hours = (now_dt - entry_dt).total_seconds() / 3600
                    
                    # 1. Hard Time Stop (48h)
                    if held_hours >= Config.MAX_HOLDING_HOURS:
                        self.close_position(symbol, f"🕒 TIME-STOP: Held for {held_hours:.1f}h (Limit: {Config.MAX_HOLDING_HOURS}h)")
                        return None
                    
                    # 2. Stagnation Check (12h near entry)
                    if held_hours >= Config.TRADE_STAGNANT_HOURS:
                        ticker = self.exchange.fetch_ticker(symbol)
                        if ticker:
                            curr_px = ticker['last']
                            price_dev = abs(curr_px - p_info['entry']) / p_info['entry']
                            if price_dev < 0.005: # Stays within +/- 0.5%
                                self.close_position(symbol, f"💤 STAGNATION: Inactive for {held_hours:.1f}h (Exit near Entry)")
                                return None
                except Exception as e:
                    logger.error(f"Error checking time-limits: {e}")
            
            # Use current ticker price for most responsive TP/SL check (Live)
            ticker = self.exchange.fetch_ticker(symbol)
            if not ticker: return
            cur_price = ticker['last']
            side = p_info['side'] # 'LONG' or 'SHORT'

            # 🛡️ DYNAMIC TRAILING & BREAKEVEN
            # Moves SL to Entry after TP1 or trails after +2.5R profit
            atr_val = signal_data.get('atr', 0)
            if atr_val > 0:
                new_sl = update_dynamic_exit(
                    cur_price, p_info['entry'], p_info['sl'], 
                    side, atr_val, p_info.get('tp1_done', False)
                )
                if new_sl != p_info['sl']:
                    p_info['sl'] = new_sl
                    self.exchange.update_position_metadata(symbol, {'sl': new_sl})
                    logger.info(f"🛡️ DYNAMIC SL UPDATE: {symbol} Moved to {new_sl:.4f}")
            
            # A. STOP LOSS CHECK
            is_sl = (side == 'LONG' and cur_price <= p_info['sl']) or \
                    (side == 'SHORT' and cur_price >= p_info['sl'])
            if is_sl:
                self.close_position(symbol, f"SMC Stop Loss Hit @ {p_info['sl']:.4f}")
                return None 

            # B. PARTIAL TP1 (33%)
            if not p_info.get('tp1_done'):
                is_tp1 = (side == 'LONG' and cur_price >= p_info['tp1']) or \
                         (side == 'SHORT' and cur_price <= p_info['tp1'])
                if is_tp1:
                    close_amt = contracts * 0.33
                    logger.info(f"SMC: TP1 Hit for {symbol} at {cur_price}! Closing 33% ({close_amt:.2f})")
                    self.exchange.create_order(symbol, 'sell' if side == 'LONG' else 'buy', close_amt)
                    p_info['tp1_done'] = True
                    p_info['sl'] = p_info['entry'] # Move to Break-even
                    
                    # Persist metadata change
                    self.exchange.update_position_metadata(symbol, {'tp1_done': True, 'sl': p_info['sl']})
                    
                    logger.info(f"SMC: Moved SL to Breakeven ({p_info['sl']:.4f})")
                    notify_trade_closed(symbol, 0, f"TP1 Partial Closed (33%) - Moved to BE")
                    return None

            # C. PARTIAL TP2 (33%)
            if p_info.get('tp1_done') and not p_info.get('tp2_done'):
                is_tp2 = (side == 'LONG' and cur_price >= p_info['tp2']) or \
                         (side == 'SHORT' and cur_price <= p_info['tp2'])
                if is_tp2:
                    close_amt = contracts * 0.50 
                    logger.info(f"SMC: TP2 Hit for {symbol} at {cur_price}! Closing 33% ({close_amt:.2f})")
                    self.exchange.create_order(symbol, 'sell' if side == 'LONG' else 'buy', close_amt)
                    p_info['tp2_done'] = True
                    p_info['sl'] = p_info['tp1'] # Lock profit at TP1
                    
                    # Persist metadata change
                    self.exchange.update_position_metadata(symbol, {'tp2_done': True, 'sl': p_info['sl']})
                    
                    logger.info(f"SMC: Locked Profit at TP1 ({p_info['sl']:.4f})")
                    notify_trade_closed(symbol, 0, f"TP2 Partial Closed (33%) - Locked Profit at TP1")
                    return None

            # D. FULL TP3 (Final Target)
            if p_info.get('tp2_done'):
                is_tp3 = (side == 'LONG' and cur_price >= p_info.get('tp3', p_info['tp2'] * 1.05)) or \
                         (side == 'SHORT' and cur_price <= p_info.get('tp3', p_info['tp2'] * 0.95))
                if is_tp3:
                    self.close_position(symbol, f"SMC Final TP3 Target Hit")
                    return None

            # E. REVERSAL CHECK
            side_actual = 'LONG' if float(pos['contracts']) > 0 else 'SHORT'
            if (side_actual == 'LONG' and signal == 'SHORT') or (side_actual == 'SHORT' and signal == 'LONG'):
                self.close_position(symbol, "SMC Signal Reversal")
                return None

        # 4. Return for state sync
        return {
            "Symbol": symbol,
            "Signal": signal,
            "Price": signal_data.get('entry', 0.0),
            "Score": score,
            "Regime": signal_data.get('confluences', {}).get('regime', 'N/A'),
            "Reason": signal_data.get('reason', 'N/A')
        }

    def open_position(self, symbol, signal_data):
        side_cmd = 'buy' if signal_data['signal'] == 'LONG' else 'sell'
        price = signal_data['entry']
        amount = signal_data['size']
        
        if amount <= 0: return

        self.exchange.set_leverage(symbol, Config.LEVERAGE)
        
        logger.info(f"🔥 ENTRY KÍCH HOẠT: {symbol} {signal_data['signal']} | Reason: {signal_data['reason']}")
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
                'tp2': signal_data['tp2'],
                'tp3': signal_data.get('tp3')
            }
            logger.info(f"✅ ĐÃ VÀO LỆNH: {symbol} @ {price} | SL: {signal_data['sl']:.2f} | TP1: {signal_data['tp1']:.2f}")
            notify_trade_opened(symbol, side_cmd, price, amount, signal_data['sl'], signal_data['tp1'])
            logger.info("📡 Đã gởi thông báo tới Discord.")

    def close_position(self, symbol, reason):
        positions = self.exchange.fetch_positions([symbol])
        if not positions: return
        
        pos = positions[0]
        side_cmd = 'sell' if float(pos['contracts']) > 0 else 'buy'
        amount = abs(float(pos['contracts']))
        
        order = self.exchange.create_order(symbol, side_cmd, amount)
        if order:
            logger.info(f"🏁 TẤT TOÁN LỆNH: {symbol} - {reason}")
            if symbol in self.active_positions: del self.active_positions[symbol]
            
            # 🔧 SYNC FIX: Update dry-run positions file for dashboard
            all_positions = self.exchange._load_dry_positions()
            updated_positions = [p for p in all_positions if p['symbol'] != symbol]
            self.exchange._save_dry_positions(updated_positions)
            
            notify_trade_closed(symbol, 0, reason)
            logger.info("📡 Đã gởi thông báo tới Discord.")

    def start(self):
        logger.info("Professional SMC Bot Active...")
        while True:
            self.run_cycle()
            time.sleep(60)
