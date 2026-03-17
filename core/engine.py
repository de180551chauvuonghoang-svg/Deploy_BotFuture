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
from ai.sentiment_engine import sentiment_engine

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
                    'sl': float(pos.get('sl') or 0),
                    'tp1': float(pos.get('tp1') or 0),
                    'tp2': float(pos.get('tp2') or 0),
                    'tp3': float(pos.get('tp3') or 0),
                    'tp3': float(pos.get('tp3') or 0),
                    'tp1_done': pos.get('tp1_done', False),
                    'tp2_done': pos.get('tp2_done', False),
                    'tp3_done': pos.get('tp3_done', False),
                    'tp1_time': pos.get('tp1_time', ""),
                    'tp2_time': pos.get('tp2_time', ""),
                    'tp3_time': pos.get('tp3_time', ""),
                    'sl_order_id': pos.get('sl_order_id', None)
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
            # Optimized: Fetch all positions and open orders once
            all_active_positions = self.exchange.fetch_positions(Config.TRADING_PAIRS)
            all_open_orders = self.exchange.fetch_open_orders()
            
            total_margin = sum(float(p.get('initialMargin', 0)) for p in all_active_positions)
            total_upnl = sum(float(p.get('unrealizedPnl', 0)) for p in all_active_positions)
            available = (equity + total_upnl) - total_margin

            # ... (emergency deleveraging code) ...
            
            # --- AI SENTIMENT SAFETY SWITCH (Phase 2) ---
            sentiment_score = sentiment_engine.fetch_global_sentiment()
            market_summary = sentiment_engine.get_market_summary()
            
            # 2. Iterate through symbols and collect scan data
            scan_results = []
            
            # GLOBAL MARGIN LIMIT & SENTIMENT CHECK
            margin_usage_ratio = total_margin / equity if equity > 0 else 1.0
            margin_safe = margin_usage_ratio < 0.70
            sentiment_safe = sentiment_score >= Config.SENTIMENT_THRESHOLD
            
            can_open_new = margin_safe and sentiment_safe
            
            # Create lookups for positions and orders using normalized symbols
            pos_map = {}
            for p in all_active_positions:
                p_norm = self.exchange._normalize_symbol(p['symbol'])
                pos_map[p_norm] = p
                
            order_map = {}
            for o in all_open_orders:
                # Only check entry orders (Limit orders), not stop losses
                if o['type'].upper() == 'LIMIT':
                    o_norm = self.exchange._normalize_symbol(o['symbol'])
                    order_map[o_norm] = o

            for symbol in Config.TRADING_PAIRS:
                symbol = symbol.strip()
                if not symbol: continue
                # Pass the pre-fetched position and order status to process_symbol
                s_norm = self.exchange._normalize_symbol(symbol)
                symbol_pos = pos_map.get(s_norm)
                has_order = s_norm in order_map
                res = self.process_symbol(symbol, equity, can_open_new, symbol_pos, has_order)
                if res:
                    scan_results.append(res)
            
            # 3. Save shared state for Dashboard sync
            self._save_scan_state(scan_results, {
                "score": sentiment_score,
                "summary": market_summary
            })
                
            logger.info("--- Cycle Complete ---")
            return True
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return True

    def _save_scan_state(self, scan_results, sentiment_data=None):
        import json
        state_file = os.path.join(Config.DATA_DIR, "market_scanner.json")
        payload = {
            "results": scan_results,
            "sentiment": sentiment_data,
            "upTime": time.time()
        }
        try:
            with open(state_file, 'w') as f:
                json.dump(payload, f, indent=2)
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

    def process_symbol(self, symbol, equity, can_open_new=True, existing_pos=None, has_order=False):
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

        # 3. Check existing positions or orders
        has_position = existing_pos is not None
        
        if not has_position and not has_order:
            if signal != 'NONE':
                if can_open_new:
                    self.open_position(symbol, signal_data)
                else:
                    logger.info(f"⏭️ Skipping {symbol} {signal} signal: Capital Preservation Mode (Margin Limit).")
        elif has_order:
            logger.info(f"⏳ {symbol} has an active limit order. Waiting for fill...")
        else:
            # 🔄 PROFESSIONAL TP/SL EXECUTION (Live/Real-time)
            pos = existing_pos
            contracts = abs(float(pos['contracts']))
            
            # If the bot was restarted, we sync the memory but we need to ensure p_info is available
            if symbol not in self.active_positions:
                 # Reconstruct p_info from the exchange data if it exists
                 self.active_positions[symbol] = {
                    'side': pos['side'].upper(),
                    'entry': float(pos['entryPrice']),
                    'entryTime': pos.get('entryTime'),
                    'sl': float(pos.get('sl') or 0),
                    'tp1': float(pos.get('tp1') or 0),
                    'tp2': float(pos.get('tp2') or 0),
                    'tp3': float(pos.get('tp3') or 0),
                    'tp1_done': pos.get('tp1_done', False),
                    'tp2_done': pos.get('tp2_done', False),
                    'tp3_done': pos.get('tp3_done', False),
                    'tp1_time': pos.get('tp1_time', ""),
                    'tp2_time': pos.get('tp2_time', ""),
                    'tp3_time': pos.get('tp3_time', ""),
                    'sl_order_id': pos.get('sl_order_id', None)
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
            # Always calculate ATR for active position management, regardless of signal
            import pandas_ta as ta
            atr_15m_all = ta.atr(df_15m['high'], df_15m['low'], df_15m['close'])
            atr_val = atr_15m_all.iloc[-1] if atr_15m_all is not None else 0
            
            if atr_val > 0:
                new_sl_unrounded = update_dynamic_exit(
                    cur_price, p_info['entry'], p_info['sl'], 
                    side, atr_val, p_info
                )
                new_sl = self.exchange.price_to_precision(symbol, new_sl_unrounded)
                
                if new_sl != p_info['sl']:
                    old_sl = p_info['sl']
                    p_info['sl'] = new_sl
                    logger.info(f"🛡️ DYNAMIC SL UPDATE: {symbol} Moved from {old_sl:.4f} to {new_sl:.4f}")
                    
                    # 🚀 NEW HARD STOP LOGIC: Cancel old SL order, place new one
                    if p_info.get('sl_order_id'):
                         try: self.exchange.cancel_order(symbol, p_info['sl_order_id'])
                         except: pass
                    
                    sl_side = 'sell' if side == 'LONG' else 'buy'
                    sl_order = self.exchange.place_stop_order(symbol, sl_side, contracts, new_sl)
                    
                    sl_order_id = sl_order['id'] if sl_order else None
                    p_info['sl_order_id'] = sl_order_id
                    
                    self.exchange.update_position_metadata(symbol, {'sl': new_sl, 'sl_order_id': sl_order_id})
            
            # A. STOP LOSS CHECK
            # We still keep the soft check as a fallback (in case exchange order failed or for dry run simulation)
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
                    
                    # Precision and Notional Safeguards
                    # Bitcoin testnet often requires $100 notional
                    min_notional = 100.0 if Config.USE_TESTNET else 10.0
                    notional = close_amt * cur_price
                    
                    if notional >= min_notional: 
                        logger.info(f"SMC: TP1 Hit for {symbol} at {cur_price}! Closing 33% ({close_amt:.4f})")
                        self.exchange.create_order(symbol, 'sell' if side == 'LONG' else 'buy', close_amt)
                    else:
                        logger.warning(f"SMC: TP1 Hit for {symbol} but partial close skipped (Size {close_amt:.4f} or Notional {notional:.2f} too small for Exchange).")
                    now_str = pd.Timestamp.now().strftime('%H:%M:%S')
                    tp1_usd = (cur_price - p_info['entry']) * close_amt if side == 'LONG' else (p_info['entry'] - cur_price) * close_amt
                    p_info['tp1_done'] = True
                    p_info['tp1_time'] = now_str
                    p_info['tp1_usd'] = round(tp1_usd, 2)
                    p_info['realizedPnl'] = float(p_info.get('realizedPnl', 0)) + tp1_usd
                    
                    # 🚀 DECISIVE MOVE: Force SL to Entry Price (Hard BE) IMMEDIATELY
                    # Use exchange precision
                    new_sl = self.exchange.price_to_precision(symbol, p_info['entry'])
                    p_info['sl'] = new_sl
                    
                    # 🛡️ Update exchange stop order immediately
                    if p_info.get('sl_order_id'):
                        try: self.exchange.cancel_order(symbol, p_info['sl_order_id'])
                        except: pass
                    
                    sl_side = 'sell' if side == 'LONG' else 'buy'
                    remaining_contracts = contracts - close_amt
                    sl_order = self.exchange.place_stop_order(symbol, sl_side, remaining_contracts, new_sl)
                    p_info['sl_order_id'] = sl_order['id'] if sl_order else None
                    
                    p_info['contracts'] = contracts - close_amt
                    
                    # Persist all changes to metadata
                    self.exchange.update_position_metadata(symbol, {
                        'tp1_done': True, 
                        'tp1_time': now_str,
                        'tp1_usd': p_info['tp1_usd'],
                        'realizedPnl': p_info['realizedPnl'],
                        'contracts': p_info['contracts'],
                        'sl': new_sl,
                        'sl_order_id': p_info['sl_order_id']
                    })
                    
                    logger.info(f"SMC: Moved SL to Hard Breakeven ({new_sl:.4f})")
                    from utils.notifications import notify_trade_closed
                    notify_trade_closed(symbol, 0, f"TP1 Reached for {symbol} at {now_str} (+{tp1_usd:.2f} USDT) - HARD BE ACTIVE")
                    return None

            # C. PARTIAL TP2 (33%)
            if p_info.get('tp1_done') and not p_info.get('tp2_done'):
                is_tp2 = (side == 'LONG' and cur_price >= p_info['tp2']) or \
                         (side == 'SHORT' and cur_price <= p_info['tp2'])
                if is_tp2:
                    close_amt = contracts * 0.50 
                    min_notional = 100.0 if Config.USE_TESTNET else 10.0
                    notional = close_amt * cur_price
                    if notional >= min_notional:
                        logger.info(f"SMC: TP2 Hit for {symbol} at {cur_price}! Closing 50% ({close_amt:.4f})")
                        self.exchange.create_order(symbol, 'sell' if side == 'LONG' else 'buy', close_amt)
                    else:
                        logger.warning(f"SMC: TP2 Hit for {symbol} but partial close skipped (Size {close_amt:.4f} too small).")
                    now_str = pd.Timestamp.now().strftime('%H:%M:%S')
                    tp2_usd = (cur_price - p_info['entry']) * close_amt if side == 'LONG' else (p_info['entry'] - cur_price) * close_amt
                    p_info['tp2_done'] = True
                    p_info['tp2_time'] = now_str
                    p_info['tp2_usd'] = round(tp2_usd, 2)
                    p_info['realizedPnl'] = float(p_info.get('realizedPnl', 0)) + tp2_usd
                    
                    # 🚀 SNIPER LOCK: Move SL to TP1 Price immediately
                    new_sl = self.exchange.price_to_precision(symbol, p_info['tp1'])
                    p_info['sl'] = new_sl
                    
                    # 🛡️ Update exchange stop order immediately
                    if p_info.get('sl_order_id'):
                        try: self.exchange.cancel_order(symbol, p_info['sl_order_id'])
                        except: pass
                    
                    sl_side = 'sell' if side == 'LONG' else 'buy'
                    remaining_contracts = contracts - close_amt
                    sl_order = self.exchange.place_stop_order(symbol, sl_side, remaining_contracts, new_sl)
                    p_info['sl_order_id'] = sl_order['id'] if sl_order else None
                    
                    p_info['contracts'] = contracts - close_amt
                    
                    # Persist metadata change
                    self.exchange.update_position_metadata(symbol, {
                        'tp2_done': True, 
                        'tp2_time': now_str,
                        'tp2_usd': p_info['tp2_usd'],
                        'realizedPnl': p_info['realizedPnl'],
                        'contracts': p_info['contracts'],
                        'sl': new_sl,
                        'sl_order_id': p_info['sl_order_id']
                    })
                    
                    logger.info(f"SMC: Locked Profit at TP1 ({new_sl:.4f})")
                    from utils.notifications import notify_trade_closed
                    notify_trade_closed(symbol, 0, f"TP2 Partial Closed (50% of rem) at {now_str} (+{tp2_usd:.2f} USDT) - Profit Locked at TP1")
                    return None

            # D. PARTIAL TP3 (17% - Total Chốt 83%)
            if p_info.get('tp2_done') and not p_info.get('tp3_done'):
                is_tp3 = (side == 'LONG' and cur_price >= p_info['tp3']) or \
                         (side == 'SHORT' and cur_price <= p_info['tp3'])
                if is_tp3:
                    # Close 50% of REMAINDER (Total closed: 33% + 33.5% + 16.5% = 83%)
                    # Leaving ~17% as a "Moonshot Runner"
                    close_amt = contracts * 0.50 
                    notional = close_amt * cur_price
                    if notional >= 10.0 and close_amt >= 0.001:
                        logger.info(f"SMC: TP3 Hit for {symbol}! Closing part of remainder. Leaving 17% as Moonshot Runner.")
                        self.exchange.create_order(symbol, 'sell' if side == 'LONG' else 'buy', close_amt)
                    else:
                        logger.warning(f"SMC: TP3 Hit for {symbol} but partial close skipped (Size too small).")
                    
                    now_str = pd.Timestamp.now().strftime('%H:%M:%S')
                    tp3_usd = (cur_price - p_info['entry']) * close_amt if side == 'LONG' else (p_info['entry'] - cur_price) * close_amt
                    p_info['tp3_done'] = True
                    p_info['tp3_time'] = now_str
                    p_info['tp3_usd'] = round(tp3_usd, 2)
                    p_info['realizedPnl'] = float(p_info.get('realizedPnl', 0)) + tp3_usd
                    
                    # 🚀 MOONSHOT LOCK: Move SL to TP2 Price and activate Super Tight Trail
                    new_sl = p_info['tp2']
                    p_info['sl'] = new_sl
                    
                    # 🛡️ Update exchange stop order
                    if p_info.get('sl_order_id'):
                        try: self.exchange.cancel_order(symbol, p_info['sl_order_id'])
                        except: pass
                        
                    sl_side = 'sell' if side == 'LONG' else 'buy'
                    remaining_contracts = contracts - close_amt 
                    sl_order = self.exchange.place_stop_order(symbol, sl_side, remaining_contracts, new_sl)
                    p_info['sl_order_id'] = sl_order['id'] if sl_order else None
                    
                    p_info['contracts'] = contracts - close_amt
                    
                    self.exchange.update_position_metadata(symbol, {
                        'tp3_done': True, 
                        'tp3_time': now_str,
                        'tp3_usd': p_info['tp3_usd'],
                        'realizedPnl': p_info['realizedPnl'],
                        'contracts': p_info['contracts'],
                        'sl': new_sl,
                        'sl_order_id': p_info['sl_order_id']
                    })
                    
                    logger.info(f"SMC: Moonshot Activated! SL at TP2 ({new_sl:.4f})")
                    from utils.notifications import notify_trade_closed
                    notify_trade_closed(symbol, 0, f"TP3 Semi-Closed at {now_str} (+{tp3_usd:.2f} USDT) - MOONSHOT RUNNER (17%) ACTIVE 🚀")
                    return None

            # E. REVERSAL CHECK & AI SHIELD
            should_exit, exit_reason = self.strategy.check_early_exit(symbol, side_actual, df_15m, df_1h, p_info)
            if should_exit:
                self.close_position(symbol, exit_reason)
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

        # Round values for exchange
        price = self.exchange.price_to_precision(symbol, price)
        amount = self.exchange.amount_to_precision(symbol, amount)
        sl = self.exchange.price_to_precision(symbol, signal_data['sl'])
        tp1 = self.exchange.price_to_precision(symbol, signal_data['tp1'])
        tp2 = self.exchange.price_to_precision(symbol, signal_data['tp2'])
        tp3 = self.exchange.price_to_precision(symbol, signal_data.get('tp3'))

        self.exchange.set_leverage(symbol, Config.LEVERAGE)
        
        logger.info(f"🔥 ENTRY KÍCH HOẠT: {symbol} {signal_data['signal']} | Reason: {signal_data['reason']}")
        order = self.exchange.create_order(
            symbol, side_cmd, amount, 
            type='limit', price=price,
            sl=sl, 
            tp1=tp1, 
            tp2=tp2,
            tp3=tp3
        )
        
        if order:
            self.active_positions[symbol] = {
                'side': signal_data['signal'],
                'entry': price,
                'sl': sl,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'ob_top': signal_data.get('confluences', {}).get('ob_hit_top'), 
                'ob_bottom': signal_data.get('confluences', {}).get('ob_hit_bottom'),
                'entryTime': pd.Timestamp.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            }
            logger.info(f"✅ ĐÃ VÀO LỆNH: {symbol} @ {price} | SL: {sl} | TP1: {tp1}")
            
            # 🚀 Save metadata immediately to ensure it persists across modes
            self.exchange.update_position_metadata(symbol, self.active_positions[symbol])
            
            # 🚀 NEW HARD STOP LOGIC: Place initial hard SL order
            sl_side = 'sell' if side_cmd == 'buy' else 'buy'
            sl_order = self.exchange.place_stop_order(symbol, sl_side, amount, sl)
            sl_order_id = sl_order['id'] if sl_order else None
            self.active_positions[symbol]['sl_order_id'] = sl_order_id
            self.exchange.update_position_metadata(symbol, {'sl_order_id': sl_order_id})
            
            notify_trade_opened(symbol, side_cmd, price, amount, sl, tp1)
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
            
            # Fetch current ticker for record
            ticker = self.exchange.fetch_ticker(symbol)
            exit_price = ticker['last'] if ticker else pos.get('markPrice', 0)
            
            # Calculate final PnL
            entry_px = float(pos.get('entryPrice', 0))
            side = 'long' if side_cmd == 'sell' else 'short'
            
            pnl_final_lot = (exit_price - entry_px) * amount if side == 'long' else (entry_px - exit_price) * amount
            total_realized_pnl = float(pos.get('realizedPnl', 0)) + pnl_final_lot
            margin = float(pos.get('initialMargin', 1))
            roi = (total_realized_pnl / margin * 100) if margin > 0 else 0
            
            # 🚀 GHI LỊCH SỬ GIAO DỊCH (Excel reporting fix)
            self.exchange._record_trade(
                symbol, side, entry_px, exit_price, 
                amount, # Total amount should be total? 
                # Actually amount here is current amount. But record_trade expects original metadata if any.
                # Let's just record this exit.
                total_realized_pnl, roi, pos.get('entryTime'), pos
            )
            
            # 🚀 Cancel SL order if it exists
            if symbol in self.active_positions and self.active_positions[symbol].get('sl_order_id'):
                self.exchange.cancel_order(symbol, self.active_positions[symbol]['sl_order_id'])
            
            # 🔧 Update metadata with reason before it gets deleted from active
            self.exchange.update_position_metadata(symbol, {'close_reason': reason})
            
            if symbol in self.active_positions:
                del self.active_positions[symbol]
            
            # 🔧 SYNC FIX: Update dry-run positions file for dashboard
            all_positions = self.exchange._load_dry_positions()
            updated_positions = [p for p in all_positions if p['symbol'] != symbol]
            self.exchange._save_dry_positions(updated_positions)
            
            notify_trade_closed(symbol, total_realized_pnl, reason)
            logger.info("📡 Đã gởi thông báo tới Discord.")

    def start(self):
        logger.info("Professional SMC Bot Active...")
        logger.info("Cycle Interval: 30 seconds (Optimized for Multi-Symbol Scanning)")
        while True:
            self.run_cycle()
            time.sleep(30) # Increased to 30s to avoid Binance rate limits with many symbols
