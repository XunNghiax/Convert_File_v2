import sys
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Union, Iterable

# Đảm bảo đường dẫn gốc của project có trong sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.scanner.scanner_engine import ProgressPrinter

DEFAULT_VN_WORDS_PATH = Path("resources/dictionaries/vietnamese_words.txt")
DEFAULT_MARKERS_PATH = Path("resources/dictionaries/hanviet_markers.json")
DEFAULT_PROMPT_PATH = Path("resources/prompts/prompt_hanviet.md")
DEFAULT_OUTPUT_DIR = Path("scanner/hanviet")
DEFAULT_CHAR_DICT = Path("resources/dictionaries/character_dict.json")
DEFAULT_COMMON_DICT = Path("resources/dictionaries/common_dict.json")
DEFAULT_HANVIET_DICT = Path("resources/dictionaries/hanviet_dict.json")
DEFAULT_FILTERS_DIR = Path("resources/filters")

PREPOSITIONS_AND_PARTICLES = {
    "của", "cho", "với", "trong", "ở", "tại", "từ", "đến", "về", "lên", "xuống",
    "ra", "vào", "cùng", "và", "hoặc", "nhưng", "bằng", "do", "bởi", "vì", "như", "đối với"
}
TRAILING_PARTICLES = {
    "của", "cho", "với", "trong", "ở", "tại", "và", "hoặc", "nhưng", "là", "mà", "thì", "cũng"
}
NUMBER_WORDS = {
    "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười", "mấy", "vài", "những", "các", "mỗi", "mọi"
}
COMMON_FUNCTION_WORDS = {
    "không", "có", "chẳng", "chưa", "cũng", "đều", "sẽ", "đã", "đang", "được", "bị", "phải", "rất", "quá", "lắm",
    "hắn", "nàng", "ta", "ngươi", "mình", "họ", "chúng", "ai", "gì", "nào", "sao", "đâu", "đấy", "đó", "này", "kia",
    "thế", "vậy", "rồi", "nữa", "luôn", "thật", "liền"
}

@dataclass
class HanVietBlock:
    id: str
    source: str
    suggested_target: str
    context: str
    yeu_to_nhan_biet: str
    so_lan_xuat_hien: int = 1

    def to_output_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "suggested_target": self.suggested_target,
            "context": self.context,
            "yeu_to_nhan_biet": self.yeu_to_nhan_biet,
            "so_lan_xuat_hien": self.so_lan_xuat_hien
        }

def load_vietnamese_words(file_path: Union[str, Path]) -> set[str]:
    p = Path(file_path)
    if not p.exists():
        return set()
    words = set()
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if w:
                words.add(w)
    return words

