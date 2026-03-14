# 🚀 Advanced SMC Trading Bot v2.0 - Sniper Elite Edition

Hệ thống giao dịch tự động AI dựa trên phương pháp **Smart Money Concepts (SMC)** được tối ưu hóa cho thị trường Crypto Futures trên sàn Binance. Bot sử dụng mô hình đa khung thời gian (MTF) để xác định xu hướng dòng tiền lớn và thực hiện các lệnh Sniper với tỷ lệ R/R cực cao.

## 📈 Kết quả Backtest Danh mục (90 Ngày Gần Nhất)
> [!IMPORTANT]
> Đây là kết quả test thực tế trên **100+ cặp coin** với các thông số trượt giá (0.1%) và phí giao dịch (0.04%) sát với thực tế.

- **Vốn ban đầu**: 1,300 USDT
- **Số dư cuối**: **2,943.47 USDT**
- **Lợi nhuận ròng**: `+1,643.47 USDT` (**+126.42%**)
- **Tỷ lệ thắng (Win Rate)**: **67.19%**
- **Sụt giảm tài khoản tối đa (Max DD)**: **11.40%**
- **Profit Factor**: **4.28**

---

## 🛡️ Chiến thuật Giao dịch & Quản trị Rủi ro

Hệ thống hiện tại là sự kết hợp giữa **Phân tích kỹ thuật chuyên sâu** và **Logic quản trị vốn chủ động**:

### 1. Phân tích Đa khung thời gian (MTF Strategy)
*   **4H Trend (Macro)**: Sử dụng cấu hình Market Structure (BOS/CHOCH) cùng EMA 200 để xác định thiên hướng (Bias). Chỉ giao dịch thuận xu hướng lớn.
*   **1H Zone (Execution)**: Tìm kiếm các vùng mất cân bằng thanh khoản **Fair Value Gap (FVG)** và các khối lệnh **Order Block (OB)** để xác định điểm entry tối ưu.
*   **15M Sniper**: Dùng để lọc nhiễu, xác nhận lực mua/bán và kiểm tra **Liquidity Sweep** (quét thanh khoản) trước khi mở lệnh.

### 2. Quản trị lệnh thông minh (Smart Exit Logic)
Bot không giữ lệnh cố định mà chủ động quản lý rủi ro ngay khi lệnh đang chạy:
*   **Chốt lời 3 phần**: 
    *   **TP1 (33%)**: Khóa lợi nhuận sớm để bảo vệ tâm lý.
    *   **TP2 (33%)**: Chốt lời chính tại vùng cản 1H.
    *   **TP3 (34%)**: Gồng Moonshot cho các đợt bùng nổ mạnh.
*   **Break-even**: Ngay khi giá chạm TP1, Stop Loss sẽ được dời về giá vào lệnh (Entry Price) để đảm bảo lệnh trở nên "Không rủi ro".
*   **Trailing Stop (ATR)**: Sử dụng ATR (biến động thực tế) để bám theo xu hướng, khóa thêm lợi nhuận nếu giá tiếp tục đi lên mà chưa tới TP2/TP3.

### 3. Cơ chế Chống ngâm lệnh (Anti-Stuck Mechanism)
Giải quyết vấn đề kẹt vốn và phí funding fee:
*   **Hard Time-Stop (48h)**: Tự động đóng lệnh sau 2 ngày nếu giá không đạt mục tiêu để giải phóng vốn.
*   **Stagnation Exit (12h)**: Nếu giá đi ngang trong 12 giờ quanh Entry (+/- 0.5%), Bot sẽ tự động cắt lệnh vì setup này đã mất xung lực.

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
