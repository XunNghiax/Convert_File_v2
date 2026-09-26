from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
from character_scanner.resource_loader import ResourceLoader
from character_scanner.boundary_trimmer import BoundaryTrimmer
from character_scanner.candidate_extractor import CandidateExtractor
from character_scanner.context_expander import ContextExpander

@dataclass
class CharacterBlock:
    id: str
    source: str
    target: str
    context: str
    yeu_to_nhan_biet: str
    so_lan_xuat_hien: int = 1
    # internal fields used during scan and ranking
    dong_xuat_hien: int = 0
    confidence: float = 0.0
    cac_dong_xuat_hien: list[int] = field(default_factory=list)

    def to_output_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "context": self.context,
            "yeu_to_nhan_biet": self.yeu_to_nhan_biet,
            "so_lan_xuat_hien": self.so_lan_xuat_hien
        }

    def to_dict(self):
        return self.to_output_dict()

class ScannerEngine:
    def __init__(self, loader: ResourceLoader):
        self.loader = loader
        self.trimmer = BoundaryTrimmer(self.loader.trailing_stopwords)
        self.extractor = CandidateExtractor(self.loader, self.trimmer)
        self.expander = ContextExpander()

    def scan_file(self, filepath: Path, deduplicate: bool = True) -> list[CharacterBlock]:
        raw_blocks: list[CharacterBlock] = []
        counter = 1
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                candidates = self.extractor.extract_candidates(line)
                for cand in candidates:
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
                    raw_blocks.append(block)
                    counter += 1

        if deduplicate:
            return self.deduplicate_blocks(raw_blocks)
        return raw_blocks

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
