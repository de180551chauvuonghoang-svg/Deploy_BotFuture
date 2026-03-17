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

print("🧪 BẮT ĐẦU MÔ PHỎNG CHỐT LỜI TP CHO ETH/USDT...")

# 1. Đặt TP1 thấp để kích hoạt ngay
positions = get_positions()
for p in positions:
    if "ETH" in p['symbol']:
        p['tp1'] = 2200.0  # Chắc chắn thấp hơn giá hiện tại (~2340)
        p['tp2'] = 2210.0
        p['tp3'] = 2220.0
        # Reset các trạng thái nếu có
        p['tp1_done'] = False
        p['tp2_done'] = False
        p['tp3_done'] = False
        print(f"✅ Đã cấu hình TP ảo cho ETH: TP1={p['tp1']}, TP2={p['tp2']}, TP3={p['tp3']}")
        break

save_positions(positions)

print("\n🚀 Bot sẽ quét và chốt lời TP1 trong vòng vài giây tới.")
print("Vui lòng theo dõi Dashboard: Size ETH sẽ giảm 33% và Stop Loss sẽ dời về Entry.")
