import os
import requests
import sys
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def test_discord():
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    print(f"--- Kiểm tra cấu hình Discord ---")
    if not webhook_url:
        print("❌ LỖI: Không tìm thấy DISCORD_WEBHOOK_URL trong file .env")
        return

    print(f"✅ Đã tìm thấy Webhook URL: {webhook_url[:30]}...")
    
    test_message = {
        "embeds": [
            {
                "title": "✅ KẾT NỐI BOT TRADE THÀNH CÔNG",
                "description": "Bot đã kết nối với Discord thành công! Bạn sẽ nhận được các thông báo dự đoán và tín hiệu từ SMC Strategy tại đây.",
                "color": 65280, # Màu xanh lá
                "fields": [
                    {"name": "Trạng thái", "value": "🟢 Hoạt động", "inline": True},
                    {"name": "Dự đoán", "value": "🔍 Sẵn sàng", "inline": True}
                ],
                "footer": {"text": "Advanced SMC Trading Bot"}
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=test_message)
        if response.status_code == 204:
            print("🚀 THÀNH CÔNG: Tin nhắn thử nghiệm đã được gửi đến Discord của bạn!")
        else:
            print(f"❌ THẤT BẠI: Lỗi từ Discord (Mã: {response.status_code})")
            print(f"Chi tiết: {response.text}")
    except Exception as e:
        print(f"❌ LỖI KẾT NỐI: {e}")

if __name__ == "__main__":
    test_test_discord = test_discord()
