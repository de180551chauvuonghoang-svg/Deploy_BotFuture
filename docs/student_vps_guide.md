# Hướng dẫn nhận VPS FREE bằng Email .EDU (Không cần thẻ)

Vì bạn có email `.edu`, đây là cách tốt nhất và uy tín nhất để có VPS chạy bot mà không cần thẻ tín dụng.

## 1. Microsoft Azure for Students (Nên dùng nhất)
Chương trình này tặng bạn **100$ Credit** dùng trong 12 tháng và một số dịch vụ miễn phí trọn đời.

### Cách đăng ký:
1. Truy cập: [azure.microsoft.com/free/students/](https://azure.microsoft.com/free/students/)
2. Nhấn **Activate now**.
3. Đăng nhập bằng tài khoản Microsoft (Hotmail/Outlook) hoặc tạo mới.
4. Hệ thống sẽ yêu cầu xác thực bằng Email học sinh. Hãy nhập email `.edu` của bạn.
5. Kiểm tra hộp thư `.edu` để lấy mã xác thực hoặc nhấn Link kích hoạt.
6. **Không cần nhập thẻ tín dụng.**

### Cách tạo VPS trên Azure:
1. Vào [Azure Portal](https://portal.azure.com/).
2. Chọn **Create a resource** -> **Virtual Machine**.
3. **Cấu hình khuyên dùng**:
   - Image: **Ubuntu 22.04 LTS**.
   - Size: Chọn loại **B1s** (Miễn phí 750 giờ/tháng) hoặc **B2s** (Cần trả phí bằng 100$ được tặng, chạy mượt hơn cho cả Bot + Dashboard).
4. **Authentication type**: Chọn **Password** cho dễ sử dụng hoặc **SSH Public Key** nếu biết dùng.
5. Sau khi tạo xong, hãy mở Port `8501` trong phần **Networking** -> **Inbound port rules**.

---

## 2. GitHub Student Developer Pack
Đây là "kho báu" cho sinh viên, bao gồm rất nhiều coupon VPS.

### Cách đăng ký:
1. Truy cập: [education.github.com/pack](https://education.github.com/pack)
2. Nhấn **Get your pack**.
3. Kết nối với tài khoản GitHub của bạn và upload ảnh thẻ sinh viên (hoặc dùng mail .edu để xác thực).

### Các lợi ích liên quan đến VPS:
- **DigitalOcean**: Tặng **200$ credit** (dùng trong 60 ngày - Cần thẻ để verify nhưng GitHub Pack đôi khi cho phép bỏ qua hoặc dùng PayPal).
- **Heroku**: Miễn phí Hosting (nhưng không phải VPS full quyền).
- **Namecheap/Name.com**: Miễn phí 1 tên miền `.me` hoặc `.com` (để làm đẹp địa chỉ Dashboard).

## Lời khuyên:
Bạn hãy bắt đầu với **Azure for Students** trước vì nó chắc chắn không cần thẻ và cấu hình đủ mạnh để chạy bot này 24/24. 

Sau khi có IP của VPS từ Azure, hãy quay lại file [deployment.md](./deployment.md) để cài đặt.
