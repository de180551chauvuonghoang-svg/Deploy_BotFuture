# 🚀 HƯỚNG DẪN QUẢN LÝ VÀ CẬP NHẬT BOT (AZURE VPS)

Tài liệu này tổng hợp các bước để bạn tạm dừng Bot trên máy chủ để sửa code ở Local, và cách đẩy bản mới lên sau khi sửa xong.

---

## 🛠 1. KHI MUỐN DỪNG SERVER ĐỂ SỬA CODE Ở LOCAL

Khi bạn muốn sửa code và chạy thử trên máy tính của mình, hãy tắt Bot trên Azure để tránh bị trùng lệnh.

### Bước 1: Tắt Bot trên Azure

Vào **Azure Portal** -> Tìm máy ảo **BotTrade** -> **Run command** -> **RunShellScript**, dán lệnh sau và nhấn **Run**:

```bash
  cd /home/bottradefuture
  docker-compose down
```

### Bước 2: Chỉnh sửa và Test ở Local

- Bây giờ bạn có thể thoải mái sửa code trong VS Code.
- Chạy `main.py` và `streamlit` ở máy tính của bạn để kiểm tra.

---

## ☁️ 2. KHI ĐÃ SỬA XONG VÀ MUỐN ĐẨY CODE MỚI LÊN VPS

Sau khi code ở máy tính đã chạy ngon lành, hãy làm 3 bước này để đưa lên "mây".

### Bước A: Nén Code (Chạy tại PowerShell máy tính)

Mở PowerShell tại thư mục bot và chạy:

```powershell
# Xóa file nén cũ nếu có
rm bot.tar.gz

# Nén bản mới (loại bỏ các file rác và logs cũ)
tar -cvzf bot.tar.gz --exclude=.venv --exclude=__pycache__ --exclude=.git --exclude=logs --exclude=data .
```

### Bước B: Gửi file lên Azure (Chạy tại PowerShell máy tính)

```powershell
scp bot.tar.gz bottradefuture@20.2.139.254:/home/bottradefuture/
```

> **Mẹo:** Copy mật khẩu `BotTrade2024!`, Click **Chuột phải** vào màn hình đen để dán (không thấy gì hiện ra là đúng), rồi nhấn **Enter**.

### Bước C: Giải nén và Chạy Bot (Chạy tại Azure Run Command)

Vào lại Azure Portal -> **Run command** -> **RunShellScript**, dán lệnh này và nhấn **Run**:

```bash
cd /home/bottradefuture
# Giải nén đè lên code cũ
tar -xvzf bot.tar.gz
# Xóa sạch triệt để container cũ (kể cả các bản lỗi có tiền tố lạ)
docker-compose down --remove-orphans
docker ps -a | grep -i "trading" | awk '{print $1}' | xargs -r docker rm -f
# Khởi động lại Bot và tự động cài thêm thư viện mới
docker-compose up -d --build
```

---

## 📊 THÔNG TIN TRUY CẬP NHANH

- **Link Dashboard:** [http://20.2.139.254:8501](http://20.2.139.254:8501)
- **Username VPS:** `bottradefuture`
- **Mật khẩu VPS/SSH:** `BotTrade2024!`
- **Lệnh kiểm tra log (chạy ở Azure Run Command):**
  ```bash
  docker logs --tail 50 trading-bot
  ```

---

_Chúc bạn có những bản cập nhật thắng lợi! 🚀_
