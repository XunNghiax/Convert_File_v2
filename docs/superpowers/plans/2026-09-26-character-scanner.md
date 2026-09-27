# Character Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng hệ thống thuật toán tự động quét và nhận diện tên nhân vật từ văn bản truyện convert (`exam.txt`), phân đoạn và trích xuất ngữ cảnh trung tâm, đóng gói kết quả ra thư mục `scanner/` gồm file master JSON và các file `.md` (30-50 block kèm prompt hướng dẫn AI), kèm bộ kiểm thử benchmark đối chiếu với `file_nhan_vat.json`.

**Architecture:** Kiến trúc Pipeline phân tầng tuần tự:
1. `ResourceLoader`: Đọc và tối ưu các bộ từ điển `filters/` và `data/` thành Set/Trie O(1).
2. `CandidateExtractor`: Nhận diện ứng viên đa tầng (Hồ sơ tuổi/giới tính/quan hệ, Họ đơn/kép, Hội thoại/kính ngữ, Cache phiên) và tính Confidence Score.
3. `BoundaryTrimmer`: Cắt tỉa ranh giới từ dính đuôi theo `trailing_stopwords.txt`.
4. `ContextExpander`: Trích xuất câu trung tâm chứa `source`, tự động mở rộng câu lân cận nếu câu ngắn.
5. `ScannerEngine`: Quét toàn văn theo dòng, khử trùng lặp thực thể.
6. `OutputPackager`: Xuất `scanner/scanner_master.json` và phân trang `scanner/scanner_N.md` tích hợp `prompt.md`.
7. `Benchmark`: Đánh giá Recall, Precision, F1 so với `file_nhan_vat.json`.

**Tech Stack:** Python 3.10+, `pytest`, regex `re`, `json`, `dataclasses`, `pathlib`.

## Global Constraints
- Không sử dụng thư viện bên ngoài nặng nề (giữ cho script chạy bằng chuẩn thư viện Python, chỉ dùng `pytest` để chạy kiểm thử).
- Toàn bộ đọc ghi file văn bản sử dụng encoding `utf-8` hoặc `utf-8-sig`.
- Cấu trúc block đầu ra bắt buộc tuân thủ: `id`, `source`, `target`, `context`, `dong_xuat_hien`, `confidence`, `yeu_to_nhan_biet`.
- Mỗi file markdown con chứa từ 30 đến 50 block (mặc định 40).

---

### Task 1: Scaffolding & ResourceLoader

**Files:**
- Create: `character_scanner/__init__.py`
- Create: `character_scanner/resource_loader.py`
- Test: `tests/test_resource_loader.py`

