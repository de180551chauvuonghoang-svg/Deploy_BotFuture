# Báo cáo Backtest Chiến lược SMC - 360 Ngày

## Tổng quan Chiến lược

Chiến lược **Advanced SMC** (Smart Money Concepts) đã được kiểm thử trên dữ liệu lịch sử trong vòng **1 năm (360 ngày)** để đánh giá hiệu suất dài hạn và khả năng chống chịu qua các chu kỳ thị trường khác nhau.

### Đặc điểm hệ thống:

- **Thời gian test:** 360 ngày.
- **Dữ liệu:** BTC, ETH, SOL, BNB, XRP, AVAX (Vốn 10k mỗi cặp).
- **Cơ chế:** Đa khung thời gian (4H xu hướng, 1H vùng giá, 15m vào lệnh).
- **Quản lý vốn:** Chốt lời 3 phần, Trailing Stop Loss về BE sau TP1.

---

## Kết quả Tổng quát (Global Report - 360 Days)

| Thông số                    | Giá trị             |
| :-------------------------- | :------------------ |
| **Tổng lợi nhuận (PnL)**    | **+18,446.21 USDT** |
| **Tỷ suất lợi nhuận (ROI)** | **+30.74%**         |
| **Tỷ lệ thắng (Win Rate)**  | **55.58%**          |
| **Tổng số lệnh**            | **815**             |
| **Số dư cuối cùng**         | **78,446.21 USDT**  |

---

## Kết quả chi tiết theo từng cặp tiền

| Cặp tiền      | Vốn cuối cùng (USDT) | Lợi nhuận (USDT) | ROI (%) |
| :------------ | :------------------- | :--------------- | :------ |
| **SOL/USDT**  | 16,508.26            | +6,508.26        | +65.08% |
| **BTC/USDT**  | 15,405.56            | +5,405.56        | +54.06% |
| **ETH/USDT**  | 13,927.41            | +3,927.41        | +39.27% |
| **XRP/USDT**  | 11,828.19            | +1,828.19        | +18.28% |
| **BNB/USDT**  | 10,623.60            | +623.60          | +6.24%  |
| **AVAX/USDT** | 10,153.18            | +153.18          | +1.53%  |

---

## Phân tích & So sánh

1.  **Tính ổn định:** Trong 360 ngày, bot thực hiện tổng cộng 815 lệnh, trung bình **2.26 lệnh/ngày**. Tần suất này khá ổn định so với kết quả 180 ngày trước đó.
2.  **Hiệu suất SOL & BTC:** Điểm sáng nhất trong báo cáo 1 năm là **SOL** và **BTC**, cho thấy chiến lược SMC cực kỳ hiệu quả với các đồng coin có vốn hóa lớn và xu hướng mạnh.
3.  **Tỷ lệ thắng:** Tỷ lệ thắng giảm từ 61% (180 ngày) xuống còn **55.58%** (360 ngày). Điều này cho thấy trong giai đoạn từ 360 đến 180 ngày trước, thị trường có thể đã có nhiều biến động hoặc sideway khiến các vùng OB/FVG bị vi phạm nhiều hơn.
4.  **Kết luận:** Mặc dù tỷ lệ thắng giảm nhẹ, nhưng tổng PnL vẫn dương hơn **18,400 USDT**, chứng minh chiến lược vẫn có lợi nhuận bền vững trong dài hạn.

**Lời khuyên:** Nên ưu tiên chạy bot trên các cặp **SOL, BTC và ETH** để tối ưu hóa lợi nhuận tốt nhất dựa trên dữ liệu lịch sử.
