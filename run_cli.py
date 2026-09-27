import sys
import os
import json
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

def get_data_stats():
    """Lấy số lượng mục hiện tại trong các file từ điển và kết quả."""
    char_path = Path("resources/dictionaries/character_dict.json")
    comm_path = Path("resources/dictionaries/common_dict.json")
    import_path = Path("samples/import.json")

    char_cnt = 0
    if char_path.exists():
        try:
            with open(char_path, "r", encoding="utf-8") as f:
                char_cnt = len(json.load(f))
        except Exception:
            pass

    comm_cnt = 0
    if comm_path.exists():
        try:
            with open(comm_path, "r", encoding="utf-8") as f:
                comm_cnt = len(json.load(f))
        except Exception:
            pass

    import_cnt = None
    if import_path.exists():
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                import_cnt = len(json.load(f))
        except Exception:
            pass

    return {
        "character": char_cnt,
        "common": comm_cnt,
        "import_json": import_cnt
    }

def print_banner():
    stats = get_data_stats()
    print("=" * 68)
    print("      HỆ THỐNG QUÉT NHÂN VẬT & BIÊN TẬP TỪ ĐIỂN DỊCH THUẬT V2")
    print("                      Dự án: Convert_File_v2")
    print("=" * 68)
    print("  📊 TRẠNG THÁI DỮ LIỆU HIỆN TẠI:")
    print(f"     • character_dict.json : {stats['character']} mục (Tên nhân vật)")
    print(f"     • common_dict.json    : {stats['common']} mục (Từ ngữ chung / Thành ngữ)")
    if stats['import_json'] is not None:
        print(f"     • samples/import.json : {stats['import_json']} mục (Sẵn sàng nạp vào từ điển)")
    else:
        print("     • samples/import.json : Chưa có (Chạy quét + Gemini để tạo)")
    print("-" * 68)

def get_sample_txt_files():
    """Tìm danh sách file văn bản trong samples/."""
    samples_dir = Path("samples")
    if not samples_dir.exists():
        return []
    return [f for f in samples_dir.glob("*.txt") if f.is_file()]

def prompt_input_file(default="samples/exam.txt"):
    """Hỏi người dùng file đầu vào kèm gợi ý danh sách trong samples/."""
    txt_files = get_sample_txt_files()
    if txt_files:
        print("\n📂 Danh sách file văn bản tìm thấy trong samples/:")
        for idx, f in enumerate(txt_files, start=1):
            print(f"   [{idx}] {f.name}")
        val = input(f"\n👉 Chọn số thứ tự (1-{len(txt_files)}) hoặc nhập đường dẫn [Mặc định: {default}]: ").strip()
        if not val:
            return default
        if val.isdigit() and 1 <= int(val) <= len(txt_files):
            return str(txt_files[int(val) - 1])
        return val
    else:
        val = input(f"Nhập đường dẫn file văn bản [Mặc định: {default}]: ").strip()
        return val or default

