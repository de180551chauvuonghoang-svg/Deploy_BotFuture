import json
import os

def update_active_tps():
    file_path = "data/dry_run_positions.json"
    if not os.path.exists(file_path):
        print("Data file not found.")
        return

    # New Ratios
    TP1_RR = 1.0
    TP2_RR = 2.0
    TP3_RR = 4.0

    with open(file_path, 'r') as f:
        positions = json.load(f)

    updated_count = 0
    for pos in positions:
        # We only update active or pending orders for the symbols the user mentioned
        # or all active ones to be safe
        entry = float(pos.get('entryPrice', 0))
        sl = float(pos.get('sl', 0))
        
        if entry > 0 and sl > 0:
            sl_dist = abs(entry - sl)
            side = pos.get('side', 'LONG').upper()
            
            if side == "LONG":
                pos['tp1'] = round(entry + (sl_dist * TP1_RR), 6)
                pos['tp2'] = round(entry + (sl_dist * TP2_RR), 6)
                pos['tp3'] = round(entry + (sl_dist * TP3_RR), 6)
            else:
                pos['tp1'] = round(entry - (sl_dist * TP1_RR), 6)
                pos['tp2'] = round(entry - (sl_dist * TP2_RR), 6)
                pos['tp3'] = round(entry - (sl_dist * TP3_RR), 6)
            
            print(f"✅ Updated {pos['symbol']}: TP1={pos['tp1']}, TP2={pos['tp2']}, TP3={pos['tp3']}")
            updated_count += 1

    with open(file_path, 'w') as f:
        json.dump(positions, f, indent=2)
    
    print(f"\nDone. Updated {updated_count} positions.")

if __name__ == "__main__":
    update_active_tps()
