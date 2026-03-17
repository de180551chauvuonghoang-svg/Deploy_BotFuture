import sys
import os
sys.path.append(os.getcwd())
from ai.inference import ai_engine
import pandas as pd
import joblib

# Dummy features matching the model's expected features
features = {
    'score': 8.5,
    'rsi_15m': 60,
    'vol_ratio_15m': 1.5,
    'dist_ema200_h4': 0.02,
    'sl_dist_pct': 0.01,
    'tp_dist_pct': 0.02,
    'rr': 2.0,
    'body_ratio': 0.6,
    'vol_24h_usdt': 100_000_000,
    'side': 1
}

print(f"Model loaded: {ai_engine.model is not None}")
print(f"Features loaded: {ai_engine.features}")

try:
    confidence = ai_engine.get_confidence(features)
    print(f"AI Confidence for dummy features: {confidence}")
except Exception as e:
    print(f"Error during inference check: {e}")
