import json
import re
import time
from pathlib import Path
from typing import Optional, Union, Dict, List, Tuple
from dataclasses import dataclass, field
from collections import Counter
import sys

# Đường dẫn mặc định chuẩn của dự án
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHARACTER_DICT = DEFAULT_PROJECT_ROOT / "resources" / "dictionaries" / "character_dict.json"
DEFAULT_HANVIET_DICT = DEFAULT_PROJECT_ROOT / "resources" / "dictionaries" / "hanviet_dict.json"
DEFAULT_COMMON_DICT = DEFAULT_PROJECT_ROOT / "resources" / "dictionaries" / "common_dict.json"

DESCRIPTIVE_PREFIXES = [
    "một", "những", "các", "từng", "thật là", "vóc dáng", "thân hình",
    "dáng dấp", "chiếc", "bóng dáng", "đường nét"
]

AMBIGUOUS_DESCRIPTIVE_WORDS = {
    "bóng hình xinh đẹp",
    "hình xinh đẹp"
}

@dataclass
class ReplaceStats:
    total_lines: int = 0
    total_replacements: int = 0
    elapsed_seconds: float = 0.0
    lines_per_second: float = 0.0
    input_size: int = 0
    output_size: int = 0
    top_replacements: List[Tuple[str, str, int]] = field(default_factory=list)

