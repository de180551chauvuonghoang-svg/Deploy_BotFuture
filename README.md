# 🚀 Advanced Futures Trading Bot

A production-ready futures trading bot built with Python, CCXT, and Pandas-TA.

## ✨ Features

- **Multi-Exchange Support**: Built on CCXT (supports Binance, Bybit, OKX).
- **Trend-Following Strategy**: Robust logic using EMA crossovers and RSI momentum.
- **Advanced Risk Management**:
  - Dynamic position sizing.
  - ATR-based Stop Loss & Take Profit.
  - Max Drawdown & Daily Loss safeguards.
- **Monitoring & Alerts**: Discord notifications for every trade action.
- **Backtesting Module**: Integrated backtester to validate strategies on historical data.
- **Modular Architecture**: Easy to extend with new strategies or risk rules.

## 🛠 Setup

### 1. Requirements

Ensure you have Python 3.10+ installed.

```bash
pip install -r requirements.txt
```

### 2. Configuration

Rename `.env.example` (or edit the existing `.env`) and add your API keys:

- `BINANCE_API_KEY`: Your exchange API key.
- `BINANCE_SECRET`: Your exchange secret key.
- `DISCORD_WEBHOOK_URL`: For alerts.

### 3. Usage

#### Run Live/Paper Trading

By default, the bot starts in **Paper Trading** mode (`PAPER_TRADING=True` in `.env`).

```bash
python main.py
```

#### Backtesting

To run a backtest on a specific symbol:

```bash
python run_backtest.py
```

### 📊 Backtest Report (180 Days)

We ran a backtest for the last 180 days on **BTC/USDT** (1h timeframe) using the **TrendFollowing** strategy.

| Metric              | Value                        |
| :------------------ | :--------------------------- |
| **Initial Capital** | 10,000 USDT                  |
| **Final Capital**   | 9,745.67 USDT                |
| **Total Net PnL**   | -254.33 USDT (-2.54%)        |
| **Win Rate**        | 28.98%                       |
| **Total Trades**    | 176                          |
| **Max Drawdown**    | 5.30%                        |
| **Time Period**     | Last 180 Days (1h Timeframe) |

> [!TIP]
> **Performance Analysis**: A win rate of ~29% is common for trend-following strategies which wait for big moves. The slight loss indicates the market might have been range-bound during this period. Try adjusting the EMA periods (`ema_fast` and `ema_slow`) to optimize for current market conditions.

## ⚠️ Security

- Never share your `.env` file.
- Use API keys with **READ** and **TRADE** permissions only.
- **Disable withdrawals** on your API keys.

## 📈 Monitoring

Logs are saved to `trading.log`. Real-time alerts are sent to your Discord channel.

---

_Disclaimer: Trading cryptocurrencies involves significant risk. This bot is for educational purposes. Use at your own risk._

# Run Dashboard
$env:PYTHONPATH = "."; streamlit run dashboard/app.py --server.port 8501 --browser.gatherUsageStats false

# run backtest
python run_backtest.py

# Dry-run project
python main.py