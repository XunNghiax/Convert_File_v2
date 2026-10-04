# Kế hoạch Triển khai: Bộ lọc Nhiễu, Làm sạch Từ Rác và Khử Trùng Lặp Nâng Cao cho Scanner

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp toàn diện bộ trích xuất và khử trùng lặp của `src/scanner/` để triệt tiêu từ rác thông thường (dựa trên 31.061 từ ghép tiếng Việt 2 từ và từ chức năng ngữ pháp), bảo tồn tên viết thường hợp lệ, tách đúng động từ hành động đuôi theo họ đơn/họ kép, giữ nguyên các nhân vật khác tên chính, và loại bỏ nhân vật đã biết từ từ điển.

**Architecture:** 
1. `ResourceLoader` nạp đồng bộ `chinese_names_dict.json` và tập `vn_2word_set` từ `vietnamese_words.txt`.
2. `BoundaryTrimmer` được trang bị cơ chế nhận biết cấu trúc họ (đơn 1 chữ vs kép 2 chữ) để bóc tách chính xác động từ hành động đuôi (`trim_action_suffix`) và bóc tách hậu tố từ điển 2 từ (`trim_vn_compound_suffix`).
3. `CandidateExtractor` mở rộng `_is_negative()` để chặn các từ trong `vn_2word_set`, từ chức năng ngữ pháp ở giữa tên, và chuẩn hóa trích xuất tên viết thường.
4. `ScannerEngine` áp dụng luật bất biến tên chính (Given Name Invariant) trong `cluster_aliases` để không gộp các nhân vật khác tên chính (như `Tần Khả Cầm` vs `Tần Khả Phi`), bóc tách tiền tố rác đơn (`hoa Mã Lan` $\rightarrow$ `Mã Lan`), và đảm bảo streaming ghi `scanner_all.json` sạch sẽ.

**Tech Stack:** Python 3.10+, pytest, standard library (`re`, `pathlib`, `json`, `collections`).

## Global Constraints
- Phải bảo tồn khả năng nhận diện tên nhân vật viết thường (`tần khả cầm`, `tần khả phi`, `la mẫn`...).
- Chỉ lọc bỏ / kiểm tra từ điển tiếng Việt đối với các từ ghép 2 từ (`vn_2word_set`), tuyệt đối không lọc từ 1 từ vì trùng với họ và tên tiếng Việt.
- Quy tắc độ dài họ và tên:
  - Họ đơn (1 từ): tên người tối đa 3 từ; nếu từ thứ 4 là động từ hành động $\rightarrow$ cắt bỏ từ thứ 4.
  - Họ kép (2 từ): tên người tối đa 4 từ; nếu từ thứ 5 là động từ hành động $\rightarrow$ cắt bỏ từ thứ 5.
- Luật bất biến tên chính: Hai nhân vật có cùng họ nhưng khác từ cuối (tên chính) tuyệt đối không được gộp vào nhau.
- Không làm gãy bất kỳ bài kiểm thử nào trong số 106 tests hiện có của dự án.

---

### Task 1: Nâng cấp `ResourceLoader` để nạp `chinese_names_dict.json` và `vn_2word_set`

**Files:**
- Modify: `src/scanner/resource_loader.py:12-21, 102-121`
- Test: `tests/test_scanner_resource_loader.py`

**Interfaces:**
- Consumes: `resources/dictionaries/vietnamese_words.txt`, `resources/dictionaries/chinese_names_dict.json`
- Produces:
  - `ResourceLoader.vn_2word_set: set[str]` (tập hợp các từ ghép đúng 2 từ tiếng Việt viết thường)
  - `ResourceLoader.known_characters: dict[str, str]` (chứa cả nhân vật từ `character_dict.json` và `chinese_names_dict.json`, lưu cả source và target)
  - `ResourceLoader.load_vn_2word_set(path: Path) -> set[str]`

- [ ] **Step 1: Viết test kiểm tra nạp `vn_2word_set` và `chinese_names_dict.json`**

