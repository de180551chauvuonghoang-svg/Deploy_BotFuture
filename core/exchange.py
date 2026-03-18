import ccxt
import ccxt.pro as ccxtpro
import time
import asyncio
import pandas as pd
import json
import os
from config.config import Config
from core.logger import logger

class ExchangeHandler:
    def __init__(self):
        exchange_id = Config.EXCHANGE
        ccxt.binance.options = {'adjustForTimeDifference': True}
        exchange_class = getattr(ccxt, exchange_id)
        
        self.dry_run_file = os.path.join(Config.DATA_DIR, "dry_run_positions.json")
        self.trade_history_file = os.path.join(Config.DATA_DIR, "trade_history.json")
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)
        
        # 🚀 WebSocket / Async Exchange Initialization
        self.ws_exchange = getattr(ccxtpro, exchange_id)({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
            }
        })
        
        # Cache for real-time data
        self.ohlcv_cache = {} # symbol -> {timeframe: df}
        self.ticker_cache = {} # symbol -> price
        self.ws_active = False
        
        # Authenticated instance (Synchronous - kept for existing logic stability)
        self.exchange = exchange_class({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
                'warnOnFetchOpenOrdersWithoutSymbol': False,
            }
        })
        
        # Public instance for OHLCV data
        self.public_exchange = exchange_class({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        
        self.dry_run = Config.PAPER_TRADING  # Default to dry run if paper trading is on
        
        if Config.PAPER_TRADING:
            # Force LOCAL DRY RUN simulation immediately
            logger.info("Running in LOCAL DRY RUN (Simulation) mode.")
            self.dry_run = True
        elif Config.USE_TESTNET:
            logger.info("🚀 KÍCH HOẠT BINANCE FUTURE TESTNET (Surgical Sign Hijack)")
            # We use standard mode but surgically hijack URLs just before signing
            self.exchange.set_sandbox_mode(False)
            self.public_exchange.set_sandbox_mode(False)
            self.ws_exchange.set_sandbox_mode(True) # 🚀 WebSocket Testnet Support
            
            def create_custom_sign(original_sign):
                def custom_sign(path, api='public', method='GET', params={}, headers=None, body=None):
                    result = original_sign(path, api, method, params, headers, body)
                    # Redirect any futures-related binance traffic to the testnet domain
                    original_url = result['url']
                    if 'binance.com' in result['url'] or 'binancefuture.com' in result['url']:
                        result['url'] = result['url'].replace('fapi.binance.com', 'testnet.binancefuture.com')
                        result['url'] = result['url'].replace('dapi.binance.com', 'testnet.binancefuture.com')
                        result['url'] = result['url'].replace('sapi.binance.com', 'testnet.binancefuture.com')
                        result['url'] = result['url'].replace('api.binance.com', 'testnet.binancefuture.com')
                    
                    return result
                return custom_sign
            
            self.exchange.sign = create_custom_sign(self.exchange.sign)
            self.public_exchange.sign = create_custom_sign(self.public_exchange.sign)
            
            self.exchange.options['adjustForTimeDifference'] = True
            self.exchange.options['recvWindow'] = 60000
            
            try:
                self.exchange.load_time_difference()
                logger.info("✅ Đã đồng bộ thời gian với Binance Testnet Server")
            except Exception as e:
                logger.warning(f"Không thể đồng bộ thời gian: {e}")
                
            self.dry_run = False
        else:
            self.dry_run = False
        
        # Load market info for limits (maxQty, precision, etc.)
        try:
            self.exchange.load_markets()
            logger.info("✅ Market limits loaded from Binance.")
        except Exception as e:
            logger.error(f"Error loading market limits: {e}")

    async def watch_ohlcv_all(self, symbols, timeframe='15m'):
        """
        Continuous WebSocket loop to watch OHLCV for multiple symbols.
        """
        self.ws_active = True
        logger.info(f"🌐 WebSocket: Starting OHLCV stream for {len(symbols)} symbols ({timeframe})")
        
        while self.ws_active:
            try:
                # 🛡️ Subscription Limit Fix: Subscribe in smaller batches if needed
                # However, with just 1 timeframe (15m), 86 symbols fits within 200.
                ohlcvs = await self.ws_exchange.watch_ohlcv_for_symbols([[s, timeframe] for s in symbols])
                
                for symbol, timeframe_data in ohlcvs.items():
                    for tf, candles in timeframe_data.items():
                        # ... (existing logging/processing) ...
                        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                        df.dropna(subset=['close'], inplace=True)
                        df.set_index('timestamp', inplace=True)
                        
                        if symbol not in self.ohlcv_cache:
                            self.ohlcv_cache[symbol] = {}
                        self.ohlcv_cache[symbol][tf] = df
                        
            except Exception as e:
                logger.error(f"WebSocket OHLCV Error ({timeframe}): {e}")
                # Exponential backoff for 1006 / Disconnects
                await asyncio.sleep(10) # Wait 10s before retrying
                try: 
                    await self.ws_exchange.close()
                    # Re-initialize or re-auth if needed
                except: pass

    async def watch_tickers(self, symbols):
        """
        Continuous WebSocket loop to watch real-time prices (tickers).
        """
        logger.info(f"🌐 WebSocket: Starting Ticker stream for {len(symbols)} symbols")
        while self.ws_active:
            try:
                tickers = await self.ws_exchange.watch_tickers(symbols)
                for symbol, ticker in tickers.items():
                    self.ticker_cache[symbol] = float(ticker['last'])
            except Exception as e:
                logger.error(f"WebSocket Ticker Error: {e}")
                await asyncio.sleep(5)

    def fetch_ohlcv(self, symbol, timeframe='15m', limit=100):
        # 🎯 High Performance: Use WebSocket Cache if available
        cache_df = self.ohlcv_cache.get(symbol, {}).get(timeframe)
        if cache_df is not None:
            # If cache has enough data, return it
            if len(cache_df) >= limit:
                return cache_df.iloc[-limit:]
            return cache_df

        # Fallback to REST if cache is empty
        retries = 3
        delay = 1 # seconds
        for i in range(retries):
            try:
                ohlcv = self.public_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                if not ohlcv:
                    return None
                    
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                # Ensure numeric types
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                df.dropna(subset=['close'], inplace=True)
                df.set_index('timestamp', inplace=True)
                return df
            except Exception as e:
                if i < retries - 1:
                    logger.warning(f"Retry {i+1}/{retries} fetching {symbol} {timeframe} due to: {e}")
                    time.sleep(delay * (i + 1))
                else:
                    logger.error(f"Final error fetching OHLCV for {symbol} after {retries} retries: {e}")
                    return None

    def get_balance(self, asset='USDT'):
        if self.dry_run:
            history = self._load_trade_history()
            total_realized_pnl = sum(float(trade.get('pnl', 0)) for trade in history)
            return Config.INITIAL_DRY_BALANCE + total_realized_pnl
        try:
            balance = self.exchange.fetch_balance()
            return balance.get('total', {}).get(asset, 0)
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 0

    def get_market_limits(self, symbol):
        """
        Retrieves market limits (maxQty, minQty, stepSize) for a specific symbol.
        """
        try:
            if not self.exchange.markets:
                self.exchange.load_markets()
            
            market = self.exchange.market(symbol)
            limits = market.get('limits', {})
            amount_limits = limits.get('amount', {})
            
            return {
                'minQty': float(amount_limits.get('min', 0)),
                'maxQty': float(amount_limits.get('max', 0)),
                'stepSize': float(market.get('precision', {}).get('amount', 0.0001))
            }
        except Exception as e:
            logger.error(f"Error fetching market limits for {symbol}: {e}")
            return {'minQty': 0, 'maxQty': 0, 'stepSize': 0.0001}

    def set_leverage(self, symbol, leverage):
        if self.dry_run:
            return
        try:
            self.exchange.set_leverage(leverage, symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
        except Exception as e:
            logger.error(f"Error setting leverage for {symbol}: {e}")

    def create_order(self, symbol, side, amount, type='market', price=None, **kwargs):
        """
        Creates an order (market or limit).
        """
        if Config.PAPER_TRADING:
            # --- DRY RUN LOGIC ---
            positions = self._load_dry_positions()
            existing = next((p for p in positions if p['symbol'] == symbol), None)
            price = self.fetch_ohlcv(symbol, '15m', limit=1)['close'].iloc[-1]
            
            if side.lower() == 'buy':
                if existing and existing['side'] == 'long':
                    logger.info(f"[DRY RUN] Position already exists for {symbol}, skipping additive order to prevent size doubling.")
                    return {'id': 'dry_run_skipped', 'status': 'ignored'}
                elif existing and existing['side'] == 'short':
                    # Close short
                    new_contracts = float(existing['contracts']) - amount
                    if new_contracts <= 0:
                        actual_close_amount = float(existing['contracts'])
                        final_pnl = (float(existing['entryPrice']) - price) * actual_close_amount
                        total_pnl = final_pnl + float(existing.get('realizedPnl', 0))
                        roi = (total_pnl / float(existing['initialMargin'])) * 100 if float(existing['initialMargin']) > 0 else 0
                        self._record_trade(symbol, 'short', existing['entryPrice'], price, actual_close_amount, total_pnl, roi, existing['entryTime'], existing)
                        positions = [p for p in positions if p['symbol'] != symbol]
                    else:
                        # Partial close - track realized PnL
                        partial_pnl = (float(existing['entryPrice']) - price) * amount
                        existing['realizedPnl'] = str(float(existing.get('realizedPnl', 0)) + partial_pnl)
                        existing['contracts'] = str(new_contracts)
                else:
                    # New Long
                    margin_required = (price * amount) / Config.LEVERAGE
                    # Check available balance
                    current_bal = self.get_balance()
                    total_margin = sum(float(p.get('initialMargin', 0)) for p in positions)
                    if (current_bal - total_margin) < margin_required:
                        logger.warning(f"[DRY RUN] Insufficient balance for {symbol}. Required: {margin_required:.2f}, Available: {current_bal - total_margin:.2f}")
                        return {'id': 'insufficient_funds', 'status': 'rejected'}

                    positions.append({
                        'symbol': symbol,
                        'side': 'long',
                        'entryPrice': str(price),
                        'entryTime': pd.Timestamp.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                        'contracts': str(amount),
                        'initialMargin': str(margin_required),
                        'leverage': str(Config.LEVERAGE),
                        'sl': kwargs.get('sl'),
                        'tp1': kwargs.get('tp1'),
                        'tp2': kwargs.get('tp2'),
                        'tp3': kwargs.get('tp3'),
                        'unrealizedPnl': '0.00',
                        'realizedPnl': '0.00'
                    })
            else: # sell
                if existing and existing['side'] == 'short':
                    logger.info(f"[DRY RUN] Position already exists for {symbol}, skipping additive order to prevent size doubling.")
                    return {'id': 'dry_run_skipped', 'status': 'ignored'}
                elif existing and existing['side'] == 'long':
                    # Close long
                    new_contracts = float(existing['contracts']) - amount
                    if new_contracts <= 0:
                        actual_close_amount = float(existing['contracts'])
                        final_pnl = (price - float(existing['entryPrice'])) * actual_close_amount
                        total_pnl = final_pnl + float(existing.get('realizedPnl', 0))
                        roi = (total_pnl / float(existing['initialMargin'])) * 100 if float(existing['initialMargin']) > 0 else 0
                        self._record_trade(symbol, 'long', existing['entryPrice'], price, actual_close_amount, total_pnl, roi, existing['entryTime'], existing)
                        positions = [p for p in positions if p['symbol'] != symbol]
                    else:
                        # Partial close - track realized PnL
                        partial_pnl = (price - float(existing['entryPrice'])) * amount
                        existing['realizedPnl'] = str(float(existing.get('realizedPnl', 0)) + partial_pnl)
                        existing['contracts'] = str(new_contracts)
                else:
                    # New Short
                    margin_required = (price * amount) / Config.LEVERAGE
                    # Check available balance
                    current_bal = self.get_balance()
                    total_margin = sum(float(p.get('initialMargin', 0)) for p in positions)
                    if (current_bal - total_margin) < margin_required:
                        logger.warning(f"[DRY RUN] Insufficient balance for {symbol}. Required: {margin_required:.2f}, Available: {current_bal - total_margin:.2f}")
                        return {'id': 'insufficient_funds', 'status': 'rejected'}

                    positions.append({
                        'symbol': symbol,
                        'side': 'short',
                        'entryPrice': str(price),
                        'entryTime': pd.Timestamp.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                        'contracts': str(amount),
                        'initialMargin': str(margin_required),
                        'leverage': str(Config.LEVERAGE),
                        'sl': kwargs.get('sl'),
                        'tp1': kwargs.get('tp1'),
                        'tp2': kwargs.get('tp2'),
                        'tp3': kwargs.get('tp3'),
                        'unrealizedPnl': '0.00',
                        'realizedPnl': '0.00'
                    })
            
            self._save_dry_positions(positions)
            return {'id': 'dry_run_id', 'status': 'closed', 'side': side, 'amount': amount}
        else:
            try:
                # Live mode
                if type.lower() == 'limit':
                    order = self.exchange.create_order(symbol, type, side, amount, price, params=kwargs)
                else:
                    order = self.exchange.create_order(symbol, type, side, amount, params=kwargs)
                
                logger.info(f"Order created: {side} {amount} {symbol} @ {type} (Price: {price})")
                
                # Fetch price for metadata if market
                ticker_price = price
                if not ticker_price:
                    ticker = self.fetch_ticker(symbol)
                    ticker_price = ticker['last'] if ticker else 0

                # 🚀 Persist metadata immediately for all modes
                # ONLY for entry orders (not partial TPs or SLs)
                is_close = kwargs.get('reduceOnly') or kwargs.get('close')
                
                if not is_close:
                    meta = {
                        'symbol': symbol,
                        'side': 'long' if side.lower() in ['buy', 'long'] else 'short',
                        'entryPrice': str(ticker_price),
                        'contracts': str(amount),
                        'sl': kwargs.get('sl'),
                        'tp1': kwargs.get('tp1'),
                        'tp2': kwargs.get('tp2'),
                        'tp3': kwargs.get('tp3'),
                        'leverage': str(Config.LEVERAGE),
                        'entryTime': pd.Timestamp.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                        'tp1_done': False,
                        'tp2_done': False,
                        'tp3_done': False,
                        'tp1_time': "",
                        'tp2_time': "",
                        'tp3_time': "",
                        'tp1_usd': 0,
                        'tp2_usd': 0,
                        'tp3_usd': 0,
                        'realizedPnl': 0.0,
                        'sl_order_id': None
                    }
                    # Filter out None values
                    meta = {k: v for k, v in meta.items() if v is not None}
                    self.update_position_metadata(symbol, meta)
                
                return order
            except Exception as e:
                logger.error(f"Error creating order: {e}")
                return None

    def place_stop_order(self, symbol, side, amount, stop_price):
        """
        Places a STOP_MARKET order on the exchange.
        In dry run, we simulate it by tracking the stop price in metadata.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Simulating STOP_MARKET {side} {amount} for {symbol} at {stop_price}")
            return {'id': f'dry_stop_{int(time.time())}', 'status': 'open', 'type': 'stop_market'}
        else:
            try:
                params = {'stopPrice': stop_price, 'reduceOnly': True}
                order = self.exchange.create_order(symbol, 'STOP_MARKET', side, amount, params=params)
                logger.info(f"Stop order placed: {side} {amount} {symbol} @ {stop_price}")
                return order
            except Exception as e:
                logger.error(f"Error placing stop order for {symbol}: {e}")
                return None

    def cancel_order(self, symbol, order_id):
        """
        Cancels an open order by ID.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Simulating cancel order {order_id} for {symbol}")
            return True
        else:
            try:
                self.exchange.cancel_order(order_id, symbol)
                logger.info(f"Canceled order {order_id} for {symbol}")
                return True
            except Exception as e:
                logger.error(f"Error canceling order {order_id} for {symbol}: {e}")
                return False

    def _load_dry_positions(self):
        if not os.path.exists(self.dry_run_file): return []
        try:
            with open(self.dry_run_file, 'r') as f:
                return json.load(f)
        except: return []

    def _save_dry_positions(self, positions):
        with open(self.dry_run_file, 'w') as f:
            json.dump(positions, f, indent=2)

    def _record_trade(self, symbol, side, entry_px, exit_px, amount, pnl, roi, entry_time, meta=None):
        history = self._load_trade_history()
        now = pd.Timestamp.now(tz='UTC').replace(tzinfo=None)
        try:
            entry_dt = pd.to_datetime(entry_time, utc=True).replace(tzinfo=None)
            duration = str(now - entry_dt)
        except Exception as e:
            logger.warning(f"Failed to calculate duration for {symbol}: {e}")
            duration = "N/A"
        
        trade = {
            'symbol': symbol,
            'side': side,
            'entryPrice': float(entry_px),
            'exitPrice': float(exit_px),
            'amount': float(amount),
            'pnl': float(pnl),
            'roi': float(roi),
            'entryTime': entry_time,
            'exitTime': now.isoformat(),
            'duration': duration,
            'tp1_time': meta.get('tp1_time', "") if meta else "",
            'tp2_time': meta.get('tp2_time', "") if meta else "",
            'tp3_time': meta.get('tp3_time', "") if meta else "",
            'tp1_usd': meta.get('tp1_usd', 0) if meta else 0,
            'tp2_usd': meta.get('tp2_usd', 0) if meta else 0,
            'tp3_usd': meta.get('tp3_usd', 0) if meta else 0,
            'close_reason': meta.get('close_reason', "Manual/Target") if meta else "Manual/Target"
        }
        history.append(trade)
        self._save_trade_history(history)
        logger.info(f"TRADE RECORDED: {symbol} {side.upper()} PnL: {pnl:.2f} ({roi:.2f}%)")

    def _load_trade_history(self):
        if not os.path.exists(self.trade_history_file): return []
        try:
            with open(self.trade_history_file, 'r') as f:
                return json.load(f)
        except: return []

    def _save_trade_history(self, history):
        with open(self.trade_history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def fetch_open_orders(self, symbol=None):
        if self.dry_run:
            return []
        try:
            if symbol:
                return self.exchange.fetch_open_orders(symbol)
            else:
                # Iterate through pairs if bulk fetch fails or is not supported
                # NOTE: In a real production bot, we'd use websocket or private user data stream
                all_orders = []
                for s in Config.TRADING_PAIRS:
                    try:
                        orders = self.exchange.fetch_open_orders(s)
                        if orders: all_orders.extend(orders)
                        time.sleep(0.1) # Small delay to respect rate limits
                    except: pass
                return all_orders
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []

    def _normalize_symbol(self, symbol):
        """Normalize symbol for robust matching (e.g. TRUMP/USDT:USDT or TRUMP/USDT -> TRUMPUSDT)"""
        if not symbol: return ""
        # 1. Take part before ':'
        # 2. Remove '/'
        # 3. Uppercase
        return str(symbol).split(':')[0].replace('/', '').upper()

    def fetch_positions(self, symbols=None):
        if self.dry_run:
            positions = self._load_dry_positions()
            # Update PnL simulated
            for pos in positions:
                ticker = self.fetch_ticker(pos['symbol'])
                if ticker:
                    curr_price = ticker['last']
                    entry = float(pos['entryPrice'])
                    size = float(pos['contracts'])
                    if pos['side'] == 'long':
                        pos['unrealizedPnl'] = str((curr_price - entry) * size)
                    else:
                        pos['unrealizedPnl'] = str((entry - curr_price) * size)
                    pos['markPrice'] = str(curr_price)
            if symbols:
                return [p for p in positions if p['symbol'] in symbols]
            return positions
        else:
            try:
                positions = self.exchange.fetch_positions(symbols)
                managed = [p for p in positions if float(p.get('contracts', 0)) > 0]
                
                # 🚀 Merge with local metadata (SL, TP, etc.)
                local_data = self._load_dry_positions()
                norm_local = {self._normalize_symbol(m['symbol']): m for m in local_data}
                
                for p in managed:
                    p_norm = self._normalize_symbol(p['symbol'])
                    meta = norm_local.get(p_norm)
                    
                    # Use exact fields from Binance info for perfect sync
                    if 'info' in p:
                        # 🎯 DIRECT SYNC: Use 'unrealizedProfit' from Binance info
                        # Binance info usually provides unrealizedProfit in USDT
                        p['unrealizedPnl'] = float(p['info'].get('unrealizedProfit', p.get('unrealizedPnl', 0)))
                        p['markPrice'] = float(p['info'].get('markPrice', p.get('markPrice', 0)))
                        p['entryPrice'] = float(p['info'].get('entryPrice', p.get('entryPrice', 0)))
                        
                        # Fix ROI calculation to match Binance (PnL / Margin)
                        p_margin = float(p['info'].get('isolatedWallet', 0))
                        if p_margin == 0:
                            p_margin = float(p['info'].get('positionInitialMargin', 0))
                        
                        p['initialMargin'] = p_margin
                    else:
                        p['unrealizedPnl'] = float(p.get('unrealizedPnl', 0))
                    
                    if meta:
                        # 🚀 CRITICAL FIX: Ensure all metadata keys are synced back to UI
                        for key in ['sl', 'tp1', 'tp2', 'tp3', 'leverage', 'tp1_done', 'tp2_done', 'tp3_done', 'entryTime', 'tp1_time', 'tp2_time', 'tp3_time', 'tp1_usd', 'tp2_usd', 'tp3_usd', 'sl_order_id', 'realizedPnl']:
                            if key in meta and meta[key] is not None:
                                # Prioritize local metadata (it has moved SL, TP status, etc.)
                                p[key] = meta[key]
                        
                        # Fix side display for UI
                        if 'side' not in p or not p['side']:
                            p['side'] = meta.get('side', 'LONG')
                return managed
            except Exception as e:
                logger.error(f"Error fetching live positions: {e}")
                return []

    def fetch_ticker(self, symbol):
        # 🎯 Use WebSocket Cache if available
        if symbol in self.ticker_cache:
            return {'last': self.ticker_cache[symbol]}
            
        try:
            return self.public_exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    async def close_ws(self):
        """
        Safely closes the WebSocket connection.
        """
        self.ws_active = False
        await self.ws_exchange.close()
        logger.info("🔌 WebSocket: Connection closed.")

    def update_position_metadata(self, symbol, updates):
        """
        Updates metadata (like SL, TP status) for an existing position (dry-run or live).
        """
        positions = self._load_dry_positions()
        target_norm = self._normalize_symbol(symbol)
        found = False
        for pos in positions:
            if self._normalize_symbol(pos['symbol']) == target_norm:
                pos.update(updates)
                found = True
                break
        
        if not found:
            new_meta = {'symbol': symbol}
            new_meta.update(updates)
            positions.append(new_meta)
            
        self._save_dry_positions(positions)

    def price_to_precision(self, symbol, price):
        if self.dry_run: return price
        try:
            return float(self.exchange.price_to_precision(symbol, price))
        except: return price

    def amount_to_precision(self, symbol, amount):
        if self.dry_run: return amount
        try:
            return float(self.exchange.amount_to_precision(symbol, amount))
        except: return amount
