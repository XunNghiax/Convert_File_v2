import sys
import argparse
from pathlib import Path
import json

# Đảm bảo đường dẫn gốc của project có trong sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from .resource_loader import ResourceLoader
from .scanner_engine import ScannerEngine, CharacterBlock
from .output_packager import OutputPackager
from .benchmark import Evaluator
from .upload_to_gemini import run_upload_workflow

import gc

def stream_write_json_array(file_path: Path, items_iterable):
    """Ghi danh sách dicts ra file JSON dạng streaming để không tốn RAM."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("[\n")
        first = True
        for item in items_iterable:
            if not first:
                f.write(",\n")
            else:
                first = False
            item_json = json.dumps(item, ensure_ascii=False, indent=2)
            indented = "  " + item_json.replace("\n", "\n  ")
            f.write(indented)
        f.write("\n]\n")

def resolve_file(path_str: str, default_dir: str) -> Path:
    p = Path(path_str)
    if p.exists():
        return p
    fallback = Path(default_dir) / path_str
    if fallback.exists():
        return fallback
    fallback_name = Path(default_dir) / p.name
    if fallback_name.exists():
        return fallback_name
    return p

def main():
    parser = argparse.ArgumentParser(description="Hệ thống Quét tên nhân vật & Tự động biên tập qua Gemini")
    
    # Nhóm tham số quét văn bản
    parser.add_argument("--input", default="samples/exam.txt", help="Đường dẫn file văn bản đầu vào (mặc định: samples/exam.txt)")
    parser.add_argument("--output", default="output/scanner", help="Thư mục xuất kết quả markdown và master json (mặc định: output/scanner)")
    parser.add_argument("--prompt", default="resources/prompts/prompt.md", help="File prompt mẫu (mặc định: resources/prompts/prompt.md)")
    parser.add_argument("--ground-truth", default="samples/file_nhan_vat.json", help="File đối chiếu ground truth (mặc định: samples/file_nhan_vat.json)")
    parser.add_argument("--chunk-size", type=int, default=40, help="Số block mỗi file md (mặc định: 40)")
    parser.add_argument("--no-dedup", action="store_true", help="Không khử trùng lặp (giữ mọi vị trí xuất hiện)")
    parser.add_argument("--min-count", type=int, default=1, help="Số lần xuất hiện tối thiểu để giữ lại nhân vật (mặc định: 1)")
    parser.add_argument("--include-known", action="store_true", help="Liệt kê cả các nhân vật đã có trong từ điển (mặc định: chỉ tìm nhân vật mới)")
    parser.add_argument("--filter-only", action="store_true", help="Chỉ lọc nhanh thư mục scanner hiện có theo --min-count và đóng gói lại markdown")

    # Nhóm tham số tự động đẩy lên Gemini
    parser.add_argument("--upload-gemini", action="store_true", help="Tự động nạp các file kết quả lên Gemini sau khi quét xong")
    parser.add_argument("--upload-only", action="store_true", help="Chỉ chạy tự động nạp Gemini (bỏ qua bước quét văn bản)")
    parser.add_argument("--profile-dir", default="runtime/chrome_profiles", help="Thư mục profile Chrome (mặc định: runtime/chrome_profiles)")
    parser.add_argument("--output-import-json", default="samples/import.json", help="Đường dẫn file import.json kết quả từ Gemini (mặc định: samples/import.json)")
    parser.add_argument("--gemini-delay", type=int, default=5, help="Thời gian nghỉ (giây) giữa các file khi gửi Gemini")
    parser.add_argument("--headless", action="store_true", help="Chạy ẩn danh không mở cửa sổ Chrome")
    parser.add_argument("--reset-gemini-progress", action="store_true", help="Đặt lại (reset) tiến trình gửi Gemini cũ")
    parser.add_argument("--files-per-chat", type=int, default=3, help="Số file tối đa gửi trong 1 đoạn chat trước khi tạo đoạn chat mới (mặc định: 3)")

    args = parser.parse_args()
    prompt_path = resolve_file(args.prompt, "resources/prompts")

    # 0. Chế độ lọc nhanh file scanner hiện có theo số lần xuất hiện
    if args.filter_only:
        output_dir = Path(args.output)
        if not output_dir.exists():
            if (Path("output") / args.output).exists():
                output_dir = Path("output") / args.output
            elif Path("scanner").exists():
                output_dir = Path("scanner")
        source_path = output_dir / "scanner_all.json" if (output_dir / "scanner_all.json").exists() else (output_dir / "scanner_master.json")
        if not source_path.exists():
            print(f"[-] Không tìm thấy file nguồn: {source_path}")
            return
        
        raw_data = json.loads(source_path.read_text(encoding="utf-8"))
        orig_len = len(raw_data)
        filtered_data = [item for item in raw_data if item.get("so_lan_xuat_hien", 1) >= args.min_count]
        for idx, item in enumerate(filtered_data, start=1):
            item["id"] = f"ch_{idx:04d}"
        
        blocks = [
            CharacterBlock(
                id=item["id"],
                source=item.get("source", ""),
                target=item.get("target", ""),
                context=item.get("context", ""),
                yeu_to_nhan_biet=item.get("yeu_to_nhan_biet", ""),
                so_lan_xuat_hien=item.get("so_lan_xuat_hien", 1),
                is_character=item.get("is_character", True)
            )
            for item in filtered_data
        ]
        
        packager = OutputPackager(prompt_path)
        packager.package(blocks, output_dir, chunk_size=args.chunk_size)
        num_chunks = (len(blocks) + args.chunk_size - 1) // args.chunk_size if blocks else 0
        print(f"[+] Đã lọc nhanh theo số lần xuất hiện >= {args.min_count}: {orig_len} -> {len(blocks)} nhân vật.")
        print(f"[+] Đã ghi lại '{output_dir}/scanner_master.json' và {num_chunks} file markdown con thành công.")
        return

    # 1. Giai đoạn Quét văn bản (nếu không bật --upload-only)
    if not args.upload_only:
        base_dir = Path(".")
        print(f"[*] Nạp tài nguyên từ điển...")
        loader = ResourceLoader(base_dir)
        loader.load_all()

        dedup = not args.no_dedup
        skip_known = not args.include_known
        input_path = resolve_file(args.input, "samples")
        print(f"[*] Bắt đầu quét file: {input_path} (Khử trùng lặp: {dedup})...")
        if skip_known:
            print(f"[*] Chế độ: Chỉ tìm nhân vật MỚI (đã loại trừ các nhân vật trong từ điển)...")
        else:
            print(f"[*] Chế độ: Liệt kê TẤT CẢ nhân vật (kể cả đã có trong từ điển)...")

        engine = ScannerEngine(loader, skip_known=skip_known)
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        packager = OutputPackager(prompt_path)
        all_file = output_dir / "scanner_all.json"

        print(f"[*] Quét văn bản và lưu dữ liệu realtime vào '{all_file.name}'...")
        blocks = engine.scan_file(
            input_path,
            deduplicate=dedup,
            skip_known=skip_known,
            realtime_all_path=all_file
        )
        print(f"[+] Quét hoàn tất: {len(blocks)} nhân vật đại diện duy nhất đã được lưu realtime vào '{all_file.name}'.")

        orig_len = len(blocks)
        if args.min_count > 1:
            filtered_blocks = [b for b in blocks if b.so_lan_xuat_hien >= args.min_count]
            print(f"[+] Đã lọc theo số lần xuất hiện >= {args.min_count}: {orig_len} -> {len(filtered_blocks)} nhân vật.")
            for idx, b in enumerate(filtered_blocks, start=1):
                b.id = f"ch_{idx:04d}"
        else:
            filtered_blocks = blocks

        del blocks
        gc.collect()

        packager.package(filtered_blocks, output_dir, chunk_size=args.chunk_size)

        # Benchmark if ground truth exists
        gt_path = resolve_file(args.ground_truth, "samples")
        if gt_path.exists():
            try:
                gt_data = json.loads(gt_path.read_text(encoding="utf-8")).get("file_nhan_vat", [])
                master_file = output_dir / "scanner_master.json"
                pred_data = json.loads(master_file.read_text(encoding="utf-8")) if master_file.exists() else []
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
            reset_progress=args.reset_gemini_progress,
            files_per_chat=args.files_per_chat
        )

if __name__ == "__main__":
    main()
