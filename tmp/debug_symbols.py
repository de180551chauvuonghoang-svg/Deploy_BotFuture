import sys
import os
sys.path.append(os.getcwd())
from core.exchange import ExchangeHandler
from config.config import Config
import json

ex = ExchangeHandler()
positions = ex.exchange.fetch_positions(Config.TRADING_PAIRS)
print("Raw symbols from exchange:")
for p in positions:
    if float(p.get('contracts', 0)) > 0:
        print(f"- {p['symbol']}")

local_data = ex._load_dry_positions()
print("\nLocal metadata symbols:")
for m in local_data:
    print(f"- {m['symbol']}")
