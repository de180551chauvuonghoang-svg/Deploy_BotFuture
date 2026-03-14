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

## 📂 Thư mục Dự án (Cấu trúc mới)

```text
/
├── main.py              # File chính khởi động Bot
├── config/              # Cấu hình API và tham số Risk
├── core/                # Lõi thực thi (Exchange & Trading Engine)
├── strategy/            # Các module thuật toán SMC
├── dashboard/           # Giao diện Dashbord Streamlit
├── tools/               # Công cụ phân tích & Dự báo tín hiệu
├── backtest/            # Các script test và Báo cáo (Reports)
├── logs/                # Lưu trữ nhật ký giao dịch & backtest
├── tests/               # Script kiểm tra kết nối hệ thống
└── docs/                # Tài liệu kỹ thuật
```

## 🛠️ Hướng dẫn Sử dụng nhanh
1.  **Chạy Bot Dry Run**: `python main.py`
2.  **Mở Dashboard**: `streamlit run dashboard/app.py`
3.  **Xem dự báo tín hiệu**: `python tools/predict_signals.py`
4.  **Giám sát Real-time**: `python tools/signal_monitor.py`

---
*Cảnh báo rủi ro: Giao dịch Crypto Futures có rủi ro cao. Bot này được thiết kế để hỗ trợ ra quyết định dựa trên thuật toán, hãy luôn kiểm soát vốn của mình.*
