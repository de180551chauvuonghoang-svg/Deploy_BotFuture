import pandas as pd
import numpy as np
import os
import sys
import time
from datetime import datetime, timedelta

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from backtest.data import fetch_historical_data
from strategy.smc_strategy import SMCStrategy
from strategy.structure import detect_structure
from strategy.regime_filter import get_regime
from strategy.order_blocks import find_bullish_ob, find_bearish_ob
from strategy.fvg import find_fvg
from strategy.liquidity import detect_liquidity_sweep
from strategy.confluence import score_setup
from risk.smart_risk import calculate_smart_sl_tp
import ccxt
import warnings
warnings.filterwarnings('ignore')

os.environ['IS_BACKTEST'] = 'true'

class AIDataCollector:
    def __init__(self, symbols, strategy, initial_capital=1300):
        self.symbols = symbols
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.collected_data = []

from concurrent.futures import ProcessPoolExecutor, as_completed

def process_symbol_signals(symbol, data_map_symbol):
    df_15m = data_map_symbol['15m']
    df_1h = data_map_symbol['1h']
    df_4h = data_map_symbol['4h']
    symbol_data = []

    # A. Pre-calculate indices
    h4_biases = {}
    for i in range(100, len(df_4h)):
        struct = detect_structure(df_4h.iloc[:i+1], lookback=400)
        h4_biases[df_4h.index[i]] = struct['bias']
    
    h1_regimes = {}
    h1_zones = {}
    for i in range(100, len(df_1h)):
        ts = df_1h.index[i]
        slice_h1 = df_1h.iloc[:i+1]
        h1_regimes[ts] = get_regime(slice_h1)
        h1_zones[ts] = {
            'bull_ob': find_bullish_ob(slice_h1, lookback=200),
            'bear_ob': find_bearish_ob(slice_h1, lookback=200),
            'fvg': find_fvg(slice_h1, lookback=200)
        }

    # B. Main Signal Scan (15m)
    for i in range(100, len(df_15m) - 200):
        ts_15m = df_15m.index[i]
        ts_h4 = df_4h.index[df_4h.index <= ts_15m][-1]
        ts_h1 = df_1h.index[df_1h.index <= ts_15m][-1]
        
        bias = h4_biases.get(ts_h4, "NONE")
        regime = h1_regimes.get(ts_h1, "AVOID")
        if bias == "NONE" or regime == "AVOID": continue

        zones = h1_zones.get(ts_h1)
        if not zones: continue

        curr_candle = df_15m.iloc[i]
        px_low, px_high = curr_candle['low'], curr_candle['high']
        ob_list = zones['bull_ob'] if bias == "LONG" else zones['bear_ob']
        fvg_list = zones['fvg']
        
        ob_hit = next((z for z in ob_list if px_low <= z['top'] and px_high >= z['bottom']), None)
        fvg_hit = next((z for z in fvg_list if px_low <= z['top'] and px_high >= z['bottom']), None)
        if not (ob_hit or fvg_hit): continue

        slice_15m = df_15m.iloc[:i+1]
        slice_1h = df_1h.iloc[df_1h.index <= ts_15m]
        sweep = detect_liquidity_sweep(slice_15m)
        score = score_setup(bias, regime, ob_hit, fvg_hit, sweep, slice_15m, slice_1h)
        if score < Config.MIN_SCORE_THRESHOLD: continue

        entry_px = (ob_hit['top'] + ob_hit['bottom']) / 2 if ob_hit else curr_candle['close']
        atr_15m = df_15m['atr'].iloc[i]
        risk_data = calculate_smart_sl_tp(bias, entry_px, ob_hit, atr_15m, 10000, score)
        if not risk_data: continue

        outcome = track_outcome_standalone(symbol, {**risk_data, 'entry': entry_px, 'signal': bias}, df_15m.iloc[i+1:])
        if outcome is not None:
            features = extract_features_standalone(symbol, {**risk_data, 'entry': entry_px, 'signal': bias, 'score': score}, slice_15m, slice_1h, df_4h)
            features['outcome'] = outcome
            features['timestamp'] = ts_15m
            features['symbol'] = symbol
            symbol_data.append(features)
    
    return symbol_data

