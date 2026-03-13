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
    INITIAL_DRY_BALANCE = float(os.getenv('INITIAL_DRY_BALANCE', 10000.0))
    
    # Trading Pairs
    TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT,AVAX/USDT,ADA/USDT,DOGE/USDT,LINK/USDT,DOT/USDT,NEAR/USDT,LTC/USDT,BCH/USDT,WIF/USDT,SUI/USDT,APT/USDT,FET/USDT,RENDER/USDT,INJ/USDT,OP/USDT,ARB/USDT,TIA/USDT,STX/USDT').split(',')
    
    # Risk Management
    LEVERAGE = int(os.getenv('LEVERAGE', 5))
    POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PERCENT', 2.0)) / 100
    
    # Professional SMC Management (Synced with Backtest)
    MIN_SCORE_THRESHOLD = 8.5
    MAX_DRAWDOWN_LIMIT = 0.25 # 25% Portfolio Hard Stop
    RISK_LEVEL_1_DD = 0.15   # 15% DD -> Scale to 40%
    RISK_LEVEL_2_DD = 0.20   # 20% DD -> Scale to 10%
    RISK_LEVEL_3_DD = 0.24   # 24% DD -> Scale to 0%
    
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
