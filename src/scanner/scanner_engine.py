from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
import json
from .resource_loader import ResourceLoader
from .boundary_trimmer import BoundaryTrimmer
from .candidate_extractor import CandidateExtractor
from .context_expander import ContextExpander

@dataclass
class CharacterBlock:
    id: str
    source: str
    target: str
    context: str
    yeu_to_nhan_biet: str
    so_lan_xuat_hien: int = 1
    is_character: bool = True
    # internal fields used during scan and ranking
    dong_xuat_hien: int = 0
    confidence: float = 0.0
    cac_dong_xuat_hien: list[int] = field(default_factory=list)
    bien_the: list[str] = field(default_factory=list)

    def to_output_dict(self):
        d = {
            "id": self.id,
            "is_character": self.is_character,
            "source": self.source,
            "target": self.target,
            "context": self.context,
            "yeu_to_nhan_biet": self.yeu_to_nhan_biet,
            "so_lan_xuat_hien": self.so_lan_xuat_hien
        }
        if self.bien_the:
            d["bien_the"] = self.bien_the
        return d

    def to_dict(self):
        return self.to_output_dict()

import gc

import sys
import time
from typing import Callable, Optional

def count_file_lines(filepath: Path) -> int:
    """Đếm nhanh tổng số dòng trong file bằng đọc khối nhị phân."""
    filepath = Path(filepath)
    if not filepath.exists():
        return 1
    total = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            total += chunk.count(b"\n")
    return max(1, total)

try:
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn, TextColumn,
        TimeElapsedColumn, TimeRemainingColumn, TaskProgressColumn
    )
    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False