class ReplaceProgressPrinter:
    """Hiển thị thanh tiến trình trực quan với độ rộng an toàn cho console."""
    def __init__(self, total_lines: int, bar_width: int = 25):
        self.total_lines = max(1, total_lines)
        self.bar_width = bar_width
        self.start_time = time.time()
        self.last_update = 0.0
        self.last_milestone = -1
        self.is_tty = sys.stdout.isatty()

    def update(self, current_line: int, replaced_count: int):
        now = time.time()
        if now - self.last_update < 0.35 and current_line < self.total_lines:
            return

        self.last_update = now
        elapsed = max(0.001, now - self.start_time)
        speed = current_line / elapsed
        percent = min(100.0, (current_line / self.total_lines) * 100)

        if self.is_tty:
            eta_sec = max(0.0, (self.total_lines - current_line) / max(1.0, speed))
            eta_str = f"{int(eta_sec)}s" if eta_sec < 60 else f"{int(eta_sec//60)}m{int(eta_sec%60)}s"
            filled = int(self.bar_width * current_line / self.total_lines)
            bar = "█" * filled + "░" * (self.bar_width - filled)
            msg = f"[*] Thay thế: [{bar}] {percent:5.1f}% | {int(speed):,} d/s | Còn {eta_str} | Đã thay: {replaced_count:,} lượt"
            sys.stdout.write(f"\r{msg:<95}")
            sys.stdout.flush()
        else:
            milestone = int(percent // 10) * 10
            if milestone > self.last_milestone and milestone < 100:
                self.last_milestone = milestone
                print(
                    f"[*] Tiến độ thay thế: {percent:5.1f}% ({current_line:,}/{self.total_lines:,} dòng) | {int(speed):,} dòng/s | Đã thay: {replaced_count:,} lượt",
                    flush=True
                )

    def finish(self, replaced_count: int):
        elapsed = max(0.001, time.time() - self.start_time)
        avg_speed = int(self.total_lines / elapsed)
        if self.is_tty:
            msg = f"[+] Hoàn tất thay thế: 100% ({self.total_lines:,} dòng) trong {elapsed:.1f}s ({avg_speed:,} d/s) | {replaced_count:,} lượt thay thế"
            sys.stdout.write(f"\r{msg:<95}\n")
            sys.stdout.flush()
        else:
            print(
                f"[+] Hoàn tất thay thế {self.total_lines:,} dòng trong {elapsed:.1f}s ({avg_speed:,} dòng/s) | Tổng cộng: {replaced_count:,} lượt thay thế",
                flush=True
            )

class ReplaceEngine:
    """
    Động cơ thay thế chuỗi hiệu năng cao:
    - Longest-Match First: Sắp xếp từ dài nhất lên đầu để tránh nuốt từ.
    - Single-Pass Regex: Quét và thay thế toàn bộ từ khóa trong đúng 1 lượt duy nhất.
    - Non-cascading: Không bao giờ bị lỗi thay thế lồng nhau / vòng lặp.
    - Streaming I/O: Xử lý theo dòng, tiết kiệm RAM tuyệt đối.
    """
    def __init__(
        self,
        char_dict_path: Optional[Union[str, Path]] = DEFAULT_CHARACTER_DICT,
        hanviet_dict_path: Optional[Union[str, Path]] = DEFAULT_HANVIET_DICT,
        common_dict_path: Optional[Union[str, Path]] = DEFAULT_COMMON_DICT,
        custom_mapping: Optional[Dict[str, str]] = None
    ):
        self.char_dict_path = Path(char_dict_path) if char_dict_path else None
        self.hanviet_dict_path = Path(hanviet_dict_path) if hanviet_dict_path else None
        self.common_dict_path = Path(common_dict_path) if common_dict_path else None
        self.dict_map: Dict[str, str] = {}
        self.sorted_keys: List[str] = []
        self.pattern: Optional[re.Pattern] = None
        self.stats_counter: Counter = Counter()

        if custom_mapping:
            self.load_custom_mapping(custom_mapping)
        else:
            self.load_dictionaries()

    def load_dictionaries(self):
        """Nạp và hợp nhất từ điển nhân vật, từ điển Hán Việt và từ điển chung."""
        merged: Dict[str, str] = {}

        # 1. Nạp từ điển chung (Ưu tiên cơ bản)
        if self.common_dict_path and self.common_dict_path.exists():
            try:
                data = json.loads(self.common_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        src = str(item.get("source", "")).strip()
                        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
                        tgt = tgt.lower()
                        if src and tgt:
                            merged[src.lower()] = tgt
                elif isinstance(data, dict):
                    for k, v in data.items():
                        src = str(k).strip()
                        tgt = str(v).strip().lower()
                        if src and tgt:
                            merged[src.lower()] = tgt
            except Exception as e:
                print(f"[!] Cảnh báo: Không thể nạp common_dict: {e}")

        # 2. Nạp từ điển Hán Việt (Ưu tiên cao hơn từ điển chung)
        if self.hanviet_dict_path and self.hanviet_dict_path.exists():
            try:
                data = json.loads(self.hanviet_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        src = str(item.get("source", "")).strip()
                        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
                        if src and tgt:
                            merged[src.lower()] = tgt
                elif isinstance(data, dict):
                    for k, v in data.items():
                        src = str(k).strip()
                        tgt = str(v).strip()
                        if src and tgt:
                            merged[src.lower()] = tgt
            except Exception as e:
                print(f"[!] Cảnh báo: Không thể nạp hanviet_dict: {e}")

        # 3. Nạp từ điển nhân vật (Ghi đè, ưu tiên cao nhất)
        if self.char_dict_path and self.char_dict_path.exists():
            try:
                data = json.loads(self.char_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        src = str(item.get("source", "")).strip()
                        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
                        # Chuẩn hóa: Tên nhân vật luôn upcase chữ cái đầu mỗi từ
                        words = tgt.split()
                        tgt = " ".join(w[:1].upper() + w[1:] for w in words)
                        if src and tgt:
                            merged[src.lower()] = tgt
            except Exception as e:
                print(f"[!] Cảnh báo: Không thể nạp character_dict: {e}")

        self._compile_from_dict(merged)

    def load_custom_mapping(self, mapping: Dict[str, str]):
        """Nạp trực tiếp mapping từ điển thủ công (dùng cho testing hoặc mở rộng)."""
        clean_map = {
            str(k).strip().lower(): str(v).strip()
            for k, v in mapping.items()
            if str(k).strip() and str(v).strip()
        }
        self._compile_from_dict(clean_map)

    def _compile_from_dict(self, mapping: Dict[str, str]):
        """Sắp xếp từ điển theo độ dài giảm dần và biên dịch Regex Pattern kèm Guard an toàn."""
        self.dict_map = mapping
        # Sắp xếp: Ưu tiên chuỗi dài nhất trước (Longest Match First)
        self.sorted_keys = sorted(
            self.dict_map.keys(),
            key=lambda x: (len(x), x),
            reverse=True
        )

        if self.sorted_keys:
            pattern_parts = []
            for k in self.sorted_keys:
                tgt = self.dict_map[k]
                guards = []

                # 1. Prefix Guard: Ngăn chặn lỗi lặp họ (ví dụ Kiếm Phi -> Long Kiếm Phi khi đã có 'Long ')
                if tgt.lower().endswith(k.lower()) and len(tgt) > len(k):
                    prefix = tgt[:-len(k)].strip()
                    if prefix:
                        guards.append(f"(?<!{re.escape(prefix)}\\s)")

                # 2. Negative Context Guard: Ngăn chặn thay thế từ miêu tả vóc dáng
                if k.lower() in AMBIGUOUS_DESCRIPTIVE_WORDS:
                    for dp in DESCRIPTIVE_PREFIXES:
                        guards.append(f"(?<!{re.escape(dp)}\\s)")

                if guards:
                    pattern_parts.append(f"(?:{''.join(guards)}{re.escape(k)})")
                else:
                    pattern_parts.append(re.escape(k))

            self.pattern = re.compile("|".join(pattern_parts), flags=re.IGNORECASE)
        else:
            self.pattern = None

    def replace_line(self, line: str, track_stats: bool = True) -> str:
        """Thay thế một dòng văn bản trong một lượt duy nhất (Single-Pass) với hỗ trợ không phân biệt hoa thường."""
        if not self.pattern or not line:
            return line

        def _repl(m: re.Match) -> str:
            matched_str = m.group(0)
            canonical_key = matched_str.lower()
            target = self.dict_map.get(canonical_key, matched_str)
            if matched_str != target:
                if track_stats:
                    self.stats_counter[canonical_key] += 1
                return target
            return matched_str

        return self.pattern.sub(_repl, line)

    def replace_file(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        show_progress: bool = True,
        track_stats: bool = True
    ) -> ReplaceStats:
        """
        Thay thế file văn bản dạng streaming:
        - Đọc từng dòng -> Thay thế -> Ghi vào file tạm .tmp
        - Sau khi xong, atomic replace sang file đích
        - Trả về thống kê chi tiết ReplaceStats
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file nguồn: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_output_path = output_path.with_suffix(output_path.suffix + ".tmp")

        # Đếm tổng số dòng
        total_lines = 0
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                total_lines += 1

        self.stats_counter.clear()
        progress = ReplaceProgressPrinter(total_lines) if show_progress else None
        start_time = time.time()
        total_replacements = 0

        try:
            with open(input_path, "r", encoding="utf-8", errors="ignore") as f_in, \
                 open(tmp_output_path, "w", encoding="utf-8") as f_out:
                for line_idx, line in enumerate(f_in, start=1):
                    new_line = self.replace_line(line, track_stats=track_stats)
                    f_out.write(new_line)

                    if progress and line_idx % 200 == 0:
                        current_reps = sum(self.stats_counter.values()) if track_stats else 0
                        progress.update(line_idx, current_reps)

            if progress:
                current_reps = sum(self.stats_counter.values()) if track_stats else 0
                progress.finish(current_reps)

            # Atomic swap
            tmp_output_path.replace(output_path)

        except Exception as e:
            if tmp_output_path.exists():
                try:
                    tmp_output_path.unlink()
                except Exception:
                    pass
            raise e

        elapsed = max(0.001, time.time() - start_time)
        total_replacements = sum(self.stats_counter.values())
        top_list = [
            (src_key, self.dict_map.get(src_key, ""), count)
            for src_key, count in self.stats_counter.most_common(20)
        ]

        return ReplaceStats(
            total_lines=total_lines,
            total_replacements=total_replacements,
            elapsed_seconds=elapsed,
            lines_per_second=total_lines / elapsed,
            input_size=input_path.stat().st_size,
            output_size=output_path.stat().st_size if output_path.exists() else 0,
            top_replacements=top_list
        )
