import json
import os
import pandas as pd
from datetime import datetime

def sync_tp_hits_to_history():
    pos_file = "data/dry_run_positions.json"
    hist_file = "data/trade_history.json"
    
    if not os.path.exists(pos_file):
        print("No positions to sync.")
        return

    with open(pos_file, 'r') as f:
        positions = json.load(f)
    
    if os.path.exists(hist_file):
        with open(hist_file, 'r') as f:
            history = json.load(f)
    else:
        history = []

    # Track what's already in history to avoid duplicates
    # We use a simple key: symbol + entryTime + tp_marker
    existing_keys = set()
    for t in history:
        key = f"{t['symbol']}_{t['entryTime']}_{t.get('close_reason', '')}"
        existing_keys.add(key)

    new_entries = 0
    
    print("🔍 Scanning active positions for unrecorded TP hits...")

    for pos in positions:
        symbol = pos['symbol']
        entry_time = pos.get('entryTime')
        entry_px = float(pos.get('entryPrice', 0))
        
        # Check TP1
        if pos.get('tp1_done'):
            reason = "TP1 Partial Hit"
            key = f"{symbol}_{entry_time}_{reason}"
            if key not in existing_keys:
                # Approximate amount closed (33% of original)
                # If contracts is remaining (67%), then original = contracts / 0.67
                current_contracts = float(pos['contracts'])
                original_total = current_contracts / 0.67
                closed_amount = original_total * 0.33
                
                trade = {
                    'symbol': symbol,
                    'side': pos['side'].lower(),
                    'entryPrice': entry_px,
                    'exitPrice': float(pos.get('tp1', 0)),
                    'amount': round(closed_amount, 4),
                    'pnl': float(pos.get('tp1_usd', 0)),
                    'roi': (float(pos.get('tp1_usd', 0)) / (float(pos.get('initialMargin', 1)) * 0.33) * 100) if float(pos.get('initialMargin', 1)) > 0 else 0,
                    'entryTime': entry_time,
                    'exitTime': datetime.now().isoformat(),
                    'duration': "TP Hit",
                    'close_reason': reason
                }
                history.append(trade)
                existing_keys.add(key)
                new_entries += 1
                print(f"✅ Added {symbol} TP1 to history.")

        # Check TP2
        if pos.get('tp2_done'):
            reason = "TP2 Partial Hit"
            key = f"{symbol}_{entry_time}_{reason}"
            if key not in existing_keys:
                current_contracts = float(pos['contracts'])
                # Remaining was 67%, we closed 50% of that (33.5%), remaining is 33.5%
                # This logic is getting complex, let's just use the USD value from meta
                trade = {
                    'symbol': symbol,
                    'side': pos['side'].lower(),
                    'entryPrice': entry_px,
                    'exitPrice': float(pos.get('tp2', 0)),
                    'amount': 0, # Approximation
                    'pnl': float(pos.get('tp2_usd', 0)),
                    'roi': 0,
                    'entryTime': entry_time,
                    'exitTime': datetime.now().isoformat(),
                    'duration': "TP Hit",
                    'close_reason': reason
                }
                history.append(trade)
                existing_keys.add(key)
                new_entries += 1
                print(f"✅ Added {symbol} TP2 to history.")

    if new_entries > 0:
        with open(hist_file, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"🚀 Sync complete. Added {new_entries} new entries to history.")
    else:
        print("ℹ️ No new trade records to add.")

if __name__ == "__main__":
    sync_tp_hits_to_history()
