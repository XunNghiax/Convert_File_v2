from dataclasses import dataclass
import re
from .resource_loader import ResourceLoader
from .boundary_trimmer import BoundaryTrimmer

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

    ANCHOR_TERMS = {
        "bảo mẫu", "mẹ kế", "mẹ ruột", "mẹ", "mẫu thân", "tiểu di", "cô cô", "cô",
        "bà ngoại", "ngoại bà", "bà nội", "nữ nhi", "con gái", "tỷ tỷ", "muội muội",
        "biểu tỷ", "biểu muội", "đường tỷ", "đường muội", "tẩu tử", "chị dâu", "dượng",
        "lão sư", "thầy giáo", "cô giáo", "chủ nhiệm", "bạn học", "đồng học", "hoa khôi",
        "bác sĩ", "y tá", "viện trưởng", "chủ tịch", "tổng tài", "thị trưởng", "cục trưởng",
        "tên là", "tên gọi là", "kêu là", "kêu", "ta gọi", "tự xưng là", "vị hôn thê", "hôn phu"
    }

    ACTION_VERBS = {
        "nói", "hỏi", "la lớn", "thở dài", "cười", "nghĩ", "quát", "kêu"
    }

    ACTION_OBJECT_VERBS = {
        "nhìn", "thấy", "ôm", "gặp", "hỏi", "đánh", "giết", "tìm", "thương",
        "cưới", "hôn", "nhớ", "chờ", "yêu", "trêu", "khiêu", "bóp", "sờ"
    }

    def __init__(self, loader: ResourceLoader, trimmer: BoundaryTrimmer, skip_known: bool = False):
        self.loader = loader
        self.trimmer = trimmer
        self.skip_known = skip_known
        self.session_cache: set[str] = set()

        # Pre-compile static regex patterns once
        self.profile_age_pattern = re.compile(
            rf'\b({VN_WORD}+(?:\s+{VN_WORD}+){{1,4}})\s*,\s*(?:(?:nam|nữ)\s*,\s*)?(\d{{1,2}}\s*tuổi)\b',
            re.IGNORECASE
        )
        self.profile_gender_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\s*,\s*(nam|nữ)\s*,',
            re.IGNORECASE
        )

        sorted_relations = sorted(self.RELATION_TERMS, key=len, reverse=True)
        rel_group = "|".join(re.escape(r) for r in sorted_relations)
        self.comb_rel_pattern = re.compile(
            rf'\b({VN_WORD}+(?:\s+{VN_WORD}+){{0,3}})\s+({rel_group})\b',
            re.IGNORECASE
        )

        sorted_jobs = sorted(self.JOB_TERMS, key=len, reverse=True)
        job_group = "|".join(re.escape(j) for j in sorted_jobs)
        self.comb_job_pattern = re.compile(
            rf'(?i:\b({job_group})\s+)([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\b'
        )

        sorted_anchors = sorted(self.ANCHOR_TERMS, key=len, reverse=True)
        anchor_group = "|".join(re.escape(a) for a in sorted_anchors)
        self.anchor_pattern = re.compile(
            rf'(?i:\b({anchor_group})(?:\s+(?:tên là|gọi là|kêu là|tên gọi là|đích|của ta|của hắn|của nàng))?\s*[:\-—]?\s*)([{VN_UPPER}{VN_LOWER}]+(?:\s+[{VN_UPPER}{VN_LOWER}]+){{1,3}})\b'
        )

        self.dialogue_speaker_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})(?:\s+[^:\n"“”]{{1,30}})?\s+(?:nói|hỏi|cười|quát|thở dài|lẩm bẩm|thầm nghĩ|đáp|kêu|hét)\s*:\s*["“]'
        )
        self.dialogue_after_pattern = re.compile(
            rf'["”]\s*([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})(?:\s+[^,\n"“”]{{1,30}})?\s+(?:nói|hỏi|cười|quát|thở dài|lẩm bẩm|đáp)\b'
        )

        self.cap_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\b'
        )

    def extract_candidates(self, line: str, skip_known: bool | None = None) -> list[CandidateMatch]:
        effective_skip = self.skip_known if skip_known is None else skip_known
        results: list[CandidateMatch] = []
        line_clean = line.strip()
        if not line_clean:
            return results

        line_lower = line_clean.lower()

        # -1. Direct match from deconvert dictionary (khôi phục từ dịch thô)
        if self.loader.deconvert_dict:
            for src, tgt in self.loader.deconvert_dict.items():
                if src in line_lower:
                    pattern_deconvert = re.compile(rf'\b{re.escape(src)}\b', re.IGNORECASE)
                    for m in pattern_deconvert.finditer(line):
                        cand = m.group(0).strip()
                        results.append(CandidateMatch(
                            name=tgt,
                            raw=cand,
                            start=m.start(),
                            end=m.end(),
                            confidence=1.0,
                            reason=f"Khôi phục từ dịch thô '{src}'"
                        ))

        # 0. Direct match from known characters dictionary (only when not skipping known)
        if not effective_skip and self.loader.known_characters:
            for src, tgt in self.loader.known_characters.items():
                if src in line_lower:
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

        # 1a. Profile with explicit age (Fast-path: chỉ chạy khi có chữ "tuổi")
        if "tuổi" in line_lower:
            for m in self.profile_age_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                age_str = m.group(2).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed, skip_known=effective_skip):
                    continue
                if trimmed.lower() in self.loader.known_characters:
                    if effective_skip:
                        continue
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

        # 1b. Standalone gender profile (Fast-path: chỉ chạy khi có "nam" hoặc "nữ")
        if "nam" in line_lower or "nữ" in line_lower:
            for m in self.profile_gender_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                detail = m.group(2).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed, skip_known=effective_skip):
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

        # 2. Relation combined regex (Fast-path: chỉ chạy khi có từ quan hệ trong dòng)
        if any(rel in line_lower for rel in self.RELATION_TERMS):
            for m in self.comb_rel_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                rel = m.group(2).strip()
                if not raw_cand:
                    continue
                # Nếu từ quan hệ là "con" nhưng đi kèm "ngươi" (con ngươi - con mắt/đồng tử)
                if rel.lower() == "con" and line[m.end():m.end() + 10].lower().startswith("ngươi"):
                    continue
                words_before = raw_cand.lower().split()
                if words_before and words_before[-1] in self.ACTION_OBJECT_VERBS:
                    continue
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed, skip_known=effective_skip):
                    continue
                if trimmed.lower() in self.loader.known_characters:
                    if effective_skip:
                        continue
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

        # 3. Job titles combined regex (Fast-path: chỉ chạy khi có chức danh trong dòng)
        if any(job in line_lower for job in self.JOB_TERMS):
            for m in self.comb_job_pattern.finditer(line):
                job = m.group(1).strip()
                raw_cand = m.group(2).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed, skip_known=effective_skip):
                    continue
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(2),
                        end=m.start(2) + len(trimmed),
                        confidence=0.92,
                        reason=f"Đứng sau chức danh '{job}', mang họ hợp lệ"
                    ))

        # 4. Anchor pattern for relations/roles followed by names (even lowercase)
        if any(anc in line_lower for anc in self.ANCHOR_TERMS):
            for m in self.anchor_pattern.finditer(line):
                anc = m.group(1).strip()
                raw_cand = m.group(2).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[0].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                words = trimmed.split()
                if len(words) == 4:
                    first_two = f"{words[0].lower()} {words[1].lower()}"
                    if first_two not in self.loader.compound_surnames:
                        trimmed = " ".join(words[:3])
                        trimmed, _ = self.trimmer.trim(trimmed)
                        words = trimmed.split()
                if len(words) == 3:
                    first_two = f"{words[0].lower()} {words[1].lower()}"
                    if first_two not in self.loader.compound_surnames and words[2].lower() in self.trimmer.trailing_stopwords:
                        trimmed = " ".join(words[:2])
                        trimmed, _ = self.trimmer.trim(trimmed)
                if self._is_negative(trimmed, skip_known=effective_skip):
                    continue
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(2),
                        end=m.start(2) + len(trimmed),
                        confidence=0.94,
                        reason=f"Đứng sau mỏ neo xưng hô '{anc}', mang họ hợp lệ"
                    ))

        # 5. Dialogue speaker patterns
        if (':' in line or '：' in line) and ('"' in line or '“' in line):
            for m in self.dialogue_speaker_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed, skip_known=effective_skip):
                    continue
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.96,
                        reason="Chủ thể phát ngôn hội thoại, mang họ hợp lệ"
                    ))

        if '"' in line or '”' in line:
            for m in self.dialogue_after_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[0].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed, skip_known=effective_skip):
                    continue
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.95,
                        reason="Chủ thể phát ngôn sau lời thoại, mang họ hợp lệ"
                    ))

        # 6. Capitalized TitleCase regex: 2 to 4 words starting with known surname
        # Fast-path: chỉ chạy khi dòng có ít nhất 1 chữ in hoa
        if any(c.isupper() for c in line):
            for m in self.cap_pattern.finditer(line):
                cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', cand)[-1].strip()
                trimmed, _ = self.trimmer.trim(clean_cand)
                if self._is_negative(trimmed, skip_known=effective_skip):
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

        # 7. Session cache matches (Fast-path: chỉ quét những tên thực sự xuất hiện trong dòng)
        if self.session_cache:
            for known in self.session_cache:
                if known.lower() in line_lower:
                    if effective_skip and (known.lower() in self.loader.known_characters):
                        continue
                    cache_pattern = re.compile(rf'\b{re.escape(known)}\b', re.IGNORECASE)
                    for m in cache_pattern.finditer(line):
                        cand = m.group(0).strip()
                        if self._is_negative(cand, skip_known=effective_skip):
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
        if effective_skip:
            unique_results = [
                cand for cand in unique_results
                if cand.raw.lower().strip() not in self.loader.known_characters
                and cand.name.lower().strip() not in self.loader.known_characters
            ]

        # Chỉ cache các ứng viên có độ tin cậy rất cao (>= 0.94) và bắt buộc không nằm trong non_person
        for cand in unique_results:
            cand_low = cand.name.lower()
            raw_low = cand.raw.lower().strip()
            if effective_skip and (cand_low in self.loader.known_characters or raw_low in self.loader.known_characters):
                continue
            if (cand.confidence >= 0.94 and 
                self._starts_with_surname(cand.name) and 
                cand_low not in self.loader.non_person and 
                raw_low not in self.loader.non_person and 
                cand_low not in self.loader.blacklist and 
                cand_low not in self.loader.common_dict and 
                2 <= len(cand.name.split()) <= 4):
                self.session_cache.add(cand.name)
        return unique_results

    def _is_negative(self, text: str, skip_known: bool = False) -> bool:
        clean = text.strip()
        low = clean.lower()
        if low in self.loader.known_characters:
            return True if skip_known else False
        words = low.split()
        if len(words) < 2 or len(words) > 5:
            return True
        if low in self.loader.pronouns or low in self.loader.non_person:
            return True
        if low in self.loader.blacklist or low in self.loader.common_dict:
            return True
        # Nếu cụm từ viết thường và từ đầu là đại từ/phó từ/động từ (và không phải họ hợp lệ)
        if clean and clean[0].islower() and not self._starts_with_surname(clean) and (
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

