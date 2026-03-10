import ccxt
import time
import pandas as pd
from config.config import Config
from core.logger import logger

class ExchangeHandler:
    def __init__(self):
        exchange_id = Config.EXCHANGE
        ccxt.binance.options = {'adjustForTimeDifference': True}
        exchange_class = getattr(ccxt, exchange_id)
        
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
        
        # Public instance for OHLCV data (avoiding recvWindow issues)
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
        try:
            ohlcv = self.public_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return None

    def get_balance(self, asset='USDT'):
        if self.dry_run:
            return 10000.0 # Simulated balance for dry run
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

    def create_order(self, symbol, side, amount, type='market', params={}):
        if self.dry_run:
            logger.info(f"[DRY RUN] Simulating {side} {amount} {symbol} @ {type}")
            return {'id': 'dry_run_id', 'status': 'closed', 'side': side, 'amount': amount}
        try:
            order = self.exchange.create_order(symbol, type, side, amount, params=params)
            logger.info(f"Order created: {side} {amount} {symbol} @ {type}")
            return order
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    def fetch_positions(self, symbols=None):
        if self.dry_run:
            return [] # In a real dry run, you'd track this locally. For now, empty list.
        try:
            positions = self.exchange.fetch_positions(symbols)
            return [p for p in positions if float(p['contracts']) > 0]
        except Exception as e:
            # logger.error(f"Error fetching positions: {e}")
            return []

    def fetch_ticker(self, symbol):
        try:
            return self.public_exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
