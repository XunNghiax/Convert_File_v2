from dataclasses import dataclass, asdict
from pathlib import Path
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
    dong_xuat_hien: int
    confidence: float
    yeu_to_nhan_biet: str

    def to_dict(self):
        return asdict(self)

class ScannerEngine:
    def __init__(self, loader: ResourceLoader):
        self.loader = loader
        self.trimmer = BoundaryTrimmer(self.loader.trailing_stopwords)
        self.extractor = CandidateExtractor(self.loader, self.trimmer)
        self.expander = ContextExpander()

    def scan_file(self, filepath: Path) -> list[CharacterBlock]:
        blocks: list[CharacterBlock] = []
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
                        dong_xuat_hien=line_idx,
                        confidence=cand.confidence,
                        yeu_to_nhan_biet=cand.reason
                    )
                    blocks.append(block)
                    counter += 1
        return blocks
