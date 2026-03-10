import pandas as pd
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    Ensures a consistent interface for the Signal Generator and Backtester.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, df_4h: pd.DataFrame = None, df_1h: pd.DataFrame = None) -> dict:
        """
        Generate trading signals based on provided OHLCV data.
        Returns a dictionary with signal details.
        """
        pass