def track_outcome_standalone(symbol, signal_data, future_df):
    entry = signal_data['entry']
    sl = signal_data['sl']
    tp1 = signal_data['tp1']
    side = signal_data['signal']
    max_candles = 192
    track_df = future_df.head(max_candles)
    for idx, row in track_df.iterrows():
        if side == 'LONG':
            if row['low'] <= sl: return 0
            if row['high'] >= tp1: return 1
        else:
            if row['high'] >= sl: return 0
            if row['low'] <= tp1: return 1
    return None

def extract_features_standalone(symbol, signal_data, df_15m, df_1h, df_4h):
    curr = df_15m.iloc[-1]
    score = signal_data.get('score', 0)
    rsi = df_15m['rsi'].iloc[-1]
    vol_ratio = curr['volume'] / df_15m['vol_sma'].iloc[-1] if df_15m['vol_sma'].iloc[-1] > 0 else 1.0
    ema200 = df_4h['ema_200'].asof(curr.name)
    dist_ema200 = (curr['close'] - ema200) / ema200 if ema200 > 0 else 0
    entry = signal_data['entry']
    sl = signal_data['sl']
    tp1 = signal_data['tp1']
    sl_dist_pct = abs(entry - sl) / entry
    tp_dist_pct = abs(tp1 - entry) / entry
    rr = tp_dist_pct / sl_dist_pct if sl_dist_pct > 0 else 1.0
    body_ratio = abs(curr['close'] - curr['open']) / (curr['high'] - curr['low']) if (curr['high'] - curr['low']) > 0 else 0
    return {
        'score': score,
        'rsi_15m': rsi,
        'vol_ratio_15m': vol_ratio,
        'dist_ema200_h4': dist_ema200,
        'sl_dist_pct': sl_dist_pct,
        'tp_dist_pct': tp_dist_pct,
        'rr': rr,
        'body_ratio': body_ratio,
        'vol_24h_usdt': curr.get('vol_24h_usdt', 0),
        'side': 1 if signal_data['signal'] == 'LONG' else 0
    }

class AIDataCollector:
    def __init__(self, symbols, strategy, initial_capital=1300):
        self.symbols = symbols
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.collected_data = []

    def collect(self, data_map, days=180):
        print("\n--- STARTING PARALLEL AI DATA COLLECTION ---")
        
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = {executor.submit(process_symbol_signals, s, data_map[s]): s for s in self.symbols}
            
            for future in as_completed(futures):
                s = futures[future]
                try:
                    res = future.result()
                    self.collected_data.extend(res)
                    print(f"[{s}] Completed. Samples: {len(res)}")
                except Exception as e:
                    print(f"[{s}] Failed: {e}")

        # Save to CSV
        if self.collected_data:
            df_final = pd.DataFrame(self.collected_data)
            output_path = "data/ai_training_data.csv"
            os.makedirs("data", exist_ok=True)
            df_final.to_csv(output_path, index=False)
            print(f"✅ AI Training data saved: {len(df_final)} samples -> {output_path}")
        else:
            print("❌ No signals found for data collection.")

    def _extract_features(self, symbol, signal_data, df_15m, df_1h, df_4h):
        # Current candle info
        curr = df_15m.iloc[-1]
        prev = df_15m.iloc[-2]
        
        # 1. SMC Features
        score = signal_data.get('score', 0)
        
        # 2. Indicators
        rsi = df_15m['rsi'].iloc[-1] if 'rsi' in df_15m.columns else 50
        vol_sma = df_15m['vol_sma'].iloc[-1] if 'vol_sma' in df_15m.columns else curr['volume']
        vol_ratio = curr['volume'] / vol_sma if vol_sma > 0 else 1.0
        
        # 3. Multi-TF Features
        close_h4 = df_4h['close'].iloc[-1]
        ema200_h4 = df_4h['ema_200'].iloc[-1] if 'ema_200' in df_4h.columns else close_h4
        dist_ema200 = (close_h4 - ema200_h4) / ema200_h4
        
        # 4. Signal Specifics
        entry = signal_data['entry']
        sl = signal_data['sl']
        tp1 = signal_data['tp1']
        
        sl_dist_pct = abs(entry - sl) / entry
        tp_dist_pct = abs(tp1 - entry) / entry
        rr = tp_dist_pct / sl_dist_pct if sl_dist_pct > 0 else 1.0
        
        # 5. Candle geometry
        high_low = curr['high'] - curr['low']
        body = abs(curr['close'] - curr['open'])
        body_ratio = body / high_low if high_low > 0 else 0
        
        return {
            'score': score,
            'rsi_15m': rsi,
            'vol_ratio_15m': vol_ratio,
            'dist_ema200_h4': dist_ema200,
            'sl_dist_pct': sl_dist_pct,
            'tp_dist_pct': tp_dist_pct,
            'rr': rr,
            'body_ratio': body_ratio,
            'vol_24h_usdt': curr.get('vol_24h_usdt', 0),
            'side': 1 if signal_data['signal'] == 'LONG' else 0
        }

    def _track_outcome(self, symbol, signal_data, future_df):
        """
        Tracks if the signal hits TP1 or SL first.
        Returns 1 for TP1 (Win), 0 for SL (Loss), None if not hit in timeframe.
        """
        entry = signal_data['entry']
        sl = signal_data['sl']
        tp1 = signal_data['tp1']
        side = signal_data['signal']
        
        # Limit tracking to next 48 hours (standard bot rule)
        max_candles = 4 * 48 # 192 candles for 15m
        track_df = future_df.head(max_candles)
        
        for idx, row in track_df.iterrows():
            if side == 'LONG':
                if row['low'] <= sl: return 0
                if row['high'] >= tp1: return 1
            else:
                if row['high'] <= sl: return 0 # Wait, for SHORT SL is higher
                # Signal data for short has SL > Entry and TP < Entry
                if row['high'] >= sl: return 0
                if row['low'] <= tp1: return 1
        
        return None # Inconclusive

