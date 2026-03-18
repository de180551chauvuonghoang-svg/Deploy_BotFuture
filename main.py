from core.engine import TradingEngine
from core.logger import logger
import sys
import warnings
import pandas as pd

# Silence annoying pandas warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
pd.set_option('future.no_silent_downcasting', True)

def main():
    """
    Main entry point for the Advanced SMC Trading Bot.
    Initializes the engine and starts the main trading loop.
    """
    try:
        logger.info("==================================================")
        logger.info("  ADVANCED SMC TRADING BOT IS STARTING [WS]")
        logger.info("  Regime: Multi-Timeframe (4H, 1H, 15M)")
        logger.info("  Modules: Structure, Order Block, FVG, Confluence")
        logger.info("  Dashboard: http://localhost:8501")
        logger.info("==================================================")
        
        import asyncio
        engine = TradingEngine()
        asyncio.run(engine.start())
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