Tạo file `tests/test_scanner_resource_loader.py`:
```python
from pathlib import Path
import json
import pytest
from src.scanner.resource_loader import ResourceLoader

def test_load_vn_2word_set(tmp_path: Path):
    dict_file = tmp_path / "vietnamese_words.txt"
    dict_file.write_text(
        "hoa\n"              # 1 từ -> bỏ qua
        "xoáy thuận\n"       # 2 từ -> nhận
        "từ chối\n"          # 2 từ -> nhận
        "cổ kính\n"          # 2 từ -> nhận
        "bác sĩ gia đình\n"  # 3 từ -> bỏ qua
        "# ghi chú\n"        # comment -> bỏ qua
        "\n",
        encoding="utf-8"
    )
    loader = ResourceLoader(base_dir=tmp_path)
    words = loader.load_vn_2word_set(dict_file)
    
    assert "xoáy thuận" in words
    assert "từ chối" in words
    assert "cổ kính" in words
    assert "hoa" not in words
    assert "bác sĩ gia đình" not in words
    assert len(words) == 3

def test_load_all_includes_chinese_names_and_vn_2word(tmp_path: Path):
    resources_dir = tmp_path / "resources"
    dict_dir = resources_dir / "dictionaries"
    filters_dir = resources_dir / "filters"
    dict_dir.mkdir(parents=True)
    filters_dir.mkdir(parents=True)

    (filters_dir / "surnames.txt").write_text("tần\nâu dương\n", encoding="utf-8")
    (dict_dir / "character_dict.json").write_text(json.dumps({"Tiêu Viêm": "Tiêu Viêm"}), encoding="utf-8")
    (dict_dir / "chinese_names_dict.json").write_text(json.dumps({"Dược Lão": "Dược Lão"}), encoding="utf-8")
    (dict_dir / "vietnamese_words.txt").write_text("xoáy thuận\nhoa\n", encoding="utf-8")

    loader = ResourceLoader(base_dir=tmp_path)
    loader.load_all()

    assert "tiêu viêm" in loader.known_characters
    assert "dược lão" in loader.known_characters
    assert "xoáy thuận" in loader.vn_2word_set
    assert "hoa" not in loader.vn_2word_set
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `pytest tests/test_scanner_resource_loader.py -v`
Expected: FAIL với lỗi `AttributeError: 'ResourceLoader' object has no attribute 'load_vn_2word_set'` hoặc `vn_2word_set`

- [ ] **Step 3: Cập nhật `src/scanner/resource_loader.py`**

Thêm thuộc tính `self.vn_2word_set`, hàm `load_vn_2word_set`, và cập nhật `load_all()`:
```python
    def __init__(self, base_dir: Path | None = None):
        # Giữ nguyên code cũ và thêm:
        self.vn_2word_set: set[str] = set()

    def load_vn_2word_set(self, path: Path) -> set[str]:
        words = set()
        if not path.exists():
            return words
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) == 2:
                        words.add(line)
        except Exception:
            pass
        return words
```
Trong `load_all(self)`:
```python
        # Nạp character_dict và chinese_names_dict
        self.known_characters = self.load_character_dict(data_dir / "character_dict.json")
        chinese_names = self.load_character_dict(data_dir / "chinese_names_dict.json")
        self.known_characters.update(chinese_names)

        # Nạp từ ghép 2 từ tiếng Việt
        vn_words_path = data_dir / "vietnamese_words.txt"
        if not vn_words_path.exists():
            vn_words_path = self.base_dir / "resources" / "dictionaries" / "vietnamese_words.txt"
        self.vn_2word_set = self.load_vn_2word_set(vn_words_path)