def main_menu():
    while True:
        try:
            clear_screen()
            print_banner()
            print("  [ QUY TRÌNH QUÉT & BIÊN TẬP AI ]")
            print("  [1] 🚀 Toàn trình: Quét văn bản + Tự động gửi Gemini -> samples/import.json")
            print("  [2] 🔍 Chỉ quét văn bản (Xuất thư mục scanner/ gồm .md & master JSON)")
            print("  [3] 🌐 Chỉ gửi các file trong scanner/ lên Gemini -> samples/import.json")
            print("  [4] 🎯 Lọc nhanh scanner/ theo số lần xuất hiện (min-count)")
            print("  [5] ♻️  Đặt lại tiến trình (Reset progress) gửi Gemini")
            print()
            print("  [ TỪ ĐIỂN & IMPORT DỮ LIỆU ]")
            print("  [6] 📥 Nạp dữ liệu vào từ điển (Tự động phân bổ theo 'is_character')")
            print("  [7] ✍️  Nhập thủ công từng từ vào từ điển (Interactive mode)")
            print()
            print("  [ HỆ THỐNG ]")
            print("  [8] 🧪 Chạy kiểm thử tự động hệ thống (Run Unit Tests)")
            print("  [0] ❌ Thoát chương trình")
            print("=" * 68)

            choice = input("👉 Nhập lựa chọn của bạn (0-8) [Mặc định: 1]: ").strip()
            if not choice:
                choice = "1"

            if choice == "0":
                print("\n👋 Cảm ơn bạn đã sử dụng chương trình. Tạm biệt!")
                break

            elif choice == "1":
                print("\n--- [1] TOÀN TRÌNH: QUÉT VĂN BẢN VÀ TỰ ĐỘNG GỬI GEMINI ---")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                include_known = input("Liệt kê cả nhân vật đã có trong từ điển? (y/N) [Mặc định: N (chỉ tìm nhân vật mới)]: ").strip().lower() == "y"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import.json]: ").strip() or "samples/import.json"

                cmd = [
                    sys.executable, "-m", "src.scanner.main",
                    "--input", inp,
                    "--output", "output/scanner",
                    "--chunk-size", chunk,
                    "--min-count", min_cnt,
                    "--upload-gemini",
                    "--profile-dir", prof,
                    "--output-import-json", out_json
                ]
                if include_known:
                    cmd.append("--include-known")
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            elif choice == "2":
                print("\n--- [2] CHỈ QUÉT VĂN BẢN ---")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                include_known = input("Liệt kê cả nhân vật đã có trong từ điển? (y/N) [Mặc định: N (chỉ tìm nhân vật mới)]: ").strip().lower() == "y"

                cmd = [
                    sys.executable, "-m", "src.scanner.main",
                    "--input", inp,
                    "--output", "output/scanner",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]
                if include_known:
                    cmd.append("--include-known")
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            elif choice == "3":
                print("\n--- [3] CHỈ GỬI CÁC FILE SCANNER CÓ SẴN LÊN GEMINI ---")
                scanner_dir = input("Thư mục chứa các file .md [Mặc định: output/scanner]: ").strip() or "output/scanner"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import.json]: ").strip() or "samples/import.json"
                delay = input("Thời gian nghỉ giữa các file (giây) [Mặc định: 5]: ").strip() or "5"

                cmd = [
                    sys.executable, "-m", "src.scanner.main",
                    "--upload-only",
                    "--output", scanner_dir,
                    "--profile-dir", prof,
                    "--output-import-json", out_json,
                    "--gemini-delay", delay
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            elif choice == "4":
                print("\n--- [4] LỌC NHANH FILE SCANNER THEO SỐ LẦN XUẤT HIỆN (MIN-COUNT) ---")
                print("💡 Lọc lại các block hiện có mà không cần quét lại file văn bản gốc.")
                min_cnt = input("Số lần xuất hiện tối thiểu cần giữ lại [Mặc định: 2]: ").strip() or "2"
                chunk = input("Số block mỗi file .md [Mặc định: 40]: ").strip() or "40"

                cmd = [
                    sys.executable, "-m", "src.scanner.main",
                    "--filter-only",
                    "--output", "output/scanner",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            elif choice == "5":
                print("\n--- [5] ĐẶT LẠI TIẾN TRÌNH & GỬI LẠI LÊN GEMINI ---")
                confirm = input("⚠️ Bạn có chắc muốn xóa lịch sử tiến trình cũ và gửi lại từ file đầu tiên? (y/n): ").strip().lower()
                if confirm in ("y", "yes"):
                    prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                    cmd = [
                        sys.executable, "-m", "src.scanner.main",
                        "--upload-only",
                        "--output", "output/scanner",
                        "--profile-dir", prof,
                        "--reset-gemini-progress"
                    ]
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                    subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            elif choice == "6":
                print("\n--- [6] NẠP DỮ LIỆU VÀO TỪ ĐIỂN (IMPORT) ---")
                print("💡 Cơ chế tự động phân bổ:")
                print("   • is_character == true  -> nạp vào character_dict.json")
                print("   • is_character == false -> nạp vào common_dict.json")
                print()
                file_imp = input("Nhập đường dẫn file cần import [Mặc định: samples/import.json]: ").strip() or "samples/import.json"
                dict_dst = input("Đường dẫn từ điển đích [Để trống: Tự động phân bổ theo is_character]: ").strip()

                cmd = [sys.executable, "-m", "src.importer.main", "--file", file_imp]
                if dict_dst:
                    cmd.extend(["--dict", dict_dst])

                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            elif choice == "7":
                print("\n--- [7] NHẬP THỦ CÔNG TỪNG TỪ VÀO TỪ ĐIỂN ---")
                cmd = [sys.executable, "-m", "src.importer.main", "--interactive"]
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            elif choice == "8":
                print("\n--- [8] CHẠY KIỂM THỬ HỆ THỐNG (UNIT TESTS) ---")
                cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để quay lại menu chính...")

            else:
                print("❌ Lựa chọn không hợp lệ. Vui lòng chọn lại!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n\n[!] Đã hủy thao tác qua phím tắt (Ctrl+C). Quay lại menu chính...")
            input("👉 Nhấn Enter để tiếp tục...")

if __name__ == "__main__":
    main_menu()