**Interfaces:**
- Produces: `ResourceLoader` class:
  - `load_surnames(path: Path) -> tuple[set[str], set[str]]` (single surnames & compound surnames)
  - `load_word_set(path: Path) -> set[str]` (pronouns, non_person, trailing stopwords, blacklist)
  - `load_common_dict(path: Path) -> set[str]`
  - `load_character_dict(path: Path) -> dict[str, str]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_resource_loader.py
from pathlib import Path
from character_scanner.resource_loader import ResourceLoader

def test_load_surnames(tmp_path):
    f = tmp_path / "surnames.txt"
    f.write_text("# Surnames\ntrương\nlâm\nâu dương\n", encoding="utf-8")
    loader = ResourceLoader()
    single, compound = loader.load_surnames(f)
    assert "trương" in single
    assert "lâm" in single
    assert "âu dương" in compound

def test_load_word_set(tmp_path):
    f = tmp_path / "pronouns.txt"
    f.write_text("# Pronouns\nchúng ta\nbọn họ\n", encoding="utf-8")
    loader = ResourceLoader()
    words = loader.load_word_set(f)
    assert "chúng ta" in words
    assert "bọn họ" in words
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_resource_loader.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'character_scanner')

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/__init__.py
"""Character Scanner Package"""

# character_scanner/resource_loader.py
from pathlib import Path
import json

class ResourceLoader:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(".")
        self.single_surnames: set[str] = set()
        self.compound_surnames: set[str] = set()
        self.pronouns: set[str] = set()
        self.non_person: set[str] = set()
        self.trailing_stopwords: set[str] = set()
        self.blacklist: set[str] = set()
        self.common_dict: set[str] = set()
        self.known_characters: dict[str, str] = {}

    def load_surnames(self, path: Path) -> tuple[set[str], set[str]]:
        single, compound = set(), set()
        if not path.exists():
            return single, compound
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            if " " in line:
                compound.add(line)
            else:
                single.add(line)
        return single, compound

    def load_word_set(self, path: Path) -> set[str]:
        words = set()
        if not path.exists():
            return words
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            words.add(line)
        return words

    def load_common_dict(self, path: Path) -> set[str]:
        words = set()
        if not path.exists():
            return words
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            for item in data:
                src = item.get("source", "").strip().lower()
                if src:
                    words.add(src)
        except Exception:
            pass
        return words

    def load_character_dict(self, path: Path) -> dict[str, str]:
        chars = {}
        if not path.exists():
            return chars
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            for item in data:
                src = item.get("source", "").strip()
                tgt = item.get("target", "").strip()
                if src:
                    chars[src.lower()] = tgt
        except Exception:
            pass
        return chars

    def load_all(self):
        filters_dir = self.base_dir / "filters"
        data_dir = self.base_dir / "data"
        self.single_surnames, self.compound_surnames = self.load_surnames(filters_dir / "surnames.txt")
        self.pronouns = self.load_word_set(filters_dir / "pronouns.txt")
        self.non_person = self.load_word_set(filters_dir / "non_person.txt")
        self.trailing_stopwords = self.load_word_set(filters_dir / "trailing_stopwords.txt")
        self.blacklist = self.load_word_set(filters_dir / "blacklist.txt")
        self.common_dict = self.load_common_dict(data_dir / "common_dict.json")
        self.known_characters = self.load_character_dict(data_dir / "character_dict.json")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_resource_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/__init__.py character_scanner/resource_loader.py tests/test_resource_loader.py
git commit -m "feat(scanner): add ResourceLoader and unit tests"
```

---

### Task 2: BoundaryTrimmer

**Files:**
- Create: `character_scanner/boundary_trimmer.py`
- Test: `tests/test_boundary_trimmer.py`

**Interfaces:**
- Consumes: `trailing_stopwords: set[str]` from `ResourceLoader`
- Produces: `BoundaryTrimmer` class:
  - `trim(text: str) -> tuple[str, str]` (returns trimmed_name, removed_suffix)
  - `normalize_name(text: str) -> str` (returns TitleCased clean name)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_boundary_trimmer.py
from character_scanner.boundary_trimmer import BoundaryTrimmer

def test_trim_trailing_stopwords():
    stopwords = {"hai", "người", "thân", "con", "của"}
    trimmer = BoundaryTrimmer(stopwords)

    trimmed, suffix = trimmer.trim("Nguyễn mai hai")
    assert trimmed == "Nguyễn mai"
    assert suffix == "hai"

    trimmed, suffix = trimmer.trim("Ngọc Thiến thân")
    assert trimmed == "Ngọc Thiến"
    assert suffix == "thân"

def test_normalize_name():
    trimmer = BoundaryTrimmer(set())
    assert trimmer.normalize_name("lâm bằng tường") == "Lâm Bằng Tường"
    assert trimmer.normalize_name("Trương Tử Kiến") == "Trương Tử Kiến"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_boundary_trimmer.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/boundary_trimmer.py
import re

