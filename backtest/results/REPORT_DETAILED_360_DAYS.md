# BÁO CÁO BACKTEST CHI TIẾT CHIẾN LƯỢC SMC (360 NGÀY)

## 1. Tóm tắt Hiệu suất (Global Performance)

Chiến lược **Advanced SMC** đã hoàn thành kiểm thử trên 6 cặp tiền tệ Crypto Futures hàng đầu trong thời gian 1 năm.

- **Thời gian:** 360 Ngày (1 năm dữ liệu lịch sử)
- **Vốn khởi đầu:** 60,000 USDT (10,000 USDT cho mỗi cặp)
- **Số dư cuối cùng:** **79,667.72 USDT**
- **Tổng lợi nhuận (PnL):** **+19,667.72 USDT**
- **Tỷ suất lợi nhuận (ROI):** **+32.78%**
- **Tỷ lệ thắng (Win Rate):** **54.49%**
- **Tổng số lệnh:** **925 lệnh**

---

## 2. Kết quả chi tiết theo từng Cặp tiền

| Cặp tiền      | Vốn cuối (USDT) | Lợi nhuận (USDT) | ROI (%) | Nhận xét                                                     |
| :------------ | :-------------- | :--------------- | :------ | :----------------------------------------------------------- |
| **SOL/USDT**  | 15,339.19       | +5,339.19        | +53.39% | Hiệu suất cực tốt, xu hướng SMC rõ ràng.                     |
| **BTC/USDT**  | 15,236.34       | +5,236.34        | +52.36% | Rất ổn định, ít biến động nhiễu.                             |
| **AVAX/USDT** | 14,620.16       | +4,620.16        | +46.20% | Đột phá so với lần test trước (tăng từ 1.5% lên 46%).        |
| **ETH/USDT**  | 13,403.39       | +3,403.39        | +34.03% | Lợi nhuận khá, tuân thủ cấu trúc thị trường tốt.             |
| **XRP/USDT**  | 10,884.96       | +884.96          | +8.85%  | Biến động khó lường, nhưng vẫn có lãi.                       |
| **BNB/USDT**  | 10,183.67       | +183.67          | +1.84%  | Cực khó đánh SMC do tính chất token sàn, tuy nhiên không lỗ. |

---

## 3. Phân tích Chiến lược & Cải tiến

So với lần backtest 360 ngày trước đó, kết quả hiện tại có sự cải thiện đáng kể:

- **Lợi nhuận tăng:** Từ **18,446 USDT** lên **19,667 USDT**.
- **Cải thiện AVAX:** Việc cập nhật logic tính toán cấu trúc thị trường (fix lỗi EMA200 rỗng) đã giúp cặp AVAX tận dụng được các sóng lớn thay vì bỏ qua tín hiệu như trước.
- **Tần suất giao dịch:** Tăng từ 815 lên 925 lệnh (khoảng **2.5 lệnh/ngày** cho toàn bộ portfolio). Tần suất cao hơn cho phép lãi kép hoạt động tốt hơn.

---

## 4. Đặc điểm lệnh giao dịch

1.  **Quản lý rủi ro:** Sử dụng SL dựa trên ATR và các vùng OB/FVG giúp giảm thiểu tối đa rủi ro mỗi lệnh (Risk 1-2%).
2.  **Take Profit 3 giai đoạn:**
    - TP1 (khóa lợi nhuận & dời SL về BE)
    - TP2 (khóa thêm lợi nhuận & dời SL lên TP1)
    - TP3 (gồng lãi tối đa)
      Cơ chế này giúp bot sống sót qua những cú quay đầu của thị trường nhưng vẫn ăn được cả con sóng lớn.

## 5. Kết luận & Khuyến nghị

- **Chiến lược đạt lợi nhuận bền vững:** ROI 32%/năm là mức hiệu suất chuyên nghiệp và an toàn cho một hệ thống giao dịch tự động.
- **Ưu tiên đầu tư:** Nên tập trung vốn lớn cho **SOL, BTC và AVAX** (3 cặp này đóng góp ~75% tổng lợi nhuận).
- **Tránh thông báo:** Quá trình backtest đã được cấu hình để không làm phiền Discord của bạn, đảm bảo tốc độ tính toán nhanh nhất.

**Báo cáo này đã được lưu lại để bạn tham khảo.**