def load_hanviet_markers(file_path: Union[str, Path]) -> list[dict]:
    p = Path(file_path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []

def load_dictionary_keys(file_path: Optional[Union[str, Path]]) -> set[str]:
    """Tải tập hợp các từ khóa (source) đã tồn tại trong từ điển để loại trừ."""
    if not file_path:
        return set()
    p = Path(file_path)
    if not p.exists():
        return set()
    keys = set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    src = str(item.get("source", "")).strip().lower()
                    if src:
                        keys.add(src)
        elif isinstance(data, dict):
            for k in data.keys():
                src = str(k).strip().lower()
                if src:
                    keys.add(src)
    except Exception:
        pass
    return keys

def load_filter_word_set(file_path: Union[str, Path]) -> set[str]:
    """Tải tập hợp từ từ các file bộ lọc trong resources/filters."""
    p = Path(file_path)
    if not p.exists():
        return set()
    words = set()
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        words.add(line)
    return words

class HanVietScanner:
    def __init__(
        self,
        words_path: Union[str, Path] = DEFAULT_VN_WORDS_PATH,
        markers_path: Union[str, Path] = DEFAULT_MARKERS_PATH,
        char_dict_path: Optional[Union[str, Path]] = DEFAULT_CHAR_DICT,
        common_dict_path: Optional[Union[str, Path]] = DEFAULT_COMMON_DICT,
        hanviet_dict_path: Optional[Union[str, Path]] = DEFAULT_HANVIET_DICT,
        filters_dir: Optional[Union[str, Path]] = DEFAULT_FILTERS_DIR
    ):
        self.vn_words = load_vietnamese_words(words_path)
        self.markers = load_hanviet_markers(markers_path)
        self.known_keys: set[str] = set()
        self.character_keys = load_dictionary_keys(char_dict_path)
        self.known_keys.update(self.character_keys)
        self.known_keys.update(load_dictionary_keys(common_dict_path))
        self.known_keys.update(load_dictionary_keys(hanviet_dict_path))

        # Nạp các bộ lọc từ resources/filters
        f_dir = Path(filters_dir) if filters_dir else DEFAULT_FILTERS_DIR
        self.blacklist = load_filter_word_set(f_dir / "blacklist.txt")
        self.pronouns = load_filter_word_set(f_dir / "pronouns.txt")
        self.trailing_stopwords = load_filter_word_set(f_dir / "trailing_stopwords.txt")

        # Tập hợp tất cả các từ dừng chức năng tiếng Việt
        self.all_stopwords = (
            self.pronouns
            | self.trailing_stopwords
            | PREPOSITIONS_AND_PARTICLES
            | COMMON_FUNCTION_WORDS
            | NUMBER_WORDS
        )

    def extract_context(self, text: str, match_start: int, match_end: int, max_len: int = 120) -> str:
        """Trích xuất câu hoặc đoạn xung quanh từ được tìm thấy để làm ngữ cảnh."""
        left = max(0, match_start - max_len // 2)
        right = min(len(text), match_end + max_len // 2)

        # Căn chỉnh theo dấu ngắt câu hoặc khoảng trắng nếu có thể
        sub = text[left:right].strip()
        # Thay thế ký tự xuống dòng nhiều lần thành khoảng trắng
        sub = re.sub(r"\s+", " ", sub)
        return sub

    def scan_text(
        self,
        text: str,
        scan_anomalies: bool = True,
        show_progress: bool = True
    ) -> list[HanVietBlock]:
        """
        Quét văn bản để tìm từ Hán Việt thô và cụm từ bất thường với thanh tiến trình trực quan.
        Trả về danh sách HanVietBlock đã thống kê tần suất và sắp xếp theo số lần xuất hiện.
        """
        counts: dict[str, int] = {}
        first_contexts: dict[str, str] = {}
        reasons: dict[str, str] = {}
        suggestions: dict[str, str] = {}

        # 1. Biên dịch regex gộp cho toàn bộ markers để quét siêu tốc
        marker_map: dict[str, tuple[str, str]] = {}
        for item in self.markers:
            pat = item.get("pattern", "").strip().lower()
            if pat and pat not in self.known_keys:
                marker_map[pat] = (item.get("suggestion", ""), item.get("category", "hanviet_marker"))

        marker_regex = None
        if marker_map:
            sorted_pats = sorted(marker_map.keys(), key=len, reverse=True)
            escaped_pats = "|".join(re.escape(p) for p in sorted_pats)
            marker_regex = re.compile(rf"(?i)(?<!\w)({escaped_pats})(?!\w)")

        lines = text.splitlines()
        total_lines = len(lines)
        progress = ProgressPrinter(total_lines=total_lines, label="mục", update_interval=0.3) if show_progress else None

        for idx, line in enumerate(lines, start=1):
            line_clean = line.strip()
            if not line_clean:
                if progress:
                    progress.update(idx, len(counts))
                continue

            # Giai đoạn 1: Quét markers Hán Việt trong dòng
            if marker_regex:
                for m in marker_regex.finditer(line_clean):
                    word_match = m.group(0).lower()
                    counts[word_match] = counts.get(word_match, 0) + 1
                    if word_match not in first_contexts:
                        first_contexts[word_match] = self.extract_context(line_clean, m.start(), m.end())
                        sug, cat = marker_map.get(word_match, ("", "hanviet_marker"))
                        reasons[word_match] = f"Hán Việt thô ({cat})"
                        suggestions[word_match] = sug

            # Giai đoạn 2: Quét cụm từ bất thường (2-3 tiếng) không có trong từ điển tiếng Việt chuẩn
            if scan_anomalies and self.vn_words:
                sentences = re.split(r"[\n.!?…]+", line_clean)
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    tokens = [t for t in re.split(r"[^\w]+", s_clean) if t and not t.isdigit()]
                    for n in (2, 3):
                        for i in range(len(tokens) - n + 1):
                            ngram_tokens = tokens[i:i+n]
                            ngram_str = " ".join(ngram_tokens).lower()
                            first_word = ngram_tokens[0].lower()
                            last_word = ngram_tokens[-1].lower()

                            # 1. Bỏ qua nếu là marker, đã có trong từ điển, hoặc nằm trong blacklist / pronouns
                            if (ngram_str in marker_map or 
                                ngram_str in self.known_keys or 
                                ngram_str in self.blacklist or 
                                ngram_str in self.pronouns):
                                continue

                            # 2. Bỏ qua nếu bắt đầu hoặc kết thúc bằng giới từ / liên từ / hư từ
                            if first_word in PREPOSITIONS_AND_PARTICLES:
                                continue
                            if last_word in TRAILING_PARTICLES:
                                continue

                            # 3. Bỏ qua nếu toàn bộ cụm từ đều là từ dừng / hư từ chức năng (VD: không có, cũng không, không thể...)
                            if all(t.lower() in self.all_stopwords for t in ngram_tokens):
                                continue

                            # 4. Bỏ qua số đếm + danh từ thông thường (VD: hai tay, một tiếng, một bên)
                            if first_word in NUMBER_WORDS and last_word in self.vn_words:
                                continue

                            # 5. Bỏ qua nếu chứa từ quá ngắn / vỡ dấu (VD: 'rô i')
                            if any(len(t) == 1 and t not in {"ý", "ở", "ổ", "ô", "ả", "e"} for t in ngram_tokens):
                                continue

                            # 6. Bỏ qua nếu là tên riêng viết hoa hoặc chứa tên nhân vật đã biết
                            if all(t[0].isupper() for t in ngram_tokens):
                                continue
                            if any(char_name in ngram_str for char_name in self.character_keys if len(char_name) >= 3):
                                continue

                            # 7. Nếu cụm từ KHÔNG có trong từ điển tiếng Việt chuẩn
                            if ngram_str not in self.vn_words:
                                counts[ngram_str] = counts.get(ngram_str, 0) + 1
                                if ngram_str not in first_contexts:
                                    first_contexts[ngram_str] = s_clean
                                    reasons[ngram_str] = "Cụm từ ngoài từ điển chuẩn"
                                    suggestions[ngram_str] = ""

            if progress:
                progress.update(idx, len(counts))

        if progress:
            progress.finish(len(counts))

        # Giai đoạn 3: Gom nhóm, gán ID và tạo danh sách kết quả
        sorted_keys = sorted(counts.keys(), key=lambda k: counts[k], reverse=True)
        blocks: list[HanVietBlock] = []
        for idx, key in enumerate(sorted_keys, start=1):
            block = HanVietBlock(
                id=f"hv_{idx:04d}",
                source=key,
                suggested_target=suggestions.get(key, ""),
                context=first_contexts.get(key, ""),
                yeu_to_nhan_biet=reasons.get(key, "Từ bất thường"),
                so_lan_xuat_hien=counts[key]
            )
            blocks.append(block)

        return blocks

class HanVietPackager:
    def __init__(self, prompt_path: Union[str, Path] = DEFAULT_PROMPT_PATH):
        self.prompt_path = Path(prompt_path)

    def package(
        self,
        blocks: Iterable[HanVietBlock],
        output_dir: Union[str, Path] = DEFAULT_OUTPUT_DIR,
        chunk_size: int = 40
    ) -> int:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        folder_name = out_dir.name

        # Xóa các file md cũ
        for old_file in out_dir.glob(f"{folder_name}_*.md"):
            try:
                old_file.unlink()
            except Exception:
                pass

        prompt_content = ""
        if self.prompt_path.exists():
            prompt_content = self.prompt_path.read_text(encoding="utf-8").strip()

        master_path = out_dir / f"{folder_name}_master.json"
        total_blocks = 0
        chunk_idx = 0
        current_chunk: list[HanVietBlock] = []

        with open(master_path, "w", encoding="utf-8") as f_master:
            f_master.write("[\n")
            first_entry = True

            for block in blocks:
                total_blocks += 1
                current_chunk.append(block)

                if not first_entry:
                    f_master.write(",\n")
                else:
                    first_entry = False
                f_master.write(json.dumps(block.to_output_dict(), ensure_ascii=False, indent=2))

                if len(current_chunk) >= chunk_size:
                    chunk_idx += 1
                    self._write_chunk(out_dir, folder_name, chunk_idx, current_chunk, prompt_content)
                    current_chunk = []

            if current_chunk:
                chunk_idx += 1
                self._write_chunk(out_dir, folder_name, chunk_idx, current_chunk, prompt_content)

            f_master.write("\n]\n")

        return total_blocks

    def _write_chunk(
        self,
        output_dir: Path,
        folder_name: str,
        chunk_idx: int,
        chunk: list[HanVietBlock],
        prompt_content: str
    ):
        md_path = output_dir / f"{folder_name}_{chunk_idx}.md"
        payload = [b.to_output_dict() for b in chunk]
        json_str = json.dumps(payload, ensure_ascii=False, indent=2)

        content = f"{prompt_content}\n\n```json\n{json_str}\n```\n"
        md_path.write_text(content, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Bộ quét từ ngữ Hán Việt thô và cụm từ bất thường (Han-Viet Scanner)")
    parser.add_argument("--input", "-i", default="samples/exam.txt", help="File văn bản đầu vào (mặc định: samples/exam.txt)")
    parser.add_argument("--output", "-o", default="scanner/hanviet", help="Thư mục xuất kết quả (mặc định: scanner/hanviet)")
    parser.add_argument("--prompt", default="resources/prompts/prompt_hanviet.md", help="Đường dẫn file prompt mẫu cho Gemini")
    parser.add_argument("--words-file", default="resources/dictionaries/vietnamese_words.txt", help="Đường dẫn từ điển tiếng Việt chuẩn")
    parser.add_argument("--markers-file", default="resources/dictionaries/hanviet_markers.json", help="Đường dẫn file Hán Việt markers")
    parser.add_argument("--char-dict", default=str(DEFAULT_CHAR_DICT), help="Đường dẫn từ điển nhân vật (để loại trừ)")
    parser.add_argument("--common-dict", default=str(DEFAULT_COMMON_DICT), help="Đường dẫn từ điển chung (để loại trừ)")
    parser.add_argument("--hanviet-dict", default=str(DEFAULT_HANVIET_DICT), help="Đường dẫn từ điển Hán Việt (để loại trừ)")
    parser.add_argument("--filters-dir", default=str(DEFAULT_FILTERS_DIR), help="Thư mục chứa các bộ lọc (blacklist, pronouns, stopwords...)")
    parser.add_argument("--chunk-size", type=int, default=40, help="Số block mỗi file markdown con (mặc định: 40)")
    parser.add_argument("--min-count", type=int, default=1, help="Số lần xuất hiện tối thiểu để giữ lại (mặc định: 1)")
    parser.add_argument("--filter-only", action="store_true", help="Chỉ lọc nhanh từ kết quả quét hiện có mà không quét lại")

    # Tham số đẩy lên Gemini
    parser.add_argument("--upload-gemini", action="store_true", help="Tự động nạp các file kết quả lên Gemini sau khi quét xong")
    parser.add_argument("--upload-only", action="store_true", help="Chỉ chạy tự động nạp Gemini (bỏ qua bước quét)")
    parser.add_argument("--profile-dir", default="runtime/chrome_profiles", help="Thư mục profile Chrome")
    parser.add_argument("--output-import-json", default="samples/import_hanviet.json", help="File import.json kết quả từ Gemini")
    parser.add_argument("--gemini-delay", type=int, default=5, help="Thời gian nghỉ (giây) giữa các file khi gửi Gemini")
    parser.add_argument("--headless", action="store_true", help="Chạy ẩn danh không mở cửa sổ Chrome")
    parser.add_argument("--reset-gemini-progress", action="store_true", help="Đặt lại tiến trình gửi Gemini cũ")
    parser.add_argument("--files-per-chat", type=int, default=3, help="Số file tối đa gửi trong 1 đoạn chat")
    parser.add_argument("--quiet", action="store_true", help="Chạy chế độ yên lặng, không hiển thị thanh tiến trình")

    args = parser.parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.filter_only:
        all_path = out_dir / f"{out_dir.name}_all.json"
        if not all_path.exists():
            all_path = out_dir / f"{out_dir.name}_master.json"
        if not all_path.exists():
            print(f"[-] Lỗi: Không tìm thấy file dữ liệu cũ tại {out_dir}")
            return

        raw_data = json.loads(all_path.read_text(encoding="utf-8"))
        filtered = [item for item in raw_data if item.get("so_lan_xuat_hien", 1) >= args.min_count]
        for idx, item in enumerate(filtered, start=1):
            item["id"] = f"hv_{idx:04d}"

        blocks = [HanVietBlock(**item) for item in filtered]
        packager = HanVietPackager(args.prompt)
        packager.package(blocks, out_dir, chunk_size=args.chunk_size)
        print(f"[+] Đã lọc xong: Giữ lại {len(blocks)}/{len(raw_data)} mục với số lần xuất hiện >= {args.min_count}.")
        return

    if not args.upload_only:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"[-] Lỗi: Không tìm thấy file đầu vào '{args.input}'!")
            return

        print("=" * 68)
        print("      🏮 BỘ QUÉT TỪ NGỮ HÁN VIỆT & CỤM TỪ BẤT THƯỜNG")
        print("=" * 68)
        print(f"[*] File nguồn          : {input_path}")
        print(f"[*] Thư mục đích        : {out_dir}")
        print(f"[*] Từ điển tiếng Việt  : {args.words_file}")
        print(f"[*] Danh mục Markers    : {args.markers_file}")
        print(f"[*] Thư mục Bộ lọc      : {args.filters_dir}")
        print(f"[*] Ngưỡng xuất hiện min: {args.min_count}")

        text = input_path.read_text(encoding="utf-8")
        scanner = HanVietScanner(
            words_path=args.words_file,
            markers_path=args.markers_file,
            char_dict_path=args.char_dict,
            common_dict_path=args.common_dict,
            hanviet_dict_path=args.hanviet_dict,
            filters_dir=args.filters_dir
        )
        print(f"[*] Đã nạp {len(scanner.known_keys):,} từ đã biết từ các từ điển để loại trừ.")
        print("[*] Đang phân tích văn bản và nhận diện từ bất thường...")
        all_blocks = scanner.scan_text(text, show_progress=not args.quiet)
        print(f"[+] Tìm thấy tổng cộng {len(all_blocks):,} từ/cụm từ bất thường.")

        # Lưu file all_json
        all_file = out_dir / f"{out_dir.name}_all.json"
        all_file.write_text(json.dumps([b.to_output_dict() for b in all_blocks], ensure_ascii=False, indent=2), encoding="utf-8")

        # Lọc min_count
        filtered_blocks = [b for b in all_blocks if b.so_lan_xuat_hien >= args.min_count]
        for idx, b in enumerate(filtered_blocks, start=1):
            b.id = f"hv_{idx:04d}"

        packager = HanVietPackager(args.prompt)
        packager.package(filtered_blocks, out_dir, chunk_size=args.chunk_size)
        print(f"[+] Đã đóng gói {len(filtered_blocks):,} mục vào '{out_dir}' thành công.")

    if args.upload_gemini or args.upload_only:
        print("\n=======================================================")
        print("[*] BẮT ĐẦU QUY TRÌNH GỬI CÁC FILE HÁN VIỆT LÊN GEMINI...")
        try:
            try:
                from .upload_to_gemini import run_upload_workflow
            except ImportError:
                from src.scanner.upload_to_gemini import run_upload_workflow
        except Exception as e:
            print(f"\n[-] Không thể khởi động tiến trình gửi Gemini: {e}")
            print("👉 Vui lòng kích hoạt môi trường ảo (venv): .\\venv\\Scripts\\activate")
            print("   Hoặc cài đặt playwright: pip install playwright && playwright install chromium\n")
            return

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
