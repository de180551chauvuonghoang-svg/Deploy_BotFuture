# Hướng dẫn chi tiết đăng ký Oracle Cloud "Always Free"

Đây là các bước để bạn có một VPS cấu hình mạnh (4 CPU, 24GB RAM) hoàn toàn miễn phí.

## Bước 1: Đăng ký tài khoản
1. Truy cập: [oracle.com/cloud/free/](https://www.oracle.com/cloud/free/)
2. Nhấn **Start for free**.
3. Nhập Email và chọn Quốc gia (Vietnam).
4. **Lưu ý quan trọng:** Chọn "Home Region" gần Vietnam nhất để tốc độ bot nhanh nhất (ví dụ: **Singapore** hoặc **Tokyo**). Sau khi chọn xong bạn sẽ không đổi được.

## Bước 2: Xác thực thẻ thanh toán
- Bạn cần một thẻ **Visa** hoặc **Mastercard** (Credit hoặc Debit đều được).
- Oracle sẽ thực hiện một giao dịch khoảng 1$ (23.000đ - 30.000đ) để kiểm tra thẻ, sau đó sẽ hoàn lại tiền ngay lập tức (thường trong vài phút đến 1 tiếng).
- Đảm bảo thẻ của bạn đã bật thanh toán quốc tế và có sẵn ít nhất 50k trong tài khoản.

## Bước 3: Tạo máy chủ (Compute Instance)
1. Trong giao diện Console, chọn **Create a VM instance**.
2. **Chọn Image và Shape:**
   - Nhấn **Edit** ở phần Image and Shape.
   - Chọn **Image**: Oracle Linux 8 (mặc định) hoặc Ubuntu 22.04.
   - Chọn **Shape**: Nhấn **Change Shape** -> Chọn **Ampere (ARM-based)**.
   - Kéo thanh OCPU lên 2 hoặc 4, RAM lên 8GB hoặc 24GB (Tùy nhu cầu, Always Free cho tối đa 24GB).
3. **Networking:** Để mặc định.
4. **SSH Keys:** 
   - Nhấn **Save Private Key** về máy tính (Rất quan trọng để đăng nhập sau này).
5. Nhấn **Create**.

## Bước 4: Mở Port Firewall (Để vào Dashboard)
Máy chủ Oracle rất bảo mật, bạn phải mở port thủ công trên giao diện Web:
1. Vào phần **Instance Details** -> Nhấn vào **Subnet** (ví dụ: Public Subnet-...).
2. Nhấn vào **Security Lists** -> Chọn cái mặc định.
3. Nhấn **Add Ingress Rules**:
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: `TCP`
   - **Destination Port Range**: `8501` (Của Dashboard)
   - Nhấn **Add**.

## Bước 5: Đăng nhập và cài đặt
Sử dụng file `.key` đã tải ở bước 3 để đăng nhập qua SSH (User mặc định là `ubuntu` hoặc `opc`).

Sau đó quay lại file [deployment.md](./deployment.md) để cài đặt Docker và chạy Bot.
