import sys
import os
sys.path.append(os.getcwd())

from core.exchange import ExchangeHandler
from config.config import Config

def list_all():
    ex = ExchangeHandler()
    print("--------------------------------")
    for symbol in Config.TRADING_PAIRS:
        orders = ex.exchange.fetch_open_orders(symbol)
        if orders:
            print(f"SYMBOL: {symbol} | Orders found: {len(orders)}")
            for o in orders:
                print(f"  - ID: {o['id']} | Type: {o['type']} | Side: {o['side']} | Price: {o['price']} | Amount: {o['amount']}")
    print("--------------------------------")

if __name__ == "__main__":
    list_all()
