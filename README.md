# 🚀 Advanced SMC Crypto Futures Trading Bot

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Strategy: SMC](https://img.shields.io/badge/Strategy-Smart%20Money%20Concepts-green.svg)]()
[![Backtest: 111.79%](https://img.shields.io/badge/Backtest-111.79%25%20PnL-brightgreen.svg)]()

A professional-grade, multi-timeframe cryptocurrency futures bot implementing **Smart Money Concepts (SMC)** logic. Designed for high-conviction trades with institutional-level risk management.

---

## 💎 Strategy Engine: Smart Money Concepts (SMC)

Our bot doesn't just follow simple indicators; it decodes market structure like a pro:

- **Multi-Timeframe Analysis**: Macro bias on **4H**, structure on **1H**, and entries/sweeps on **15M**.
- **Order Blocks (OB)**: Detects institutional zones where massive buy/sell orders are expected.
- **Fair Value Gaps (FVG)**: Identifies liquidity imbalances that price often seeks to fill.
- **Liquidity Sweeps**: Detects "Stop Hunts" to enter after retail traders are flushed out.
- **SMC Quality Score**: Each setup is scored (1-10) based on confluence.

---

## 📈 Backtest Performance (Live-Trader Mock)

| Metric              | Portfolio Result (700 Days)     |
| :------------------ | :------------------------------ |
| **Duration**        | 700 Days (Last ~2 Years)        |
| **Initial Capital** | 10,000 USDT                     |
| **Net Profit**      | **+11,179.50 USDT (+111.79%)**  |
| **Win Rate**        | 50.58% (High-precision entries) |
| **Profit Factor**   | 1.85+                           |
| **Max Drawdown**    | 21.20%                          |
| **Symbols**         | BTC, ETH, SOL, BNB, XRP, AVAX   |

---

## 📊 Dynamic Control Dashboard

The bot comes with a premium **Streamlit** dashboard for monitoring and manual control:

- **Real-time Metrics**: Track Account Balance, Active Positions, and Unrealized PnL.
- **Active Management**: View SL/TP targets and close positions with a single click.
- **Market Hub**: Visual charts for SMC structures (OB/FVG) and signal scores.
- **Financial Reports**: Export your trade history and performance metrics to **Excel**.

---

## 🛠 Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Configuration (`.env`)

Add your API keys and Discord webhook:

```bash
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
TRADING_PAIRS=BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT,AVAX/USDT
PAPER_TRADING=True
```

### 3. Execution

**Run both Bot and Dashboard (Windows PowerShell):**

```powershell
$env:PYTHONPATH = "."; Start-Process python -ArgumentList "main.py" -NoNewWindow; streamlit run dashboard/app.py
```

**Run Backtest Portfolio (800 Days):**

```bash
python backtest/run_backtest_portfolio.py
```

---

## 🛡 Risk Management

- **Smart SL/TP**: ATR-based buffers and Order Block protection.
- **Partial Takes**: Automatic 33% profit taking at TP1, TP2, and TP3.
- **Breakeven Stops**: Automatically moves SL to breakeven after TP1 is hit.
- **Dynamic Sizing**: Scales position size up to 3% for Alpha setups (9.5+ score).

---

## 📜 Disclaimer

_Trading cryptocurrencies involves significant risk. This bot is for educational and simulation purposes. Past performance is not indicative of future results. Use at your own risk._

---

Developed with ❤️ by the **Antigravity AI Team**.

streamlit run dashboard/app.py

python main.py
