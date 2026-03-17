import json
import os

data_file = "data/dry_run_positions.json"

def get_positions():
    if not os.path.exists(data_file): return []
    with open(data_file, 'r') as f:
        return json.load(f)

def save_positions(pos):
    with open(data_file, 'w') as f:
        json.dump(pos, f, indent=2)

print("⚡ SỬA DATA VÀ KÍCH HOẠT TP2 CHO BTC/USDT...")

positions = get_positions()
# Chú ý: bot có thể tạo nhiều bản ghi do lỗi trùng lặp symbol trước đó, ta dọn dẹp luôn
cleaned_positions = []
btc_found = False

# Giữ lại các symbol khác, gộp BTC
for p in positions:
    if "BTC" in p['symbol']:
        if not btc_found:
            p['side'] = 'long' # Sửa thành LONG
            p['tp2'] = 10000.0 # Target mồi để trigger ngay
            p['tp1_done'] = True
            p['tp2_done'] = False
            cleaned_positions.append(p)
            btc_found = True
    else:
        cleaned_positions.append(p)

save_positions(cleaned_positions)
print("✅ Đã sửa BTC thành LONG và đặt TP2 mục tiêu. Bot sẽ thực hiện chốt lời trong giây lát.")
