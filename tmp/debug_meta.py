"""
Debug script to check what's in dry_run_positions.json vs what Binance returns.
Run this on VPS: ./venv/bin/python tmp/debug_meta.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from config.config import Config

# --- 1. Read local metadata file ---
meta_path = os.path.join(Config.DATA_DIR, "dry_run_positions.json")
print(f"\n📁 DATA_DIR: {Config.DATA_DIR}")
print(f"📄 Metadata file path: {meta_path}")
print(f"📄 File exists: {os.path.exists(meta_path)}")

if os.path.exists(meta_path):
    with open(meta_path, 'r') as f:
        positions = json.load(f)
    print(f"\n📊 Found {len(positions)} positions in metadata:")
    for p in positions:
        print(f"\n  Symbol : {p.get('symbol')}")
        print(f"  Side   : {p.get('side')}")
        print(f"  Entry  : {p.get('entryPrice')}")
        print(f"  SL     : {p.get('sl')}  <-- This should update when Bot moves SL")
        print(f"  TP1    : {p.get('tp1')} (Done: {p.get('tp1_done', False)})")
        print(f"  TP2    : {p.get('tp2')} (Done: {p.get('tp2_done', False)})")
        print(f"  TP3    : {p.get('tp3')} (Done: {p.get('tp3_done', False)})")
else:
    print("\n❌ Metadata file does NOT EXIST!")
    print("This means either:")
    print("  1. The bot has never opened any position.")
    print("  2. The bot is writing to a different DATA_DIR path.")

# --- 2. Show what Config.DATA_DIR resolves to ---
print(f"\n🔎 Config.BASE_DIR = {Config.BASE_DIR}")
print(f"🔎 Config.DATA_DIR = {Config.DATA_DIR}")
