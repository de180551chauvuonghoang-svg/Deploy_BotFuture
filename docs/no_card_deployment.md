# Hướng dẫn chạy Bot 24/24 MIỄN PHÍ (Không cần thẻ tín dụng)

Nếu bạn không muốn sử dụng thẻ Visa, giải pháp ổn định nhất là sử dụng chính máy tính của bạn (hoặc máy tính cũ) và biến nó thành một "Server tại gia".

## Giải pháp 1: Sử dụng Email .EDU (Dành cho bạn - KHUYÊN DÙNG)
Vì bạn có mail .edu, bạn có thể nhận 100$-200$ credit để thuê VPS xịn mà không cần thẻ.
- Xem chi tiết tại: [student_vps_guide.md](./student_vps_guide.md)

## Giải pháp 2: Sử dụng PC/Laptop tại gia + Cloudflare Tunnel

### Bước 1: Cài đặt Docker Desktop
Tải và cài đặt tại: [docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)

### Bước 2: Chạy Bot bằng Docker
1. Mở Terminal (PowerShell/CMD) tại thư mục bot.
2. Chạy lệnh: `docker-compose up -d --build`

### Bước 3: Đưa Dashboard lên Internet (Miễn phí & Bảo mật)
Để truy cập Dashboard từ xa mà không cần mở Port modem (rất nguy hiểm), hãy dùng **Cloudflare Tunnel**:
1. Đăng ký tài khoản [Cloudflare](https://dash.cloudflare.com/) (Miễn phí).
2. Vào phần **Zero Trust** -> **Networks** -> **Tunnels**.
3. Tạo một Tunnel mới (ví dụ tên: `bot-trade`).
4. Cài đặt Cloudflare Connector lên máy tính của bạn (theo hướng dẫn trên web Cloudflare).
5. Cấu hình **Public Hostname**:
   - Subdomain: `bot`
   - Domain: (Sử dụng một domain miễn phí hoặc domain bạn có)
   - Service: `http://localhost:8501`

Bây giờ bạn có thể vào `https://bot.yourdomain.com` để xem bot trade từ bất cứ đâu.

---

## Giải pháp 2: Sử dụng VPS cho Sinh viên (Nếu có email .edu)

Nếu bạn là sinh viên hoặc có bạn bè là sinh viên, bạn có thể mượn email `.edu` để đăng ký:
- **Microsoft Azure for Students**: Tặng 100$ (Dùng được khoảng 8-12 tháng VPS cấu hình thấp).
- Không yêu cầu thẻ tín dụng.
- Đăng ký: [azure.microsoft.com/free/students/](https://azure.microsoft.com/free/students/)

---

## Giải pháp 3: Dùng thử VPS Việt Nam (Ngắn hạn)

Bạn có thể tìm các nhà cung cấp như **DataOnline.vn**. Họ thường cho dùng thử vài ngày đến 1 tuần bằng cách xác thực qua Số điện thoại hoặc Zalo.
- Cách này chỉ mang tính chất dùng thử, không ổn định lâu dài.
