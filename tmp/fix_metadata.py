import json
import os

data_file = "data/dry_run_positions.json"

if os.path.exists(data_file):
    with open(data_file, 'r') as f:
        positions = json.load(f)
else:
    positions = []

# Update or Add TRUMP positions
trump_meta = {
    "symbol": "TRUMP/USDT",
    "side": "long",
    "entryPrice": "3.8500",
    "sl": 3.81,
    "tp1": 3.89,
    "tp2": 3.93,
    "tp3": 3.97,
    "leverage": "10"
}

# Update or Add BTC positions
btc_meta = {
    "symbol": "BTC/USDT",
    "side": "long",
    "entryPrice": "75263.5000",
    "sl": 74510.8,
    "tp1": 76016.1,
    "tp2": 76768.8,
    "tp3": 77521.4,
    "leverage": "10"
}

def update_meta(data, meta):
    found = False
    for pos in data:
        if pos['symbol'] == meta['symbol']:
            pos.update(meta)
            found = True
            break
    if not found:
        data.append(meta)

update_meta(positions, trump_meta)
update_meta(positions, btc_meta)

with open(data_file, 'w') as f:
    json.dump(positions, f, indent=2)

print("✅ Metadata updated successfully!")