class ProgressPrinter:
    """Quản lý hiển thị tiến trình trực quan bằng Rich hoặc fallback console."""
    def __init__(self, total_lines: int, label: str = "nhân vật", update_interval: float = 0.3):
        self.total_lines = max(1, total_lines)
        self.label = label
        self.update_interval = update_interval
        self.start_time = time.time()
        self.last_update = 0.0
        self.is_tty = sys.stdout.isatty()
        self.last_milestone = -1
        self.bar_width = 14

        self.rich_progress = None
        self.task_id = None
        if HAVE_RICH and self.is_tty:
            try:
                self.rich_progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(bar_width=25),
                    TaskProgressColumn(),
                    TextColumn("• [yellow]{task.fields[found]:,} {task.fields[label]}[/yellow]"),
                    "•",
                    TimeElapsedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    transient=False
                )
                self.rich_progress.start()
                self.task_id = self.rich_progress.add_task(
                    "Đang quét",
                    total=self.total_lines,
                    found=0,
                    label=self.label
                )
            except Exception:
                self.rich_progress = None

    def update(self, current_line: int, found_count: int, force: bool = False):
        if self.rich_progress and self.task_id is not None:
            self.rich_progress.update(
                self.task_id,
                completed=min(current_line, self.total_lines),
                found=found_count,
                description=f"Đang quét [{min(current_line, self.total_lines):,}/{self.total_lines:,}]"
            )
            return

        now = time.time()
        current_line = min(current_line, self.total_lines)
        if not force and (now - self.last_update < self.update_interval) and (current_line < self.total_lines):
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
            msg = f"[*] Quét: [{bar}] {percent:5.1f}% | {int(speed):,} d/s | Còn {eta_str} | Tìm thấy: {found_count:,} {self.label}"
            sys.stdout.write(f"\r{msg:<95}")
            sys.stdout.flush()
        else:
            milestone = int(percent // 10) * 10
            if milestone > self.last_milestone and milestone < 100:
                self.last_milestone = milestone
                print(
                    f"[*] Tiến độ: {percent:5.1f}% ({current_line:,}/{self.total_lines:,} dòng) | {int(speed):,} dòng/s | Tìm thấy: {found_count:,} {self.label}",
                    flush=True
                )

    def finish(self, found_count: int):
        elapsed = max(0.001, time.time() - self.start_time)
        avg_speed = int(self.total_lines / elapsed)
        if self.rich_progress and self.task_id is not None:
            try:
                self.rich_progress.update(
                    self.task_id,
                    completed=self.total_lines,
                    found=found_count,
                    description="[bold green]✓ Hoàn tất quét"
                )
                self.rich_progress.stop()
            except Exception:
                pass
            print(f"[+] Hoàn tất quét: {self.total_lines:,} dòng ({avg_speed:,} d/s) | Tìm thấy: {found_count:,} {self.label}\n")
            return

        if self.is_tty:
            msg = f"[+] Quét xong: 100% ({self.total_lines:,} dòng) trong {elapsed:.1f}s ({avg_speed:,} d/s) | {found_count:,} {self.label}"
            sys.stdout.write(f"\r{msg:<95}\n")
            sys.stdout.flush()
        else:
            print(
                f"[+] Hoàn tất quét {self.total_lines:,} dòng trong {elapsed:.1f}s ({avg_speed:,} dòng/s) | Tìm thấy: {found_count:,} {self.label}",
                flush=True
            )

class ScannerEngine:
    HUMAN_ACTION_VERBS = {
        "nói", "hỏi", "cười", "quát", "thở dài", "đáp", "gật đầu", "lắc đầu",
        "ôm", "nhìn", "bước", "đi", "nghĩ", "thầm nghĩ", "lẩm bẩm", "hét", "kêu"
    }

    ACTION_CLEANUP_WORDS = {
        # Hành động, cử chỉ, chuyển động
        "khiêu", "dùng", "lấy", "cầm", "đưa", "mang", "trêu", "nhìn", "thấy", "nghe",
        "biết", "nói", "cười", "hỏi", "bước", "đi", "ngồi", "đứng", "chạy", "nhảy",
        "ngã", "ôm", "hôn", "đánh", "giết", "bóp", "sờ", "kéo", "buông", "vỗ",
        "mắng", "quát", "hét", "kêu", "đáp", "thở", "nghĩ", "lẩm", "bẩm", "gật", "lắc",
        "chạm", "chỉ", "hiểu", "xem", "uống", "ăn", "nuốt", "rót", "mở", "đóng",
        "tiến", "lùi", "quay", "xoay", "cúi", "ngẩng", "nhíu", "nhướng", "trừng",
        "liếc", "nhòm", "dòm", "la", "nhắc", "than",
        # Hư từ, trạng từ, danh từ dính đuôi phổ biến trong convert
        "lời", "tiếng", "lúc", "khi", "mau", "nháy", "phủi", "dọa", "nụ", "eo",
        "buồn", "mẹ", "bố", "ba", "cha", "con", "a", "bỉ", "điềm", "tồn"
    }

    def __init__(self, loader: Optional[ResourceLoader] = None, skip_known: bool = True):
        self.loader = loader
        self.skip_known = skip_known
        stopwords = self.loader.trailing_stopwords if self.loader else set()
        self.trimmer = BoundaryTrimmer(stopwords)
        self.extractor = CandidateExtractor(self.loader, self.trimmer, skip_known=skip_known) if self.loader else None
        self.expander = ContextExpander()

    def _is_action_verb_or_noise(self, tail_words: list[str]) -> bool:
        if not tail_words:
            return False
        tail_words_low = [w.lower() for w in tail_words]
        tail_str = " ".join(tail_words_low)
        # Nếu có từ thuộc danh sách từ được bảo vệ trong tên người thì không coi là động từ/từ rác
        if any(w in BoundaryTrimmer.PROTECTED_NAME_WORDS for w in tail_words_low):
            return False
        if tail_str in self.HUMAN_ACTION_VERBS:
            return True
        if any(w in self.ACTION_CLEANUP_WORDS for w in tail_words_low):
            return True
        trailing = self.trimmer.trailing_stopwords if hasattr(self, 'trimmer') and self.trimmer else BoundaryTrimmer.DEFAULT_TRAILING
        if any(w in trailing for w in tail_words_low):
            return True
        return False

    def _starts_with_surname(self, text: str) -> bool:
        words = text.strip().split()
        if not words:
            return False
        if hasattr(self, 'trimmer') and self.trimmer:
            if self.trimmer.starts_with_surname(words):
                return True
        if hasattr(self, 'loader') and self.loader:
            words_low = [w.lower() for w in words]
            if len(words_low) >= 2 and f"{words_low[0]} {words_low[1]}" in self.loader.compound_surnames:
                return True
            if words_low[0] in self.loader.single_surnames:
                return True
        words_low = [w.lower() for w in words]
        if len(words_low) >= 2 and f"{words_low[0]} {words_low[1]}" in BoundaryTrimmer.FALLBACK_SURNAMES:
            return True
        if words_low[0] in BoundaryTrimmer.FALLBACK_SURNAMES:
            return True
        return False

    def _starts_with_compound_surname(self, text: str) -> bool:
        words = text.strip().split()
        if len(words) < 2:
            return False
        words_low = [w.lower() for w in words]
        pair = f"{words_low[0]} {words_low[1]}"
        if hasattr(self, 'loader') and self.loader and pair in self.loader.compound_surnames:
            return True
        if pair in BoundaryTrimmer.FALLBACK_SURNAMES:
            return True
        return False

    def _is_negative(self, text: str, skip_known: bool = False) -> bool:
        if self.extractor and hasattr(self.extractor, "_is_negative"):
            return self.extractor._is_negative(text, skip_known=skip_known)
        return False

    @staticmethod
    def _merge_block_counts_and_lines(target_block: CharacterBlock, donor_block: CharacterBlock):
        target_block.so_lan_xuat_hien += donor_block.so_lan_xuat_hien
        lines = set(target_block.cac_dong_xuat_hien)
        if not lines and target_block.dong_xuat_hien:
            lines.add(target_block.dong_xuat_hien)
        for l in donor_block.cac_dong_xuat_hien:
            lines.add(l)
        if donor_block.dong_xuat_hien:
            lines.add(donor_block.dong_xuat_hien)
        target_block.cac_dong_xuat_hien = sorted(list(lines))
        if target_block.cac_dong_xuat_hien:
            target_block.dong_xuat_hien = target_block.cac_dong_xuat_hien[0]
        if not target_block.context and donor_block.context:
            target_block.context = donor_block.context

    @staticmethod
    def _merge_variant(target_block: CharacterBlock, variant_name: str):
        var_clean = variant_name.strip()
        if var_clean and var_clean.lower() != target_block.target.lower() and not any(v.lower() == var_clean.lower() for v in target_block.bien_the):
            target_block.bien_the.append(var_clean)

    @staticmethod
    def _score_block(confidence: float, context: str, line_idx: int) -> tuple:
        ctx_low = context.lower()
        has_dialogue = '"' in context or '“' in context or '”' in context or ':' in context or '：' in context
        has_action = any(v in ctx_low for v in ScannerEngine.HUMAN_ACTION_VERBS)
        has_profile_cue = any(kw in ctx_low for kw in ("tuổi", "thê tử", "mẫu thân", "bảo mẫu", "tiểu di", "tỷ tỷ", "bang chủ", "tỉnh trưởng"))
        action_score = (2 if has_dialogue else 0) + (2 if has_action else 0) + (1 if has_profile_cue else 0)
        tier = 2 if confidence >= 0.90 else (1 if confidence >= 0.80 else 0)
        return (tier, action_score, confidence, len(context), -line_idx)

    def scan_file_stream(
        self,
        filepath: Path,
        deduplicate: bool = True,
        show_progress: bool = True,
        skip_known: Optional[bool] = None
    ):
        """
        Quét file dạng generator kèm tiến trình % trực quan:
        Mỗi khi gặp ứng viên (hoặc nhân vật mới nếu deduplicate=True), yield ngay CharacterBlock.
        """
        filepath = Path(filepath)
        effective_skip = self.skip_known if skip_known is None else skip_known
        total_lines = count_file_lines(filepath)
        counter = 1
        seen_names: set[str] = set()
        label = "nhân vật" if deduplicate else "ứng viên"
        progress = ProgressPrinter(total_lines, label=label) if show_progress else None

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                if clean_line:
                    candidates = self.extractor.extract_candidates(line, skip_known=effective_skip)
                    for cand in candidates:
                        if effective_skip:
                            if (cand.raw.lower().strip() in self.loader.known_characters or 
                                cand.name.lower().strip() in self.loader.known_characters):
                                continue
                        if self._is_negative(cand.name, skip_known=effective_skip):
                            continue

                        name_key = cand.name.lower().strip()
                        if deduplicate:
                            if name_key in seen_names:
                                continue
                            seen_names.add(name_key)

                        ctx = self.expander.expand_context(clean_line, cand.start, cand.end)
                        block = CharacterBlock(
                            id=f"ch_{counter:04d}",
                            source=cand.raw,
                            target=cand.name,
                            context=ctx,
                            yeu_to_nhan_biet=cand.reason,
                            so_lan_xuat_hien=1,
                            dong_xuat_hien=line_idx,
                            confidence=cand.confidence,
                            cac_dong_xuat_hien=[line_idx]
                        )
                        counter += 1
                        yield block

                if progress:
                    found_count = len(seen_names) if deduplicate else (counter - 1)
                    progress.update(line_idx, found_count)

                if line_idx % 20000 == 0:
                    gc.collect()

        if progress:
            found_count = len(seen_names) if deduplicate else (counter - 1)
            progress.finish(found_count)

    def scan_file(
        self,
        filepath: Path,
        deduplicate: bool = True,
        show_progress: bool = True,
        skip_known: Optional[bool] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
        realtime_all_path: Optional[Path] = None,
        realtime_interval: float = 1.0
    ) -> list[CharacterBlock]:
        """
        Quét văn bản với cơ chế Khử trùng lặp trực tiếp (Online Deduplication),
        hiển thị thanh tiến trình % trực quan thời gian thực, và hỗ trợ lưu
        kết quả realtime vào scanner_all.json liên tục trong quá trình quét.
        """
        effective_skip = self.skip_known if skip_known is None else skip_known
        if not deduplicate:
            return list(self.scan_file_stream(filepath, show_progress=show_progress, skip_known=effective_skip))

        total_lines = count_file_lines(filepath)
        tracked: dict[str, CharacterBlock] = {}
        best_scores: dict[str, tuple] = {}
        progress = ProgressPrinter(total_lines, label="nhân vật") if show_progress else None

        last_realtime_save = time.time()
        is_dirty = False

        def _save_realtime(target_path: Path):
            nonlocal is_dirty, last_realtime_save
            if not target_path or not is_dirty:
                return
            target_path = Path(target_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = target_path.with_suffix(target_path.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f_out:
                f_out.write("[\n")
                first = True
                for b in tracked.values():
                    if self._is_negative(b.target, skip_known=effective_skip):
                        continue
                    if not first:
                        f_out.write(",\n")
                    else:
                        first = False
                    item_json = json.dumps(b.to_output_dict(), ensure_ascii=False, indent=2)
                    indented = "  " + item_json.replace("\n", "\n  ")
                    f_out.write(indented)
                f_out.write("\n]\n")
            tmp_path.replace(target_path)
            is_dirty = False
            last_realtime_save = time.time()

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f, start=1):
                    clean_line = line.strip()
                    if not clean_line:
                        if progress:
                            progress.update(line_idx, len(tracked))
                        continue

                    candidates = self.extractor.extract_candidates(line, skip_known=effective_skip)
                    for cand in candidates:
                        if effective_skip:
                            if (cand.raw.lower().strip() in self.loader.known_characters or 
                                cand.name.lower().strip() in self.loader.known_characters):
                                continue
                        if self._is_negative(cand.name, skip_known=effective_skip):
                            continue
                        name_key = cand.name.lower().strip()

                        if name_key in tracked:
                            existing = tracked[name_key]
                            existing.so_lan_xuat_hien += 1
                            if len(existing.cac_dong_xuat_hien) < 100 and line_idx not in existing.cac_dong_xuat_hien:
                                existing.cac_dong_xuat_hien.append(line_idx)
                            is_dirty = True
                            # Chỉ mở rộng ngữ cảnh khi độ tin cậy có thể vượt qua điểm số tốt nhất hiện có
                            cand_tier = 2 if cand.confidence >= 0.90 else (1 if cand.confidence >= 0.80 else 0)
                            if cand_tier >= best_scores[name_key][0]:
                                ctx = self.expander.expand_context(clean_line, cand.start, cand.end)
                                score = self._score_block(cand.confidence, ctx, line_idx)
                                if score > best_scores[name_key]:
                                    existing.source = cand.raw
                                    existing.target = cand.name
                                    existing.context = ctx
                                    existing.yeu_to_nhan_biet = cand.reason
                                    existing.confidence = cand.confidence
                                    best_scores[name_key] = score
                        else:
                            ctx = self.expander.expand_context(clean_line, cand.start, cand.end)
                            score = self._score_block(cand.confidence, ctx, line_idx)
                            block = CharacterBlock(
                                id=f"ch_{len(tracked) + 1:04d}",
                                source=cand.raw,
                                target=cand.name,
                                context=ctx,
                                yeu_to_nhan_biet=cand.reason,
                                so_lan_xuat_hien=1,
                                dong_xuat_hien=line_idx,
                                confidence=cand.confidence,
                                cac_dong_xuat_hien=[line_idx]
                            )
                            tracked[name_key] = block
                            best_scores[name_key] = score
                            is_dirty = True

                    if progress:
                        progress.update(line_idx, len(tracked))

                    if progress_callback:
                        progress_callback(line_idx, total_lines, len(tracked))

                    # Flush dữ liệu realtime theo khoảng thời gian
                    if realtime_all_path and is_dirty and (time.time() - last_realtime_save >= realtime_interval):
                        _save_realtime(realtime_all_path)

                    if line_idx % 20000 == 0:
                        gc.collect()
        finally:
            # Luôn đảm bảo dữ liệu cuối cùng được ghi đĩa dù bị ngắt tiến trình
            if realtime_all_path:
                _save_realtime(realtime_all_path)

        if progress:
            progress.finish(len(tracked))

        deduped = self.cluster_aliases(list(tracked.values()))
        deduped = [b for b in deduped if not self._is_negative(b.target, skip_known=effective_skip)]
        for idx, b in enumerate(deduped, start=1):
            b.id = f"ch_{idx:04d}"

        if realtime_all_path:
            realtime_all_path = Path(realtime_all_path)
            realtime_all_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = realtime_all_path.with_suffix(realtime_all_path.suffix + ".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f_out:
                f_out.write("[\n")
                first = True
                for b in deduped:
                    if not first:
                        f_out.write(",\n")
                    else:
                        first = False
                    item_json = json.dumps(b.to_output_dict(), ensure_ascii=False, indent=2)
                    indented = "  " + item_json.replace("\n", "\n  ")
                    f_out.write(indented)
                f_out.write("\n]\n")
            tmp_path.replace(realtime_all_path)

        return deduped

    def cluster_aliases(self, blocks: list[CharacterBlock]) -> list[CharacterBlock]:
        if not blocks:
            return []

        # Chuẩn hóa target về TitleCase nếu đang viết thường hoàn toàn
        for b in blocks:
            words = b.target.strip().split()
            if words and all(w.islower() for w in words):
                b.target = " ".join(w.capitalize() for w in words)

        alias_prefix_words = {"tiểu", "lão", "đại"}
        alias_suffix_words = {
            "thiếu gia", "công tử", "tiểu thư", "tổng", "lão sư",
            "thúc", "bá", "di", "ca", "muội", "tỷ", "đệ"
        }

        full_name_blocks: dict[str, CharacterBlock] = {}
        alias_blocks: list[CharacterBlock] = []

        for b in blocks:
            target_clean = b.target.strip()
            words = target_clean.split()
            target_low = target_clean.lower()

            is_alias = False
            if len(words) == 2 and words[0].lower() in alias_prefix_words:
                is_alias = True
            elif any(target_low.endswith(" " + s) for s in alias_suffix_words):
                is_alias = True

            if is_alias:
                alias_blocks.append(b)
            else:
                if target_low in full_name_blocks:
                    existing = full_name_blocks[target_low]
                    self._merge_block_counts_and_lines(existing, b)
                    for bt in b.bien_the:
                        self._merge_variant(existing, bt)
                    if not existing.target[0].isupper() and b.target[0].isupper():
                        existing.target = b.target
                else:
                    full_name_blocks[target_low] = b

        # 1. Action verb cleanup:
        # Nếu một khối tên có đuôi là động từ hành động/từ rác dính kèm (vd "Từ Thanh khiêu", "Từ Thanh dùng")
        # và khối tên gốc ("Từ Thanh") đã tồn tại, gộp khối dính động từ vào tên gốc.
        to_remove = set()
        for target_low, b in list(full_name_blocks.items()):
            if target_low in to_remove:
                continue
            words_b = b.target.strip().split()
            if len(words_b) < 3:
                continue
            for prefix_len in range(len(words_b) - 1, 1, -1):
                prefix_words = words_b[:prefix_len]
                prefix_key = " ".join(prefix_words).lower()
                if prefix_key in full_name_blocks and prefix_key not in to_remove:
                    base_block = full_name_blocks[prefix_key]
                    if base_block.so_lan_xuat_hien >= b.so_lan_xuat_hien:
                        tail = [w.lower() for w in words_b[prefix_len:]]
                        if self._is_action_verb_or_noise(tail):
                            self._merge_block_counts_and_lines(base_block, b)
                            for bt in b.bien_the:
                                self._merge_variant(base_block, bt)
                            to_remove.add(target_low)
                            break

        for k in to_remove:
            del full_name_blocks[k]

        # 2. Super-string Consolidation:
        # Khi tên ngắn hơn (vd "Đường Thiền" - 2 từ) và tên dài đầy đủ hợp lệ (vd "Đường Thiền Y" - 3 từ)
        # cùng tồn tại (cùng họ và tiền tố từ đầu):
        # Chọn tên dài đầy đủ làm khối mục tiêu chính, gộp số lần xuất hiện/dòng xuất hiện từ tên ngắn,
        # và thêm tên ngắn vào danh sách biến thể (bien_the).
        to_remove = set()
        sorted_keys = sorted(
            full_name_blocks.keys(),
            key=lambda k: len(full_name_blocks[k].target.split())
        )

        for short_key in sorted_keys:
            if short_key in to_remove:
                continue
            b_short = full_name_blocks[short_key]
            words_short = b_short.target.strip().split()
            words_short_low = [w.lower() for w in words_short]

            is_compound = self._starts_with_compound_surname(b_short.target)
            max_short_len = 3 if is_compound else 2
            if len(words_short) < 2 or len(words_short) > max_short_len:
                continue
            if not self._starts_with_surname(b_short.target):
                continue

            candidates = []
            for other_key, b_other in full_name_blocks.items():
                if other_key == short_key or other_key in to_remove:
                    continue
                words_other = b_other.target.strip().split()
                if len(words_other) <= len(words_short) or len(words_other) > 4:
                    continue
                words_other_low = [w.lower() for w in words_other]
                if words_other_low[:len(words_short)] == words_short_low:
                    tail = words_other_low[len(words_short):]
                    if not self._is_action_verb_or_noise(tail):
                        candidates.append(b_other)

            # Kiểm tra xung đột: nếu có các ứng viên cùng độ dài nhưng khác tên chính cuối cùng
            # (ví dụ: 'Tần Khả Cầm' và 'Tần Khả Phi' cùng là ứng viên của 'Tần Khả')
            # thì tuyệt đối KHÔNG gộp để bảo vệ luật bất biến tên chính.
            has_conflict = False
            by_length: dict[int, str] = {}
            for c in candidates:
                words_c = c.target.strip().split()
                l = len(words_c)
                given = words_c[-1].lower()
                if l in by_length and by_length[l] != given:
                    has_conflict = True
                    break
                by_length[l] = given

            if has_conflict:
                continue

            if candidates:
                best_long = max(candidates, key=lambda c: (c.so_lan_xuat_hien, -c.dong_xuat_hien))
                self._merge_block_counts_and_lines(best_long, b_short)
                self._merge_variant(best_long, b_short.target)
                for bt in b_short.bien_the:
                    self._merge_variant(best_long, bt)
                to_remove.add(short_key)

        for k in to_remove:
            del full_name_blocks[k]

        # 2b. Prefix Stripping: Gộp các khối dính 1 từ rác ở đầu vào tên chuẩn đã có
        # Ví dụ: "Hoa Mã Lan" (3 từ) khi đã có "Mã Lan" (2 từ, tần suất cao)
        to_remove = set()
        for target_low, b in list(full_name_blocks.items()):
            if target_low in to_remove:
                continue
            words_b = b.target.strip().split()
            if len(words_b) >= 3:
                # Không strip nếu 2 từ đầu là họ kép (ví dụ "Hoàng Phủ Thiền")
                if self._starts_with_compound_surname(b.target):
                    continue
                tail_candidate = " ".join(words_b[1:]).lower()
                if tail_candidate in full_name_blocks and tail_candidate not in to_remove:
                    base_block = full_name_blocks[tail_candidate]
                    if base_block.so_lan_xuat_hien >= b.so_lan_xuat_hien:
                        self._merge_block_counts_and_lines(base_block, b)
                        for bt in b.bien_the:
                            self._merge_variant(base_block, bt)
                        self._merge_variant(base_block, b.target)
                        to_remove.add(target_low)

        for k in to_remove:
            del full_name_blocks[k]

        # 3. Alias Clustering:
        merged_aliases = set()
        for ab in alias_blocks:
            alias_name = ab.target.strip()
            alias_words = alias_name.split()
            matched_full: Optional[CharacterBlock] = None

            # Case 1: "Tiểu X" -> tìm người có tên là X (hoặc biến thể có tên là X)
            if len(alias_words) == 2 and alias_words[0].lower() in alias_prefix_words:
                given_name = alias_words[1].lower()
                candidates = [
                    fb for fb in full_name_blocks.values()
                    if fb.target.split()[-1].lower() == given_name
                    or any(bt.split()[-1].lower() == given_name for bt in fb.bien_the)
                ]
                if candidates:
                    matched_full = max(candidates, key=lambda c: (c.so_lan_xuat_hien, -c.dong_xuat_hien))

            # Case 2: "Họ + chức vị/xưng hô" -> tìm người có họ tương ứng
            elif any(alias_name.lower().endswith(" " + s) for s in alias_suffix_words):
                for s in sorted(alias_suffix_words, key=len, reverse=True):
                    if alias_name.lower().endswith(" " + s):
                        surname_part = alias_name[:-len(s)].strip().lower()
                        candidates = [
                            fb for fb in full_name_blocks.values()
                            if fb.target.split()[0].lower() == surname_part
                        ]
                        if len(candidates) == 1:
                            matched_full = candidates[0]
                        elif candidates:
                            matched_full = max(candidates, key=lambda c: (c.so_lan_xuat_hien, -c.dong_xuat_hien))
                        break

            if matched_full:
                self._merge_block_counts_and_lines(matched_full, ab)
                self._merge_variant(matched_full, alias_name)
                for bt in ab.bien_the:
                    self._merge_variant(matched_full, bt)
                merged_aliases.add(ab.id)

        # Giữ lại các alias không ghép được vào nhân vật nào
        final_blocks = list(full_name_blocks.values())
        for ab in alias_blocks:
            if ab.id not in merged_aliases:
                final_blocks.append(ab)

        # Sắp xếp theo dòng xuất hiện đầu tiên
        final_blocks.sort(key=lambda b: b.dong_xuat_hien)

        # Đánh chỉ mục id tuần tự
        for idx, b in enumerate(final_blocks, start=1):
            b.id = f"ch_{idx:04d}"

        return final_blocks

    def deduplicate_blocks(self, blocks: list[CharacterBlock]) -> list[CharacterBlock]:
        grouped: dict[str, list[CharacterBlock]] = defaultdict(list)
        for b in blocks:
            grouped[b.target.lower().strip()].append(b)

        deduped: list[CharacterBlock] = []
        for name_key, group in grouped.items():
            all_lines = sorted(list(set(line for b in group for line in (b.cac_dong_xuat_hien or [b.dong_xuat_hien]))))
            total_count = sum(b.so_lan_xuat_hien for b in group)

            best_block = max(group, key=lambda b: self._score_block(b.confidence, b.context, b.dong_xuat_hien))
            best_block.so_lan_xuat_hien = total_count
            best_block.cac_dong_xuat_hien = all_lines
            best_block.dong_xuat_hien = all_lines[0] if all_lines else best_block.dong_xuat_hien
            for b in group:
                for bt in b.bien_the:
                    ScannerEngine._merge_variant(best_block, bt)
            deduped.append(best_block)

        return self.cluster_aliases(deduped)
