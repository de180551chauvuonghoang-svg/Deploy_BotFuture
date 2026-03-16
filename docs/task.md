# Danh sách nhiệm vụ Tích hợp AI (Chi tiết)

- [x] **Tối ưu hóa Chiến thuật Gồng lời (Hot-fix)**
    - [x] Nghiên cứu logic "Soft Breakeven" (Dời SL bảo vệ 80% vốn thay vì 100% tại TP1)
    - [x] Áp dụng bộ lọc ATR-Buffer cho Stop Loss sau khi chốt lời từng phần
    - [x] Kiểm tra thực tế trên Dashboard

- [ ] **Giai đoạn 1: Bộ lọc tín hiệu AI (Machine Learning)**
    - [x] Tạo [ai/data_collector.py](file:///c:/Users/Shi%20Iu%20Oi/Desktop/bottradefuture/ai/data_collector.py) thực hiện trích xuất Feature (RSI, ATR, OB Vol, FVG Size)
    - [x] Tiền xử lý dữ liệu và gắn nhãn Win/Loss từ lịch sử giao dịch (5019 mẫu)
    - [x] Xây dựng mô hình XGBoost với Hyperopt tối ưu hóa (Độ chính xác: 81%)
    - [x] Viết API nội bộ cho [ai/inference.py](file:///c:/Users/Shi%20Iu%20Oi/Desktop/bottradefuture/ai/inference.py) để dự đoán xác suất
    - [x] Tích hợp logic chặn lệnh nếu `AI_Confidence < 70%`
    - [x] Chạy Backtest 90 ngày để xác minh độ hiệu quả của bộ lọc (Kết quả: Winrate 64%, PF 2.15)

- [x] **Giai đoạn 2: Phân tích tâm lý AI (News & Social)**
    - [x] Đăng ký và cấu hình NewsAPI / CryptoPanic API
    - [x] Triển khai module `ai/sentiment_engine.py` sử dụng FinBERT
    - [x] Tích hợp "Sentiment Safety Switch" vào engine chính
    - [x] Hiển thị bản tin tâm lý tóm tắt lên Dashboard Streamlit
    - [x] Kiểm tra phản ứng của Bot với tin tức giả lập (Extreme Fear)

- [x] **Giai đoạn 3: Học tăng cường (Tự tối ưu hóa)**
    - [x] Thiết lập môi trường mô phỏng (Gym-like) cho RL
    - [x] Huấn luyện Agent PPO điều chỉnh `MIN_SCORE` và `RISK_PCT`
    - [x] Triển khai cơ chế tự động ghi đè [config.py](file:///c:/Users/Shi%20Iu%20Oi/Desktop/bottradefuture/config/config.py) theo khuyến nghị của AI
    - [x] Kiểm tra độ ổn định của lợi nhuận sau khi tối ưu hóa tham số

- [x] **Nâng cấp UI Lộ trình TP (4 Giai đoạn)**
    - [x] Bổ sung cột Moonshot 🚀 vào Dashboard
    - [x] Triển khai logic làm nổi bật mục tiêu tiếp theo (Next Target)
    - [x] Đồng bộ trạng thái chốt lời TP1/TP2/TP3 thời gian thực

- [x] **Giai đoạn 4: Hoàn thiện & Dashboard**
    - [x] Thiết kế lại giao diện Dashboard hiển thị AI Metrics
    - [x] Tích hợp hệ thống cảnh báo Discord về tâm lý thị trường
    - [x] Tổng kết và đóng dự án feature_ai
