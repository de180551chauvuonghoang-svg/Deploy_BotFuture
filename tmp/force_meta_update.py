import json
import os

data_file = "data/dry_run_positions.json"

if os.path.exists(data_file):
    with open(data_file, 'r') as f:
        positions = json.load(f)
else:
    positions = []

target_positions = [
    {
        "symbol": "TRUMP/USDT",
        "side": "long",
        "entryPrice": "3.8500",
        "sl": 3.85, # Hard BE set by bot
        "tp1": 3.89,
        "tp2": 3.93,
        "tp3": 3.97,
        "leverage": "10"
    },
    {
        "symbol": "SOL/USDT",
        "side": "long",
        "entryPrice": "95.12",
        "sl": 93.69,
        "tp1": 96.55,
        "tp2": 98.00,
        "tp3": 100.00,
        "leverage": "10"
    }
]

def update_meta(data, meta):
    found = False
    # Use normalized comparison for safety
    norm_target = meta['symbol'].replace("/", "").replace(":", "").upper()
    for pos in data:
        norm_pos = pos['symbol'].replace("/", "").replace(":", "").upper()
        if norm_pos == norm_target:
            pos.update(meta)
            found = True
            break
    if not found:
        data.append(meta)

for target in target_positions:
    update_meta(positions, target)

with open(data_file, 'w') as f:
    json.dump(positions, f, indent=2)

print("✅ Metadata updated manually for SOL and TRUMP.")
