import sys
import json
import re
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine


def load_gold_dataset(gold_path: Path) -> list[dict]:
    """Parse 91 gold standard characters from danh_sach_nhan_vat.md."""
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold file not found: {gold_path}")
    text = gold_path.read_text(encoding="utf-8")
    json_match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if not json_match:
        raise ValueError(f"No json block found in {gold_path}")
    return json.loads(json_match.group(1))


def evaluate_blocks(gold_list: list[dict], pred_blocks: list[dict]) -> dict:
    """
    Evaluate predicted character blocks against gold entities.
    Returns structured metrics: full_matches, variant_matches, partial_matches, missing.
    """
    targets_map = {}
    variants_map = {}

    for b in pred_blocks:
        t = b.get("target", "").strip()
        if t:
            targets_map[t.lower()] = b
        for v in b.get("bien_the", []):
            v_clean = v.strip()
            if v_clean:
                variants_map[v_clean.lower()] = b

    full_matches = []
    variant_matches = []
    partial_matches = []
    missing = []

    for g in gold_list:
        gold_name = g["ten_han_viet"].strip()
        gold_low = gold_name.lower()

        if gold_low in targets_map:
            matched_b = targets_map[gold_low]
            full_matches.append({
                "gold": gold_name,
                "target": matched_b["target"],
                "count": matched_b.get("so_lan_xuat_hien", 1),
                "variants": matched_b.get("bien_the", [])
            })
        elif gold_low in variants_map:
            matched_b = variants_map[gold_low]
            variant_matches.append({
                "gold": gold_name,
                "target": matched_b["target"],
                "count": matched_b.get("so_lan_xuat_hien", 1),
                "variants": matched_b.get("bien_the", [])
            })
        else:
            # Check for partial matches
            partials = []
            for b in pred_blocks:
                b_tgt = b.get("target", "").strip()
                b_low = b_tgt.lower()
                if (len(gold_low) >= 4 and gold_low in b_low) or (len(b_low) >= 4 and b_low in gold_low):
                    partials.append(b_tgt)
                elif any(w in b_low.split() for w in gold_low.split() if len(w) >= 3):
                    partials.append(b_tgt)
            if partials:
                partial_matches.append({
                    "gold": gold_name,
                    "similar": partials[:3],
                    "context": g.get("ngu_canh_chung_minh", "")
                })
            else:
                missing.append({
                    "gold": gold_name,
                    "variants": g.get("bien_the_danh_xung", []),
                    "context": g.get("ngu_canh_chung_minh", "")
                })

    total_gold = len(gold_list)
    total_captured = len(full_matches) + len(variant_matches)
    recall_captured = total_captured / total_gold if total_gold else 0.0
    recall_full = len(full_matches) / total_gold if total_gold else 0.0

    return {
        "total_gold": total_gold,
        "total_predictions": len(pred_blocks),
        "full_matches": full_matches,
        "variant_matches": variant_matches,
        "total_captured": total_captured,
        "recall_captured": recall_captured,
        "recall_full": recall_full,
        "partial_matches": partial_matches,
        "missing": missing
    }


def print_evaluation_report(title: str, results: dict, show_details: bool = True):
    print("\n" + "=" * 70)
    print(f"=== {title.upper()} ===")
    print("=" * 70)
    total = results["total_gold"]
    full_count = len(results["full_matches"])
    var_count = len(results["variant_matches"])
    captured = results["total_captured"]
    partial_count = len(results["partial_matches"])
    missing_count = len(results["missing"])

    print(f"- Tổng số nhân vật chuẩn (Gold Standard): {total}")
    print(f"- Tổng số nhân vật trích xuất (Predictions): {results['total_predictions']}")
    print(f"- Khớp trọn vẹn (Full Match Target == Gold): {full_count}/{total} ({results['recall_full']*100:.1f}%)")
    print(f"- Khớp biến thể/biệt danh (Gold in Variants/Alias): {var_count}/{total} ({var_count/total*100:.1f}%)")
    print(f"- TỔNG ĐỘ PHỦ THỰC TẾ (RECALL TỔNG CỘNG): {captured}/{total} ({results['recall_captured']*100:.1f}%)")
    print(f"- Khớp một phần / Substring (Partial Match): {partial_count}")
    print(f"- Chưa bắt được (Missing): {missing_count}")

    if show_details:
        if results["variant_matches"]:
            print(f"\n--- DANH SÁCH KHỚP QUA BIẾN THỂ / SIÊU CHUỖI ({var_count} nhân vật) ---")
            for item in results["variant_matches"]:
                print(f"  * Gold: '{item['gold']}' -> Đại diện chính: '{item['target']}' (Xuất hiện: {item['count']} lần)")

        if results["partial_matches"]:
            print(f"\n--- KHỚP MỘT PHẦN / GẦN ĐÚNG ({partial_count} nhân vật) ---")
            for item in results["partial_matches"]:
                name = item["gold"]
                reason = ""
                if name == "Vân Bách Xuyên":
                    reason = " (Nguyên tác dịch thô thành 'vân trăm sông', không xuất hiện tên Hán Việt)"
                elif name == "Đường Khiếu Thiên":
                    reason = " (Nguyên tác chỉ xuất hiện 'Đường Khiếu', Scanner đã bắt đúng 'Đường Khiếu')"
                elif name == "Tử Lâm":
                    reason = " (Thần long tử lâm, xuất hiện 3 lần dạng viết thường 'tử lâm')"
                elif name == "Đường Thủy Nguyệt":
                    reason = " (Xuất hiện dạng chữ thường/nửa hoa 'Đường thủy nguyệt')"
                print(f"  * Gold: '{name}'{reason} -> Gần giống trong Scanner: {item['similar']}")

        if results["missing"]:
            print(f"\n--- NHÂN VẬT CHƯA BẮT ĐƯỢC & PHÂN TÍCH NGUYÊN NHÂN ({missing_count} nhân vật) ---")
            for item in results["missing"]:
                name = item["gold"]
                reason = "Tên ít gặp / viết thường hoặc dịch thô"
                if name == "Vân Bách Xuyên":
                    reason = "Bản dịch thô chỉ xuất hiện 'vân trăm sông' (Bách = trăm, Xuyên = sông), không có chữ 'Vân Bách Xuyên'"
                elif name == "Đường Khiếu Thiên":
                    reason = "Nguyên tác chỉ gọi là 'Đường Khiếu' (Scanner đã bắt 'Đường Khiếu'), không xuất hiện hậu tố 'Thiên'"
                elif name == "Từ Ninh":
                    reason = "Chỉ xuất hiện 1 lần duy nhất trong toàn truyện dạng viết thường: 'từ Ninh'"
                elif name == "Đại Na · Hải Ngũ Đức":
                    reason = "Tên nước ngoài phiên âm có dấu chấm giữa '·', xuất hiện 1 lần với chữ thường ở giữa: 'Đại Na · hải Ngũ Đức'"
                elif name == "Tử Lâm":
                    reason = "Xuất hiện dạng xưng thần long viết thường 'tử lâm' (3 lần trong truyện)"
                elif name == "Đường Thủy Nguyệt":
                    reason = "Tên xuất hiện viết thường/nửa hoa 'Đường thủy nguyệt' (13 lần)"
                print(f"  * '{name}': {reason}")
                print(f"    Ngữ cảnh: {item['context'][:90]}...")


