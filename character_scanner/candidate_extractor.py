from dataclasses import dataclass
import re
from character_scanner.resource_loader import ResourceLoader
from character_scanner.boundary_trimmer import BoundaryTrimmer

@dataclass
class CandidateMatch:
    name: str
    raw: str
    start: int
    end: int
    confidence: float
    reason: str

class CandidateExtractor:
    RELATION_TERMS = {
        "thê tử", "mẫu thân", "tỷ tỷ", "muội muội", "kế mẫu", "đệ đệ", "con",
        "nữ nhi", "ba ba", "mẹ", "chị dâu", "dì", "vợ trước", "vợ", "chồng",
        "đường muội", "đường huynh", "biểu muội", "phu nhân"
    }
    
    JOB_TERMS = {
        "bang chủ", "đà chủ", "tỉnh trưởng", "thị trưởng", "cục trưởng",
        "tổng giám đốc", "phó quản lý", "giáo sư", "y tá trưởng", "y tá",
        "người chủ trì", "diễn viên", "học sinh", "chủ quản"
    }

    ACTION_VERBS = {
        "nói", "hỏi", "la lớn", "thở dài", "cười", "nghĩ", "quát", "kêu"
    }

    def __init__(self, loader: ResourceLoader, trimmer: BoundaryTrimmer):
        self.loader = loader
        self.trimmer = trimmer
        self.session_cache: set[str] = set()

    def extract_candidates(self, line: str) -> list[CandidateMatch]:
        results: list[CandidateMatch] = []
        line_clean = line.strip()
        if not line_clean:
            return results

        # 1. Profile regex: <name 2-4 words> [,\s-]+ (\d+ tuổi|nam|nữ|...)
        profile_pattern = re.compile(
            r'\b([A-ZÀ-Ỹa-zà-ỹ]+(?:\s+[A-ZÀ-Ỹa-zà-ỹ]+){1,3})\s*,\s*(\d{1,2}\s*tuổi|nam|nữ|thiếu phụ|mỹ phụ|thiếu nữ)',
            re.IGNORECASE | re.UNICODE
        )
        for m in profile_pattern.finditer(line):
            raw_cand = m.group(1).strip()
            detail = m.group(2).strip()
            trimmed, _ = self.trimmer.trim(raw_cand)
            if self._is_negative(trimmed):
                continue
            norm_name = self.trimmer.normalize_name(trimmed)
            if self._starts_with_surname(norm_name):
                conf = 0.90
                reason = f"Cấu trúc hồ sơ giới thiệu, đi kèm '{detail}', mang họ hợp lệ"
            else:
                conf = 0.70
                reason = f"Cấu trúc hồ sơ giới thiệu, đi kèm '{detail}'"
            results.append(CandidateMatch(
                name=norm_name,
                raw=raw_cand,
                start=m.start(1),
                end=m.end(1),
                confidence=conf,
                reason=reason
            ))

        # 2. Relation regex: <name> + <relation> or <relation> + <name>
        for rel in self.RELATION_TERMS:
            rel_pattern = re.compile(
                rf'\b([A-ZÀ-Ỹa-zà-ỹ]+(?:\s+[A-ZÀ-Ỹa-zà-ỹ]+){{1,3}})\s+{re.escape(rel)}\b',
                re.IGNORECASE | re.UNICODE
            )
            for m in rel_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                trimmed, _ = self.trimmer.trim(raw_cand)
                if self._is_negative(trimmed):
                    continue
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=raw_cand,
                        start=m.start(1),
                        end=m.end(1),
                        confidence=0.85,
                        reason=f"Đứng trước từ chỉ quan hệ '{rel}', mang họ hợp lệ"
                    ))

        # 3. Capitalized TitleCase regex: 2 to 4 words starting with known surname
        cap_pattern = re.compile(r'\b([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,3})\b', re.UNICODE)
        for m in cap_pattern.finditer(line):
            cand = m.group(1).strip()
            trimmed, _ = self.trimmer.trim(cand)
            if self._is_negative(trimmed):
                continue
            norm_name = self.trimmer.normalize_name(trimmed)
            if self._starts_with_surname(norm_name):
                after_text = line[m.end():m.end() + 20].lower()
                has_action = any(v in after_text for v in self.ACTION_VERBS)
                conf = 0.80 if has_action else 0.65
                reason = f"Viết hoa chữ cái đầu, mang họ hợp lệ" + (f", đi kèm hành động" if has_action else "")
                results.append(CandidateMatch(
                    name=norm_name,
                    raw=cand,
                    start=m.start(1),
                    end=m.end(1),
                    confidence=conf,
                    reason=reason
                ))

        # 4. Session cache matches
        for known in self.session_cache:
            cache_pattern = re.compile(rf'\b{re.escape(known)}\b', re.IGNORECASE | re.UNICODE)
            for m in cache_pattern.finditer(line):
                cand = m.group(0).strip()
                results.append(CandidateMatch(
                    name=self.trimmer.normalize_name(cand),
                    raw=cand,
                    start=m.start(),
                    end=m.end(),
                    confidence=0.90,
                    reason="Khớp với tên nhân vật đã xác nhận trước đó"
                ))

        # Deduplicate overlapping spans (keep highest confidence)
        unique_results = self._deduplicate_spans(results)
        for cand in unique_results:
            if cand.confidence >= 0.70:
                self.session_cache.add(cand.name)
        return unique_results

    def _is_negative(self, text: str) -> bool:
        low = text.lower().strip()
        words = low.split()
        if len(words) < 2 or len(words) > 4:
            return True
        if low in self.loader.pronouns or low in self.loader.non_person:
            return True
        if low in self.loader.blacklist or low in self.loader.common_dict:
            return True
        return False

    def _starts_with_surname(self, text: str) -> bool:
        words = text.lower().split()
        if len(words) >= 2 and f"{words[0]} {words[1]}" in self.loader.compound_surnames:
            return True
        if words and words[0] in self.loader.single_surnames:
            return True
        return False

    def _deduplicate_spans(self, candidates: list[CandidateMatch]) -> list[CandidateMatch]:
        candidates.sort(key=lambda x: (-x.confidence, -(x.end - x.start)))
        kept: list[CandidateMatch] = []
        for c in candidates:
            overlap = False
            for k in kept:
                if max(c.start, k.start) < min(c.end, k.end) or c.name == k.name:
                    overlap = True
                    break
            if not overlap:
                kept.append(c)
        return sorted(kept, key=lambda x: x.start)
