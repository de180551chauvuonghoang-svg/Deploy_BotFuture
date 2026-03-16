import os
import json
import pandas as pd
import numpy as np
from config.config import Config
from core.logger import logger

class TradingEnv:
    """
    Simplified Gym-like environment for optimizing trading parameters.
    """
    def __init__(self, history_file):
        self.history_file = history_file
        self.params = {
            'min_score': Config.MIN_SCORE_THRESHOLD,
            'risk_pct': Config.BASE_RISK_PCT
        }
        
    def get_state(self):
        """
        Calculates current state based on recent trade history.
        """
        if not os.path.exists(self.history_file):
            return np.zeros(5)
            
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            
            if not history: return np.zeros(5)
            
            df = pd.DataFrame(history)
            recent = df.tail(10)
            
            win_rate = len(recent[recent['pnl'] > 0]) / len(recent)
            avg_pnl = recent['pnl'].mean()
            drawdown = (df['pnl'].cumsum().max() - df['pnl'].cumsum().iloc[-1])
            
            # Normalize state
            return np.array([
                win_rate, 
                avg_pnl / 100, 
                drawdown / 500,
                self.params['min_score'] / 15,
                self.params['risk_pct'] / 0.05
            ])
        except:
            return np.zeros(5)

    def suggest_optimization(self):
        """
        Uses a simple 'Policy' to suggest parameter adjustments.
        In a real PPO, this would be an inference step.
        """
        state = self.get_state()
        win_rate = state[0]
        pnl = state[1]
        
        updates = {}
        
        # If win rate is low, increase quality threshold (min_score)
        if win_rate < 0.45:
            updates['MIN_SCORE_THRESHOLD'] = min(13.0, Config.MIN_SCORE_THRESHOLD + 0.5)
            updates['BASE_RISK_PCT'] = max(0.005, Config.BASE_RISK_PCT - 0.002)
            logger.info("AI RL: Low win rate detected. Suggesting HIGHER score threshold and LOWER risk.")
            
        # If win rate is high and pnl is positive, we can be more aggressive
        elif win_rate > 0.65 and pnl > 0:
            updates['MIN_SCORE_THRESHOLD'] = max(7.0, Config.MIN_SCORE_THRESHOLD - 0.5)
            updates['BASE_RISK_PCT'] = min(0.03, Config.BASE_RISK_PCT + 0.005)
            logger.info("AI RL: High performance detected. Suggesting LOWER score threshold to capture more trades.")
            
        return updates

def apply_optimization():
    """
    Entry point for the RL Optimizer.
    """
    history_file = "data/trade_history.json"
    env = TradingEnv(history_file)
    recommendations = env.suggest_optimization()
    
    if recommendations:
        config_path = "config/config.py"
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            for key, val in recommendations.items():
                import re
                # Professional regex to swap values
                pattern = rf"{key} = .*"
                replacement = f"{key} = {val}"
                content = re.sub(pattern, replacement, content)
            
            with open(config_path, 'w') as f:
                f.write(content)
            
            logger.info(f"AI RL: Optimization Applied to Config: {recommendations}")
            return True
        except Exception as e:
            logger.error(f"AI RL: Failed to apply optimization: {e}")
            return False
    return False

if __name__ == "__main__":
    apply_optimization()
