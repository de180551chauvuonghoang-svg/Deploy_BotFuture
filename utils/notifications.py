import os
import requests
from config.config import Config
from core.logger import logger

def send_discord_notification(message):
    if not Config.DISCORD_WEBHOOK_URL or os.environ.get('IS_BACKTEST') == 'true':
        return
        
    try:
        data = {"content": message}
        response = requests.post(Config.DISCORD_WEBHOOK_URL, json=data)
        if response.status_code != 204:
            logger.error(f"Failed to send Discord notification: {response.text}")
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")

def notify_trade_opened(symbol, side, price, size, sl, tp):
    msg = f"🚀 **Trade Opened**\n" \
          f"Symbol: `{symbol}`\n" \
          f"Direction: `{side.upper()}`\n" \
          f"Entry: `{price}`\n" \
          f"Size: `{size:.4f}`\n" \
          f"SL: `{sl:.2f}` | TP: `{tp:.2f}`"
    send_discord_notification(msg)

def notify_trade_closed(symbol, pnl, reason):
    msg = f"🏁 **Trade Closed**\n" \
          f"Symbol: `{symbol}`\n" \
          f"PnL: `{pnl:.2f} USDT`\n" \
          f"Reason: `{reason}`"
    send_discord_notification(msg)
