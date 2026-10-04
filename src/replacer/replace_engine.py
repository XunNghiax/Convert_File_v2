import json
import re
import time
from pathlib import Path
from typing import Optional, Union, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from collections import Counter
import concurrent.futures
import shutil
import sys

try:
    from ..utils.chunk_splitter import split_file_line_ranges
except (ImportError, ValueError):
    from src.utils.chunk_splitter import split_file_line_ranges

PARALLEL_MIN_LINES = 500


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

def count_file_lines(filepath: Union[str, Path]) -> int:
    """Đếm nhanh tổng số dòng trong file bằng đọc khối nhị phân 1MB."""
    filepath = Path(filepath)
    if not filepath.exists():
        return 0
    total = 0
    last_byte = b""
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            total += chunk.count(b"\n")
            if chunk:
                last_byte = chunk[-1:]
    if last_byte and last_byte != b"\n":
        total += 1
    return total

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
    """Hiển thị thanh tiến trình trực quan bằng Rich hoặc fallback console."""
    def __init__(self, total_lines: int, bar_width: int = 25):
        self.total_lines = max(1, total_lines)
        self.bar_width = bar_width
        self.start_time = time.time()
        self.last_update = 0.0
        self.last_milestone = -1
        self.is_tty = sys.stdout.isatty()

        self.rich_progress = None
        self.task_id = None
        try:
            from rich.progress import (
                Progress, SpinnerColumn, BarColumn, TextColumn,
                TimeElapsedColumn, TimeRemainingColumn, TaskProgressColumn
            )
            if self.is_tty:
                self.rich_progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(bar_width=25),
                    TaskProgressColumn(),
                    TextColumn("• [green]{task.fields[replaced]:,} lượt thay[/green]"),
                    "•",
                    TimeElapsedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    transient=False
                )
                self.rich_progress.start()
                self.task_id = self.rich_progress.add_task(
                    "Đang thay thế",
                    total=self.total_lines,
                    replaced=0
                )
        except Exception:
            self.rich_progress = None

    def update(self, current_line: int, replaced_count: int):
        if self.rich_progress and self.task_id is not None:
            self.rich_progress.update(
                self.task_id,
                completed=min(current_line, self.total_lines),
                replaced=replaced_count,
                description=f"Thay thế [{min(current_line, self.total_lines):,}/{self.total_lines:,}]"
            )
            return

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

    def close(self):
        """Dọn dẹp an toàn tài nguyên hiển thị của Rich progress."""
        if self.rich_progress:
            try:
                self.rich_progress.stop()
            except Exception:
                pass
            self.rich_progress = None

    def finish(self, replaced_count: int):
        elapsed = max(0.001, time.time() - self.start_time)
        avg_speed = int(self.total_lines / elapsed)
        if self.rich_progress and self.task_id is not None:
            try:
                self.rich_progress.update(
                    self.task_id,
                    completed=self.total_lines,
                    replaced=replaced_count,
                    description="[bold green]✓ Hoàn tất thay thế"
                )
                self.rich_progress.stop()
            except Exception:
                pass
            self.rich_progress = None
            print(f"[+] Hoàn tất thay thế: {self.total_lines:,} dòng ({avg_speed:,} d/s) | {replaced_count:,} lượt thay thế\n")
            return

        if self.is_tty:
            msg = f"[+] Hoàn tất thay thế: 100% ({self.total_lines:,} dòng) trong {elapsed:.1f}s ({avg_speed:,} d/s) | {replaced_count:,} lượt thay thế"
            sys.stdout.write(f"\r{msg:<95}\n")
            sys.stdout.flush()
        else:
            print(
                f"[+] Hoàn tất thay thế {self.total_lines:,} dòng trong {elapsed:.1f}s ({avg_speed:,} dòng/s) | Tổng cộng: {replaced_count:,} lượt thay thế",
                flush=True
            )

