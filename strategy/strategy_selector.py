from strategy.signal_generator import SignalGenerator
from strategy.market_regime import MarketRegimeDetector

class StrategySelector:
    """
    Auto-selects the optimal strategy based on the current market condition.
    """
    def __init__(self):
        self.regime_detector = MarketRegimeDetector()
        self.signal_generator = SignalGenerator(name="DynamicSMC")

    def get_signal(self, df_15m, df_4h, df_1h):
        """
        Calculates signals based on detection.
        Currently defaults to SignalGenerator, but can be expanded for Mean-Reversion.
        """
        regime_data = self.regime_detector.detect(df_15m)
        regime = regime_data['regime']
        
        # Select strategy logic
        if regime == "RANGING":
            # For now, we still use the master signal generator, 
            # but this module is ready for future mean-reversion strategies.
            return self.signal_generator.generate_signals(df_15m, df_4h, df_1h)
            
        elif regime == "TRENDING":
            return self.signal_generator.generate_signals(df_15m, df_4h, df_1h)
            
        return {"signal": 0, "reason": f"Regime: {regime}", "regime": regime}
