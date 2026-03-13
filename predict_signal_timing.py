#!/usr/bin/env python3
"""
Signal Prediction Calculator
Dự đoán khi nào sẽ có tín hiệu giao dịch tiếp theo
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Thông tin từ backtest
STANDARD_STATS = {
    'total_trades': 1012,
    'total_pnl': 15857.90,
    'avg_pnl_per_trade': 15.67,
    'win_rate': 0.5761,
    'time_period_days': 365  # Giả sử là 1 năm data
}

HARD_STOP_STATS = {
    'total_trades': 703,
    'total_pnl': 199086.80,
    'avg_pnl_per_trade': 283.20,
    'win_rate': 0.6230,
    'time_period_days': 365
}

def calculate_signal_frequency():
    """
    Tính toán tần suất tín hiệu dựa trên backtest
    """
    print("=" * 80)
    print("📊 PHÂN TÍCH TẦN SUẤT TÍN HIỆU GIAO DỊCH")
    print("=" * 80)
    print()
    
    # 1. Tính trades/day từ backtest
    standard_trades_per_day = STANDARD_STATS['total_trades'] / STANDARD_STATS['time_period_days']
    hard_stop_trades_per_day = HARD_STOP_STATS['total_trades'] / HARD_STOP_STATS['time_period_days']
    
    print("📈 TỪ DỮ LIỆU BACKTEST:")
    print(f"  Standard Strategy:  {standard_trades_per_day:.2f} lệnh/ngày")
    print(f"  Hard Stop Strategy: {hard_stop_trades_per_day:.2f} lệnh/ngày")
    print()
    
    # 2. Tính trades/hour
    standard_trades_per_hour = standard_trades_per_day / 24
    hard_stop_trades_per_hour = hard_stop_trades_per_day / 24
    
    print("⏰ TÍNH TOÁN TẦN SUẤT:")
    print(f"  Standard Strategy:  {standard_trades_per_hour:.3f} lệnh/giờ")
    print(f"  Hard Stop Strategy: {hard_stop_trades_per_hour:.3f} lệnh/giờ")
    print()
    
    # 3. Tính thời gian trung bình giữa 2 signal
    hours_between_signals_standard = 1 / standard_trades_per_hour if standard_trades_per_hour > 0 else float('inf')
    hours_between_signals_hardstop = 1 / hard_stop_trades_per_hour if hard_stop_trades_per_hour > 0 else float('inf')
    
    mins_between_signals_standard = hours_between_signals_standard * 60
    mins_between_signals_hardstop = hours_between_signals_hardstop * 60
    
    print("⏳ THỜI GIAN TRUNG BÌNH GIỮA 2 TÍN HIỆU:")
    print(f"  Standard Strategy:")
    print(f"    • {hours_between_signals_standard:.1f} giờ")
    print(f"    • {mins_between_signals_standard:.0f} phút")
    print(f"    • {mins_between_signals_standard/60:.1f} lệnh/24h")
    print()
    print(f"  Hard Stop Strategy:")
    print(f"    • {hours_between_signals_hardstop:.1f} giờ")
    print(f"    • {mins_between_signals_hardstop:.0f} phút")
    print(f"    • {mins_between_signals_hardstop/60:.1f} lệnh/24h")
    print()
    
    # 4. Số cặp tiền quét
    num_symbols = 24
    print(f"🔎 THÔNG TIN QUÉT:")
    print(f"  Số cặp tiền: {num_symbols}")
    print(f"  Thời gian quét/cycle: ~25-30 giây (1 giây/cặp)")
    print()
    
    # 5. Dự đoán signal trên từng symbol
    standard_trades_per_symbol = STANDARD_STATS['total_trades'] / num_symbols
    hard_stop_trades_per_symbol = HARD_STOP_STATS['total_trades'] / num_symbols
    
    days_between_signals_per_symbol_standard = STANDARD_STATS['time_period_days'] / standard_trades_per_symbol
    days_between_signals_per_symbol_hardstop = HARD_STOP_STATS['time_period_days'] / hard_stop_trades_per_symbol
    
    print("📍 THỜI GIAN TRUNG BÌNH GIỮA 2 TÍN HIỆU CHO MỖI CẶP:")
    print(f"  Standard Strategy:  {days_between_signals_per_symbol_standard:.1f} ngày/lệnh/cặp")
    print(f"  Hard Stop Strategy: {days_between_signals_per_symbol_hardstop:.1f} ngày/lệnh/cặp")
    print()
    
    # 6. Tính kèm vào
    if os.path.exists('data/market_scanner.json'):
        try:
            with open('data/market_scanner.json', 'r') as f:
                scan_data = json.load(f)
                print(f"✅ LẦN QUÉT CUỐI (Từ market_scanner.json):")
                print(f"  Tổng score trung bình: {sum([s.get('score', 0) for s in scan_data if isinstance(s, dict)]) / len(scan_data) if scan_data else 0:.2f}")
                print(f"  Cấp độ quét cao nhất: {max([s.get('score', 0) for s in scan_data if isinstance(s, dict)]) if scan_data else 0:.2f}")
                print()
        except:
            pass
    
    # 7. Dự báo
    print("🎯 DỰ BÁODỰ BÁO :")
    print()
    
    print("✨ TÌNH HUỐNG TÍCH CỰC:")
    print(f"  • Nếu market trend mạnh: Signal có thể đến trong {hours_between_signals_standard:.0f}-{hours_between_signals_hardstop:.0f} giờ")
    print(f"  • Nếu market sideways: Signal có thể bị trì hoãn 3-7 ngày")
    print(f"  • Peak time: Khi 1-2 cặp trong 24 đồng thời lập setup → ~{24 * (hours_between_signals_standard / 24):.1f} giờ tiếp theo")
    print()
    
    print("⚠️  THÁCH THỨC:")
    print(f"  • MIN_SCORE_THRESHOLD = 8.5 (rất cao!)")
    print(f"  • Từ quét cuối: Score tối đa chỉ 4.0 (XRP, STX)")
    print(f"  • Cần gấp 2x điểm số hiện tại → Phải chờ confluence tốt hơn")
    print()
    
    # 8. Khuyến nghị
    print("💡 KHUYẾN NGHỊ:")
    print(f"  1. Chờ đợi bình thường: 2-4 giờ cho signal đầu tiên")
    print(f"  2. Nếu chờ quá 6 giờ: Kiểm tra config MIN_SCORE_THRESHOLD (8.5)")
    print(f"  3. Có thể giảm threshold xuống 6.5-7.0 để tăng tần suất")
    print(f"  4. Monitor bất kỳ scores > 4.5 → Có khả năng → signal sắp tới")
    print()
    
    # 9. Timeline dự báo cụ thể
    print("📅 TIMELINE DỰ BÁO CỤ THỂ:")
    print()
    now = datetime.now()
    for i, hours in enumerate([1, 2, 4, 6, 12, 24], 1):
        future_time = now + timedelta(hours=hours)
        # Xác suất Poisson: P(≥1) = 1 - exp(-λt)
        lambda_rate = 1.0 / hours_between_signals_standard
        prob_standard = 1.0 - (2.71828 ** (-lambda_rate * hours))
        prob_standard = min(max(prob_standard, 0.0), 1.0)
        print(f"  {hours:2d}h từ giờ ({future_time.strftime('%H:%M')}): ~{prob_standard * 100:.0f}% xác suất có signal")
    print()
    
    print("=" * 80)

def analyze_current_signals():
    """
    Phân tích tín hiệu hiện tại từ market scanner
    """
    print("=" * 80)
    print("🔍 PHÂN TÍCH TÍN HIỆU HIỆN TẠI")
    print("=" * 80)
    print()
    
    if not os.path.exists('data/market_scanner.json'):
        print("❌ Không tìm thấy market_scanner.json")
        print("   Hãy đợi bot quét ít nhất 1 cycle...")
        return
    
    try:
        with open('data/market_scanner.json', 'r') as f:
            scan_data = json.load(f)
        
        if not scan_data:
            print("❌ Chưa có dữ liệu quét")
            return
        
        # Lọc dữ liệu hợp lệ
        valid_scans = [s for s in scan_data if isinstance(s, dict)]
        
        if not valid_scans:
            print("❌ Dữ liệu quét không hợp lệ")
            return
        
        print(f"📊 Dữ liệu từ lần quét gần nhất:")
        print()
        
        # Sắp xếp theo score
        sorted_scans = sorted(valid_scans, key=lambda x: x.get('score', 0), reverse=True)
        
        print("🏆 TOP 10 CẶP TIỀN CÓ SCORE CAO:")
        print()
        for i, scan in enumerate(sorted_scans[:10], 1):
            symbol = scan.get('symbol', 'N/A')
            score = scan.get('score', 0)
            signal = scan.get('signal', 'NONE')
            reason = scan.get('reason', '')
            
            # Tô màu dựa trên score
            if score >= 8.5:
                status = "✅ SIGNAL!"
            elif score >= 7.0:
                status = "⚠️  GẦN"
            elif score >= 5.0:
                status = "🟡 TRUNG"
            else:
                status = "🔵 THẤP"
            
            print(f"  {i:2d}. {symbol:12} | Score: {score:5.2f} | {status} | {reason[:30]}")
        
        print()
        print("📊 THỐNG KÊ:")
        scores = [s.get('score', 0) for s in valid_scans]
        signals_count = len([s for s in valid_scans if s.get('signal') != 'NONE'])
        avg_score = sum(scores) / len(scores) if scores else 0
        max_score = max(scores) if scores else 0
        
        print(f"  • Tổng số cặp quét: {len(valid_scans)}")
        print(f"  • Số có tín hiệu: {signals_count}")
        print(f"  • Điểm trung bình: {avg_score:.2f}/10.0")
        print(f"  • Điểm cao nhất: {max_score:.2f}/10.0")
        print(f"  • Ngưỡng cần: 8.5/10.0")
        print(f"  • Chênh lệch: {8.5 - max_score:.2f} điểm")
        print()
        
        if max_score >= 8.5:
            print("✅ ĐÃ CÓ SIGNAL! Kiểm tra position...")
        elif max_score >= 7.0:
            print(f"⚠️  GẦN! Chỉ cần {8.5 - max_score:.2f} điểm nữa → Signal sắp tới")
            print(f"   Cặp: {sorted_scans[0].get('symbol')}")
        else:
            print(f"🔵 CHỜ ĐỢI: Cần thêm {8.5 - max_score:.1f} điểm để có signal")
            print(f"   Dự tính: 2-6 giờ nữa (phụ thuộc thị trường)")
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
    
    print()

if __name__ == "__main__":
    print()
    calculate_signal_frequency()
    print()
    analyze_current_signals()
    print()
