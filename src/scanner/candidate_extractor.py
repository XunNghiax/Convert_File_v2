from dataclasses import dataclass
import re
from .resource_loader import ResourceLoader
from .boundary_trimmer import BoundaryTrimmer
from ..utils.trie_matcher import TrieMatcher

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
    INTERNAL_GRAMMAR_STOPWORDS = {
        "có", "của", "được", "bị", "đang", "đã", "sẽ", "lại", "rất",
        "quá", "nhiều", "một", "hai", "ba", "cái", "thì", "mà", "là"
    }

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
        "tên là", "tên gọi là", "kêu là", "kêu", "ta gọi", "tự xưng là", "vị hôn thê", "hôn phu",
        "ba ba", "bố", "ông ngoại", "nha đầu", "tiểu nha đầu", "thích khách", "gọi là", "giám đốc", "thê tử"
    }

    ACTION_VERBS = {
        "nói", "hỏi", "la lớn", "thở dài", "cười", "nghĩ", "quát", "kêu"
    }

    ACTION_OBJECT_VERBS = {
        "nhìn", "thấy", "ôm", "gặp", "hỏi", "đánh", "giết", "tìm", "thương",
        "cưới", "hôn", "nhớ", "chờ", "yêu", "trêu", "khiêu", "bóp", "sờ"
    }

    LOWERCASE_ACTION_TERMS = sorted([
        "cưng chìu", "cưng chiều", "đưa ra", "nghiêm túc nhìn", "nhìn đến", "trong lòng",
        "ôm", "nói", "bước", "đi", "nghĩ", "hỏi", "cười", "quát", "thở dài", "thở", "lẩm bẩm",
        "thầm nghĩ", "đáp", "kêu", "hét", "mắng", "nhắc nhở", "giải thích", "than thở",
        "tức giận", "vui mừng", "kinh hãi", "hoảng hốt", "bối rối", "ngạc nhiên", "sợ hãi",
        "cảm thấy", "ghen tị", "ngơ ngác", "do dự", "trầm ngâm",
        "chạy", "đứng", "ngồi", "ngã", "nhảy", "tiến vào", "bước vào", "rời đi", "quay đầu",
        "xoay người", "lùi lại", "tiến lên", "bước tới", "đi tới", "bước ra", "đi ra",
        "nhìn", "thấy", "gặp", "tìm", "gật đầu", "lắc đầu", "vỗ", "kéo", "nắm", "buông",
        "nhíu mày", "nhướng mày", "trừng mắt", "đưa tay", "giơ tay", "cúi đầu", "ngẩng đầu"
    ], key=len, reverse=True)

    CLAUSE_STARTERS = {"mà", "nhưng", "còn", "khi", "nếu", "bởi vì", "do", "chỉ thấy", "liền thấy", "bỗng", "chợt", "thấy", "tại", "ở"}

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
            rf'(?i:\b({anchor_group})(?:\s+(?:tên là|gọi là|kêu là|tên gọi là|đích|của ta|của hắn|của nàng))?\s*[:\-—]?\s*)([{VN_UPPER}{VN_LOWER}]+(?:\s+[{VN_UPPER}{VN_LOWER}]+){{0,3}})\b'
        )

        self.foreign_dot_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+)*(?:\s*[·\-\u2022]\s*[{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+)*)+)\b'
        )

        self.dialogue_speaker_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{0,3}})(?:\s+[^:\n"“”]{{1,30}})?\s+(?:nói|hỏi|cười|quát|thở dài|lẩm bẩm|thầm nghĩ|đáp|kêu|hét)\s*:\s*["“]'
        )
        self.dialogue_after_pattern = re.compile(
            rf'["”]\s*([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{0,3}})(?:\s+[^,\n"“”]{{1,30}})?\s+(?:nói|hỏi|cười|quát|thở dài|lẩm bẩm|đáp)\b'
        )

        self.cap_pattern = re.compile(
            rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\b'
        )

        # 1. Biên dịch Trie cho deconvert_dict và known_characters
        self.deconvert_trie: TrieMatcher | None = None
        self.known_trie: TrieMatcher | None = None
        self._deconvert_dict_id: int | None = None
        self._deconvert_dict_len: int = -1
        self._known_chars_id: int | None = None
        self._known_chars_len: int = -1
        self._ensure_tries()

        # 2. Biên dịch 61 LOWERCASE_ACTION_TERMS thành 1 regex Trie duy nhất
        action_alts = "|".join(re.escape(a) for a in self.LOWERCASE_ACTION_TERMS)
        self.lowercase_action_regex = re.compile(rf'^(?:{action_alts})\b', re.IGNORECASE)

        # 3. Tập hợp các từ khóa nhanh để lọc cấp dòng
        self.fast_cue_words: set[str] = set()
        self._surnames_len: int = -1
        self._update_fast_cue_words()

    def _update_fast_cue_words(self):
        single = getattr(self.loader, 'single_surnames', set()) or set()
        compound = getattr(self.loader, 'compound_surnames', set()) or set()
        self.fast_cue_words = (
            single |
            compound |
            self.ANCHOR_TERMS |
            self.RELATION_TERMS |
            self.JOB_TERMS |
            {"tuổi", "·", "-", "\u2022"}
        )

    def _ensure_tries(self):
        deconv = getattr(self.loader, 'deconvert_dict', None)
        d_len = len(deconv) if deconv else 0
        if id(deconv) != self._deconvert_dict_id or d_len != self._deconvert_dict_len:
            self._deconvert_dict_id = id(deconv)
            self._deconvert_dict_len = d_len
            self.deconvert_trie = TrieMatcher({k.lower(): v for k, v in deconv.items()}) if deconv else None

        known = getattr(self.loader, 'known_characters', None)
        k_len = len(known) if known else 0
        if id(known) != self._known_chars_id or k_len != self._known_chars_len:
            self._known_chars_id = id(known)
            self._known_chars_len = k_len
            self.known_trie = TrieMatcher({k.lower(): v for k, v in known.items()}) if known else None

    @staticmethod
    def _is_word_boundary(text: str, start: int, end: int) -> bool:
        if start > 0 and (text[start - 1].isalnum() or text[start - 1] == '_'):
            return False
        if end < len(text) and (text[end].isalnum() or text[end] == '_'):
            return False
        return True

    def _fast_should_scan_line(self, line: str, line_lower: str) -> bool:
        """
        Fast-Path Line Screening:
        Nếu dòng không có chữ hoa VÀ không chứa bất kỳ từ khóa họ / mỏ neo nào -> False (bỏ qua dòng).
        Ngược lại -> True (cần quét).
        """
        if any(c.isupper() for c in line):
            return True
        return any(kw in line_lower for kw in self.fast_cue_words)

    def extract_candidates(self, line: str, skip_known: bool | None = None) -> list[CandidateMatch]:
        effective_skip = self.skip_known if skip_known is None else skip_known
        results: list[CandidateMatch] = []
        line_clean = line.strip()
        if not line_clean:
            return results

        line_lower = line.lower()
        vn_words = getattr(self.loader, "vn_2word_set", set())

        self._ensure_tries()
        single = getattr(self.loader, 'single_surnames', set()) or set()
        if len(single) != self._surnames_len:
            self._surnames_len = len(single)
            self._update_fast_cue_words()

        # -1. Direct match from deconvert dictionary (khôi phục từ dịch thô)
        if self.deconvert_trie:
            for start, end, src, tgt in self.deconvert_trie.find_matches(line_lower):
                if not self._is_word_boundary(line_lower, start, end):
                    continue
                cand = line[start:end].strip()
                results.append(CandidateMatch(
                    name=tgt,
                    raw=cand,
                    start=start,
                    end=end,
                    confidence=1.0,
                    reason=f"Khôi phục từ dịch thô '{src}'"
                ))

        # 0. Direct match from known characters dictionary (only when not skipping known)
        if not effective_skip and self.known_trie:
            for start, end, src, tgt in self.known_trie.find_matches(line_lower):
                if not self._is_word_boundary(line_lower, start, end):
                    continue
                cand = line[start:end].strip()
                results.append(CandidateMatch(
                    name=tgt,
                    raw=cand,
                    start=start,
                    end=end,
                    confidence=1.0,
                    reason="Khớp với từ điển nhân vật đã quy chuẩn"
                ))

        # Fast-Path Line Screening:
        # Nếu dòng không có chữ hoa VÀ không chứa bất kỳ từ khóa họ / mỏ neo nào -> Bỏ qua ngay
        if not self._fast_should_scan_line(line, line_lower):
            return results

        # 1a. Profile with explicit age (Fast-path: chỉ chạy khi có chữ "tuổi")
        if "tuổi" in line_lower:
            for m in self.profile_age_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                age_str = m.group(2).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
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
                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
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
                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
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
                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
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

        # 3b. Foreign name with middle dot / dash / Latin word support
        if '·' in line or '-' in line or '\u2022' in line:
            for m in self.foreign_dot_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—"]', raw_cand)[0].strip()
                trimmed = clean_cand
                if not self._is_negative(trimmed, skip_known=effective_skip):
                    norm_name = self.trimmer.normalize_name(trimmed)
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.95,
                        reason="Tên phiên âm nước ngoài có dấu nối"
                    ))

        # 4. Anchor pattern for relations/roles followed by names (even lowercase or Latin)
        if any(anc in line_lower for anc in self.ANCHOR_TERMS):
            for m in self.anchor_pattern.finditer(line):
                anc = m.group(1).strip()
                raw_cand = m.group(2).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-"]', raw_cand)[0].strip()
                words = clean_cand.split()
                if not words:
                    continue
                # Support Latin name directly following anchor
                if self._is_latin_name(words[0]):
                    latin_words = []
                    for w in words:
                        if self._is_latin_name(w):
                            latin_words.append(w)
                        else:
                            break
                    trimmed = " ".join(latin_words)
                    if not self._is_negative(trimmed, skip_known=effective_skip):
                        norm_name = trimmed
                        results.append(CandidateMatch(
                            name=norm_name,
                            raw=trimmed,
                            start=m.start(2),
                            end=m.start(2) + len(trimmed),
                            confidence=0.94,
                            reason=f"Đứng sau mỏ neo xưng hô '{anc}', là tên Latinh hợp lệ"
                        ))
                    continue

                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
                words = trimmed.split()
                if len(words) == 4:
                    first_two = f"{words[0].lower()} {words[1].lower()}"
                    if first_two not in self.loader.compound_surnames and not self.trimmer.is_surname(first_two):
                        trimmed = " ".join(words[:3])
                        trimmed = self.trimmer.clean_candidate(trimmed, vn_words)
                        words = trimmed.split()
                if len(words) == 3:
                    first_two = f"{words[0].lower()} {words[1].lower()}"
                    if (first_two not in self.loader.compound_surnames and not self.trimmer.is_surname(first_two) and 
                        not self._starts_with_surname(trimmed) and 
                        words[2].lower() in self.trimmer.trailing_stopwords):
                        trimmed = " ".join(words[:2])
                        trimmed = self.trimmer.clean_candidate(trimmed, vn_words)
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

        # 4b. Lowercase name with action pattern
        lowercase_matches = self._extract_lowercase_action_candidates(line, skip_known=effective_skip)
        results.extend(lowercase_matches)

        # 5. Dialogue speaker patterns
        if (':' in line or '：' in line) and ('"' in line or '“' in line):
            for m in self.dialogue_speaker_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[-1].strip()
                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
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
                elif self._is_latin_name(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.95,
                        reason="Chủ thể phát ngôn hội thoại, là tên Latinh hợp lệ"
                    ))

        if '"' in line or '”' in line:
            for m in self.dialogue_after_pattern.finditer(line):
                raw_cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', raw_cand)[0].strip()
                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
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
                elif self._is_latin_name(norm_name):
                    results.append(CandidateMatch(
                        name=norm_name,
                        raw=trimmed,
                        start=m.start(1),
                        end=m.start(1) + len(trimmed),
                        confidence=0.95,
                        reason="Chủ thể phát ngôn sau lời thoại, là tên Latinh hợp lệ"
                    ))

        # 6. Capitalized TitleCase regex: 2 to 4 words starting with known surname
        # Fast-path: chỉ chạy khi dòng có ít nhất 1 chữ in hoa
        if any(c.isupper() for c in line):
            for m in self.cap_pattern.finditer(line):
                cand = m.group(1).strip()
                clean_cand = re.split(r'[\n\r\t,.;:!?—\-]', cand)[-1].strip()
                trimmed = clean_cand if clean_cand.lower() in self.loader.known_characters else self.trimmer.clean_candidate(clean_cand, vn_words)
                if self._is_negative(trimmed, skip_known=effective_skip):
                    continue
                norm_name = self.trimmer.normalize_name(trimmed)
                if self._starts_with_surname(norm_name):
                    after_text = line[m.end():m.end() + 20].lower()
                    has_action = (
                        any(v in after_text for v in self.ACTION_VERBS) or
                        any(v in after_text for v in self.trimmer.SINGLE_ACTION_VERBS) or
                        any(act in after_text for act in self.LOWERCASE_ACTION_TERMS)
                    )
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

        # Cache high confidence candidates
        for cand in unique_results:
            cand_low = cand.name.lower()
            raw_low = cand.raw.lower().strip()
            if effective_skip and (cand_low in self.loader.known_characters or raw_low in self.loader.known_characters):
                continue
            if (cand.confidence >= 0.94 and 
                (self._starts_with_surname(cand.name) or '·' in cand.name or '-' in cand.name or self._is_latin_name(cand.name)) and 
                cand_low not in self.loader.non_person and 
                raw_low not in self.loader.non_person and 
                cand_low not in self.loader.blacklist and 
                cand_low not in self.loader.common_dict and 
                1 <= len(cand.name.split()) <= 8):
                self.session_cache.add(cand.name)
        return unique_results

    def _is_latin_name(self, text: str) -> bool:
        clean = text.strip()
        words = clean.split()
        if not words:
            return False
        for w in words:
            if not re.match(r'^[A-Z][a-z]{1,}$', w):
                return False
            w_low = w.lower()
            if w_low in self.loader.common_dict or w_low in self.loader.single_surnames or w_low in self.loader.pronouns:
                return False
            has_foreign_char = any(c in w_low for c in "fjwz")
            has_double = bool(re.search(r'([a-z])\1', w_low))
            has_foreign_end = bool(re.search(r'(?:[bdfgjlrvwz]|th|sh|ck|rt|ld|nd|st|nt|ph)$', w_low))
            has_foreign_cluster = bool(re.search(r'(?:br|cr|dr|fr|gr|pr|str|spr|spl|scr|cl|fl|gl|pl|bl)', w_low))
            is_multisyllable = len(re.findall(r'[aeiouy]', w_low)) >= 2 and len(w) >= 4
            if not (has_foreign_char or has_double or has_foreign_end or has_foreign_cluster or is_multisyllable):
                return False
        return True

    def _is_clause_boundary(self, line: str, start_pos: int) -> bool:
        if start_pos == 0:
            return True
        before = line[:start_pos].rstrip()
        if not before:
            return True
        if before[-1] in ',.;:!?—-"“”\'’':
            return True
        last_word = before.split()[-1].lower() if before.split() else ""
        if last_word in self.CLAUSE_STARTERS:
            return True
        return False

    def _extract_lowercase_action_candidates(self, line: str, skip_known: bool = False) -> list[CandidateMatch]:
        results: list[CandidateMatch] = []
        tokens = list(re.finditer(rf'\b{VN_WORD}+\b', line))
        n = len(tokens)
        i = 0
        vn_words = getattr(self.loader, "vn_2word_set", set())
        while i < n:
            tok = tokens[i]
            w1 = tok.group(0).lower()
            cand_spans = []

            # Check compound surname (2 words)
            if i + 1 < n:
                w2 = tokens[i+1].group(0).lower()
                two_words = f"{w1} {w2}"
                if two_words in self.loader.compound_surnames or self.trimmer.is_surname(two_words):
                    if i + 3 < n:
                        cand_spans.append((i, i + 3))  # 4 words total
                    if i + 2 < n:
                        cand_spans.append((i, i + 2))  # 3 words total

            # Check single surname (1 word)
            if not cand_spans and (w1 in self.loader.single_surnames or self.trimmer.is_surname(w1)):
                if i + 3 < n:
                    cand_spans.append((i, i + 3))  # 4 words total
                if i + 2 < n:
                    cand_spans.append((i, i + 2))  # 3 words total
                if i + 1 < n:
                    cand_spans.append((i, i + 1))  # 2 words total

            matched = False
            for start_idx, end_idx in cand_spans:
                cand_raw = line[tokens[start_idx].start():tokens[end_idx].end()]
                if not re.match(rf'^{VN_WORD}+(?:\s+{VN_WORD}+)+$', cand_raw):
                    continue
                if not self._is_clause_boundary(line, tokens[start_idx].start()):
                    continue
                words_in_cand = cand_raw.lower().split()
                is_compound = len(words_in_cand) >= 2 and (f"{words_in_cand[0]} {words_in_cand[1]}" in self.loader.compound_surnames or self.trimmer.is_surname(f"{words_in_cand[0]} {words_in_cand[1]}"))
                surname_len = 2 if is_compound else 1
                given_words = words_in_cand[surname_len:]
                if any(gw in self.ACTION_VERBS or gw in self.trimmer.SINGLE_ACTION_VERBS for gw in given_words):
                    continue
                raw_words = cand_raw.split()
                if any(w[0].isupper() for w in raw_words[surname_len:]):
                    continue
                if any(phrase in cand_raw.lower() for phrase in self.trimmer.DEFAULT_LEADING_PHRASES):
                    continue

                after_text = line[tokens[end_idx].end():].lstrip()
                after_text_lower = after_text.lower()

                matched_action = None
                m_act = self.lowercase_action_regex.match(after_text_lower)
                if m_act:
                    matched_action = m_act.group(0)

                if matched_action:
                    trimmed = self.trimmer.clean_candidate(cand_raw, vn_words)
                    if not self._is_negative(trimmed, skip_known=skip_known):
                        norm_name = self.trimmer.normalize_name(trimmed)
                        results.append(CandidateMatch(
                            name=norm_name,
                            raw=trimmed,
                            start=tokens[start_idx].start(),
                            end=tokens[start_idx].start() + len(trimmed),
                            confidence=0.95,
                            reason=f"Tên viết thường mang họ hợp lệ, đi kèm hành động/cảm xúc '{matched_action}'"
                        ))
                        matched = True
                        i = end_idx + 1
                        break
            if not matched:
                i += 1
        return results

    def _is_negative(self, text: str, skip_known: bool = False) -> bool:
        clean = text.strip()
        low = clean.lower()

        # 1. Kiểm tra từ điển nhân vật đã biết
        if skip_known:
            if low in self.loader.known_characters:
                return True
            norm_name = self.trimmer.normalize_name(clean)
            if norm_name.lower() in self.loader.known_characters:
                return True
        else:
            if low in self.loader.known_characters:
                return False
            norm_name = self.trimmer.normalize_name(clean)
            if norm_name.lower() in self.loader.known_characters:
                return False

        words = low.split()
        is_foreign = ('·' in clean or '-' in clean or '\u2022' in clean or self._is_latin_name(clean))
        if is_foreign:
            words_clean = [w for w in words if w not in ('·', '-', '\u2022', '.') and not w.startswith('·') and not w.startswith('-')]
            if len(words_clean) < 1 or len(words_clean) > 8:
                return True
        else:
            if len(words) < 2 or len(words) > 5:
                return True

        # 2. Kiểm tra từ ghép 2 từ tiếng Việt (vn_2word_set)
        vn_words = getattr(self.loader, "vn_2word_set", set())
        if len(words) == 2 and " ".join(words) in vn_words:
            return True

        # 3. Kiểm tra từ chức năng ngữ pháp ở giữa tên
        if not is_foreign:
            surname_len = 2 if (len(words) >= 2 and (f"{words[0]} {words[1]}" in self.loader.compound_surnames or self.trimmer.is_surname(f"{words[0]} {words[1]}"))) else 1
            given_words = words[surname_len:]
            if any(gw in self.INTERNAL_GRAMMAR_STOPWORDS for gw in given_words):
                return True

        if low in self.loader.pronouns or low in self.loader.non_person:
            return True
        if low in self.loader.blacklist or low in self.loader.common_dict:
            return True
        if any(b in low for b in self.loader.blacklist):
            return True

        # Nếu cụm từ viết thường và từ đầu là đại từ/phó từ/động từ (và không phải họ hợp lệ)
        if clean and clean[0].islower() and not self._starts_with_surname(clean) and (
            words[0] in self.loader.pronouns or 
            words[0] in self.trimmer.DEFAULT_TRAILING or
            words[0] in self.trimmer.DEFAULT_LEADING
        ):
            return True

        # Không bắt cụm từ có từ cuối là từ nối/chỉ quan hệ/đại từ
        if not is_foreign and (words[-1] in self.trimmer.DEFAULT_TRAILING or words[-1] in self.trimmer.DEFAULT_LEADING):
            return True

        return False

    def _starts_with_surname(self, text: str) -> bool:
        words = text.lower().split()
        if not words:
            return False
        if len(words) >= 2 and (f"{words[0]} {words[1]}" in self.loader.compound_surnames or self.trimmer.is_surname(f"{words[0]} {words[1]}")):
            return True
        if words[0] in self.loader.single_surnames or self.trimmer.is_surname(words[0]):
            return True
        return False

    def _deduplicate_spans(self, candidates: list[CandidateMatch]) -> list[CandidateMatch]:
        # Filter out shorter candidates that are strictly subsumed by a candidate starting with a surname or foreign/latin
        filtered: list[CandidateMatch] = []
        for c in candidates:
            is_subsumed = False
            for other in candidates:
                if other is c:
                    continue
                if (other.start <= c.start and other.end >= c.end and (other.end - other.start > c.end - c.start)):
                    if (self._starts_with_surname(other.name) or '·' in other.name or '-' in other.name or self._is_latin_name(other.name)) and other.confidence >= 0.85:
                        is_subsumed = True
                        break
            if not is_subsumed:
                filtered.append(c)

        filtered.sort(key=lambda x: (-x.confidence, -(x.end - x.start)))
        kept: list[CandidateMatch] = []
        for c in filtered:
            overlap = False
            for k in kept:
                if max(c.start, k.start) < min(c.end, k.end) or c.name == k.name:
                    overlap = True
                    break
            if not overlap:
                kept.append(c)
        return sorted(kept, key=lambda x: x.start)