```

- [ ] **Step 4: Chạy test để xác nhận test thành công**

Run: `pytest tests/test_scanner_resource_loader.py -v`
Expected: PASS

- [ ] **Step 5: Chạy lại toàn bộ test suite để kiểm tra tính hồi quy**

Run: `pytest tests/test_resource_loader.py -v`
Expected: PASS

- [ ] **Step 6: Commit code Task 1**

```bash
git add src/scanner/resource_loader.py tests/test_scanner_resource_loader.py
git commit -m "feat(scanner): add vn_2word_set and chinese_names_dict loading to ResourceLoader"
```

---

### Task 2: Nâng cấp `BoundaryTrimmer` với khả năng nhận diện họ đơn/họ kép để bóc tách động từ và hậu tố từ điển

**Files:**
- Modify: `src/scanner/boundary_trimmer.py:35-163`
- Test: `tests/test_scanner_boundary_trimmer.py`

**Interfaces:**
- Consumes: `text: str`, `vn_2word_set: set[str] | None`
- Produces:
  - `BoundaryTrimmer.SINGLE_ACTION_VERBS: set[str]`
  - `BoundaryTrimmer.trim_action_suffix(text: str) -> tuple[str, str]`
  - `BoundaryTrimmer.trim_vn_compound_suffix(text: str, vn_2word_set: set[str]) -> tuple[str, str]`
  - `BoundaryTrimmer.clean_candidate(text: str, vn_2word_set: set[str] | None = None) -> str`

- [ ] **Step 1: Viết test cho `trim_action_suffix` và `trim_vn_compound_suffix`**

Tạo file `tests/test_scanner_boundary_trimmer.py`:
```python
import pytest
from src.scanner.boundary_trimmer import BoundaryTrimmer

def test_trim_action_suffix_single_surname():
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames={"tần", "trần", "lâm"})
    
    # Họ đơn + 2 từ tên + 1 động từ hành động = 4 từ -> Cắt động từ
    trimmed, removed = trimmer.trim_action_suffix("tần khả cầm đi")
    assert trimmed == "tần khả cầm"
    assert removed == "đi"

    trimmed, removed = trimmer.trim_action_suffix("tần khả phi thở")
    assert trimmed == "tần khả phi"
    assert removed == "thở"

    # Họ đơn + 2 từ tên (không có động từ thừa) -> Không cắt
    trimmed, removed = trimmer.trim_action_suffix("tần khả cầm")
    assert trimmed == "tần khả cầm"
    assert removed == ""

    # Họ đơn + từ cuối nằm trong PROTECTED_NAME_WORDS (vd: y, lan, ngọc) -> Không cắt
    trimmed, removed = trimmer.trim_action_suffix("tần khả lan")
    assert trimmed == "tần khả lan"
    assert removed == ""

def test_trim_action_suffix_compound_surname():
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames={"âu dương", "thượng quan"})
    
    # Họ kép + 2 từ tên + 1 động từ = 5 từ -> Cắt động từ
    trimmed, removed = trimmer.trim_action_suffix("âu dương như tuyết đi")
    assert trimmed == "âu dương như tuyết"
    assert removed == "đi"

    # Họ kép + 2 từ tên = 4 từ -> Không cắt
    trimmed, removed = trimmer.trim_action_suffix("âu dương như tuyết")
    assert trimmed == "âu dương như tuyết"
    assert removed == ""

def test_trim_vn_compound_suffix():
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames={"vũ", "trần"})
    vn_2word = {"vương phi", "chủ tịch", "bác sĩ"}

    # 4 từ, kết thúc bằng "vương phi" -> Cắt còn "vũ mỹ"
    trimmed, removed = trimmer.trim_vn_compound_suffix("vũ mỹ vương phi", vn_2word)
    assert trimmed == "vũ mỹ"
    assert removed == "vương phi"

    # Tên chỉ có 2 từ ("vũ mỹ") -> Không cắt dù có trong từ điển hay không
    trimmed, removed = trimmer.trim_vn_compound_suffix("vũ mỹ", vn_2word)
    assert trimmed == "vũ mỹ"
    assert removed == ""
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `pytest tests/test_scanner_boundary_trimmer.py -v`
Expected: FAIL với lỗi `AttributeError: 'BoundaryTrimmer' object has no attribute 'trim_action_suffix'`

- [ ] **Step 3: Triển khai các phương thức trong `src/scanner/boundary_trimmer.py`**