class BoundaryTrimmer:
    def __init__(self, trailing_stopwords: set[str]):
        self.trailing_stopwords = trailing_stopwords

    def trim(self, text: str) -> tuple[str, str]:
        words = text.strip().split()
        removed = []
        while len(words) > 1 and words[-1].lower() in self.trailing_stopwords:
            removed.insert(0, words.pop())
        return " ".join(words), " ".join(removed)

    def normalize_name(self, text: str) -> str:
        words = text.strip().split()
        return " ".join(w.capitalize() for w in words)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_boundary_trimmer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/boundary_trimmer.py tests/test_boundary_trimmer.py
git commit -m "feat(scanner): add BoundaryTrimmer and name normalization"
```

---

### Task 3: CandidateExtractor & Scorer

**Files:**
- Create: `character_scanner/candidate_extractor.py`
- Test: `tests/test_candidate_extractor.py`

**Interfaces:**
- Consumes: `ResourceLoader`, `BoundaryTrimmer`
- Produces: `CandidateMatch` dataclass:
  - `name: str`, `raw: str`, `start: int`, `end: int`, `confidence: float`, `reason: str`
- Produces: `CandidateExtractor` class:
  - `extract_candidates(line: str) -> list[CandidateMatch]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_candidate_extractor.py
from character_scanner.resource_loader import ResourceLoader
from character_scanner.boundary_trimmer import BoundaryTrimmer
from character_scanner.candidate_extractor import CandidateExtractor

def test_extract_profile_candidate():
    loader = ResourceLoader()
    loader.single_surnames = {"trương", "lâm", "mã"}
    trimmer = BoundaryTrimmer({"hai", "người", "thân"})
    extractor = CandidateExtractor(loader, trimmer)

    line = "Trương Tử Kiến, nam, 30 tuổi."
    candidates = extractor.extract_candidates(line)
    assert any(c.name == "Trương Tử Kiến" and c.confidence >= 0.5 for c in candidates)

