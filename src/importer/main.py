import argparse
import sys
from pathlib import Path

# Đảm bảo thư mục gốc dự án có trong sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.importer.dictionary_importer import (
    DEFAULT_IMPORT_JSON,
    DEFAULT_CHARACTER_DICT,
    DEFAULT_COMMON_DICT,
    distribute_and_import,
    import_entries,
    parse_source_file
)

def main():
    parser = argparse.ArgumentParser(
        description="Script import dữ liệu vào từ điển (Tự động phân bổ dựa vào 'is_character' vào character_dict.json hoặc common_dict.json)"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=str(DEFAULT_IMPORT_JSON),
        help=f"Đường dẫn file nguồn cần import (mặc định: {DEFAULT_IMPORT_JSON})"
    )
    parser.add_argument(
        "--dict", "-d",
        type=str,
        default=None,
        help="Đường dẫn file từ điển đích (Nếu để trống: Tự động phân bổ theo trường 'is_character')"
    )
    parser.add_argument("--source", "-s", type=str, help="Từ/Cụm từ gốc (nhập lẻ)")
    parser.add_argument("--target", "-t", type=str, help="Từ/Cụm từ thay thế (nhập lẻ)")
    parser.add_argument("--tag", type=str, default="", help="Nhãn ghi chú (Tag / category)")
    parser.add_argument("--id", type=str, default="", help="ID (tùy chọn, vd: ch-51)")
    parser.add_argument("--is-character", action="store_true", default=None, help="Chỉ định mục nhập lẻ là nhân vật")
    parser.add_argument("--not-character", action="store_true", default=None, help="Chỉ định mục nhập lẻ là từ chung (is_character = False)")
    parser.add_argument("--no-overwrite", action="store_true", help="Không ghi đè mục đã tồn tại trong từ điển")
    parser.add_argument("--interactive", "-i", action="store_true", help="Chế độ nhập tay từng từ qua console")
    parser.add_argument("--warning-file", type=str, default="samples/warning.json", help="Đường dẫn file lưu các mục lệch số từ cần cảnh báo (mặc định: samples/warning.json)")
    parser.add_argument("--no-word-count-check", action="store_true", help="Bỏ qua kiểm tra độ lệch số từ giữa source và target")

    args = parser.parse_args()

    items_to_import = []

    # 1. Chế độ nhập lẻ qua tham số dòng lệnh
    if args.source and args.target:
        is_char = True
        if args.not_character:
            is_char = False
        elif args.is_character:
            is_char = True

        items_to_import.append({
            "id": args.id,
            "is_character": is_char,
            "source": args.source,
            "target": args.target,
            "Tag": args.tag,
            "category": args.tag
        })
    # 2. Chế độ nhập tay tương tác
    elif args.interactive:
        print("=== CHẾ ĐỘ NHẬP TỪ ĐIỂN TƯƠNG TÁC ===")
        print("(Để trống 'Source' và nhấn Enter để kết thúc)")
        while True:
            try:
                src = input("\nSource (gốc): ").strip()
                if not src:
                    break
                tgt = input("Target (thay thế): ").strip()
                if not tgt:
                    print("[!] Target không được để trống!")
                    continue
                is_char_str = input("Có phải tên nhân vật? (y/n, Mặc định: y): ").strip().lower()
                is_char = False if is_char_str in ("n", "no", "0") else True

                tag_label = "Tag (nhân vật)" if is_char else "Category (loại từ)"
                tag = input(f"{tag_label} [tùy chọn]: ").strip()
                cid = input("ID (tùy chọn, Enter để tự sinh): ").strip()
                items_to_import.append({
                    "id": cid,
                    "is_character": is_char,
                    "source": src,
                    "target": tgt,
                    "Tag": tag,
                    "category": tag
                })
            except (KeyboardInterrupt, EOFError):
                break
    # 3. Mặc định: Đọc từ file (mặc định là samples/import.json)
    else:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[!] Không tìm thấy file nguồn: {file_path}")
            print(f"    Gợi ý: Kiểm tra đường dẫn hoặc chạy scanner để tạo {DEFAULT_IMPORT_JSON}")
            return

        print(f"[*] Đang đọc file nguồn: {file_path}")
        try:
            items_to_import = parse_source_file(file_path)
        except Exception as e:
            print(f"[X] Lỗi đọc file: {e}")
            return

    if not items_to_import:
        print("[!] Không có mục nào hợp lệ để import.")
        return

    print(f"[*] Bắt đầu xử lý {len(items_to_import)} mục...")

    # Nếu người dùng chỉ định file từ điển cụ thể:
    if args.dict:
        dict_path = Path(args.dict)
        result = import_entries(
            items_to_import,
            dict_path=dict_path,
            warning_path=args.warning_file,
            overwrite_existing=not args.no_overwrite,
            filter_characters=False,
            validate_word_count=not args.no_word_count_check
        )
        print("\n" + "=" * 55)
        print("              KẾT QUẢ IMPORT TỪ ĐIỂN")
        print("=" * 55)
        print(f"➕ Thêm mới : {result['added']}")
        print(f"🔄 Cập nhật : {result['updated']}")
        print(f"⏭️ Bỏ qua   : {result['skipped']}")
        print(f"📚 Tổng mục : {result['total']}")
        print(f"📁 File đích: {result['target_file']}")
        if result.get("warning_count", 0) > 0:
            print(f"⚠️ Cảnh báo : {result['warning_count']} mục lệch số từ đã xuất ra '{result['warning_file']}'")
        print("=" * 55)
    else:
        # Tự động phân bổ dựa vào 'is_character'
        dist_res = distribute_and_import(
            items_to_import,
            char_dict_path=DEFAULT_CHARACTER_DICT,
            common_dict_path=DEFAULT_COMMON_DICT,
            warning_path=args.warning_file,
            overwrite_existing=not args.no_overwrite,
            validate_word_count=not args.no_word_count_check
        )
        char_res = dist_res["character"]
        comm_res = dist_res["common"]

        print("\n" + "=" * 65)
        print("           KẾT QUẢ PHÂN BỔ VÀ IMPORT TỪ ĐIỂN")
        print("=" * 65)
        print(f"[1] TỪ ĐIỂN NHÂN VẬT (character_dict.json) - is_character: true")
        print(f"    ➕ Thêm mới : {char_res['added']}")
        print(f"    🔄 Cập nhật : {char_res['updated']}")
        print(f"    ⏭️ Bỏ qua   : {char_res['skipped']}")
        print(f"    📚 Tổng mục : {char_res['total']}")
        print(f"    📁 File     : {char_res['target_file']}")
        print("-" * 65)
        print(f"[2] TỪ ĐIỂN THÔNG DỤNG (common_dict.json) - is_character: false")
        print(f"    ➕ Thêm mới : {comm_res['added']}")
        print(f"    🔄 Cập nhật : {comm_res['updated']}")
        print(f"    ⏭️ Bỏ qua   : {comm_res['skipped']}")
        print(f"    📚 Tổng mục : {comm_res['total']}")
        print(f"    📁 File     : {comm_res['target_file']}")
        if dist_res.get("warning_count", 0) > 0:
            print("-" * 65)
            print(f"⚠️  PHÁT HIỆN {dist_res['warning_count']} MỤC LỆCH SỐ TỪ GIỮA SOURCE & TARGET!")
            print(f"👉 File cảnh báo: {dist_res['warning_file']}")
            print(f"💡 Lưu ý: Các mục này KHÔNG được nạp vào từ điển để tránh lỗi lặp họ khi replace.")
        print("=" * 65)

if __name__ == "__main__":
    main()
