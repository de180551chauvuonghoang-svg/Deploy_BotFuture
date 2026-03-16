import requests
import time
import os
import json
from config.config import Config
from core.logger import logger

def notify_sentiment(summary, score):
    webhook_url = Config.DISCORD_WEBHOOK_URL
    if not webhook_url: return
    
    import requests
    color = 0x2ebd85 if score > 0.1 else 0xf6465d if score < -0.3 else 0xf0b90b
    payload = {
        "embeds": [{
            "title": "🧠 AI Market Sentiment Alert",
            "description": f"**Status:** {summary}\n**Score:** {score:+.2f}",
            "color": color,
            "footer": {"text": "SMC Bot Intelligence Stage 2"}
        }]
    }
    try: requests.post(webhook_url, json=payload, timeout=5)
    except: pass

class SentimentEngine:
    def __init__(self):
        self.api_key = Config.CRYPTOPANIC_API_KEY
        self.base_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.cache_file = os.path.join(Config.DATA_DIR, "sentiment_cache.json")
        self.last_score = 0.0 # Neutral
        self.last_fetch = 0
        self.model = None
        self.tokenizer = None
        
        # Try to load FinBERT
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
            import torch
            
            logger.info("AI: Loading FinBERT for sentiment analysis...")
            model_name = "ProsusAI/finbert"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.nlp = pipeline("sentiment-analysis", model=self.model, tokenizer=self.tokenizer)
            logger.info("AI: FinBERT loaded successfully.")
        except ImportError:
            logger.warning("AI: Transformers/Torch not found. Sentiment analysis will use fallback (Neutral).")
            self.nlp = None

    def fetch_global_sentiment(self):
        """
        Fetches latest news from CryptoPanic and calculates aggregate sentiment.
        """
        now = time.time()
        # Cache for 1 hour to avoid API rate limits
        if now - self.last_fetch < 3600 and os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                self.last_score = data.get('score', 0.0)
                return self.last_score

        if not self.api_key:
            logger.warning("AI: CryptoPanic API Key missing. Skipping sentiment fetch.")
            return 0.0

        try:
            params = {
                'auth_token': self.api_key,
                'public': 'true',
                'filter': 'hot'
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code != 200:
                logger.error(f"AI: News fetch failed: {response.status_code}")
                return self.last_score

            data = response.json()
            posts = data.get('results', [])
            
            if not posts:
                return 0.0

            scores = []
            for post in posts[:10]: # Analyze top 10 hot posts
                title = post.get('title', '')
                if self.nlp:
                    # FinBERT returns: [{'label': 'positive', 'score': 0.99}]
                    result = self.nlp(title)[0]
                    label = result['label']
                    conf = result['score']
                    
                    if label == 'positive': scores.append(conf)
                    elif label == 'negative': scores.append(-conf)
                    else: scores.append(0)
                else:
                    # Fallback: Basic keyword matching
                    title_lower = title.lower()
                    if any(w in title_lower for w in ['bull', 'high', 'moon', 'gain', 'growth']):
                        scores.append(0.5)
                    elif any(w in title_lower for w in ['bear', 'crash', 'dump', 'fear', 'drop']):
                        scores.append(-0.5)
                    else:
                        scores.append(0.0)

            avg_score = sum(scores) / len(scores) if scores else 0.0
            self.last_score = avg_score
            self.last_fetch = now
            
            # 🔔 Notify if significant shift
            if abs(avg_score) > 0.4:
                notify_sentiment(self.get_market_summary(), avg_score)
            
            # Save to cache
            with open(self.cache_file, 'w') as f:
                json.dump({'score': avg_score, 'timestamp': now}, f)
                
            logger.info(f"AI: Global Sentiment Updated: {avg_score:.2f}")
            return avg_score

        except Exception as e:
            logger.error(f"AI: Sentiment Engine Error: {e}")
            return self.last_score

    def get_market_summary(self):
        """
        Returns a human-readable summary for Dashboard.
        """
        score = self.last_score
        if score > 0.4: return "🚀 Bullish Euphoria"
        if score > 0.1: return "📈 Mild Optimism"
        if score > -0.1: return "😐 Neutral - Mixed Signals"
        if score > -0.4: return "📉 Mild Concern"
        return "😱 Extreme Fear / Panic"

# Global Instance
sentiment_engine = SentimentEngine()