Thêm hằng số `SINGLE_ACTION_VERBS` và các phương thức vào lớp `BoundaryTrimmer`:
```python
    SINGLE_ACTION_VERBS = {
        "đi", "thở", "nói", "hỏi", "cười", "quát", "nghĩ", "nhìn", "bước",
        "chạy", "ngồi", "đứng", "ôm", "hôn", "đáp", "kêu", "hét", "lẩm",
        "bẩm", "gật", "lắc", "la", "nhăn", "nháy", "trừng", "liếc"
    }

    def is_compound_surname(self, words: list[str]) -> bool:
        if len(words) >= 2:
            return f"{words[0]} {words[1]}".lower() in self.surnames
        return False

    def trim_action_suffix(self, text: str) -> tuple[str, str]:
        words = text.strip().split()
        if len(words) < 3:
            return text.strip(), ""

        last_word_low = words[-1].lower()
        if last_word_low in self.PROTECTED_NAME_WORDS:
            return text.strip(), ""

        if last_word_low in self.SINGLE_ACTION_VERBS:
            # Trường hợp họ kép: độ dài tiêu chuẩn là 4 từ (2 họ + 2 tên).
            # Nếu có 5 từ trở lên và từ cuối là động từ hành động -> cắt.
            if self.is_compound_surname(words) and len(words) >= 5:
                removed = words.pop()
                return " ".join(words), removed
            # Trường hợp họ đơn: độ dài tiêu chuẩn là 3 từ (1 họ + 2 tên).
            # Nếu có 4 từ trở lên và từ cuối là động từ hành động -> cắt.
            elif not self.is_compound_surname(words) and self.starts_with_surname(words) and len(words) >= 4:
                removed = words.pop()
                return " ".join(words), removed

        return text.strip(), ""

    def trim_vn_compound_suffix(self, text: str, vn_2word_set: set[str]) -> tuple[str, str]:
        words = text.strip().split()
        if len(words) >= 4 and vn_2word_set:
            tail_compound = f"{words[-2]} {words[-1]}".lower()
            if tail_compound in vn_2word_set:
                remaining_words = words[:-2]
                if len(remaining_words) >= 2 and self.starts_with_surname(remaining_words):
                    return " ".join(remaining_words), tail_compound
        return text.strip(), ""

    def clean_candidate(self, text: str, vn_2word_set: set[str] | None = None) -> str:
        s, _ = self.trim(text)
        s, _ = self.trim_action_suffix(s)
        if vn_2word_set:
            s, _ = self.trim_vn_compound_suffix(s, vn_2word_set)
        return s
```

- [ ] **Step 4: Chạy test để xác nhận test vừa viết thành công**

Run: `pytest tests/test_scanner_boundary_trimmer.py -v`
Expected: PASS

- [ ] **Step 5: Chạy lại toàn bộ test suite để kiểm tra tính hồi quy**

Run: `pytest tests/ -k "trimmer or extractor" -v`
Expected: PASS

- [ ] **Step 6: Commit code Task 2**

```bash
git add src/scanner/boundary_trimmer.py tests/test_scanner_boundary_trimmer.py
git commit -m "feat(scanner): add surname-aware action verb trimming and vn compound suffix trimming to BoundaryTrimmer"
```

---

### Task 3: Nâng cấp `CandidateExtractor` (Loại bỏ từ rác `vn_2word_set`, từ ngữ pháp, trích xuất chuẩn tên viết thường)

**Files:**
- Modify: `src/scanner/candidate_extractor.py:517-618`
- Test: `tests/test_candidate_extractor_noise.py`

**Interfaces:**
- Consumes: `ResourceLoader.vn_2word_set`, `ResourceLoader.known_characters`, `ResourceLoader.common_dict`
- Produces:
  - `CandidateExtractor._is_negative(text: str, skip_known: bool = False) -> bool` (lọc bỏ triệt để từ điển tiếng Việt 2 từ và từ chức năng ngữ pháp)
  - `CandidateExtractor._extract_lowercase_action_candidates(line: str, skip_known: bool = False) -> list[CandidateMatch]` (trích xuất chuẩn xác, tự động bóc tách động từ đuôi)

- [ ] **Step 1: Viết test cho `_is_negative` và trích xuất tên viết thường có kèm động từ**

