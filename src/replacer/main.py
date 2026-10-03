import sys
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Đảm bảo đường dẫn gốc của project có trong sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.replacer.replace_engine import ReplaceEngine, DEFAULT_CHARACTER_DICT, DEFAULT_COMMON_DICT, DEFAULT_HANVIET_DICT

def format_size(size_bytes: int) -> str:
    """Định dạng kích thước file theo KB/MB dễ đọc."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"

def main():
    parser = argparse.ArgumentParser(description="Hệ thống thay thế văn bản hiệu năng cao bằng từ điển (Replace Engine)")
    parser.add_argument("--input", "-i", default="samples/exam.txt", help="Đường dẫn file văn bản đầu vào (mặc định: samples/exam.txt)")
    parser.add_argument("--output", "-o", default=None, help="Đường dẫn file kết quả (mặc định: convert/<tên_file>_converted.txt)")
    parser.add_argument("--char-dict", default=str(DEFAULT_CHARACTER_DICT), help="Đường dẫn từ điển nhân vật (mặc định: resources/dictionaries/character_dict.json)")
    parser.add_argument("--hanviet-dict", default=str(DEFAULT_HANVIET_DICT), help="Đường dẫn từ điển Hán Việt (mặc định: resources/dictionaries/hanviet_dict.json)")
    parser.add_argument("--common-dict", default=str(DEFAULT_COMMON_DICT), help="Đường dẫn từ điển chung (mặc định: resources/dictionaries/common_dict.json)")
    parser.add_argument("--no-stats", action="store_true", help="Không in bảng thống kê chi tiết top từ được thay thế")
    parser.add_argument("--quiet", action="store_true", help="Chạy chế độ yên lặng, không hiển thị thanh tiến trình")

    args = parser.parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        fallback = Path("samples") / args.input
        if fallback.exists():
            input_path = fallback
        else:
            print(f"[-] Lỗi: Không tìm thấy file đầu vào '{args.input}'!")
            sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        out_dir = Path("convert")
        output_path = out_dir / f"{input_path.stem}_converted{input_path.suffix}"

    print("=" * 68)
    print("      🚀 HỆ THỐNG THAY THẾ VĂN BẢN HIỆU NĂNG CAO (REPLACE ENGINE)")
    print("=" * 68)
    print(f"[*] File nguồn    : {input_path} ({format_size(input_path.stat().st_size)})")
    print(f"[*] File đích     : {output_path}")
    print(f"[*] Từ điển NV    : {args.char_dict}")
    print(f"[*] Từ điển HV    : {args.hanviet_dict}")
    print(f"[*] Từ điển chung : {args.common_dict}")

    print("[*] Đang nạp từ điển và biên dịch bộ so khớp siêu tốc (Single-Pass)...")
    engine = ReplaceEngine(
        char_dict_path=args.char_dict,
        hanviet_dict_path=args.hanviet_dict,
        common_dict_path=args.common_dict
    )
    print(f"[+] Đã biên dịch xong {len(engine.sorted_keys):,} quy tắc thay thế (Longest-Match First).")

    if not engine.sorted_keys:
        print("[!] Cảnh báo: Từ điển rỗng hoặc không có mục nào hợp lệ cần thay thế!")

    print(f"[*] Bắt đầu thay thế dòng văn bản...")
    stats = engine.replace_file(
        input_path=input_path,
        output_path=output_path,
        show_progress=not args.quiet,
        track_stats=not args.no_stats
    )

    print("\n" + "=" * 68)
    print("                 📊 KẾT QUẢ THAY THẾ VĂN BẢN")
    print("=" * 68)
    print(f" • Tổng số dòng xử lý   : {stats.total_lines:,} dòng")
    print(f" • Tổng lượt thay thế   : {stats.total_replacements:,} lượt")
    print(f" • Thời gian thực hiện  : {stats.elapsed_seconds:.2f} giây")
    print(f" • Tốc độ xử lý         : {int(stats.lines_per_second):,} dòng/giây")
    print(f" • Kích thước file gốc  : {format_size(stats.input_size)}")
    print(f" • Kích thước file xuất : {format_size(stats.output_size)}")
    print(f" • File kết quả đã lưu  : {output_path.resolve()}")

    if not args.no_stats and stats.top_replacements:
        print("\n🏆 TOP TỪ ĐƯỢC THAY THẾ NHIỀU NHẤT:")
        print(f" {'STT':<4} | {'Từ gốc (Source)':<25} | {'Từ mới (Target)':<25} | {'Số lượt':>8}")
        print("-" * 68)
        for idx, (src, tgt, count) in enumerate(stats.top_replacements, start=1):
            src_display = (src[:22] + "...") if len(src) > 25 else src
            tgt_display = (tgt[:22] + "...") if len(tgt) > 25 else tgt
            print(f" {idx:<4} | {src_display:<25} | {tgt_display:<25} | {count:>8,}")

    print("=" * 68)

if __name__ == "__main__":
    main()
