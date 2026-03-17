
from core.exchange import ExchangeHandler
from core.logger import logger
import pandas as pd

def check_current_positions():
    exchange = ExchangeHandler()
    positions = exchange.fetch_positions()
    print(f"\n--- CÁC VỊ THẾ ĐANG CHẠY TRÊN TESTNET ---")
    if not positions:
        print("Không có vị thế nào đang mở.")
    else:
        for pos in positions:
            print(f"Symbol: {pos['symbol']} | Side: {pos['side']} | Entry: {pos['entryPrice']} | Size: {pos['contracts']}")
    print("------------------------------------------\n")

if __name__ == "__main__":
    check_current_positions()
