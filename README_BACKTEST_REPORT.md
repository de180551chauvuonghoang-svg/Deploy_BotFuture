# Báo cáo Backtest Chiến lược SMC (Smart Money Concepts)

## Tổng quan Chiến lược

Chiến lược **Advanced SMC** là một hệ thống giao dịch chuyên nghiệp dựa trên các khái niệm dòng tiền thông minh (Smart Money Concepts), kết hợp đa khung thời gian (Multi-Timeframe) để lọc tín hiệu chất lượng cao.

### Các thành phần chính:

1.  **Market Regime (Khung 1H):** Xác định trạng thái thị trường (Trending, Sideways, Volatile) để tránh giao dịch trong điều kiện xấu.
2.  **Macro Structure (Khung 4H):** Xác định xu hướng chính (Bullish/Bearish) để đảm bảo luôn giao dịch thuận xu hướng.
3.  **Key Zones (OB & FVG):** Tìm kiếm các vùng Order Block và Fair Value Gap trên khung 1H làm điểm tựa vào lệnh.
4.  **Liquidity Sweep (Khung 15m):** Kiểm tra quét thanh khoản để xác nhận sự tham gia của Smart Money.
5.  **Quality Scoring:** Mỗi setup được chấm điểm dựa trên sự hội tụ của nhiều yếu tố (Confluences). Chỉ các lệnh có điểm từ 6.0 trở lên mới được thực thi.
6.  **Quản lý rủi ro thông minh:**
    - Sử dụng ATR để tính Stop Loss.
    - Take Profit 3 giai đoạn: Chốt 33% tại TP1, 33% tại TP2 và giữ 34% còn lại cho TP3.
    - Dịch Stop Loss về Breakeven sau khi TP1 được khớp.

---

## Thông số Backtest

- **Thời gian:** 180 ngày (6 tháng)
- **Số lượng cặp tiền:** 6 (BTC, ETH, SOL, BNB, XRP, AVAX)
- **Vốn ban đầu:** 10,000 USDT mỗi cặp (Tổng 60,000 USDT)
- **Khung thời gian thực thi:** 15m (với dữ liệu tham chiếu 1H và 4H)

---

## Kết quả Tổng quát (Global Report)

| Thông số                    | Giá trị             |
| :-------------------------- | :------------------ |
| **Tổng lợi nhuận (PnL)**    | **+20,134.17 USDT** |
| **Tỷ suất lợi nhuận (ROI)** | **+33.56%**         |
| **Tỷ lệ thắng (Win Rate)**  | **61.42%**          |
| **Tổng số lệnh**            | **451**             |
| **Số dư cuối cùng**         | **80,134.17 USDT**  |

---

## Kết quả chi tiết theo từng cặp tiền

| Cặp tiền      | Vốn cuối cùng (USDT) | Lợi nhuận (USDT) | ROI (%) |
| :------------ | :------------------- | :--------------- | :------ |
| **ETH/USDT**  | 15,401.74            | +5,401.74        | +54.02% |
| **AVAX/USDT** | 14,361.89            | +4,361.89        | +43.62% |
| **SOL/USDT**  | 13,582.13            | +3,582.13        | +35.82% |
| **BTC/USDT**  | 13,484.38            | +3,484.38        | +34.84% |
| **XRP/USDT**  | 12,448.88            | +2,448.88        | +24.49% |
| **BNB/USDT**  | 10,855.15            | +855.15          | +8.55%  |

---

## Đánh giá & Kết luận

1.  **Hiệu quả cao:** Win rate > 60% là cực kỳ ấn tượng đối với một chiến lược SMC tự động hóa.
2.  **Khả năng mở rộng:** Chiến lược hoạt động tốt trên nhiều loại tài sản khác nhau, đặc biệt hiệu quả với **ETH** và **AVAX**.
3.  **Quản lý rủi ro:** Hệ thống chốt lời từng phần (Partial Close) và dời SL giúp bảo vệ lợi nhuận và giảm thiểu rủi ro tâm lý.
4.  **Tối ưu:** Cặp BNB có hiệu suất thấp nhất, có thể cần điều chỉnh lại các tham số OB/FVG riêng cho cặp này hoặc lọc thêm điều kiện Momentum.

**Kết luận:** Chiến lược hiện tại đã sẵn sàng để triển khai trên tài khoản thực hoặc tiếp tục Forward Test trong môi trường giao dịch thực tế.
