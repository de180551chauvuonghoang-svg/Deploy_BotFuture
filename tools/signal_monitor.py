#!/usr/bin/env python3
"""
Signal Monitor - Theo dõi tín hiệu real-time
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

def read_latest_scan():
    """Đọc dữ liệu quét mới nhất từ market_scanner.json"""
    scanner_file = Path('../data/market_scanner.json')
    if not scanner_file.exists():
        return None
    
    try:
        with open(scanner_file, 'r') as f:
            return json.load(f)
    except:
        return None

def read_bot_logs():
    """Đọc logs từ terminal để lấy thông tin quét"""
    log_file = Path('../logs/trading.log')
    if not log_file.exists():
        return []
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Lấy 50 dòng cuối
        scan_lines = [l for l in lines if 'Scanning' in l][-50:]
        return scan_lines
    except:
        return []

def parse_scan_line(line):
    """Parse dòng quét để lấy thông tin"""
    try:
        # Format: "Scanning BTC/USDT: Signal=NONE | Score=0.5"
        if 'Scanning' not in line:
            return None
        
        parts = line.split('|')
        symbol = line.split('Scanning ')[1].split(':')[0]
        signal = parts[0].split('Signal=')[1].strip()
        score = float(parts[1].split('Score=')[1].split('\n')[0])
        
        return {
            'symbol': symbol,
            'signal': signal,
            'score': score
        }
    except:
        return None

def display_dashboard():
    """Hiển thị dashboard theo dõi"""
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("\n" + "="*80)
    print("📡 SIGNAL MONITOR - THEO DÕI TÍN HIỆU REAL-TIME")
    print("="*80)
    print(f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}")
    print()
    
    # 1. Đọc dữ liệu
    scan_data = read_latest_scan()
    scan_lines = read_bot_logs()
    
    if not scan_lines:
        print("❌ Chưa có dữ liệu quét. Hãy đợi bot quét...")
        print("   Bot sẽ quét mỗi 25-30 giây")
        return
    
    # 2. Parse logs
    scans = []
    for line in scan_lines[-24:]:  # Lấy 24 lần quét gần nhất
        parsed = parse_scan_line(line)
        if parsed:
            scans.append(parsed)
    
    if not scans:
        print("❌ Không tìm thấy dữ liệu quét hợp lệ")
        return
    
    # 3. Sắp xếp và hiển thị
    scans_sorted = sorted(scans, key=lambda x: x['score'], reverse=True)
    
    print("🏆 TOP CANDIDATES (Sorted by Score):\n")
    print(f"  {'#':<3} {'Symbol':<15} {'Score':<8} {'Signal':<8} {'Status':<15}")
    print(f"  {'-'*60}")
    
    for i, scan in enumerate(scans_sorted[:10], 1):
        symbol = scan['symbol']
        score = scan['score']
        signal = scan['signal']
        
        # Xánh định trạng thái
        if score >= 8.5:
            status = "✅ SIGNAL!"
            color_code = "\033[92m"  # Green
        elif score >= 7.0:
            status = "⚠️  GẦN (7.0+)"
            color_code = "\033[93m"  # Yellow
        elif score >= 5.0:
            status = "🟡 TRUNG (5.0+)"
            color_code = "\033[94m"  # Blue
        else:
            status = "🔵 THẤP"
            color_code = "\033[90m"  # Gray
        
        print(f"  {i:<3} {symbol:<15} {score:<8.2f} {signal:<8} {status:<15}")
    
    print()
    
    # 4. Thống kê
    print("📊 THỐNG KÊ:")
    scores = [s['score'] for s in scans]
    avg_score = sum(scores) / len(scores)
    max_score = max(scores)
    signals_active = len([s for s in scans if s['signal'] != 'NONE'])
    
    print(f"  • Tổng cặp quét: {len(scans)}")
    print(f"  • Có tín hiệu: {signals_active}")
    print(f"  • Điểm trung bình: {avg_score:.2f}/10.0")
    print(f"  • Điểm cao nhất: {max_score:.2f}/10.0")
    print(f"  • Ngưỡng cần: 8.5/10.0")
    print(f"  • Còn thiếu: {max(0, 8.5 - max_score):.2f} điểm")
    print()
    
    # 5. Dự báo
    print("⏳ DỰ BÁO:")
    if max_score >= 8.5:
        print("  ✅ ĐÃ CÓ SIGNAL! Bot đang xử lý...")
    elif max_score >= 7.5:
        print(f"  ⚠️  GẦN! Signal sắp tới trong ~30 phút")
        print(f"     Cặp: {scans_sorted[0]['symbol']} (score {max_score:.2f})")
    elif max_score >= 7.0:
        print(f"  🔶 Có khả năng: 1-2 giờ nữa")
        print(f"     Cặp: {scans_sorted[0]['symbol']} (score {max_score:.2f})")
    elif max_score >= 5.0:
        print(f"  🟡 Chờ đợi: 2-6 giờ nữa (phụ thuộc market)")
        print(f"     Cặp hứa hẹn: {scans_sorted[0]['symbol']} (score {max_score:.2f})")
    else:
        print(f"  🔵 Chưa sẵn sàng: 6+ giờ hoặc chờ market move")
    
    print()
    print("="*80)
    print("💡 TIP: Chạy lịch để monitor: watch -n 10 'python3 signal_monitor.py'")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        while True:
            display_dashboard()
            
            if len(sys.argv) > 1 and sys.argv[1] == 'once':
                break
            
            # Cập nhật mỗi 10 giây
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n✋ Monitor dừng")
