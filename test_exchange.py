from core.exchange import ExchangeHandler
from config.config import Config

try:
    print("Testing ExchangeHandler...")
    ex = ExchangeHandler()
    print("Fetching BTC/USDT 15m...")
    df = ex.fetch_ohlcv("BTC/USDT", timeframe='15m', limit=5)
    if df is not None:
        print("Success!")
        print(df.tail())
    else:
        print("Failed to fetch data.")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
