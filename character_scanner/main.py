import argparse
from pathlib import Path
import json
from character_scanner.resource_loader import ResourceLoader
from character_scanner.scanner_engine import ScannerEngine, CharacterBlock
from character_scanner.output_packager import OutputPackager
from character_scanner.benchmark import Evaluator
from character_scanner.upload_to_gemini import run_upload_workflow

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
    parser.add_argument("--filter-only", action="store_true", help="Chỉ lọc nhanh thư mục scanner hiện có theo --min-count và đóng gói lại markdown")

    # Nhóm tham số tự động đẩy lên Gemini
    parser.add_argument("--upload-gemini", action="store_true", help="Tự động nạp các file kết quả lên Gemini sau khi quét xong")
    parser.add_argument("--upload-only", action="store_true", help="Chỉ chạy tự động nạp Gemini (bỏ qua bước quét văn bản)")
    parser.add_argument("--profile-dir", default="runtime/chrome_profiles", help="Thư mục profile Chrome (mặc định: runtime/chrome_profiles)")
    parser.add_argument("--output-import-json", default="output/import.json", help="Đường dẫn file import.json kết quả từ Gemini (mặc định: output/import.json)")
    parser.add_argument("--gemini-delay", type=int, default=5, help="Thời gian nghỉ (giây) giữa các file khi gửi Gemini")
    parser.add_argument("--headless", action="store_true", help="Chạy ẩn danh không mở cửa sổ Chrome")
    parser.add_argument("--reset-gemini-progress", action="store_true", help="Đặt lại (reset) tiến trình gửi Gemini cũ")

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
        input_path = resolve_file(args.input, "samples")
        print(f"[*] Bắt đầu quét file: {input_path} (Khử trùng lặp: {dedup})...")
        engine = ScannerEngine(loader)
        blocks = engine.scan_file(input_path, deduplicate=dedup)
        print(f"[+] Kết quả quét thô: {len(blocks)} nhân vật đại diện duy nhất.")

        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Lưu bản master đầy đủ chưa lọc vào scanner_all.json
        all_payload = [b.to_output_dict() for b in blocks]
        (output_dir / "scanner_all.json").write_text(json.dumps(all_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        # Lọc theo số lần xuất hiện nếu min_count > 1
        if args.min_count > 1:
            orig_len = len(blocks)
            blocks = [b for b in blocks if b.so_lan_xuat_hien >= args.min_count]
            for idx, b in enumerate(blocks, start=1):
                b.id = f"ch_{idx:04d}"
            print(f"[+] Đã lọc theo số lần xuất hiện >= {args.min_count}: {orig_len} -> {len(blocks)} nhân vật.")

        print(f"[*] Đóng gói xuất kết quả ra '{args.output}'...")
        packager = OutputPackager(prompt_path)
        packager.package(blocks, output_dir, chunk_size=args.chunk_size)
        num_chunks = (len(blocks) + args.chunk_size - 1) // args.chunk_size if blocks else 0
        print(f"[+] Đã ghi '{args.output}/scanner_master.json' và {num_chunks} file markdown con thành công.")

        # Benchmark if ground truth exists
        gt_path = resolve_file(args.ground_truth, "samples")
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