Tạo file `tests/test_candidate_extractor_noise.py`:
```python
import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.boundary_trimmer import BoundaryTrimmer
from src.scanner.candidate_extractor import CandidateExtractor

@pytest.fixture
def extractor():
    loader = ResourceLoader()
    loader.single_surnames = {"tần", "trần", "lâm", "đường", "hoa", "vũ"}
    loader.compound_surnames = {"âu dương"}
    loader.known_characters = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    loader.common_dict = {"không có": "không có"}
    loader.vn_2word_set = {"xoáy thuận", "từ chối", "cổ kính", "vương phi", "phương tâm"}
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames=loader.single_surnames | loader.compound_surnames)
    return CandidateExtractor(loader=loader, trimmer=trimmer, skip_known=True)

def test_is_negative_rejects_vn_2word_set(extractor):
    # Các từ ghép 2 từ tiếng Việt thông thường phải bị từ chối 100%
    assert extractor._is_negative("xoáy thuận") is True
    assert extractor._is_negative("từ chối") is True
    assert extractor._is_negative("cổ kính") is True
    assert extractor._is_negative("phương tâm") is True

def test_is_negative_rejects_grammar_connectors(extractor):
    # Cụm chứa từ chức năng ngữ pháp ở giữa tên phải bị loại
    assert extractor._is_negative("đường có mỹ nữ") is True
    assert extractor._is_negative("lâm lại chạy") is True
    assert extractor._is_negative("trần được cứu") is True

def test_is_negative_rejects_known_characters_when_skip_known(extractor):
    assert extractor._is_negative("Tiêu Viêm", skip_known=True) is True
    assert extractor._is_negative("tiêu viêm", skip_known=True) is True
    assert extractor._is_negative("Dược Lão", skip_known=True) is True

def test_is_negative_accepts_valid_names(extractor):
    # Tên nhân vật hợp lệ không nằm trong từ điển rác
    assert extractor._is_negative("tần khả cầm") is False
    assert extractor._is_negative("tần khả phi") is False
    assert extractor._is_negative("âu dương như tuyết") is False

def test_extract_lowercase_action_candidates_trims_verb(extractor):
    line = "tần khả cầm đi tới phòng khách, tần khả phi thở dài một tiếng."
    matches = extractor._extract_lowercase_action_candidates(line, skip_known=True)
    names = [m.name for m in matches]
    
    assert "Tần Khả Cầm" in names
    assert "Tần Khả Phi" in names
    assert not any("Đi" in n for n in names)
    assert not any("Thở" in n for n in names)
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `pytest tests/test_candidate_extractor_noise.py -v`
Expected: FAIL vì `_is_negative` hiện tại chưa kiểm tra `vn_2word_set` và chưa bóc tách `đi`/`thở` khi trích xuất.

- [ ] **Step 3: Triển khai logic lọc nhiễu trong `src/scanner/candidate_extractor.py`**

Định nghĩa hằng số từ chức năng ngữ pháp:
```python
    INTERNAL_GRAMMAR_STOPWORDS = {
        "có", "của", "được", "bị", "đang", "đã", "sẽ", "lại", "rất",
        "quá", "nhiều", "một", "hai", "ba", "cái", "thì", "mà", "là"
    }
```

Cập nhật `_is_negative(self, text: str, skip_known: bool = False) -> bool`:
```python
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
        if len(words) == 2 and low in vn_words:
            return True

        # 3. Kiểm tra từ chức năng ngữ pháp ở giữa tên
        surname_len = 2 if (len(words) >= 2 and f"{words[0]} {words[1]}" in self.loader.compound_surnames) else 1
        given_words = words[surname_len:]
        if any(gw in self.INTERNAL_GRAMMAR_STOPWORDS for gw in given_words):
            return True

        if low in self.loader.pronouns or low in self.loader.non_person:
            return True
        if low in self.loader.blacklist or low in self.loader.common_dict:
            return True
        if any(b in low for b in self.loader.blacklist):
            return True

        if clean and clean[0].islower() and not self._starts_with_surname(clean) and (
            words[0] in self.loader.pronouns or 
            words[0] in self.trimmer.DEFAULT_TRAILING or
            words[0] in self.trimmer.DEFAULT_LEADING
        ):
            return True

        if not is_foreign and (words[-1] in self.trimmer.DEFAULT_TRAILING or words[-1] in self.trimmer.DEFAULT_LEADING):
            return True

        return False
