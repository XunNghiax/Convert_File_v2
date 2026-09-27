import argparse
import time
import re
from pathlib import Path
from .gemini_uploader import GeminiUploader
from .progress_tracker import ProgressTracker

def sort_key_func(p: Path) -> int:
    m = re.search(r'(\d+)', p.name)
    return int(m.group(1)) if m else 0

def run_upload_workflow(
    scanner_dir: Path | str = "output/scanner",
    profile_dir: Path | str = "runtime/chrome_profiles",
    output_json: Path | str = "samples/import.json",
    delay: int = 5,
    headless: bool = False,
    reset_progress: bool = False
) -> int:
    s_dir = Path(scanner_dir)
    if not s_dir.exists():
        if (Path("output") / scanner_dir).exists():
            s_dir = Path("output") / scanner_dir
        elif Path("scanner").exists():
            s_dir = Path("scanner")
        else:
            print(f"[-] Lỗi: Không tìm thấy thư mục '{scanner_dir}'. Hãy chạy quét trước!")
            return 0

    progress_file = s_dir / ".gemini_progress.json"
    if reset_progress and progress_file.exists():
        progress_file.unlink()
        print("[*] Đã đặt lại (reset) tiến trình cũ.")

    tracker = ProgressTracker(progress_file)
    md_files = sorted(list(s_dir.glob("scanner_*.md")), key=sort_key_func)
    if not md_files:
        print(f"[-] Không tìm thấy file markdown nào trong '{scanner_dir}'.")
        return 0

    pending_files = [f for f in md_files if not tracker.is_completed(f.name)]
    print(f"[*] Tìm thấy tổng cộng {len(md_files)} file markdown.")
    print(f"[*] Số file cần xử lý: {len(pending_files)} (Đã hoàn thành trước đó: {len(md_files) - len(pending_files)} file).")

    out_path = Path(output_json)
    if not pending_files:
        print("[+] Tất cả các file đã hoàn tất từ trước!")
        total = tracker.export_to_import_json(out_path)
        print(f"[🎉] Đã xuất file tổng hợp: {output_json} với {total} mục.")
        return total

    profile_path = Path(profile_dir)
    if not profile_path.exists():
        print(f"[-] Cảnh báo: Thư mục profile '{profile_path}' chưa tồn tại. Đang tạo mới...")
        profile_path.mkdir(parents=True, exist_ok=True)

    uploader = GeminiUploader(profile_path, headless=headless)
    try:
        uploader.start()
        total_pending = len(pending_files)
        for idx, md_file in enumerate(pending_files, start=1):
            print(f"\n=======================================================")
            print(f"[*] [{idx}/{total_pending}] Đang xử lý: {md_file.name}...")
            content = md_file.read_text(encoding="utf-8")
            
            result = uploader.send_and_extract(content)
            if result:
                tracker.save_file_result(md_file.name, result)
                print(f"[+] Thành công! Gemini đã trả về {len(result)} block đã biên tập.")
            else:
                print(f"[-] Cảnh báo: Không trích xuất được JSON hợp lệ từ {md_file.name}. Sẽ thử lại ở lần sau.")

            if idx < total_pending:
                print(f"[*] Nghỉ {delay} giây trước khi gửi file tiếp theo...")
                time.sleep(delay)

        total = tracker.export_to_import_json(out_path)
        print(f"\n[🎉] HOÀN TẤT TOÀN BỘ QUÁ TRÌNH!")
        print(f"[+] Đã xuất file kết quả: {output_json} với tổng cộng {total} nhân vật.")
        return total

    except Exception as e:
        print(f"[-] Có lỗi xảy ra trong quá trình tự động hóa: {e}")
        return 0
    finally:
        uploader.close()

def main():
    parser = argparse.ArgumentParser(description="Tự động hóa nạp các file scanner lên Gemini và tạo import.json")
    parser.add_argument("--scanner-dir", default="output/scanner", help="Thư mục chứa các file scanner_*.md (mặc định: output/scanner)")
    parser.add_argument("--profile-dir", default="runtime/chrome_profiles", help="Thư mục profile Chrome (mặc định: runtime/chrome_profiles)")
    parser.add_argument("--output-json", default="samples/import.json", help="Đường dẫn file import.json kết quả (mặc định: samples/import.json)")
    parser.add_argument("--delay", type=int, default=5, help="Thời gian nghỉ (giây) giữa các file")
    parser.add_argument("--headless", action="store_true", help="Chạy ẩn danh không mở cửa sổ Chrome")
    parser.add_argument("--reset-progress", action="store_true", help="Xóa lịch sử tiến trình cũ và chạy lại từ đầu")
    args = parser.parse_args()

    run_upload_workflow(
        scanner_dir=args.scanner_dir,
        profile_dir=args.profile_dir,
        output_json=args.output_json,
        delay=args.delay,
        headless=args.headless,
        reset_progress=args.reset_progress
    )

if __name__ == "__main__":
    main()
