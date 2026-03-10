import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Exchange
    EXCHANGE = os.getenv('EXCHANGE', 'binance').lower()
    API_KEY = os.getenv(f'{EXCHANGE.upper()}_API_KEY')
    API_SECRET = os.getenv(f'{EXCHANGE.upper()}_SECRET')
    
    # Bot Mode
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'True').lower() == 'true'
    
    # Trading Pairs
    TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'BTC/USDT').split(',')
    
    # Risk Management
    LEVERAGE = int(os.getenv('LEVERAGE', 5))
    POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PERCENT', 2.0)) / 100
    STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PERCENT', 1.5)) / 100
    TAKE_PROFIT_PCT = float(os.getenv('TAKE_PROFIT_PERCENT', 3.0)) / 100
    
    TRAILING_STOP_THRESHOLD = float(os.getenv('TRAILING_STOP_THRESHOLD', 1.5)) / 100
    TRAILING_STOP_OFFSET = float(os.getenv('TRAILING_STOP_OFFSET', 0.5)) / 100
    
    MAX_DAILY_LOSS_PCT = float(os.getenv('MAX_DAILY_LOSS_PERCENT', 5.0)) / 100
    MAX_DRAWDOWN_PCT = float(os.getenv('MAX_DRAWDOWN_PERCENT', 15.0)) / 100
    
    # Notifications
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
    
    # Strategy
    TIMEFRAME = os.getenv('TIMEFRAME', '15m')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_FILE = os.path.join(BASE_DIR, 'trading.log')
    DATA_DIR = os.path.join(BASE_DIR, 'data')

if not os.path.exists(Config.DATA_DIR):
    os.makedirs(Config.DATA_DIR)