```

Cập nhật `_extract_lowercase_action_candidates(self, line: str, skip_known: bool = False)`:
Bổ sung bước chạy qua `self.trimmer.trim_action_suffix()` trên `cand_raw` và kiểm tra lại `_is_negative()` trước khi thêm vào kết quả.
Đồng thời trong `extract_candidates()`, tại các khối regex (profile, anchor, dialogue, capitalized title-case), áp dụng `self.trimmer.clean_candidate(cand, vn_2word_set)` để loại bỏ triệt để động từ hành động hoặc từ ghép rác dính đuôi.

- [ ] **Step 4: Chạy test để xác nhận test thành công**

Run: `pytest tests/test_candidate_extractor_noise.py -v`
Expected: PASS

- [ ] **Step 5: Chạy lại toàn bộ test suite để đảm bảo 106 tests cũ không bị ảnh hưởng**

Run: `pytest tests/test_candidate_extractor_greedy.py tests/test_candidate_extractor_precision.py -v`
Expected: PASS

- [ ] **Step 6: Commit code Task 3**

```bash
git add src/scanner/candidate_extractor.py tests/test_candidate_extractor_noise.py
git commit -m "feat(scanner): add vn_2word_set rejection and grammar stopword filtering to CandidateExtractor"
```

---

### Task 4: Nâng cấp `ScannerEngine` (Giữ nguyên nhân vật khác tên chính, bóc tách tiền tố đơn, khử trùng lặp an toàn)

**Files:**
- Modify: `src/scanner/scanner_engine.py:473-580, 329-472`
- Test: `tests/test_scanner_safe_dedup.py`

**Interfaces:**
- Consumes: `CharacterBlock` list from scan
- Produces:
  - `ScannerEngine.cluster_aliases(blocks: list[CharacterBlock]) -> list[CharacterBlock]`
  - Given Name Invariant: Không gộp `Tần Khả Cầm` và `Tần Khả Phi`
  - Prefix Stripping: Gộp `hoa Mã Lan` vào `Mã Lan` nếu `Mã Lan` đã tồn tại
  - TitleCase Unification: Gộp `tần khả cầm` vào `Tần Khả Cầm`

- [ ] **Step 1: Viết test cho các trường hợp khử trùng lặp an toàn**

Tạo file `tests/test_scanner_safe_dedup.py`:
```python
import pytest
from src.scanner.scanner_engine import ScannerEngine, CharacterBlock

def test_different_given_names_are_never_merged():
    engine = ScannerEngine()
    b1 = CharacterBlock(
        id="ch_0001",
        source="tần khả cầm",
        target="Tần Khả Cầm",
        context="Tần Khả Cầm bước vào phòng.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=5,
        cac_dong_xuat_hien=[1, 2]
    )
    b2 = CharacterBlock(
        id="ch_0002",
        source="tần khả phi",
        target="Tần Khả Phi",
        context="Tần Khả Phi mỉm cười.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=4,
        cac_dong_xuat_hien=[3, 4]
    )

    result = engine.cluster_aliases([b1, b2])
    targets = [b.target for b in result]

    # Cả hai nhân vật phải được giữ lại riêng biệt, KHÔNG bị gộp
    assert len(result) == 2
    assert "Tần Khả Cầm" in targets
    assert "Tần Khả Phi" in targets

def test_merge_lowercase_into_titlecase():
    engine = ScannerEngine()
    b1 = CharacterBlock(
        id="ch_0001",
        source="Tần Khả Cầm",
        target="Tần Khả Cầm",
        context="Tần Khả Cầm bước vào phòng.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=5,
        cac_dong_xuat_hien=[1, 5]
    )
    b2 = CharacterBlock(
        id="ch_0002",
        source="tần khả cầm",
        target="tần khả cầm",
        context="tần khả cầm nói nhỏ.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=2,
        cac_dong_xuat_hien=[10]
    )

    result = engine.cluster_aliases([b1, b2])
    assert len(result) == 1
    assert result[0].target == "Tần Khả Cầm"
    assert result[0].so_lan_xuat_hien == 7
    assert 10 in result[0].cac_dong_xuat_hien

