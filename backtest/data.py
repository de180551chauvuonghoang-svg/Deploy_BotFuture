import ccxt
import pandas as pd
import time
from datetime import datetime, timedelta
from core.logger import logger

def fetch_historical_data(exchange, symbol, timeframe, days=180):
    """
    Fetch historical OHLCV data for a specific number of days.
    """
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    all_ohlcv = []
    
    logger.info(f"Fetching {days} days of data for {symbol} ({timeframe})...")
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            since = ohlcv[-1][0] + 1 # Next batch starts after the last candle
            
            # Rate limit friendly
            time.sleep(exchange.rateLimit / 1000)
            
            # Check if we've reached the current time
            if ohlcv[-1][0] >= exchange.milliseconds() - (60 * 1000): # 1 min buffer
                break
                
            print(f"Fetched {len(all_ohlcv)} candles...", end="\r")
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            break
            
    if not all_ohlcv:
        return None
        
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    logger.info(f"Total candles fetched: {len(df)}")
    return df
