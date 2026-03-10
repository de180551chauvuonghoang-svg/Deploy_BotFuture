import pandas_ta as ta
import pandas as pd
from core.logger import logger

class BaseStrategy:
    def __init__(self, name="BaseStrategy"):
        self.name = name

    def generate_signals(self, df: pd.DataFrame):
        raise NotImplementedError("Subclasses must implement generate_signals")

class SniperTrendStrategy(BaseStrategy):
    """
    Expert Strategy: ATR-Trend Sniper
    - Filter 1: EMA 200 (Long-term direction)
    - Filter 2: ADX > 30 (Extreme trend strength required)
    - Filter 3: Volume Spike > 1.5x EMA (High conviction)
    - Filter 4: RSI 50-65 (Strong but not exhausted)
    """
    def __init__(self, ema_trend=200, adx_min=30):
        super().__init__(name="SniperTrend")
        self.ema_trend = ema_trend
        self.adx_min = adx_min

    def generate_signals(self, df: pd.DataFrame):
        if df is None or len(df) < self.ema_trend:
            return None
            
        # 1. Indicators
        df['ema'] = ta.ema(df['close'], length=self.ema_trend)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # ADX
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
        df['adx'] = adx_df.iloc[:, 0]
        
        # Volume EMA (20)
        df['vol_ema'] = ta.ema(df['volume'], length=20)
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        signal = 0
        
        # --- SNIPER FILTERS ---
        is_strong_trend = curr['adx'] > self.adx_min
        is_volume_spike = curr['volume'] > curr['vol_ema'] * 1.5
        
        if is_strong_trend and is_volume_spike:
            # LONG Entry
            if curr['close'] > curr['ema'] and curr['rsi'] > 50 and curr['rsi'] < 65:
                if curr['close'] > prev['close']: # Confirmation of price action
                    signal = 1
            
            # SHORT Entry
            elif curr['close'] < curr['ema'] and curr['rsi'] < 50 and curr['rsi'] > 35:
                if curr['close'] < prev['close']:
                    signal = -1
                        
        return {
            'signal': signal,
            'price': curr['close'],
            'atr': curr['atr'],
            'timestamp': curr['timestamp']
        }