def main():
    parser = argparse.ArgumentParser(description="Đo lường Recall đối chiếu scanner output với danh_sach_nhan_vat.md (91 gold)")
    parser.add_argument("--scanner-master", default="scanner/scanner_master.json", help="Đường dẫn file scanner_master.json")
    parser.add_argument("--scanner-all", default="scanner/scanner_all.json", help="Đường dẫn file scanner_all.json")
    parser.add_argument("--gold", default="danh_sach_nhan_vat.md", help="Đường dẫn danh_sach_nhan_vat.md")
    parser.add_argument("--novel", default="samples/Mỹ mẫu cám dỗ (1-309 chương kết thúc + phiên ngoại).txt", help="File nguyên tác tiểu thuyết của 91 gold")
    parser.add_argument("--scan-novel", action="store_true", help="Quét trực tiếp file tiểu thuyết để cập nhật kết quả mới nhất")
    args = parser.parse_args()

    gold_path = Path(args.gold)
    gold_list = load_gold_dataset(gold_path)
    print(f"[*] Đã nạp {len(gold_list)} nhân vật chuẩn từ: {gold_path}")

    # Check scanner_master.json
    master_path = Path(args.scanner_master)
    if master_path.exists():
        master_data = json.loads(master_path.read_text(encoding="utf-8"))
        # Check if master is from exam.txt or from the novel
        is_novel_data = any(b.get("target", "").strip().lower() == "từ thanh" for b in master_data)
        if is_novel_data:
            results = evaluate_blocks(gold_list, master_data)
            print_evaluation_report(f"KẾT QUẢ ĐỐI CHIẾU {master_path.name} VỚI 91 GOLD", results)
            return

        print(f"\n[!] CẢNH BÁO: File '{master_path}' hiện đang chứa dữ liệu của 'samples/exam.txt' (Thiếu Long truyền kỳ).")
        print(f"    -> Đang đo đối chiếu '{master_path}' với 91 gold 'Mỹ mẫu cám dỗ' (Cross-Novel check):")
        results_exam = evaluate_blocks(gold_list, master_data)
        print_evaluation_report("ĐỐI CHIẾU EXAM.TXT VS 91 GOLD (KHÁC TIỂU THUYẾT)", results_exam, show_details=False)

    # Nếu scanner_master chứa exam.txt hoặc được yêu cầu scan, tiến hành đánh giá tiểu thuyết của 91 gold
    novel_path = Path(args.novel)
    cache_path = Path("scratch/scanner_master_mymau.json")

    novel_blocks = None
    if cache_path.exists() and not args.scan_novel:
        print(f"\n[*] Sử dụng kết quả quét chuẩn của '{novel_path.name}' từ cache '{cache_path}'...")
        novel_blocks = json.loads(cache_path.read_text(encoding="utf-8"))
    elif novel_path.exists():
        print(f"\n[*] Tiến hành quét trực tiếp '{novel_path.name}' để đối chiếu chuẩn 91 nhân vật...")
        loader = ResourceLoader()
        loader.load_all()
        engine = ScannerEngine(loader=loader, skip_known=False)
        novel_blocks = [b.to_output_dict() for b in engine.scan_file(novel_path, deduplicate=True, skip_known=False, show_progress=False)]
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(novel_blocks, ensure_ascii=False, indent=2), encoding="utf-8")
    
    if novel_blocks:
        results_novel = evaluate_blocks(gold_list, novel_blocks)
        print_evaluation_report(f"KẾT QUẢ ĐỐI CHIẾU TIỂU THUYẾT '{novel_path.name}' VỚI 91 GOLD", results_novel)


if __name__ == "__main__":
    main()
