import argparse
import time
import re
from pathlib import Path
from character_scanner.gemini_uploader import GeminiUploader
from character_scanner.progress_tracker import ProgressTracker

def sort_key_func(p: Path) -> int:
    m = re.search(r'(\d+)', p.name)
    return int(m.group(1)) if m else 0

def main():
    parser = argparse.ArgumentParser(description="Tự động hóa nạp các file scanner lên Gemini và tạo import.json")
    parser.add_argument("--scanner-dir", default="scanner", help="Thư mục chứa các file scanner_*.md")
    parser.add_argument("--profile-dir", default="user_data/chrome_profiles/chrome_data_1", help="Thư mục profile Chrome")
    parser.add_argument("--output-json", default="import.json", help="Đường dẫn file import.json kết quả")
    parser.add_argument("--delay", type=int, default=5, help="Thời gian nghỉ (giây) giữa các file")
    parser.add_argument("--headless", action="store_true", help="Chạy ẩn danh không mở cửa sổ Chrome")
    parser.add_argument("--reset-progress", action="store_true", help="Xóa lịch sử tiến trình cũ và chạy lại từ đầu")
    args = parser.parse_args()

    scanner_dir = Path(args.scanner_dir)
    if not scanner_dir.exists():
        print(f"[-] Lỗi: Không tìm thấy thư mục '{args.scanner_dir}'. Hãy chạy quét trước!")
        return

    progress_file = scanner_dir / ".gemini_progress.json"
    if args.reset_progress and progress_file.exists():
        progress_file.unlink()
        print("[*] Đã đặt lại (reset) tiến trình cũ.")

    tracker = ProgressTracker(progress_file)
    md_files = sorted(list(scanner_dir.glob("scanner_*.md")), key=sort_key_func)
    if not md_files:
        print(f"[-] Không tìm thấy file markdown nào trong '{args.scanner_dir}'.")
        return

    pending_files = [f for f in md_files if not tracker.is_completed(f.name)]
    print(f"[*] Tìm thấy tổng cộng {len(md_files)} file markdown.")
    print(f"[*] Số file cần xử lý: {len(pending_files)} (Đã hoàn thành trước đó: {len(md_files) - len(pending_files)} file).")

    if not pending_files:
        print("[+] Tất cả các file đã hoàn tất từ trước!")
        total = tracker.export_to_import_json(Path(args.output_json))
        print(f"[🎉] Đã xuất file tổng hợp: {args.output_json} với {total} mục.")
        return

    profile_path = Path(args.profile_dir)
    if not profile_path.exists():
        print(f"[-] Cảnh báo: Thư mục profile '{profile_path}' chưa tồn tại. Đang tạo mới...")
        profile_path.mkdir(parents=True, exist_ok=True)

    uploader = GeminiUploader(profile_path, headless=args.headless)
    try:
        uploader.start()
        total_pending = len(pending_files)
        for idx, md_file in enumerate(pending_files, start=1):
            print(f"\n=======================================================")
            print(f"[*] [{idx}/{total_pending}] Đang xử lý: {md_file.name}...")
            content = md_file.read_text(encoding="utf-8")
            
            # Gửi và trích xuất
            result = uploader.send_and_extract(content)
            if result:
                tracker.save_file_result(md_file.name, result)
                print(f"[+] Thành công! Gemini đã trả về {len(result)} block đã biên tập.")
            else:
                print(f"[-] Cảnh báo: Không trích xuất được JSON hợp lệ từ {md_file.name}. Sẽ thử lại ở lần sau.")

            if idx < total_pending:
                print(f"[*] Nghỉ {args.delay} giây trước khi gửi file tiếp theo...")
                time.sleep(args.delay)

        total = tracker.export_to_import_json(Path(args.output_json))
        print(f"\n[🎉] HOÀN TẤT TOÀN BỘ QUÁ TRÌNH!")
        print(f"[+] Đã xuất file kết quả: {args.output_json} với tổng cộng {total} nhân vật.")

    except Exception as e:
        print(f"[-] Có lỗi xảy ra trong quá trình tự động hóa: {e}")
    finally:
        uploader.close()

if __name__ == "__main__":
    main()
