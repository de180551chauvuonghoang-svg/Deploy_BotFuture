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
    
    # Trading Pairs (Verified Top 100 Binance Futures Symbols)
    TRADING_PAIRS = os.getenv('TRADING_PAIRS', 'BTC/USDT,ETH/USDT,SOL/USDT,TRUMP/USDT,XRP/USDT,DOGE/USDT,PIXEL/USDT,BNB/USDT,RIVER/USDT,1000PEPE/USDT,ZEC/USDT,HYPE/USDT,LYN/USDT,TURBO/USDT,SUI/USDT,TAO/USDT,ADA/USDT,AVAX/USDT,BCH/USDT,PAXG/USDT,ENSO/USDT,DEGO/USDT,NEAR/USDT,LINK/USDT,UAI/USDT,FIL/USDT,RENDER/USDT,ENA/USDT,DOT/USDT,ACX/USDT,FET/USDT,HUMA/USDT,AAVE/USDT,WLD/USDT,WLFI/USDT,SIREN/USDT,LTC/USDT,OGN/USDT,UNI/USDT,PIPPIN/USDT,ASTER/USDT,WIF/USDT,1000SHIB/USDT,PENGU/USDT,VVV/USDT,XPL/USDT,CRCL/USDT,ROBO/USDT,ICP/USDT,GALA/USDT,TRIA/USDT,FARTCOIN/USDT,1000BONK/USDT,RESOLV/USDT,ARB/USDT,VIRTUAL/USDT,APT/USDT,NAORIS/USDT,OPN/USDT,TRX/USDT,COLLECT/USDT,MOODENG/USDT,BTR/USDT,XLM/USDT,ETC/USDT,HBAR/USDT,OP/USDT,NIGHT/USDT,CRV/USDT,MSTR/USDT,SIGN/USDT,FLOW/USDT,AVNT/USDT,POWER/USDT,SEI/USDT,GRT/USDT,OXT/USDT,MELANIA/USDT,BANANAS31/USDT,BARD/USDT,NEIRO/USDT,XMR/USDT,ONDO/USDT,ZRO/USDT,TIA/USDT,TON/USDT,PLAY/USDT,DASH/USDT,XAI/USDT,BERA/USDT,INJ/USDT,F/USDT,ALGO/USDT,LIT/USDT,1000SATS/USDT,MANTRA/USDT,ESP/USDT,BULLA/USDT').split(',')
    
    # Risk Management
    LEVERAGE = int(os.getenv('LEVERAGE', 5))
    POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PERCENT', 2.0)) / 100
    
    # Professional SMC Management (Hybrid Sniper Optimization)
    MIN_SCORE_THRESHOLD = 7.5
    BASE_RISK_PCT = 0.015
    MAX_RISK_PCT = 0.02       # Max 2.0% risk for A++ setups
    
    # AI System
    AI_CONFIDENCE_THRESHOLD = 0.70  # Only trade if AI is 70% confident
    
    # AI Sentiment Analysis (Phase 2)
    CRYPTOPANIC_API_KEY = os.getenv('CRYPTOPANIC_API_KEY', '') # Get from cryptopanic.com/developers/api/
    SENTIMENT_THRESHOLD = -0.3 # -1.0 to 1.0. If sentiment < -0.3 (Extreme Fear), pause trading.
    
    MAX_DRAWDOWN_LIMIT = 0.25 # 25% Portfolio Hard Stop
    RISK_LEVEL_1_DD = 0.15   # 15% DD -> Scale to 40%
    RISK_LEVEL_2_DD = 0.20   # 20% DD -> Scale to 10%
    RISK_LEVEL_3_DD = 0.24   # 24% DD -> Scale to 0%
    
    # Time Management (Anti-Stuck mechanism)
    MAX_HOLDING_HOURS = 48    # Hard exit after 48h regardless of PnL
    TRADE_STAGNANT_HOURS = 12 # Exit if price stays near entry (+/- 0.5%) for 12h
    
    # Live Stress Test Parameters
    MIN_24H_VOLUME_USDT = 50_000_000 # Skip symbols with < 50M USD volume
    LIVE_SLIPPAGE_FACTOR = 0.0015    # 0.15% per trade (More realistic for Live)
    
    # Notifications
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
    
    # Strategy
    TIMEFRAME = os.getenv('TIMEFRAME', '15m')
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_FILE = os.path.join(BASE_DIR, 'logs', 'trading.log')
    DATA_DIR = os.path.join(BASE_DIR, 'data')

if not os.path.exists(Config.DATA_DIR):
    os.makedirs(Config.DATA_DIR)
