# Tối ưu hóa Stop Loss (SL) sau TP1 - Logic "Soft Breakeven"

Cải thiện tỷ lệ giữ lệnh sau khi chốt lời từng phần, tránh bị quét Stop Loss quá sớm do biến động nhỏ xung quanh điểm vào lệnh (Entry).

## Proposed Changes

### [Risk Management]
#### [MODIFY] [smart_risk.py](file:///c:/Users/Shi%20Iu%20Oi/Desktop/bottradefuture/risk/smart_risk.py)
- Thay đổi logic dời SL tại TP1: Thay vì dời về điểm hòa vốn (BE), Bot sẽ dời về một mức an toàn dựa trên ATR (**Entry - 0.7x ATR** cho LONG) để tạo khoảng trống cho giá dao động.
- Chỉ dời về Full Breakeven hoặc cao hơn khi giá tiến gần đến TP2.

### [Core Engine]
#### [MODIFY] [engine.py](file:///c:/Users/Shi%20Iu%20Oi/Desktop/bottradefuture/core/engine.py)
- Cập nhật hàm `process_active_position` để không ghi đè cứng SL về Entry ngay khi chạm TP1, mà để cho [update_dynamic_exit](file:///c:/Users/Shi%20Iu%20Oi/Desktop/bottradefuture/risk/smart_risk.py#65-102) xử lý linh hoạt hơn.

## Verification Plan

### Automated Tests
- Chạy Backtest trên cặp coin có độ biến động cao (như TAO hoặc SOL) để xem liệu logic mới có giúp giữ lệnh lâu hơn sau TP1 không.

### Manual Verification
- Theo dõi Dashboard để xác nhận SL không còn "nhảy" sát nút Entry ngay khi TP1 vừa khớp.
