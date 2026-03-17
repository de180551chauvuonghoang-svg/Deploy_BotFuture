import sys
import os
sys.path.append(os.getcwd())

from core.exchange import ExchangeHandler

def cleanup_offline_positions():
    ex = ExchangeHandler()
    print("🧹 SYNCING POSITIONS WITH EXCHANGE...")
    
    # 1. Fetch real active positions from exchange (Testnet)
    all_positions = ex.exchange.fetch_positions()
    real_symbols = [p['symbol'] for p in all_positions if float(p['contracts']) > 0]
    
    # 2. Normalize symbols to match local storage format (though bot uses original)
    normalized_real = [ex._normalize_symbol(s) for s in real_symbols]
    print(f"DEBUG: Real symbols found: {real_symbols}")

    # 3. Load local positions
    local_pos = ex._load_dry_positions()
    
    # 4. Filter only those that exist on exchange OR are purely offline (dry run pairs)
    # Since we are in USE_TESTNET=True mode, everything SHOULD be on exchange.
    new_local = []
    for lp in local_pos:
        lp_sym = lp['symbol']
        lp_norm = ex._normalize_symbol(lp_sym)
        if lp_norm in normalized_real:
            new_local.append(lp)
            print(f"✅ Keeping {lp_sym} (Active on exchange)")
        else:
            print(f"🔥 Removing {lp_sym} (No pos on exchange)")

    ex._save_dry_positions(new_local)
    print("✅ Syncing complete.")

if __name__ == "__main__":
    cleanup_offline_positions()