def _replace_chunk_worker(
    input_path: Union[str, Path],
    out_part_path: Union[str, Path],
    start_line: int,
    end_line: int,
    pattern_or_dict: Any,
    dict_map_or_custom: Any = None,
    track_stats: bool = True
) -> Counter:
    """
    Worker độc lập ở module-level phục vụ xử lý song song đa tiến trình (ProcessPoolExecutor).
    - Đọc từ start_line đến end_line (1-indexed).
    - Thực hiện thay thế bằng regex pattern (single-pass).
    - Ghi trực tiếp ra file out_part_path với buffer tối ưu.
    - Trả về Counter thống kê số lượt thay thế cục bộ của chunk.
    """
    input_path = Path(input_path)
    out_part_path = Path(out_part_path)

    if isinstance(pattern_or_dict, dict):
        merged_map = dict(pattern_or_dict)
        if isinstance(dict_map_or_custom, dict):
            merged_map.update(dict_map_or_custom)
        temp_engine = ReplaceEngine(custom_mapping=merged_map)
        pattern = temp_engine.pattern
        dict_map = temp_engine.dict_map
    else:
        pattern = pattern_or_dict
        if isinstance(dict_map_or_custom, bool):
            track_stats = dict_map_or_custom
            dict_map = {}
        else:
            dict_map = dict_map_or_custom or {}

    local_stats = Counter()
    BUFFER_LINES = 1000
    line_buffer = []

    def _repl(m: re.Match) -> str:
        matched_str = m.group(0)
        canonical_key = matched_str.lower()
        target = dict_map.get(canonical_key, matched_str)
        if matched_str != target:
            if track_stats:
                local_stats[canonical_key] += 1
            return target
        return matched_str

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f_in, \
         open(out_part_path, "w", encoding="utf-8", buffering=64 * 1024) as f_out:
        for line_idx, line in enumerate(f_in, start=1):
            if line_idx < start_line:
                continue
            if line_idx > end_line:
                break

            if pattern and line:
                new_line = pattern.sub(_repl, line)
            else:
                new_line = line
            line_buffer.append(new_line)

            if len(line_buffer) >= BUFFER_LINES:
                f_out.writelines(line_buffer)
                line_buffer.clear()

        if line_buffer:
            f_out.writelines(line_buffer)
            line_buffer.clear()

    return local_stats

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
                if isinstance(data, dict):
                    for k, v in data.items():
                        src = str(k).strip()
                        tgt = str(v).strip()
                        words = tgt.split()
                        tgt = " ".join(w[:1].upper() + w[1:] for w in words)
                        if src and tgt:
                            merged[src.lower()] = tgt
                elif isinstance(data, list):
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
        track_stats: bool = True,
        workers: int = 1
    ) -> ReplaceStats:
        """
        Thay thế file văn bản dạng streaming:
        - workers = 1: Đọc từng dòng -> Thay thế -> Ghi vào file tạm .tmp -> Atomic swap
        - workers > 1: Chia file thành các khoảng dòng, các worker xử lý song song ra các part file .part_N,
                       sau đó ghép nhị phân vào file tạm và atomic swap sang file đích.
        - Trả về thống kê chi tiết ReplaceStats (đảm bảo 100% bit-for-bit parity).
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file nguồn: {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_output_path = output_path.with_suffix(output_path.suffix + ".tmp")

        # Đếm nhanh tổng số dòng bằng đọc khối nhị phân 1MB
        total_lines = count_file_lines(input_path)

        self.stats_counter.clear()
        progress = ReplaceProgressPrinter(total_lines) if show_progress else None
        start_time = time.time()
        part_files: List[Path] = []

        ranges = split_file_line_ranges(input_path, num_chunks=workers) if workers > 1 else []
        use_parallel = (workers > 1 and len(ranges) > 1 and total_lines >= PARALLEL_MIN_LINES)

        try:
            if use_parallel:
                part_files = [
                    output_path.with_suffix(f"{output_path.suffix}.part_{idx}")
                    for idx in range(len(ranges))
                ]
                part_results = [None] * len(ranges)

                with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                    futures = {
                        executor.submit(
                            _replace_chunk_worker,
                            input_path,
                            part_files[idx],
                            start,
                            end,
                            self.pattern,
                            self.dict_map,
                            track_stats
                        ): idx
                        for idx, (start, end) in enumerate(ranges)
                    }
                    for fut in concurrent.futures.as_completed(futures):
                        idx = futures[fut]
                        part_results[idx] = fut.result()
                        if progress:
                            done_lines = sum(
                                ranges[i][1] - ranges[i][0] + 1
                                for i, res in enumerate(part_results)
                                if res is not None
                            )
                            temp_reps = sum(
                                sum(res.values())
                                for res in part_results
                                if res is not None
                            ) if track_stats else 0
                            progress.update(min(done_lines, total_lines), temp_reps)

                # Nối các file part nhị phân vào tmp_output_path
                with open(tmp_output_path, "wb") as f_out:
                    for part_path in part_files:
                        with open(part_path, "rb") as f_in:
                            shutil.copyfileobj(f_in, f_out, length=1024 * 1024)
                        try:
                            part_path.unlink()
                        except Exception:
                            pass

                # Hợp nhất stats_counter
                self.stats_counter.clear()
                if track_stats:
                    for res in part_results:
                        if res:
                            self.stats_counter.update(res)

            else:
                # Chế độ tuần tự đơn luồng (workers == 1 hoặc file nhỏ hơn ngưỡng)
                BUFFER_LINES = 1000
                line_buffer = []

                with open(input_path, "r", encoding="utf-8", errors="ignore") as f_in, \
                     open(tmp_output_path, "w", encoding="utf-8", buffering=64 * 1024) as f_out:
                    for line_idx, line in enumerate(f_in, start=1):
                        new_line = self.replace_line(line, track_stats=track_stats)
                        line_buffer.append(new_line)

                        if len(line_buffer) >= BUFFER_LINES:
                            f_out.writelines(line_buffer)
                            line_buffer.clear()
                            if progress and line_idx % 2000 == 0:
                                current_reps = sum(self.stats_counter.values()) if track_stats else 0
                                progress.update(line_idx, current_reps)

                    if line_buffer:
                        f_out.writelines(line_buffer)
                        line_buffer.clear()

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
        finally:
            if progress:
                progress.close()
            for pf in part_files:
                try:
                    if pf.exists():
                        pf.unlink()
                except Exception:
                    pass

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
