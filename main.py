from core.engine import TradingEngine
from core.logger import logger
import sys

def main():
    try:
        logger.info("==================================================")
        logger.info("BOT IS RUNNING")
        logger.info("DASHBOARD URL: http://localhost:8501")
        logger.info("==================================================")
        engine = TradingEngine()
        engine.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