if __name__ == "__main__":
    from strategy.smc_strategy import SMCStrategy
    import ccxt
    import pandas_ta as ta
    
    # Setup
    # Process only symbols with full 800d cache to bypass Binance Ban
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "TRUMP/USDT", "RIVER/USDT"]
    days = 800
    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
    strategy = SMCStrategy()
    
    # Fetch Data (Reuse logic from backtester)
    print("Loading data for analysis...")
    data_map = {}
    valid_symbols = []
    
    # Fetch Data (Parallelized for Speed)
    print(f"--- FETCHING 800-DAY DATA FOR {len(symbols)} SYMBOLS ---")
    data_map = {}
    valid_symbols = []
    
    from concurrent.futures import ThreadPoolExecutor
    
    def fetch_symbol_data(s):
        try:
            m15 = fetch_historical_data(exchange, s, '15m', days=days)
            h1 = fetch_historical_data(exchange, s, '1h', days=days)
            h4 = fetch_historical_data(exchange, s, '4h', days=days)
            
            if m15 is not None and h1 is not None and h4 is not None:
                # Add indicators needed for features
                m15['rsi'] = ta.rsi(m15['close'], length=14)
                m15['atr'] = ta.atr(m15['high'], m15['low'], m15['close'])
                m15['vol_sma'] = m15['volume'].rolling(window=20).mean()
                m15['vol_24h_usdt'] = (m15['volume'] * m15['close']).rolling(window=96).sum()
                h4['ema_200'] = ta.ema(h4['close'], length=200)
                return s, {'15m': m15, '1h': h1, '4h': h4}
        except Exception as e:
            print(f"Error fetching {s}: {e}")
        return s, None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = []
        for i, s in enumerate(symbols):
            print(f"[{i+1}/{len(symbols)}] Scheduling {s}...")
            results.append(executor.submit(fetch_symbol_data, s))
            time.sleep(2) # Prevent rapid-fire request bursts
        
        # Wait for all to complete
        final_results = [r.result() for r in results]
        
    for s, data in final_results:
        if data:
            data_map[s] = data
            valid_symbols.append(s)

    if not valid_symbols:
        print("❌ No valid symbols fetched. Exiting.")
        sys.exit(1)

    collector = AIDataCollector(valid_symbols, strategy)
    collector.collect(data_map, days)
