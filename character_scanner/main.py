import argparse
from pathlib import Path
import json
from character_scanner.resource_loader import ResourceLoader
from character_scanner.scanner_engine import ScannerEngine
from character_scanner.output_packager import OutputPackager
from character_scanner.benchmark import Evaluator

def main():
    parser = argparse.ArgumentParser(description="Quét và nhận diện tên nhân vật")
    parser.add_argument("--input", default="exam.txt", help="Đường dẫn file văn bản đầu vào")
    parser.add_argument("--output", default="scanner", help="Thư mục xuất kết quả")
    parser.add_argument("--prompt", default="prompt.md", help="File prompt mẫu")
    parser.add_argument("--ground-truth", default="file_nhan_vat.json", help="File đối chiếu ground truth")
    parser.add_argument("--chunk-size", type=int, default=40, help="Số block mỗi file md")
    args = parser.parse_args()

    base_dir = Path(".")
    print(f"[*] Nạp tài nguyên từ điển...")
    loader = ResourceLoader(base_dir)
    loader.load_all()

    print(f"[*] Bắt đầu quét file: {args.input}...")
    engine = ScannerEngine(loader)
    blocks = engine.scan_file(Path(args.input))
    print(f"[+] Tìm thấy tổng cộng: {len(blocks)} ứng viên nhân vật.")

    print(f"[*] Đóng gói xuất kết quả ra '{args.output}'...")
    packager = OutputPackager(Path(args.prompt))
    packager.package(blocks, Path(args.output), chunk_size=args.chunk_size)
    print(f"[+] Đã ghi '{args.output}/scanner_master.json' và các file markdown con thành công.")

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
            print(f"- Trích xuất được: {metrics['total_predictions']} mục")
            print(f"- Khớp chính xác (Tên + Dòng): {metrics['matched_exact']} (Recall: {metrics['recall_exact']*100:.1f}%)")
            print(f"- Khớp tên nhân vật duy nhất: {metrics['matched_names']}/{len(set(x['ten'].lower() for x in gt_data))} (Recall: {metrics['recall_names']*100:.1f}%)")
        except Exception as e:
            print(f"[-] Lỗi khi đánh giá benchmark: {e}")

if __name__ == "__main__":
    main()
