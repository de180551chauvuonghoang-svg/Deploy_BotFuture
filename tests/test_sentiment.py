from ai.sentiment_engine import sentiment_engine
from core.logger import logger
import json

print("\n--- Testing AI Sentiment Connection ---")
score = sentiment_engine.fetch_global_sentiment()
summary = sentiment_engine.get_market_summary()

print(f"Status: SUCCESS")
print(f"Global Score: {score:+.2f}")
print(f"Market Summary: {summary}")
print("--- Test Complete ---\n")
