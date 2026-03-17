import sys
import os
sys.path.append(os.getcwd())
from core.exchange import ExchangeHandler
import json

ex = ExchangeHandler()
# Fetch positions with info
pos = ex.exchange.fetch_positions(['ZEC/USDT'])
print("--- RAW CCXT DATA ---")
print(json.dumps(pos[0], indent=2))

# Fetch directly from fapi
try:
    risk = ex.exchange.fapiPrivateGetPositionRisk({'symbol': 'ZECUSDT'})
    print("\n--- RAW FAPI DATA ---")
    print(json.dumps(risk, indent=2))
except Exception as e:
    print(f"Error fetching raw risk: {e}")