def test_prefix_stripping_single_word_noise():
    engine = ScannerEngine()
    b_main = CharacterBlock(
        id="ch_0001",
        source="Mã Lan",
        target="Mã Lan",
        context="Mã Lan xuất hiện.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=10,
        cac_dong_xuat_hien=[1, 2, 3]
    )
    b_noise = CharacterBlock(
        id="ch_0002",
        source="hoa Mã Lan",
        target="Hoa Mã Lan",
        context="hoa Mã Lan đang đi.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=1,
        cac_dong_xuat_hien=[15]
    )

    result = engine.cluster_aliases([b_main, b_noise])
    targets = [b.target for b in result]
    assert len(result) == 1
    assert result[0].target == "Mã Lan"
    assert result[0].so_lan_xuat_hien == 11
    assert 15 in result[0].cac_dong_xuat_hien
```

- [ ] **Step 2: Chạy test để xác nhận kiểm tra**

Run: `pytest tests/test_scanner_safe_dedup.py -v`
Expected: FAIL hoặc PASS phụ thuộc vào tính năng prefix stripping và titlecase normalization.

- [ ] **Step 3: Cập nhật `cluster_aliases` trong `src/scanner/scanner_engine.py`**

1. Thêm bước TitleCase chuẩn hóa ban đầu trước khi nhóm theo key:
```python
        # Chuẩn hóa target về TitleCase nếu đang viết thường hoàn toàn
        for b in blocks:
            words = b.target.strip().split()
            if words and all(w.islower() for w in words):
                b.target = " ".join(w.capitalize() for w in words)
```
2. Trong phần `Super-string Consolidation`:
Đảm bảo hai tên chỉ được gộp khi:
- Tên ngắn là tiền tố chính xác của tên dài VÀ
- Tên ngắn có $\le 2$ từ VÀ
- Không có sự xung đột giữa 2 tên cùng độ dài có cùng tiền tố nhưng khác tên chính cuối cùng (ví dụ `Tần Khả Cầm` và `Tần Khả Phi`).
3. Thêm bước bóc tách tiền tố đơn (`Prefix Stripping`):
```python
        # 2b. Prefix Stripping: Gộp các khối dính 1 từ rác ở đầu vào tên chuẩn đã có
        # Ví dụ: "Hoa Mã Lan" (3 từ) khi đã có "Mã Lan" (2 từ, tần suất cao)
        for target_low, b in list(full_name_blocks.items()):
            if target_low in to_remove:
                continue
            words_b = b.target.strip().split()
            if len(words_b) >= 3:
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
```
4. Đảm bảo dữ liệu ghi vào `realtime_all_path` (`scanner_all.json`) được lọc qua `_is_negative` và loại bỏ các khối rác trước khi xuất.

- [ ] **Step 4: Chạy test để xác nhận test Task 4 thành công**

Run: `pytest tests/test_scanner_safe_dedup.py -v`
Expected: PASS

- [ ] **Step 5: Chạy lại toàn bộ test suite để đảm bảo không lỗi**

Run: `pytest tests/test_deduplication.py tests/test_scanner_engine_superstring.py -v`
Expected: PASS

- [ ] **Step 6: Commit code Task 4**

```bash
git add src/scanner/scanner_engine.py tests/test_scanner_safe_dedup.py
git commit -m "feat(scanner): add given name invariant, titlecase unification, and prefix stripping to cluster_aliases"
```

---

### Task 5: Kiểm thử Tích hợp Toàn diện (E2E Integration Test) và Xác minh Toàn bộ Dự án

**Files:**
- Create: `tests/test_scanner_noise_and_dedup_e2e.py`
- Test: Toàn bộ test suite `pytest`

**Interfaces:**
- Consumes: Mẫu văn bản hoàn chỉnh chứa đầy đủ các trường hợp người dùng đặt ra
- Produces: Kết quả trích xuất sạch, 0 từ rác từ `vn_2word_set`, giữ trọn vẹn 2 nhân vật cùng họ, nhận diện chuẩn họ kép 2 chữ và tên 4 chữ

- [ ] **Step 1: Viết test E2E kiểm tra toàn bộ chu trình với đầy đủ các ca góc**

Tạo file `tests/test_scanner_noise_and_dedup_e2e.py`:
```python
from pathlib import Path
import json
import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine

