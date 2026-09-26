import argparse
from pathlib import Path
import json
from character_scanner.resource_loader import ResourceLoader
from character_scanner.scanner_engine import ScannerEngine
from character_scanner.output_packager import OutputPackager
from character_scanner.benchmark import Evaluator
from character_scanner.upload_to_gemini import run_upload_workflow

def main():
    parser = argparse.ArgumentParser(description="Hệ thống Quét tên nhân vật & Tự động biên tập qua Gemini")
    
    # Nhóm tham số quét văn bản
    parser.add_argument("--input", default="exam.txt", help="Đường dẫn file văn bản đầu vào")
    parser.add_argument("--output", default="scanner", help="Thư mục xuất kết quả markdown và master json")
    parser.add_argument("--prompt", default="prompt.md", help="File prompt mẫu")
    parser.add_argument("--ground-truth", default="file_nhan_vat.json", help="File đối chiếu ground truth")
    parser.add_argument("--chunk-size", type=int, default=40, help="Số block mỗi file md (mặc định: 40)")
    parser.add_argument("--no-dedup", action="store_true", help="Không khử trùng lặp (giữ mọi vị trí xuất hiện)")

    # Nhóm tham số tự động đẩy lên Gemini
    parser.add_argument("--upload-gemini", action="store_true", help="Tự động nạp các file kết quả lên Gemini sau khi quét xong")
    parser.add_argument("--upload-only", action="store_true", help="Chỉ chạy tự động nạp Gemini (bỏ qua bước quét văn bản)")
    parser.add_argument("--profile-dir", default="chrome_profiles", help="Thư mục profile Chrome (mặc định: chrome_profiles)")
    parser.add_argument("--output-import-json", default="import.json", help="Đường dẫn file import.json kết quả từ Gemini")
    parser.add_argument("--gemini-delay", type=int, default=5, help="Thời gian nghỉ (giây) giữa các file khi gửi Gemini")
    parser.add_argument("--headless", action="store_true", help="Chạy ẩn danh không mở cửa sổ Chrome")
    parser.add_argument("--reset-gemini-progress", action="store_true", help="Đặt lại (reset) tiến trình gửi Gemini cũ")

    args = parser.parse_args()

    # 1. Giai đoạn Quét văn bản (nếu không bật --upload-only)
    if not args.upload_only:
        base_dir = Path(".")
        print(f"[*] Nạp tài nguyên từ điển...")
        loader = ResourceLoader(base_dir)
        loader.load_all()

        dedup = not args.no_dedup
        print(f"[*] Bắt đầu quét file: {args.input} (Khử trùng lặp: {dedup})...")
        engine = ScannerEngine(loader)
        blocks = engine.scan_file(Path(args.input), deduplicate=dedup)
        print(f"[+] Kết quả: {len(blocks)} nhân vật đại diện duy nhất.")

        print(f"[*] Đóng gói xuất kết quả ra '{args.output}'...")
        packager = OutputPackager(Path(args.prompt))
        packager.package(blocks, Path(args.output), chunk_size=args.chunk_size)
        num_chunks = (len(blocks) + args.chunk_size - 1) // args.chunk_size if blocks else 0
        print(f"[+] Đã ghi '{args.output}/scanner_master.json' và {num_chunks} file markdown con thành công.")

        # Benchmark if ground truth exists
        gt_path = Path(args.ground_truth)
        if gt_path.exists():
            try:
                gt_data = json.loads(gt_path.read_text(encoding="utf-8")).get("file_nhan_vat", [])
                pred_data = [b.to_dict() for b in blocks]
                ev = Evaluator()
                metrics = ev.evaluate(pred_data, gt_data)
                print("\n=== KẾT QUẢ ĐÁNH GIÁ (BENCHMARK) ===")
                print(f"- Ground Truth: {metrics['total_ground_truth']} mục ({len(set(x['ten'].lower() for x in gt_data))} tên duy nhất)")
                print(f"- Trích xuất được: {metrics['total_predictions']} nhân vật duy nhất")
                print(f"- Khớp tên nhân vật duy nhất: {metrics['matched_names']}/{len(set(x['ten'].lower() for x in gt_data))} (Recall: {metrics['recall_names']*100:.1f}%)")
            except Exception as e:
                print(f"[-] Lỗi khi đánh giá benchmark: {e}")

    # 2. Giai đoạn Tự động nạp lên Gemini (nếu có cờ --upload-gemini hoặc --upload-only)
    if args.upload_gemini or args.upload_only:
        print("\n=======================================================")
        print("[*] BẮT ĐẦU QUY TRÌNH TỰ ĐỘNG GỬI FILE LÊN GEMINI...")
        run_upload_workflow(
            scanner_dir=args.output,
            profile_dir=args.profile_dir,
            output_json=args.output_import_json,
            delay=args.gemini_delay,
            headless=args.headless,
            reset_progress=args.reset_gemini_progress
        )

if __name__ == "__main__":
    main()
