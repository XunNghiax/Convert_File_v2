import sys
import os
from pathlib import Path
import subprocess

# Đảm bảo UTF-8 cho console Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    print("=" * 65)
    print("    HỆ THỐNG QUÉT TÊN NHÂN VẬT & BIÊN TẬP QUA GEMINI AI")
    print("                Dự án: Convert_File_v2")
    print("=" * 65)

def main_menu():
    while True:
        clear_screen()
        print_banner()
        print("[1] 🚀 Quét văn bản + Tự động gửi lên Gemini -> Tạo import.json")
        print("[2] 🔍 Chỉ quét văn bản (Xuất thư mục scanner/ gồm master JSON & MD)")
        print("[3] 🌐 Chỉ gửi các file trong scanner/ lên Gemini -> Tạo import.json")
        print("[4] ♻️  Đặt lại tiến trình (Reset) và gửi lại toàn bộ lên Gemini")
        print("[5] 🧪 Chạy kiểm thử tự động hệ thống (Run Unit Tests)")
        print("[0] ❌ Thoát chương trình")
        print("=" * 65)

        choice = input("👉 Nhập lựa chọn của bạn (0-5) [Mặc định: 1]: ").strip()
        if not choice:
            choice = "1"

        if choice == "0":
            print("\n👋 Cảm ơn bạn đã sử dụng chương trình. Tạm biệt!")
            break

        elif choice == "1":
            print("\n--- [1] QUÉT VĂN BẢN VÀ TỰ ĐỘNG GỬI GEMINI ---")
            inp = input("Nhập tên file văn bản cần quét [Mặc định: exam.txt]: ").strip() or "exam.txt"
            prof = input("Nhập thư mục Profile Chrome [Mặc định: chrome_profiles]: ").strip() or "chrome_profiles"
            out_json = input("Nhập tên file kết quả [Mặc định: import.json]: ").strip() or "import.json"

            cmd = [
                sys.executable, "-m", "character_scanner.main",
                "--input", inp,
                "--output", "scanner",
                "--upload-gemini",
                "--profile-dir", prof,
                "--output-import-json", out_json
            ]
            print(f"\n[*] Đang thực thi lệnh: {' '.join(cmd)}\n")
            subprocess.run(cmd)
            input("\n👉 Nhấn Enter để quay lại menu chính...")

        elif choice == "2":
            print("\n--- [2] CHỈ QUÉT VĂN BẢN ---")
            inp = input("Nhập tên file văn bản cần quét [Mặc định: exam.txt]: ").strip() or "exam.txt"
            chunk = input("Số lượng block mỗi file .md [Mặc định: 40]: ").strip() or "40"

            cmd = [
                sys.executable, "-m", "character_scanner.main",
                "--input", inp,
                "--output", "scanner",
                "--chunk-size", chunk
            ]
            print(f"\n[*] Đang thực thi lệnh: {' '.join(cmd)}\n")
            subprocess.run(cmd)
            input("\n👉 Nhấn Enter để quay lại menu chính...")

        elif choice == "3":
            print("\n--- [3] CHỈ GỬI CÁC FILE SCANNER CÓ SẴN LÊN GEMINI ---")
            prof = input("Nhập thư mục Profile Chrome [Mặc định: chrome_profiles]: ").strip() or "chrome_profiles"
            out_json = input("Nhập tên file kết quả [Mặc định: import.json]: ").strip() or "import.json"
            delay = input("Thời gian nghỉ giữa các file (giây) [Mặc định: 5]: ").strip() or "5"

            cmd = [
                sys.executable, "-m", "character_scanner.main",
                "--upload-only",
                "--output", "scanner",
                "--profile-dir", prof,
                "--output-import-json", out_json,
                "--gemini-delay", delay
            ]
            print(f"\n[*] Đang thực thi lệnh: {' '.join(cmd)}\n")
            subprocess.run(cmd)
            input("\n👉 Nhấn Enter để quay lại menu chính...")

        elif choice == "4":
            print("\n--- [4] ĐẶT LẠI TIẾN TRÌNH & GỬI LẠI LÊN GEMINI ---")
            confirm = input("⚠️ Bạn có chắc muốn xóa lịch sử tiến trình cũ và gửi lại từ file 1? (y/n): ").strip().lower()
            if confirm in ("y", "yes"):
                prof = input("Nhập thư mục Profile Chrome [Mặc định: chrome_profiles]: ").strip() or "chrome_profiles"
                cmd = [
                    sys.executable, "-m", "character_scanner.main",
                    "--upload-only",
                    "--profile-dir", prof,
                    "--reset-gemini-progress"
                ]
                print(f"\n[*] Đang thực thi lệnh: {' '.join(cmd)}\n")
                subprocess.run(cmd)
            input("\n👉 Nhấn Enter để quay lại menu chính...")

        elif choice == "5":
            print("\n--- [5] CHẠY KIỂM THỬ HỆ THỐNG (UNIT TESTS) ---")
            cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
            print(f"\n[*] Đang thực thi lệnh: {' '.join(cmd)}\n")
            subprocess.run(cmd)
            input("\n👉 Nhấn Enter để quay lại menu chính...")

        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng chọn lại!")
            input("👉 Nhấn Enter để tiếp tục...")

if __name__ == "__main__":
    main_menu()
