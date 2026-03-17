# Hướng dẫn Deploy Bot 24/7 (Sử dụng Docker)

Để chạy bot online 24/24, tôi khuyên bạn nên sử dụng một máy chủ ảo (VPS) chạy Linux (như Ubuntu).

## 1. Lựa chọn VPS Miễn Phí (Không cần thẻ - No Credit Card)
Nếu bạn không muốn sử dụng thẻ Visa/Mastercard, đây là các giải pháp thay thế:

### Option A: Sử dụng VPS Việt Nam (Dùng thử)
Một số nhà cung cấp Việt Nam cho phép dùng thử không cần thẻ (thường qua xác thực số điện thoại):
- **DataOnline.vn**: Có gói dùng thử miễn phí, kích hoạt tự động.
- **Cloudfly.vn / Vietnamsol.com**: Đôi khi có các chương trình dùng thử ngắn hạn.

### Option B: Tận dụng PC cũ / Laptop cũ (Tốt nhất cho "Free" vĩnh viễn)
Nếu bạn có một máy tính cũ hoặc máy tính luôn bật, bạn có thể biến nó thành server:
- **Ưu điểm**: Không cần thẻ, không giới hạn cấu hình.
- **Cách làm**: Cài đặt Docker lên máy đó, sau đó dùng **Cloudflare Tunnel** (miễn phí) để truy cập Dashboard từ xa qua internet.

### Option C: Microsoft Azure cho Sinh viên (Nếu bạn có email .edu)
- Miễn phí 100$ credit và không cần thẻ tín dụng.
- Đăng ký tại: [azure.microsoft.com/free/students/](https://azure.microsoft.com/free/students/)

## 2. Cài đặt Docker trên VPS
Sau khi đăng nhập vào VPS (thường dùng phần mềm **Termius** hoặc **Putty** trên Windows), hãy chạy các lệnh sau:

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt docker
sudo apt install docker.io docker-compose -y

# Khởi động docker
sudo systemctl start docker
sudo systemctl enable docker
```

## 3. Upload Source Code
Upload code lên VPS sử dụng Git hoặc SCP. (Ví dụ dùng Git):
```bash
git clone <your-repo-url>
cd bottradefuture
```

## 4. Cấu hình Environment
Tạo file `.env` trên server và điền API Key của bạn:
```bash
cp .env.example .env # Nếu có file example
nano .env
```

## 5. Chạy Bot với Docker Compose
Chạy lệnh này để build và chạy tất cả các dịch vụ (Bot + Dashboard) dưới dạng nền (background):

```bash
docker-compose up -d --build
```

## 6. Kiểm tra
- **Xem log bot**: `docker logs -f trading-bot`
- **Xem log dashboard**: `docker logs -f trading-dashboard`
- **Truy cập Dashboard**: Mở trình duyệt và vào địa chỉ `http://<IP_CỦA_VPS>:8501`

## 7. Lưu ý an toàn
- Đảm bảo mở port `8501` trong firewall của VPS để truy cập dashboard.
- Không bao giờ chia sẻ API Secret của bạn.
- Sử dụng **Binance Testnet** trước khi chạy Live.