def test_scanner_noise_filtering_and_dedup_e2e(tmp_path: Path):
    # Chuẩn bị dữ liệu mẫu
    resources_dir = tmp_path / "resources"
    dict_dir = resources_dir / "dictionaries"
    filters_dir = resources_dir / "filters"
    dict_dir.mkdir(parents=True)
    filters_dir.mkdir(parents=True)

    (filters_dir / "surnames.txt").write_text("tần\nâu dương\ntrần\n", encoding="utf-8")
    (dict_dir / "character_dict.json").write_text(json.dumps({"Tiêu Viêm": "Tiêu Viêm"}), encoding="utf-8")
    (dict_dir / "chinese_names_dict.json").write_text(json.dumps({"Hàn Lập": "Hàn Lập"}), encoding="utf-8")
    (dict_dir / "vietnamese_words.txt").write_text("xoáy thuận\ntừ chối\ncổ kính\nvương phi\n", encoding="utf-8")

    sample_text = (
        "Trong căn phòng có một hiện tượng xoáy thuận kỳ lạ. Cổ kính phản chiếu ánh trăng.\n"
        "tần khả cầm đi tới chiếc bàn, khẽ mỉm cười.\n"
        "tần khả phi thở dài một hơi rồi ngồi xuống bên cạnh.\n"
        "âu dương như tuyết đi vào với vẻ mặt lạnh lùng.\n"
        "trần ngọc ánh tuyết cười nói vui vẻ cùng mọi người.\n"
        "Tiêu Viêm và Hàn Lập cũng đứng ở đằng xa quan sát.\n"
    )

    test_file = tmp_path / "test_novel.txt"
    test_file.write_text(sample_text, encoding="utf-8")

    loader = ResourceLoader(base_dir=tmp_path)
    loader.load_all()

    engine = ScannerEngine(loader=loader, skip_known=True)
    results = engine.scan_file(test_file, deduplicate=True, show_progress=False)
    targets = [b.target for b in results]

    # 1. Từ rác 2 từ trong từ điển tiếng Việt PHẢI BỊ LOẠI BỎ
    assert "Xoáy Thuận" not in targets
    assert "Cổ Kính" not in targets
    assert "Từ Chối" not in targets

    # 2. Nhân vật đã biết trong character_dict và chinese_names_dict PHẢI BỊ BỎ QUA khi skip_known=True
    assert "Tiêu Viêm" not in targets
    assert "Hàn Lập" not in targets

    # 3. Hai nhân vật cùng họ dính động từ đuôi phải được bóc tách và giữ riêng biệt
    assert "Tần Khả Cầm" in targets
    assert "Tần Khả Phi" in targets
    assert not any("Đi" in t for t in targets)
    assert not any("Thở" in t for t in targets)

    # 4. Họ kép 2 chữ (Âu Dương) và Tên 4 chữ (Trần Ngọc Ánh Tuyết) trích xuất chính xác
    assert "Âu Dương Như Tuyết" in targets
    assert "Trần Ngọc Ánh Tuyết" in targets
```

- [ ] **Step 2: Chạy test E2E để kiểm tra toàn bộ pipeline**

Run: `pytest tests/test_scanner_noise_and_dedup_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Chạy toàn bộ 106 tests cũ + toàn bộ tests mới**

Run: `pytest -v`
Expected: 100% tests PASS (không có bất kỳ failure hoặc regression nào).

- [ ] **Step 4: Chạy thử nghiệm quét thực tế trên file `samples/exam.txt` nếu có**

Run:
```bash
python -c "
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine
from pathlib import Path

loader = ResourceLoader()
loader.load_all()
engine = ScannerEngine(loader=loader, skip_known=True)
sample = Path('samples/exam.txt')
if sample.exists():
    res = engine.scan_file(sample, deduplicate=True, show_progress=True)
    print(f'Tong so nhan vat sach tim thay: {len(res)}')
    for b in res[:10]:
        print(f' - {b.target} (xuat hien {b.so_lan_xuat_hien} lan)')
"
```
Expected: Quét thành công, hiển thị các nhân vật sạch sẽ, không dính các từ như "xoáy thuận", "cổ kính"...

- [ ] **Step 5: Commit code Task 5**

```bash
git add tests/test_scanner_noise_and_dedup_e2e.py
git commit -m "test(scanner): add comprehensive end-to-end integration tests for noise filtering and dedup"
```
