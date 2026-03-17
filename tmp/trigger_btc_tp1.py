import json
import os
import time

data_file = "data/dry_run_positions.json"

def get_positions():
    if not os.path.exists(data_file): return []
    with open(data_file, 'r') as f:
        return json.load(f)

def save_positions(pos):
    with open(data_file, 'w') as f:
        json.dump(pos, f, indent=2)

print("⚡ KÍCH HOẠT TP1 CHO BTC/USDT...")

positions = get_positions()
found = False
for p in positions:
    if "BTC" in p['symbol']:
        p['tp1'] = 10000.0  # Set rất thấp để trigger ngay
        p['tp1_done'] = False
        found = True
        break

if found:
    save_positions(positions)
    print("✅ Đã hạ target TP1 của BTC. Bot sẽ chốt lời trong chu kỳ tới.")
else:
    print("❌ Không tìm thấy vị thế BTC.")
