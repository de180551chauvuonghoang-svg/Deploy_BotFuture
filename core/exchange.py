import ccxt
import time
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
        
        self.dry_run_file = "data/dry_run_positions.json"
        self.trade_history_file = "data/trade_history.json"
        if not os.path.exists("data"):
            os.makedirs("data")
        
        # Authenticated instance
        self.exchange = exchange_class({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
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
            # Force LOCAL DRY RUN simulation immediately to bypass deprecated Sandbox
            logger.info("Running in LOCAL DRY RUN (Simulation) mode.")
            self.dry_run = True
            # We still initialize the exchange to fetch OHLCV data, but we don't use the sandbox

    def fetch_ohlcv(self, symbol, timeframe='15m', limit=100):
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

    def set_leverage(self, symbol, leverage):
        if self.dry_run:
            return
        try:
            self.exchange.set_leverage(leverage, symbol)
            logger.info(f"Leverage set to {leverage}x for {symbol}")
        except Exception as e:
            logger.error(f"Error setting leverage for {symbol}: {e}")

    def create_order(self, symbol, side, amount, type='market', **kwargs):
        """
        Creates a market order (supported in dry run and live).
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
                order = self.exchange.create_order(symbol, type, side, amount, params=kwargs)
                logger.info(f"Order created: {side} {amount} {symbol} @ {type}")
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
                params = {'stopPrice': stop_price}
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
                return [p for p in positions if float(p['contracts']) > 0]
            except Exception as e:
                return []

    def fetch_ticker(self, symbol):
        try:
            return self.public_exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None

    def update_position_metadata(self, symbol, updates):
        """
        Updates metadata (like SL, TP status) for an existing dry-run position.
        """
        if not self.dry_run: return
        
        positions = self._load_dry_positions()
        for pos in positions:
            if pos['symbol'] == symbol:
                pos.update(updates)
                break
        self._save_dry_positions(positions)
