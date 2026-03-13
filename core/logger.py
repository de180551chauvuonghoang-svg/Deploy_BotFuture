import logging
import sys
from config.config import Config

def setup_logger(name="trading_bot"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    # Force UTF-8 for console output to support emojis and international characters
    import io
    wrapped_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    ch = logging.StreamHandler(wrapped_stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File Handler
    fh = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    return logger

logger = setup_logger()
