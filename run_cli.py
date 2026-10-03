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
    hanviet_path = Path("resources/dictionaries/hanviet_dict.json")
    deconvert_path = Path("resources/dictionaries/deconvert_dict.json")
    import_path = Path("samples/import.json")
    import_hanviet_path = Path("samples/import_hanviet.json")
    suggested_path = Path("samples/suggested_terms.json")

    def _count_json(path):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return len(data) if isinstance(data, (dict, list)) else 0
            except Exception:
                return 0
        return None

    return {
        "character": _count_json(char_path) or 0,
        "common": _count_json(comm_path) or 0,
        "hanviet": _count_json(hanviet_path) or 0,
        "deconvert": _count_json(deconvert_path) or 0,
        "import_json": _count_json(import_path),
        "import_hanviet": _count_json(import_hanviet_path),
        "suggested_terms": _count_json(suggested_path)
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
    print(f"     • hanviet_dict.json   : {stats['hanviet']} mục (Từ điển Hán Việt)")
    if stats['deconvert'] > 0:
        print(f"     • deconvert_dict.json : {stats['deconvert']} mục (Chống de-convert)")
    if stats['import_json'] is not None:
        print(f"     • samples/import.json : {stats['import_json']} mục (Sẵn sàng nạp nhân vật)")
    if stats['import_hanviet'] is not None:
        print(f"     • import_hanviet.json : {stats['import_hanviet']} mục (Sẵn sàng nạp Hán Việt)")
    if stats['suggested_terms'] is not None:
        print(f"     • suggested_terms.json: {stats['suggested_terms']} mục (Từ mới thu hoạch)")
    print("-" * 68)

def print_sub_banner(title: str):
    print("\n" + "=" * 68)
    print(f"  {title}")
    print("=" * 68)

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

def get_raw_txt_files():
    """Tìm danh sách file raw trong craw/ và samples/."""
    candidates = []
    for d in [Path("craw"), Path("samples")]:
        if d.exists():
            for f in sorted(d.glob("*.txt")):
                if f.is_file():
                    candidates.append(f)
    return candidates

def prompt_raw_file(default="craw/shao_long_feng_liu_raw.txt"):
    """Hỏi người dùng chọn file raw với danh sách gợi ý."""
    raw_files = get_raw_txt_files()
    if raw_files:
        print("\n📂 Danh sách file raw tìm thấy trong craw/ và samples/:")
        for idx, f in enumerate(raw_files, start=1):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   [{idx}] {f.as_posix()} ({size_mb:.2f} MB)")
        val = input(f"\n👉 Chọn số thứ tự (1-{len(raw_files)}) hoặc nhập đường dẫn [Mặc định: {default}]: ").strip()
        if not val:
            return default
        if val.isdigit() and 1 <= int(val) <= len(raw_files):
            return str(raw_files[int(val) - 1])
        return val
    else:
        val = input(f"Nhập đường dẫn file raw [Mặc định: {default}]: ").strip()
        return val or default


# =====================================================================
# MENU CON: [1] DỊCH THUẬT AI (OLLAMA / COLAB)
# =====================================================================
def menu_ai_translation():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🌐 NHÓM 1: DỊCH THUẬT AI (OLLAMA QWEN2.5 / GOOGLE COLAB)")
            print("  [1] 🚀 Dịch tiểu thuyết raw toàn trình (Colab Server API)")
            print("  [2] 📡 Kiểm tra kết nối nhanh tới máy chủ Colab / Ollama")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-2) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print("\n--- [1.1] DỊCH TIỂU THUYẾT RAW BẰNG OLLAMA QWEN2.5 ---")
                colab_url = input("👉 Nhập URL Public Colab (ví dụ: https://xxx.trycloudflare.com): ").strip()
                if not colab_url:
                    print("❌ URL không được để trống!")
                    input("👉 Nhấn Enter để tiếp tục...")
                    continue

                from src.translator.translator_engine import TranslatorEngine
                print("\n[*] Đang kiểm tra kết nối tới Colab Ollama...")
                engine = TranslatorEngine(colab_url=colab_url)
                if not engine.client.check_health():
                    print(f"❌ Không thể kết nối tới Ollama tại {colab_url}.")
                    print("    Vui lòng kiểm tra notebook Colab và đường link Cloudflare Tunnel.")
                    input("👉 Nhấn Enter để tiếp tục...")
                    continue
                print("✅ Kết nối Ollama thành công!")

                raw_file = prompt_raw_file("craw/shao_long_feng_liu_raw.txt")
                raw_path = Path(raw_file)
                if not raw_path.exists():
                    print(f"❌ Không tìm thấy file: {raw_file}")
                    input("👉 Nhấn Enter để tiếp tục...")
                    continue

                default_out = f"convert/translated/{raw_path.stem}_vietnamese.txt"
                out_file = input(f"👉 File kết quả bản dịch [Mặc định: {default_out}]: ").strip() or default_out

                start_chap_str = input("👉 Bắt đầu từ chương số (hoặc tự động resume) [Mặc định: tự động]: ").strip()
                start_chap = int(start_chap_str) if start_chap_str.isdigit() else 1

                max_chap_str = input("👉 Giới hạn số chương cần dịch (để trống = dịch toàn bộ) [Mặc định: Toàn bộ]: ").strip()
                max_chap = int(max_chap_str) if max_chap_str.isdigit() else None

                post_proc = input("👉 Tự động chạy ReplaceEngine hậu kỳ sau khi dịch? (Y/n) [Mặc định: Y]: ").strip().lower() != "n"

                print(f"\n🚀 Bắt đầu tiến trình dịch thuật...")
                print(f"   • File raw: {raw_file}")
                print(f"   • File dịch: {out_file}")
                print(f"   • Checkpoint: progress_{Path(out_file).stem}.json")
                print("-" * 68)

                def _progress_cb(cur_idx, total_cnt, chap_title, elapsed):
                    print(f"   [+] Hoàn thành [{cur_idx}/{total_cnt}] ({elapsed:.1f}s): {chap_title}")

                try:
                    engine.translate_novel(
                        raw_filepath=raw_path,
                        output_filepath=out_file,
                        start_chapter=start_chap,
                        max_chapters=max_chap,
                        run_post_processing=post_proc,
                        progress_callback=_progress_cb
                    )
                    print("\n🎉 DỊCH THUẬT HOÀN TẤT THÀNH CÔNG!")
                    print(f"📄 File kết quả đã lưu tại: {out_file}")
                except Exception as e:
                    print(f"\n❌ Lỗi trong quá trình dịch: {e}")

                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print("\n--- [1.2] KIỂM TRA KẾT NỐI MÁY CHỦ COLAB / OLLAMA ---")
                colab_url = input("👉 Nhập URL Public Colab: ").strip()
                if not colab_url:
                    print("❌ URL không được để trống!")
                else:
                    from src.translator.ollama_client import OllamaTranslatorClient
                    client = OllamaTranslatorClient(base_url=colab_url)
                    print(f"[*] Đang gửi tín hiệu kiểm tra tới {colab_url}...")
                    if client.check_health():
                        print("✅ KẾT NỐI THÀNH CÔNG! Máy chủ Ollama đang hoạt động bình thường.")
                    else:
                        print("❌ KẾT NỐI THẤT BẠI! Vui lòng kiểm tra lại Cloudflare Tunnel hoặc GPU Colab.")
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [2] QUÉT & XỬ LÝ TÊN NHÂN VẬT
# =====================================================================
def menu_character_scanner():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("👥 NHÓM 2: QUÉT & XỬ LÝ TÊN NHÂN VẬT (CHARACTER SCANNER)")
            print("  [1] 🚀 Toàn trình: Quét nhân vật + Tự động gửi Gemini -> samples/import.json")
            print("  [2] 🔍 Chỉ quét nhân vật (Xuất thư mục scanner/ gồm .md & master JSON)")
            print("  [3] 🌐 Chỉ gửi các file trong scanner/ lên Gemini -> samples/import.json")
            print("  [4] 🎯 Lọc nhanh scanner/ theo số lần xuất hiện (min-count)")
            print("  [5] ♻️  Đặt lại tiến trình (Reset progress) gửi Gemini")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-5) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print("\n--- [2.1] TOÀN TRÌNH: QUÉT VĂN BẢN VÀ TỰ ĐỘNG GỬI GEMINI ---")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                include_known = input("Liệt kê cả nhân vật đã có trong từ điển? (y/N) [Mặc định: N]: ").strip().lower() == "y"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import.json]: ").strip() or "samples/import.json"

                cmd = [
                    sys.executable, "-m", "src.scanner.main",
                    "--input", inp,
                    "--output", "scanner",
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
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print("\n--- [2.2] CHỈ QUÉT VĂN BẢN NHÂN VẬT ---")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                include_known = input("Liệt kê cả nhân vật đã có trong từ điển? (y/N) [Mặc định: N]: ").strip().lower() == "y"

                cmd = [
                    sys.executable, "-m", "src.scanner.main",
                    "--input", inp,
                    "--output", "scanner",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]
                if include_known:
                    cmd.append("--include-known")
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "3":
                print("\n--- [2.3] CHỈ GỬI CÁC FILE SCANNER CÓ SẴN LÊN GEMINI ---")
                scanner_dir = input("Thư mục chứa các file .md [Mặc định: scanner]: ").strip() or "scanner"
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
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "4":
                print("\n--- [2.4] LỌC NHANH FILE SCANNER THEO SỐ LẦN XUẤT HIỆN (MIN-COUNT) ---")
                min_cnt = input("Số lần xuất hiện tối thiểu cần giữ lại [Mặc định: 2]: ").strip() or "2"
                chunk = input("Số block mỗi file .md [Mặc định: 40]: ").strip() or "40"

                cmd = [
                    sys.executable, "-m", "src.scanner.main",
                    "--filter-only",
                    "--output", "scanner",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "5":
                print("\n--- [2.5] ĐẶT LẠI TIẾN TRÌNH & GỬI LẠI LÊN GEMINI ---")
                confirm = input("⚠️ Bạn có chắc muốn xóa lịch sử tiến trình cũ và gửi lại từ đầu? (y/N): ").strip().lower()
                if confirm in ("y", "yes"):
                    prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                    cmd = [
                        sys.executable, "-m", "src.scanner.main",
                        "--upload-only",
                        "--output", "scanner",
                        "--profile-dir", prof,
                        "--reset-gemini-progress"
                    ]
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                    subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [3] QUÉT & XỬ LÝ TỪ HÁN VIỆT / CỤM TỪ LẠ
# =====================================================================
def menu_hanviet_scanner():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🏮 NHÓM 3: QUÉT & XỬ LÝ TỪ HÁN VIỆT / CỤM TỪ LẠ (HANVIET SCANNER)")
            print("  [1] 🏮 Toàn trình: Quét Hán Việt + Tự động gửi Gemini -> samples/import_hanviet.json")
            print("  [2] 🔍 Chỉ quét từ Hán Việt & Cụm từ bất thường (Xuất scanner/hanviet/)")
            print("  [3] 🌐 Chỉ gửi các file trong scanner/hanviet/ lên Gemini")
            print("  [4] 🎯 Lọc nhanh scanner/hanviet/ theo số lần xuất hiện (min-count)")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-4) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print("\n--- [3.1] TOÀN TRÌNH: QUÉT HÁN VIỆT & TỰ ĐỘNG GỬI GEMINI ---")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import_hanviet.json]: ").strip() or "samples/import_hanviet.json"

                cmd = [
                    sys.executable, "-m", "src.scanner.hanviet_scanner",
                    "--input", inp,
                    "--output", "scanner/hanviet",
                    "--chunk-size", chunk,
                    "--min-count", min_cnt,
                    "--upload-gemini",
                    "--profile-dir", prof,
                    "--output-import-json", out_json
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print("\n--- [3.2] CHỈ QUÉT TỪ HÁN VIỆT & CỤM TỪ BẤT THƯỜNG ---")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"

                cmd = [
                    sys.executable, "-m", "src.scanner.hanviet_scanner",
                    "--input", inp,
                    "--output", "scanner/hanviet",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "3":
                print("\n--- [3.3] CHỈ GỬI CÁC FILE HÁN VIỆT LÊN GEMINI ---")
                scanner_dir = input("Thư mục chứa các file .md [Mặc định: scanner/hanviet]: ").strip() or "scanner/hanviet"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import_hanviet.json]: ").strip() or "samples/import_hanviet.json"
                delay = input("Thời gian nghỉ giữa các file (giây) [Mặc định: 5]: ").strip() or "5"

                cmd = [
                    sys.executable, "-m", "src.scanner.hanviet_scanner",
                    "--upload-only",
                    "--output", scanner_dir,
                    "--profile-dir", prof,
                    "--output-import-json", out_json,
                    "--gemini-delay", delay
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "4":
                print("\n--- [3.4] LỌC NHANH FILE HÁN VIỆT THEO MIN-COUNT ---")
                min_cnt = input("Số lần xuất hiện tối thiểu cần giữ lại [Mặc định: 2]: ").strip() or "2"
                chunk = input("Số block mỗi file .md [Mặc định: 40]: ").strip() or "40"

                cmd = [
                    sys.executable, "-m", "src.scanner.hanviet_scanner",
                    "--filter-only",
                    "--output", "scanner/hanviet",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [4] QUẢN LÝ TỪ ĐIỂN & NẠP DỮ LIỆU
# =====================================================================
def menu_dictionary_manager():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("📖 NHÓM 4: QUẢN LÝ TỪ ĐIỂN & NẠP DỮ LIỆU (DICTIONARY MANAGER)")
            print("  [1] 📥 Nạp samples/import.json vào từ điển (Tự động phân loại theo is_character)")
            print("  [2] 📥 Nạp samples/import_hanviet.json vào hanviet_dict.json")
            print("  [3] 📥 Nạp từ mới thu hoạch (samples/suggested_terms.json) vào từ điển")
            print("  [4] ✍️  Nhập thủ công từng từ vào từ điển (Interactive mode)")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-4) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print("\n--- [4.1] NẠP DỮ LIỆU VÀO TỪ ĐIỂN (IMPORT) ---")
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
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print("\n--- [4.2] NẠP KẾT QUẢ VÀO TỪ ĐIỂN HÁN VIỆT (HANVIET_DICT.JSON) ---")
                file_imp = input("File JSON cần import [Mặc định: samples/import_hanviet.json]: ").strip() or "samples/import_hanviet.json"
                dict_dst = "resources/dictionaries/hanviet_dict.json"

                cmd = [
                    sys.executable, "-m", "src.importer.main",
                    "--file", file_imp,
                    "--dict", dict_dst
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "3":
                print("\n--- [4.3] NẠP TỪ MỚI THU HOẠCH TỪ DỊCH THUẬT ---")
                suggested_file = Path("samples/suggested_terms.json")
                if not suggested_file.exists():
                    print("⚠️ Chưa có file samples/suggested_terms.json (được tự động sinh ra khi dịch tiểu thuyết ở Nhóm 1).")
                else:
                    target_dict = input("Nạp vào từ điển nào? (1: common_dict.json, 2: character_dict.json) [Mặc định: 1]: ").strip() or "1"
                    dest_file = "resources/dictionaries/character_dict.json" if target_dict == "2" else "resources/dictionaries/common_dict.json"
                    cmd = [
                        sys.executable, "-m", "src.importer.main",
                        "--file", str(suggested_file),
                        "--dict", dest_file
                    ]
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                    subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "4":
                print("\n--- [4.4] NHẬP THỦ CÔNG TỪNG TỪ VÀO TỪ ĐIỂN ---")
                cmd = [sys.executable, "-m", "src.importer.main", "--interactive"]
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [5] THAY THẾ VĂN BẢN (REPLACE ENGINE)
# =====================================================================
def menu_replace_engine():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🔄 NHÓM 5: THAY THẾ VĂN BẢN & HẬU KỲ (REPLACE ENGINE)")
            print("  [1] 🔄 Thay thế văn bản bằng từ điển (Single-Pass Longest Match)")
            print("  [2] 🛡️ Quét & Thay thế các lỗi de-convert tên riêng (deconvert_dict.json)")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-2) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print("\n--- [5.1] THAY THẾ VĂN BẢN BẰNG TỪ ĐIỂN (REPLACE ENGINE) ---")
                inp = prompt_input_file("samples/exam.txt")
                p_inp = Path(inp)
                default_out = f"convert/{p_inp.stem}_converted{p_inp.suffix}"
                out = input(f"Đường dẫn file kết quả [Mặc định: {default_out}]: ").strip() or default_out

                cmd = [
                    sys.executable, "-m", "src.replacer.main",
                    "--input", inp,
                    "--output", out
                ]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print("\n--- [5.2] LÀM SẠCH LỖI DE-CONVERT TÊN RIÊNG ---")
                inp = prompt_input_file("samples/exam.txt")
                p_inp = Path(inp)
                default_out = f"convert/{p_inp.stem}_deconverted{p_inp.suffix}"
                out = input(f"Đường dẫn file kết quả [Mặc định: {default_out}]: ").strip() or default_out

                from src.replacer.replace_engine import ReplaceEngine
                deconvert_file = Path("resources/dictionaries/deconvert_dict.json")
                if not deconvert_file.exists():
                    print("❌ Không tìm thấy resources/dictionaries/deconvert_dict.json!")
                else:
                    try:
                        mapping = json.loads(deconvert_file.read_text(encoding="utf-8"))
                        engine = ReplaceEngine(custom_mapping=mapping)
                        stats = engine.replace_file(inp, out, show_progress=True)
                        print(f"\n✅ Đã hoàn thành! Đã sửa {stats.total_replacements} vị trí lỗi.")
                        print(f"📄 Kết quả lưu tại: {out}")
                    except Exception as e:
                        print(f"❌ Lỗi: {e}")
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [6] CÔNG CỤ HỆ THỐNG & KIỂM THỬ
# =====================================================================
def menu_system_tools():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🛠️ NHÓM 6: CÔNG CỤ HỆ THỐNG & KIỂM THỬ (SYSTEM & TESTS)")
            print("  [1] 🧪 Chạy toàn bộ Unit Tests hệ thống (Pytest)")
            print("  [2] 📊 Xem chi tiết đường dẫn và số lượng file tài nguyên")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-2) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print("\n--- [6.1] CHẠY KIỂM THỬ HỆ THỐNG (UNIT TESTS) ---")
                cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
                print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print("\n--- [6.2] CHI TIẾT TÀI NGUYÊN HỆ THỐNG ---")
                stats = get_data_stats()
                print("📁 THƯ MỤC VÀ TỪ ĐIỂN:")
                for k, v in stats.items():
                    print(f"   • {k:20s}: {v if v is not None else 'Chưa có'}")
                print("\n📁 DANH SÁCH FILE RAW TRONG CRAW/ & SAMPLES/:")
                for f in get_raw_txt_files():
                    size_mb = f.stat().st_size / (1024 * 1024)
                    print(f"   • {f.as_posix()} ({size_mb:.2f} MB)")
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CHÍNH (MAIN MENU)
# =====================================================================
def main_menu():
    while True:
        try:
            clear_screen()
            print_banner()
            print("  [ CÁC NHÓM CHỨC NĂNG HỆ THỐNG ]")
            print("  [1] 🌐 Dịch thuật AI (Ollama Qwen2.5 / Google Colab)")
            print("  [2] 👥 Quét & Xử lý Tên Nhân vật (Character Scanner)")
            print("  [3] 🏮 Quét & Xử lý Từ Hán Việt / Cụm từ lạ (Hanviet Scanner)")
            print("  [4] 📖 Quản lý Từ điển & Nạp Dữ liệu (Dictionary Manager)")
            print("  [5] 🔄 Thay thế Văn bản & Hậu kỳ (Replace Engine)")
            print("  [6] 🛠️ Công cụ Hệ thống & Kiểm thử (System & Tests)")
            print("  [0] ❌ Thoát chương trình")
            print("=" * 68)

            choice = input("👉 Nhập nhóm chức năng bạn muốn chọn (0-6) [Mặc định: 1]: ").strip()
            if not choice:
                choice = "1"

            if choice == "0":
                print("\n👋 Cảm ơn bạn đã sử dụng chương trình. Tạm biệt!")
                break
            elif choice == "1":
                menu_ai_translation()
            elif choice == "2":
                menu_character_scanner()
            elif choice == "3":
                menu_hanviet_scanner()
            elif choice == "4":
                menu_dictionary_manager()
            elif choice == "5":
                menu_replace_engine()
            elif choice == "6":
                menu_system_tools()
            else:
                print("❌ Lựa chọn không hợp lệ. Vui lòng chọn số từ 0 đến 6!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n\n[!] Đã hủy thao tác qua phím tắt (Ctrl+C). Đang thoát...")
            break


if __name__ == "__main__":
    main_menu()
