from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
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
        start_time = time.time()
        last_update = 0.0
        bar_width = 25
        seen_names: set[str] = set()

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

                if show_progress:
                    now = time.time()
                    if now - last_update >= 0.15 or line_idx == total_lines or line_idx % 1000 == 0:
                        last_update = now
                        elapsed = max(0.001, now - start_time)
                        speed = line_idx / elapsed
                        eta_sec = (total_lines - line_idx) / max(1.0, speed)
                        eta_str = f"{int(eta_sec)}s" if eta_sec < 60 else f"{int(eta_sec//60)}m{int(eta_sec%60)}s"
                        percent = min(100.0, (line_idx / total_lines) * 100)
                        filled = int(bar_width * line_idx / total_lines)
                        bar = "█" * filled + "░" * (bar_width - filled)
                        found_count = len(seen_names) if deduplicate else (counter - 1)
                        label = "nhân vật" if deduplicate else "ứng viên"
                        sys.stdout.write(
                            f"\r[*] Đang quét: [{bar}] {percent:5.1f}% ({line_idx:,}/{total_lines:,} dòng) | {int(speed):,} dòng/s | Còn: {eta_str} | Tìm thấy: {found_count:,} {label}"
                        )
                        sys.stdout.flush()

                if line_idx % 20000 == 0:
                    gc.collect()

        if show_progress:
            total_elapsed = max(0.001, time.time() - start_time)
            avg_speed = int(total_lines / total_elapsed)
            found_count = len(seen_names) if deduplicate else (counter - 1)
            label = "nhân vật" if deduplicate else "ứng viên"
            sys.stdout.write(
                f"\r[*] Đang quét: [{'█' * bar_width}] 100.0% ({total_lines:,}/{total_lines:,} dòng) | {avg_speed:,} dòng/s | Xong trong: {total_elapsed:.1f}s | Tìm thấy: {found_count:,} {label}\n"
            )
            sys.stdout.flush()

    def scan_file(
        self,
        filepath: Path,
        deduplicate: bool = True,
        show_progress: bool = True,
        skip_known: Optional[bool] = None,
        progress_callback: Optional[Callable[[int, int, int], None]] = None
    ) -> list[CharacterBlock]:
        """
        Quét văn bản với cơ chế Khử trùng lặp trực tiếp (Online Deduplication)
        và hiển thị thanh tiến trình % trực quan thời gian thực.
        """
        effective_skip = self.skip_known if skip_known is None else skip_known
        if not deduplicate:
            return list(self.scan_file_stream(filepath, show_progress=show_progress, skip_known=effective_skip))

        total_lines = count_file_lines(filepath)
        tracked: dict[str, CharacterBlock] = {}
        best_scores: dict[str, tuple] = {}
        start_time = time.time()
        last_update = 0.0
        bar_width = 25

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    if show_progress:
                        now = time.time()
                        if now - last_update >= 0.15 or line_idx == total_lines:
                            last_update = now
                            elapsed = max(0.001, now - start_time)
                            speed = line_idx / elapsed
                            eta_sec = (total_lines - line_idx) / max(1.0, speed)
                            eta_str = f"{int(eta_sec)}s" if eta_sec < 60 else f"{int(eta_sec//60)}m{int(eta_sec%60)}s"
                            percent = min(100.0, (line_idx / total_lines) * 100)
                            filled = int(bar_width * line_idx / total_lines)
                            bar = "█" * filled + "░" * (bar_width - filled)
                            sys.stdout.write(
                                f"\r[*] Đang quét: [{bar}] {percent:5.1f}% ({line_idx:,}/{total_lines:,} dòng) | {int(speed):,} dòng/s | Còn: {eta_str} | Tìm thấy: {len(tracked):,} nhân vật"
                            )
                            sys.stdout.flush()
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
                            id="",
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

                if show_progress:
                    now = time.time()
                    if now - last_update >= 0.15 or line_idx == total_lines or line_idx % 1000 == 0:
                        last_update = now
                        elapsed = max(0.001, now - start_time)
                        speed = line_idx / elapsed
                        eta_sec = (total_lines - line_idx) / max(1.0, speed)
                        eta_str = f"{int(eta_sec)}s" if eta_sec < 60 else f"{int(eta_sec//60)}m{int(eta_sec%60)}s"
                        percent = min(100.0, (line_idx / total_lines) * 100)
                        filled = int(bar_width * line_idx / total_lines)
                        bar = "█" * filled + "░" * (bar_width - filled)
                        sys.stdout.write(
                            f"\r[*] Đang quét: [{bar}] {percent:5.1f}% ({line_idx:,}/{total_lines:,} dòng) | {int(speed):,} dòng/s | Còn: {eta_str} | Tìm thấy: {len(tracked):,} nhân vật"
                        )
                        sys.stdout.flush()

                if progress_callback:
                    progress_callback(line_idx, total_lines, len(tracked))

                if line_idx % 20000 == 0:
                    gc.collect()

        if show_progress:
            total_elapsed = max(0.001, time.time() - start_time)
            avg_speed = int(total_lines / total_elapsed)
            sys.stdout.write(
                f"\r[*] Đang quét: [{'█' * bar_width}] 100.0% ({total_lines:,}/{total_lines:,} dòng) | {avg_speed:,} dòng/s | Xong trong: {total_elapsed:.1f}s | Tìm thấy: {len(tracked):,} nhân vật\n"
            )
            sys.stdout.flush()

        # Sắp xếp theo dòng xuất hiện đầu tiên
        deduped = list(tracked.values())
        deduped.sort(key=lambda b: b.dong_xuat_hien)

        # Đánh chỉ mục id tuần tự
        for idx, b in enumerate(deduped, start=1):
            b.id = f"ch_{idx:04d}"

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
