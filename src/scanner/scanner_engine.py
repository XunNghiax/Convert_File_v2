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

    def to_output_dict(self):
        return {
            "id": self.id,
            "is_character": self.is_character,
            "source": self.source,
            "target": self.target,
            "context": self.context,
            "yeu_to_nhan_biet": self.yeu_to_nhan_biet,
            "so_lan_xuat_hien": self.so_lan_xuat_hien
        }

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

class ProgressPrinter:
    """Quản lý hiển thị tiến trình gọn gàng, chống tràn cột terminal và chống spam log."""
    def __init__(self, total_lines: int, label: str = "nhân vật", update_interval: float = 0.4):
        self.total_lines = max(1, total_lines)
        self.label = label
        self.update_interval = update_interval
        self.start_time = time.time()
        self.last_update = 0.0
        self.is_tty = sys.stdout.isatty()
        self.last_milestone = -1
        self.bar_width = 14  # Độ dài thanh vừa phải để toàn bộ dòng <= 75 ký tự

    def update(self, current_line: int, found_count: int, force: bool = False):
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
    def __init__(self, loader: ResourceLoader, skip_known: bool = True):
        self.loader = loader
        self.skip_known = skip_known
        self.trimmer = BoundaryTrimmer(self.loader.trailing_stopwords)
        self.extractor = CandidateExtractor(self.loader, self.trimmer, skip_known=skip_known)
        self.expander = ContextExpander()

    @staticmethod
    def _score_block(confidence: float, context: str, line_idx: int) -> tuple:
        has_profile_cue = any(kw in context.lower() for kw in ("tuổi", "thê tử", "mẫu thân", "tỷ tỷ", "bang chủ", "tỉnh trưởng"))
        return (confidence, 1 if has_profile_cue else 0, len(context), -line_idx)

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
                        name_key = cand.name.lower().strip()

                        if name_key in tracked:
                            existing = tracked[name_key]
                            existing.so_lan_xuat_hien += 1
                            if len(existing.cac_dong_xuat_hien) < 100 and line_idx not in existing.cac_dong_xuat_hien:
                                existing.cac_dong_xuat_hien.append(line_idx)
                            is_dirty = True
                            # Chỉ mở rộng ngữ cảnh khi độ tin cậy có thể vượt qua điểm số tốt nhất hiện có
                            if cand.confidence >= best_scores[name_key][0]:
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

        deduped = list(tracked.values())
        return deduped

    def deduplicate_blocks(self, blocks: list[CharacterBlock]) -> list[CharacterBlock]:
        grouped: dict[str, list[CharacterBlock]] = defaultdict(list)
        for b in blocks:
            grouped[b.target.lower().strip()].append(b)

        deduped: list[CharacterBlock] = []
        for name_key, group in grouped.items():
            all_lines = sorted(list(set(b.dong_xuat_hien for b in group)))
            total_count = len(group)

            def score_block(b: CharacterBlock) -> tuple:
                has_profile_cue = any(kw in b.context.lower() for kw in ("tuổi", "thê tử", "mẫu thân", "tỷ tỷ", "bang chủ", "tỉnh trưởng"))
                return (b.confidence, 1 if has_profile_cue else 0, len(b.context), -b.dong_xuat_hien)

            best_block = max(group, key=score_block)
            best_block.so_lan_xuat_hien = total_count
            best_block.cac_dong_xuat_hien = all_lines
            best_block.dong_xuat_hien = all_lines[0]
            deduped.append(best_block)

        # Sort by first appearance line
        deduped.sort(key=lambda b: b.dong_xuat_hien)

        # Re-index sequential ids
        for idx, b in enumerate(deduped, start=1):
            b.id = f"ch_{idx:04d}"

        return deduped
