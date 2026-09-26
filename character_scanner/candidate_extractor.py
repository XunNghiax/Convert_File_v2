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

VN_UPPER = "A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ"
VN_LOWER = "a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
VN_WORD = f"[{VN_UPPER}{VN_LOWER}]"

class CandidateExtractor:
    RELATION_TERMS = {
        "thê tử", "mẫu thân", "tỷ tỷ", "muội muội", "kế mẫu", "đệ đệ", "con",
        "nữ nhi", "ba ba", "mẹ", "chị dâu", "dì", "vợ trước", "vợ", "chồng",
        "đường muội", "đường huynh", "biểu muội", "phu nhân"
    }
    
    JOB_TERMS = {
        "bang chủ", "đà chủ", "tỉnh trưởng", "thị trưởng", "cục trưởng",
        "tổng giám đốc", "phó tổng", "phó quản lý", "giáo sư", "y tá trưởng", "y tá",
        "người chủ trì", "diễn viên", "học sinh", "chủ quản", "quản lý", "quản lí"
    }

    ACTION_VERBS = {
        "nói", "hỏi", "la lớn", "thở dài", "cười", "nghĩ", "quát", "kêu"
    }

    ACTION_OBJECT_VERBS = {
        "nhìn", "thấy", "ôm", "gặp", "hỏi", "đánh", "giết", "tìm", "thương",
        "cưới", "hôn", "nhớ", "chờ", "yêu", "trêu", "khiêu", "bóp", "sờ"
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

        # 0. Direct match from known characters dictionary
        for src, tgt in self.loader.known_characters.items():
            pattern_known = re.compile(rf'\b{re.escape(src)}\b', re.IGNORECASE)
            for m in pattern_known.finditer(line):
                cand = m.group(0).strip()
                results.append(CandidateMatch(
                    name=tgt,
                    raw=cand,
                    start=m.start(),
                    end=m.end(),
                    confidence=1.0,
                    reason="Khớp với từ điển nhân vật đã quy chuẩn"
                ))

        # 1a. Profile with explicit age: <name 2-5 words> , [nam/nữ ,] <age> tuổi
        profile_age_pattern = re.compile(
            rf'\b({VN_WORD}+(?:\s+{VN_WORD}+){{1,4}})\s*,\s*(?:(?:nam|nữ)\s*,\s*)?(\d{{1,2}}\s*tuổi)\b',
            re.IGNORECASE
        )
        for m in profile_age_pattern.finditer(line):
            raw_cand = m.group(1).strip()
            age_str = m.group(2).strip()
            clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
            trimmed, _ = self.trimmer.trim(clean_cand)
            if self._is_negative(trimmed):
                continue
            if trimmed.lower() in self.loader.known_characters:
                norm_name = self.loader.known_characters[trimmed.lower()]
                conf = 0.98
                reason = f"Cấu trúc hồ sơ giới thiệu, đi kèm '{age_str}', đã quy chuẩn Hán Việt"
            else:
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    conf = 0.95
                    reason = f"Cấu trúc hồ sơ giới thiệu, đi kèm '{age_str}', mang họ hợp lệ"
                elif all(w[0].isupper() for w in trimmed.split()):
                    conf = 0.85
                    reason = f"Cấu trúc hồ sơ giới thiệu, đi kèm '{age_str}'"
                else:
                    continue
            results.append(CandidateMatch(
                name=norm_name,
                raw=trimmed,
                start=m.start(1),
                end=m.start(1) + len(trimmed),
                confidence=conf,
                reason=reason
            ))

        # 1b. Standalone gender profile followed by comma (e.g. "Trương Tử Kiến, nam, 30 tuổi")
        profile_gender_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\s*,\s*(nam|nữ)\s*,',
            re.IGNORECASE
        )
        for m in profile_gender_pattern.finditer(line):
            raw_cand = m.group(1).strip()
            detail = m.group(2).strip()
            clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
            trimmed, _ = self.trimmer.trim(clean_cand)
            if self._is_negative(trimmed):
                continue
            norm_name = self.trimmer.normalize_name(trimmed)
            if self._starts_with_surname(norm_name):
                results.append(CandidateMatch(
                    name=norm_name,
                    raw=trimmed,
                    start=m.start(1),
                    end=m.start(1) + len(trimmed),
                    confidence=0.95,
                    reason=f"Cấu trúc hồ sơ giới thiệu, đi kèm '{detail}', mang họ hợp lệ"
                ))

        # 2. Relation regex: <name> + <relation>
        sorted_relations = sorted(self.RELATION_TERMS, key=len, reverse=True)
        for rel in sorted_relations:
            rel_pattern = re.compile(
                rf'\b({VN_WORD}+(?:\s+{VN_WORD}+){{0,3}})\s+{re.escape(rel)}\b',
                re.IGNORECASE
            )
            for m in rel_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                if not raw_cand:
                    continue
                words_before = raw_cand.lower().split()
                if words_before and words_before[-1] in self.ACTION_OBJECT_VERBS:
                    continue
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed):
                    continue
                if trimmed.lower() in self.loader.known_characters:
                    norm_name = self.loader.known_characters[trimmed.lower()]
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.92,
                        reason=f"Đứng trước từ chỉ quan hệ '{rel}', đã quy chuẩn Hán Việt"
                    ))
                    continue

                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.88,
                        reason=f"Đứng trước từ chỉ quan hệ '{rel}', mang họ hợp lệ"
                    ))
                elif len(norm_name.split()) >= 2 and all(w[0].isupper() for w in trimmed.split()) and norm_name.lower() not in self.loader.common_dict:
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.78,
                        reason=f"Đứng trước từ chỉ quan hệ '{rel}'"
                    ))

        # 3. Job titles regex: <job> + <name>
        sorted_jobs = sorted(self.JOB_TERMS, key=len, reverse=True)
        for job in sorted_jobs:
            job_pattern = re.compile(
                rf'(?i:\b{re.escape(job)}\s+)([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\b'
            )
            for m in job_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed):
                    continue
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.92,
                        reason=f"Đứng sau chức danh '{job}', mang họ hợp lệ"
                    ))

        # 4. Capitalized TitleCase regex: 2 to 4 words starting with known surname
        cap_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\b'
        )
        for m in cap_pattern.finditer(line):
            cand = m.group(1).strip()
            clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', cand)[-1].strip()
            trimmed, _ = self.trimmer.trim(clean_cand)
            if self._is_negative(trimmed):
                continue
            norm_name = self.trimmer.normalize_name(trimmed)
            if self._starts_with_surname(norm_name):
                after_text = line[m.end():m.end() + 20].lower()
                has_action = any(v in after_text for v in self.ACTION_VERBS)
                conf = 0.85 if has_action else 0.70
                reason = f"Viết hoa chữ cái đầu, mang họ hợp lệ" + (f", đi kèm hành động" if has_action else "")
                results.append(CandidateMatch(
                    name=norm_name,
                    raw=trimmed,
                    start=m.start(1),
                    end=m.start(1) + len(trimmed),
                    confidence=conf,
                    reason=reason
                ))

        # 5. Session cache matches (only match confirmed valid characters)
        for known in self.session_cache:
            cache_pattern = re.compile(rf'\b{re.escape(known)}\b', re.IGNORECASE)
            for m in cache_pattern.finditer(line):
                cand = m.group(0).strip()
                if self._is_negative(cand):
                    continue
                results.append(CandidateMatch(
                    name=self.trimmer.normalize_name(cand),
                    raw=cand,
                    start=m.start(),
                    end=m.end(),
                    confidence=0.92,
                    reason="Khớp với tên nhân vật đã xác nhận trước đó"
                ))

        # Deduplicate overlapping spans (keep highest confidence)
        unique_results = self._deduplicate_spans(results)
        for cand in unique_results:
            cand_low = cand.name.lower()
            if (cand.confidence >= 0.88 and 
                self._starts_with_surname(cand.name) and 
                cand_low not in self.loader.non_person and 
                cand_low not in self.loader.blacklist and 
                cand_low not in self.loader.common_dict and 
                len(cand.name.split()) >= 2):
                self.session_cache.add(cand.name)
        return unique_results

    def _is_negative(self, text: str) -> bool:
        clean = text.strip()
        low = clean.lower()
        if low in self.loader.known_characters:
            return False
        words = low.split()
        if len(words) < 2 or len(words) > 5:
            return True
        if low in self.loader.pronouns or low in self.loader.non_person:
            return True
        if low in self.loader.blacklist or low in self.loader.common_dict:
            return True
        # Nếu cụm từ viết thường và từ đầu là đại từ/phó từ/động từ
        if clean and clean[0].islower() and (
            words[0] in self.loader.pronouns or 
            words[0] in self.trimmer.DEFAULT_TRAILING or
            words[0] in self.trimmer.DEFAULT_LEADING
        ):
            return True
        # Không bắt cụm từ có từ cuối là từ nối/chỉ quan hệ/đại từ
        if words[-1] in self.trimmer.DEFAULT_TRAILING or words[-1] in self.trimmer.DEFAULT_LEADING:
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

