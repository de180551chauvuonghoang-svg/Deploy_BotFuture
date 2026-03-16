import xgboost as xgb
import pandas as pd
import numpy as np
import os
import joblib

class AIInference:
    def __init__(self, model_path="ai/models/signal_filter_v1.json"):
        self.model = None
        self.features = None
        self.model_path = model_path
        self.features_path = "ai/models/features_list.joblib"
        
        if os.path.exists(self.model_path):
            self.model = xgb.XGBClassifier()
            self.model.load_model(self.model_path)
            
            if os.path.exists(self.features_path):
                self.features = joblib.load(self.features_path)
                print(f"✅ AI Inference Engine loaded: {self.model_path}")
        else:
            print(f"⚠️ AI model not found at {self.model_path}. AI filtering will be disabled.")

    def get_confidence(self, features_dict):
        """
        Returns confidence score (0.0 to 1.0) for a given set of features.
        """
        if self.model is None or self.features is None:
            return 1.0 # Default to 100% if AI is not ready (avoid blocking)

        try:
            # Construct DataFrame with correct feature order
            df = pd.DataFrame([features_dict])
            df = df[self.features] # Reorder
            
            # Predict probability
            prob = self.model.predict_proba(df)[0][1] # Probability of class 1 (Win)
            return float(prob)
        except Exception as e:
            print(f"❌ AI Inference error: {e}")
            return 1.0 # Fallback

# Singleton instance
ai_engine = AIInference()