def test_extract_lowercase_intro_candidate():
    loader = ResourceLoader()
    loader.single_surnames = {"lâm"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = "Lâm bằng tường, 53 tuổi, Nam Phương tỉnh tỉnh trưởng"
    candidates = extractor.extract_candidates(line)
    assert any(c.name == "Lâm Bằng Tường" for c in candidates)

def test_filter_non_person():
    loader = ResourceLoader()
    loader.single_surnames = {"hoàng"}
    loader.non_person = {"hoàng hà"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = "Sông Viêm là Hoàng Hà một cái tiểu nhánh sông"
    candidates = extractor.extract_candidates(line)
    assert not any(c.name.lower() == "hoàng hà" for c in candidates)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_candidate_extractor.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/candidate_extractor.py
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

    INTRO_CUES = {
        "nam", "nữ", "thiếu phụ", "mỹ phụ", "thiếu nữ", "cô gái", "thành thục"
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
            re.IGNORECASE
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
                re.IGNORECASE
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
        cap_pattern = re.compile(r'\b([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,3})\b')
        for m in cap_pattern.finditer(line):
            cand = m.group(1).strip()
            trimmed, _ = self.trimmer.trim(cand)
            if self._is_negative(trimmed):
                continue
            norm_name = self.trimmer.normalize_name(trimmed)
            if self._starts_with_surname(norm_name):
                # Check dialogue action
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
            cache_pattern = re.compile(rf'\b{re.escape(known)}\b', re.IGNORECASE)
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
        if len(low.split()) < 2 or len(low.split()) > 4:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_candidate_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/candidate_extractor.py tests/test_candidate_extractor.py
git commit -m "feat(scanner): add CandidateExtractor with scoring and filtering"
```

---

### Task 4: ContextExpander

**Files:**
- Create: `character_scanner/context_expander.py`
- Test: `tests/test_context_expander.py`

**Interfaces:**
- Produces: `ContextExpander` class:
  - `expand_context(line: str, match_start: int, match_end: int) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_context_expander.py
from character_scanner.context_expander import ContextExpander

def test_expand_full_sentence():
    expander = ContextExpander()
    line = "Sáng hôm sau, Trương Tử Kiến thức dậy. Hắn đi ra bờ sông ngắm cảnh."
    start = line.index("Trương Tử Kiến")
    end = start + len("Trương Tử Kiến")
    ctx = expander.expand_context(line, start, end)
    assert ctx == "Sáng hôm sau, Trương Tử Kiến thức dậy."

def test_expand_short_sentence():
    expander = ContextExpander(min_length=30)
    line = "Hắn tỉnh lại. Long Kiếm Phi thở dài một hơi. Trời lại đổ mưa."
    start = line.index("Long Kiếm Phi")
    end = start + len("Long Kiếm Phi")
    ctx = expander.expand_context(line, start, end)
    assert "Long Kiếm Phi thở dài một hơi." in ctx
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context_expander.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/context_expander.py
import re

class ContextExpander:
    def __init__(self, min_length: int = 30):
        self.min_length = min_length
        self.sentence_regex = re.compile(r'([^.!?;\n]+[.!?;\n]*)')

    def expand_context(self, line: str, match_start: int, match_end: int) -> str:
        line_clean = line.strip()
        if not line_clean:
            return ""

        matches = list(self.sentence_regex.finditer(line))
        if not matches:
            return line_clean

        target_idx = -1
        for i, m in enumerate(matches):
            if m.start() <= match_start and match_end <= m.end():
                target_idx = i
                break

        if target_idx == -1:
            return line_clean

        ctx = matches[target_idx].group(0).strip()
        # If too short, expand to previous or next sentence
        if len(ctx) < self.min_length:
            prev_s = matches[target_idx - 1].group(0).strip() if target_idx > 0 else ""
            next_s = matches[target_idx + 1].group(0).strip() if target_idx + 1 < len(matches) else ""
            if prev_s and next_s:
                ctx = f"{prev_s} {ctx} {next_s}"
            elif prev_s:
                ctx = f"{prev_s} {ctx}"
            elif next_s:
                ctx = f"{ctx} {next_s}"

        return ctx.strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_context_expander.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/context_expander.py tests/test_context_expander.py
git commit -m "feat(scanner): add ContextExpander for centered sentence contexts"
```

---

### Task 5: ScannerEngine & OutputPackager

**Files:**
- Create: `character_scanner/scanner_engine.py`
- Create: `character_scanner/output_packager.py`
- Test: `tests/test_output_packager.py`

**Interfaces:**
- Produces: `CharacterBlock` dataclass:
  - `id: str`, `source: str`, `target: str`, `context: str`, `dong_xuat_hien: int`, `confidence: float`, `yeu_to_nhan_biet: str`
- Produces: `ScannerEngine.scan_file(filepath: Path) -> list[CharacterBlock]`
- Produces: `OutputPackager.package(blocks: list[CharacterBlock], output_dir: Path, chunk_size: int = 40)`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_output_packager.py
from pathlib import Path
from character_scanner.scanner_engine import CharacterBlock
from character_scanner.output_packager import OutputPackager

def test_package_outputs(tmp_path):
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("--- PROMPT HUONG DAN ---", encoding="utf-8")
    out_dir = tmp_path / "scanner"

    blocks = [
        CharacterBlock(
            id=f"ch_{i:04d}",
            source=f"Nhân vật {i}",
            target=f"Nhân Vật {i}",
            context=f"Bối cảnh dòng {i}",
            dong_xuat_hien=i,
            confidence=0.85,
            yeu_to_nhan_biet="Thử nghiệm"
        )
        for i in range(1, 45)
    ]

    packager = OutputPackager(prompt_path=prompt_file)
    packager.package(blocks, output_dir=out_dir, chunk_size=30)

    assert (out_dir / "scanner_master.json").exists()
    assert (out_dir / "scanner_1.md").exists()
    assert (out_dir / "scanner_2.md").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_output_packager.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/scanner_engine.py
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

# character_scanner/output_packager.py
import json
from pathlib import Path
from character_scanner.scanner_engine import CharacterBlock

class OutputPackager:
    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path

    def package(self, blocks: list[CharacterBlock], output_dir: Path, chunk_size: int = 40):
        output_dir.mkdir(parents=True, exist_ok=True)
        # 1. Master JSON
        master_path = output_dir / "scanner_master.json"
        master_data = [b.to_dict() for b in blocks]
        master_path.write_text(json.dumps(master_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. Markdown Chunks with Prompt
        prompt_content = ""
        if self.prompt_path.exists():
            prompt_content = self.prompt_path.read_text(encoding="utf-8").strip()

        for chunk_idx, i in enumerate(range(0, len(blocks), chunk_size), start=1):
            chunk = blocks[i:i + chunk_size]
            md_path = output_dir / f"scanner_{chunk_idx}.md"
            
            chunk_payload = [
                {
                    "id": b.id,
                    "source": b.source,
                    "target": b.target,
                    "context": b.context,
                    "dong_xuat_hien": b.dong_xuat_hien
                }
                for b in chunk
            ]
            json_str = json.dumps(chunk_payload, ensure_ascii=False, indent=2)
            content = f"{prompt_content}\n\n```json\n{json_str}\n```\n"
            md_path.write_text(content, encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_output_packager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/scanner_engine.py character_scanner/output_packager.py tests/test_output_packager.py
git commit -m "feat(scanner): add ScannerEngine and OutputPackager"
```

---

### Task 6: Benchmark & CLI Runner

**Files:**
- Create: `character_scanner/benchmark.py`
- Create: `character_scanner/main.py`
- Test: `tests/test_benchmark.py`

**Interfaces:**
- Produces: `BenchmarkReport` comparing scanned blocks against `file_nhan_vat.json`.
- Produces: `main()` function accepting `--input exam.txt --output scanner/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_benchmark.py
from character_scanner.benchmark import Evaluator

def test_evaluator():
    ground_truth = [
        {"ten": "Trương Tử Kiến", "dong_xuat_hien": 9},
        {"ten": "Lâm Ngọc Chi", "dong_xuat_hien": 17}
    ]
    predictions = [
        {"target": "Trương Tử Kiến", "dong_xuat_hien": 9},
        {"target": "Người Khác", "dong_xuat_hien": 20}
    ]
    ev = Evaluator()
    metrics = ev.evaluate(predictions, ground_truth)
    assert metrics["matched"] == 1
    assert metrics["recall"] == 0.5
    assert metrics["precision"] == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmark.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/benchmark.py
import json
from pathlib import Path

class Evaluator:
    def evaluate(self, predictions: list[dict], ground_truth: list[dict]) -> dict:
        gt_set = {(item["ten"].lower().strip(), item["dong_xuat_hien"]) for item in ground_truth}
        gt_names = {item["ten"].lower().strip() for item in ground_truth}

        pred_set = {(p.get("target", "").lower().strip(), p.get("dong_xuat_hien")) for p in predictions}
        pred_names = {p.get("target", "").lower().strip() for p in predictions}

        # Exact match (name + line)
        matched_exact = len(gt_set.intersection(pred_set))
        # Name match across document
        matched_names = len(gt_names.intersection(pred_names))

        recall_exact = matched_exact / len(gt_set) if gt_set else 0.0
        recall_names = matched_names / len(gt_names) if gt_names else 0.0

        precision_exact = matched_exact / len(pred_set) if pred_set else 0.0
        precision_names = matched_names / len(pred_names) if pred_names else 0.0

        return {
            "total_ground_truth": len(gt_set),
            "total_predictions": len(pred_set),
            "matched_exact": matched_exact,
            "matched_names": matched_names,
            "recall_exact": round(recall_exact, 4),
            "recall_names": round(recall_names, 4),
            "precision_exact": round(precision_exact, 4),
            "precision_names": round(precision_names, 4)
        }

# character_scanner/main.py
import argparse
from pathlib import Path
import json
from character_scanner.resource_loader import ResourceLoader
from character_scanner.scanner_engine import ScannerEngine
from character_scanner.output_packager import OutputPackager
from character_scanner.benchmark import Evaluator

def main():
    parser = argparse.ArgumentParser(description="Quét và nhận diện tên nhân vật")
    parser.add_argument("--input", default="exam.txt", help="Đường dẫn file văn bản đầu vào")
    parser.add_argument("--output", default="scanner", help="Thư mục xuất kết quả")
    parser.add_argument("--prompt", default="prompt.md", help="File prompt mẫu")
    parser.add_argument("--ground-truth", default="file_nhan_vat.json", help="File đối chiếu ground truth")
    parser.add_argument("--chunk-size", type=int, default=40, help="Số block mỗi file md")
    args = parser.parse_args()

    base_dir = Path(".")
    print(f"[*] Nạp tài nguyên từ điển...")
    loader = ResourceLoader(base_dir)
    loader.load_all()

    print(f"[*] Bắt đầu quét file: {args.input}...")
    engine = ScannerEngine(loader)
    blocks = engine.scan_file(Path(args.input))
    print(f"[+] Tìm thấy tổng cộng: {len(blocks)} ứng viên nhân vật.")

    print(f"[*] Đóng gói xuất kết quả ra '{args.output}'...")
    packager = OutputPackager(Path(args.prompt))
    packager.package(blocks, Path(args.output), chunk_size=args.chunk_size)
    print(f"[+] Đã ghi '{args.output}/scanner_master.json' và các file markdown con thành công.")

    # Benchmark if ground truth exists
    gt_path = Path(args.ground_truth)
    if gt_path.exists():
        try:
            gt_data = json.loads(gt_path.read_text(encoding="utf-8")).get("file_nhan_vat", [])
            pred_data = [b.to_dict() for b in blocks]
            ev = Evaluator()
            metrics = ev.evaluate(pred_data, gt_data)
            print("\n=== KẾT QUẢ ĐÁNH GIÁ (BENCHMARK) ===")
            print(f"- Ground Truth: {metrics['total_ground_truth']} mục ({len(set(x['ten'].lower() for x in gt_data))} tên duy nhất)")
            print(f"- Trích xuất được: {metrics['total_predictions']} mục")
            print(f"- Khớp chính xác (Tên + Dòng): {metrics['matched_exact']} (Recall: {metrics['recall_exact']*100:.1f}%)")
            print(f"- Khớp tên nhân vật duy nhất: {metrics['matched_names']}/{len(set(x['ten'].lower() for x in gt_data))} (Recall: {metrics['recall_names']*100:.1f}%)")
        except Exception as e:
            print(f"[-] Lỗi khi đánh giá benchmark: {e}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_benchmark.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/benchmark.py character_scanner/main.py tests/test_benchmark.py
git commit -m "feat(scanner): add Evaluator benchmark and CLI main entrypoint"
```

---

### Task 7: Full System Verification on `exam.txt`

- [ ] **Step 1: Run all unit tests**
Run: `pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Run CLI scanner on `exam.txt`**
Run: `python -m character_scanner.main --input exam.txt --output scanner --ground-truth file_nhan_vat.json`
Expected: Scans successfully, generates `scanner/scanner_master.json` and `scanner/scanner_*.md`, outputs benchmark metrics.

- [ ] **Step 3: Verify output files**
Check that `scanner/scanner_1.md` contains valid markdown with `prompt.md` header and JSON array payload with `id`, `source`, `target`, `context`, `dong_xuat_hien`.

- [ ] **Step 4: Final commit**
```bash
git add .
git commit -m "feat: complete character scanner algorithm and generate scanner artifacts"
```
