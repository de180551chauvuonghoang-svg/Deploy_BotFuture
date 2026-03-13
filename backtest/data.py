import ccxt
import pandas as pd
import time
import os
from datetime import datetime, timedelta
from core.logger import logger

CACHE_DIR = "data/cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def fetch_historical_data(exchange, symbol, timeframe, days=180):
    """
    Fetch historical OHLCV data with local caching.
    """
    safe_symbol = symbol.replace("/", "_")
    cache_file = f"{CACHE_DIR}/{safe_symbol}_{timeframe}_{days}d.csv"
    
    # Try loading from cache
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file, index_col='timestamp', parse_dates=True)
        # Fix: Ensure comparison is timezone-aware or both UTC
        last_candle = df.index[-1]
        now_utc = datetime.utcnow()
        if last_candle > now_utc - timedelta(hours=1):
            logger.info(f"Loaded {symbol} ({timeframe}) from cache.")
            return df

    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    all_ohlcv = []
    
    logger.info(f"Fetching {days} days of data for {symbol} ({timeframe}) from API...")
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1
            time.sleep(exchange.rateLimit / 1000)
            
            if ohlcv[-1][0] >= exchange.milliseconds() - (60 * 1000):
                break
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            break
            
    if not all_ohlcv:
        return None
        
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Save to cache
    df.to_csv(cache_file)
    logger.info(f"Total candles fetched and cached: {len(df)}")
    return df
