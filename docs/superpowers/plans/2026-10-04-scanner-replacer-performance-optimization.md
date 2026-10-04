# Kế hoạch Triển khai Tăng tốc Thuật toán Scan và Replace (Giai đoạn 1 & Giai đoạn 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tăng tốc thuật toán Scan (lên 18.000 – 45.000 dòng/s, tăng 4x - 8x) và thuật toán Replace (lên 30.000 – 100.000 dòng/s, tăng 6x - 20x) thông qua cấu trúc dữ liệu Trie/Aho-Corasick zero-dependency, Fast-path line screening, I/O buffer theo khối, và xử lý song song đa tiến trình (Multiprocessing) chia chunk an toàn, đảm bảo kết quả đầu ra giống 100% (Bit-for-bit Parity).

**Architecture:** 
1. **Module Cấu trúc Dữ liệu `TrieMatcher`**: Cung cấp cây tiền tố Trie đa mẫu thuần Python siêu nhanh (Zero external dependency), tìm kiếm tất cả từ khóa trong văn bản với độ phức tạp $O(N)$ thay vì duyệt tuần tự từ điển $O(D \times L)$.
2. **Giai đoạn 1 (Thuật toán & I/O)**:
   - Trong `CandidateExtractor`: Tích hợp `TrieMatcher` cho `known_characters` & `deconvert_dict`; biên dịch 61 `LOWERCASE_ACTION_TERMS` thành 1 Regex Trie duy nhất; bổ sung Fast-path line screening để bỏ qua sớm 40-50% số dòng không chứa dấu hiệu tên người.
   - Trong `ReplaceEngine`: Tối ưu I/O đọc ghi dạng Chunk Buffer (64KB - 1MB), loại bỏ đếm dòng 2 lần, tăng tốc thay thế chuỗi.
3. **Giai đoạn 2 (Xử lý Song song Đa tiến trình)**:
   - Module `chunk_splitter.py`: Chia file văn bản thành các phân đoạn an toàn (căn chỉnh theo ranh giới dòng `\n`).
   - `ScannerEngine`: Hỗ trợ tham số `workers=int` (mặc định số core CPU khi kích hoạt song song), chạy song song các chunk và gộp kết quả `CharacterBlock` trước khi chạy `cluster_aliases`.
   - `ReplaceEngine`: Hỗ trợ tham số `workers=int`, các workers xử lý độc lập từng chunk ra file tạm và ghép nhị phân nguyên tử (Atomic Binary Concat).

**Tech Stack:** Python 3.10+, `multiprocessing`, `concurrent.futures`, `re`, `pathlib`, `io`, `pytest`.

## Global Constraints
- **Bảo toàn Độ chính xác 100% (Mathematical Equivalence)**: Kết quả trích xuất của Scan và kết quả thay thế của Replace phải hoàn toàn giống hệt thuật toán hiện tại trên mọi file văn bản.
- **Không phụ thuộc thư viện C ngoài bắt buộc (Zero-dependency core)**: Cấu trúc TrieMatcher viết bằng Python chuẩn, sẵn sàng chạy mượt mà trên mọi hệ điều hành (Windows, Linux, macOS) mà không cần cài thêm trình biên dịch C/C++.
- **An toàn Ranh giới Dòng (Chunk Boundary Safety)**: Khi chia file để chạy song song đa tiến trình, ranh giới giữa các chunk bắt buộc phải nằm tại ký tự xuống dòng `\n`, tuyệt đối không cắt ngang câu/dòng.
- **Không hồi quy**: Đảm bảo 100% trong số 124 unit tests hiện có tiếp tục vượt qua.

---

### Task 1: Xây dựng Module `TrieMatcher` Đa Mẫu Thuần Python (Zero-dependency)

**Files:**
- Create: `src/utils/trie_matcher.py`
- Test: `tests/test_trie_matcher.py`

**Interfaces:**
- Consumes: `dict[str, str]` (từ khóa nguồn -> giá trị thay thế hoặc metadata)
- Produces:
  - `class TrieMatcher`:
    - `add_keyword(keyword: str, value: str = "") -> None`
    - `build() -> None`
    - `find_matches(text: str) -> list[tuple[int, int, str, str]]` (start, end, keyword, value)
    - `replace_all(text: str) -> str` (thay thế Longest-Match-First chuẩn xác)

- [ ] **Step 1: Viết test cho `TrieMatcher`**

Tạo file `tests/test_trie_matcher.py`:
```python
import pytest
from src.utils.trie_matcher import TrieMatcher

def test_trie_matcher_basic_find():
    matcher = TrieMatcher()
    matcher.add_keyword("tiêu viêm", "Tiêu Viêm")
    matcher.add_keyword("dược lão", "Dược Lão")
    matcher.build()

    text = "Hôm nay tiêu viêm gặp dược lão tại sơn cốc."
    matches = matcher.find_matches(text.lower())
    
    assert len(matches) == 2
    assert matches[0] == (8, 17, "tiêu viêm", "Tiêu Viêm")
    assert matches[1] == (22, 30, "dược lão", "Dược Lão")

def test_trie_matcher_longest_match_first():
    matcher = TrieMatcher()
    matcher.add_keyword("hàn lập", "Hàn Lập")
    matcher.add_keyword("hàn lập sư huynh", "Hàn Lập Sư Huynh")
    matcher.build()

    text = "hàn lập sư huynh đi vào."
    matches = matcher.find_matches(text.lower())
    
    # Phải ưu tiên chuỗi dài nhất "hàn lập sư huynh"
    assert len(matches) == 1
    assert matches[0][2] == "hàn lập sư huynh"

def test_trie_matcher_replace_all():
    matcher = TrieMatcher()
    matcher.add_keyword("tiêu viêm", "Tiêu Viêm")
    matcher.add_keyword("lão sư", "Thầy giáo")
    matcher.build()

    text = "tiêu viêm chào lão sư của hắn."
    replaced = matcher.replace_all(text.lower())
    assert replaced == "Tiêu Viêm chào Thầy giáo của hắn."
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `pytest tests/test_trie_matcher.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'src.utils.trie_matcher'`

- [ ] **Step 3: Triển khai `src/utils/trie_matcher.py`**

Tạo file `src/utils/trie_matcher.py`:
```python
from typing import Dict, List, Tuple, Optional

class TrieNode:
    __slots__ = ('children', 'is_end', 'keyword', 'value')
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_end: bool = False
        self.keyword: str = ""
        self.value: str = ""

class TrieMatcher:
    """
    Bộ so khớp đa chuỗi hiệu năng cao dựa trên Trie (Longest-Match-First):
    - Độ phức tạp tìm kiếm: O(N) theo chiều dài chuỗi văn bản.
    - Không bị ảnh hưởng bởi kích thước từ điển (1.000 hay 50.000 từ tốc độ như nhau).
    - Thuần Python chuẩn, không phụ thuộc C compiler.
    """
    def __init__(self, mapping: Optional[Dict[str, str]] = None):
        self.root = TrieNode()
        self.longest_len: int = 0
        self.word_count: int = 0
        if mapping:
            for k, v in mapping.items():
                self.add_keyword(k, v)
            self.build()

    def add_keyword(self, keyword: str, value: str = ""):
        kw = keyword.strip()
        if not kw:
            return
        node = self.root
        for char in kw:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.keyword = kw
        node.value = value if value else kw
        if len(kw) > self.longest_len:
            self.longest_len = len(kw)
        self.word_count += 1

    def build(self):
        # Có thể mở rộng failure links nếu triển khai đầy đủ Aho-Corasick
        pass

    def find_matches(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Tìm tất cả các match trong chuỗi (ưu tiên Longest-Match-First tại mỗi vị trí).
        Trả về danh sách (start, end, keyword, value).
        """
        matches = []
        n = len(text)
        i = 0
        while i < n:
            curr = self.root
            longest_match = None
            j = i
            while j < n and text[j] in curr.children:
                curr = curr.children[text[j]]
                j += 1
                if curr.is_end:
                    longest_match = (i, j, curr.keyword, curr.value)
            
            if longest_match:
                matches.append(longest_match)
                i = longest_match[1]  # Nhảy qua phần đã khớp để tránh trùng lặp
            else:
                i += 1
        return matches

    def replace_all(self, text: str) -> str:
        """Thay thế tất cả các match trong text theo Longest-Match-First."""
        if not self.word_count or not text:
            return text
        matches = self.find_matches(text)
        if not matches:
            return text

        parts = []
        last_idx = 0
        for start, end, _, val in matches:
            parts.append(text[last_idx:start])
            parts.append(val)
            last_idx = end
        parts.append(text[last_idx:])
        return "".join(parts)
```

- [ ] **Step 4: Chạy test để xác nhận test thành công**

Run: `pytest tests/test_trie_matcher.py -v`
Expected: PASS

- [ ] **Step 5: Commit Task 1**

```bash
git add src/utils/trie_matcher.py tests/test_trie_matcher.py
git commit -m "feat(utils): implement zero-dependency high-performance TrieMatcher"
```

---

### Task 2: Tối ưu hóa `CandidateExtractor` (Regex Trie, Fast-path line screening & Trie Matcher)

**Files:**
- Modify: `src/scanner/candidate_extractor.py:51-114, 122-156, 517-585`
- Test: `tests/test_candidate_extractor_optimization.py`

**Interfaces:**
- Consumes: `TrieMatcher`
- Produces:
  - `self.known_trie: TrieMatcher` (loại bỏ vòng lặp `for src, tgt in known_characters`)
  - `self.deconvert_trie: TrieMatcher` (loại bỏ vòng lặp `for src, tgt in deconvert_dict`)
  - `self.lowercase_action_regex: re.Pattern` (biên dịch 61 hành động thành 1 regex duy nhất)
  - `_fast_should_scan_line(line: str, line_lower: str) -> bool` (bỏ qua nhanh 40-50% số dòng không liên quan)

- [ ] **Step 1: Viết test kiểm tra tính tương đương và tốc độ của `CandidateExtractor` sau tối ưu**

Tạo file `tests/test_candidate_extractor_optimization.py`:
```python
import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.boundary_trimmer import BoundaryTrimmer
from src.scanner.candidate_extractor import CandidateExtractor

@pytest.fixture
def extractor():
    loader = ResourceLoader()
    loader.single_surnames = {"tần", "trần", "lâm", "tiêu"}
    loader.compound_surnames = {"âu dương"}
    loader.known_characters = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    loader.deconvert_dict = {"dược lão": "Dược Lão"}
    loader.vn_2word_set = {"xoáy thuận", "từ chối"}
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames=loader.single_surnames | loader.compound_surnames)
    return CandidateExtractor(loader=loader, trimmer=trimmer, skip_known=False)

def test_fast_line_screening_skips_empty_or_plain_lines(extractor):
    # Dòng chỉ có chữ thường thông thường không mang họ, không mỏ neo -> Bỏ qua
    plain_line = "trời hôm nay nhiều mây và có gió nhẹ thổi qua thung lũng."
    matches = extractor.extract_candidates(plain_line)
    assert len(matches) == 0

def test_trie_matcher_replaces_slow_loop_for_known_chars(extractor):
    line = "Lúc này tiêu viêm nhìn thấy dược lão đang mỉm cười."
    matches = extractor.extract_candidates(line, skip_known=False)
    targets = [m.name for m in matches]
    assert "Tiêu Viêm" in targets
    assert "Dược Lão" in targets

def test_lowercase_action_regex_matches_all_actions(extractor):
    line = "tần khả cầm đi tới chiếc bàn, khẽ mỉm cười."
    matches = extractor.extract_candidates(line, skip_known=True)
    names = [m.name for m in matches]
    assert "Tần Khả Cầm" in names
    assert not any("Đi" in n for n in names)
```

- [ ] **Step 2: Chạy test để xác nhận thất bại hoặc cần điều chỉnh**

Run: `pytest tests/test_candidate_extractor_optimization.py -v`
Expected: FAIL hoặc cần cập nhật code.

- [ ] **Step 3: Triển khai tối ưu hóa trong `src/scanner/candidate_extractor.py`**

1. Import `TrieMatcher`:
```python
from ..utils.trie_matcher import TrieMatcher
```
2. Khởi tạo `TrieMatcher` và `LOWERCASE_ACTION_REGEX` trong `__init__`:
```python
        # 1. Biên dịch Trie cho deconvert_dict và known_characters
        self.deconvert_trie = TrieMatcher(self.loader.deconvert_dict) if getattr(self.loader, 'deconvert_dict', None) else None
        self.known_trie = TrieMatcher(self.loader.known_characters) if getattr(self.loader, 'known_characters', None) else None

        # 2. Biên dịch 61 LOWERCASE_ACTION_TERMS thành 1 regex Trie duy nhất
        action_alts = "|".join(re.escape(a) for a in self.LOWERCASE_ACTION_TERMS)
        self.lowercase_action_regex = re.compile(rf'^(?:{action_alts})\b', re.IGNORECASE)

        # 3. Tập hợp các từ khóa nhanh để lọc cấp dòng
        self.fast_cue_words = (
            self.loader.single_surnames | 
            self.loader.compound_surnames | 
            self.ANCHOR_TERMS | 
            self.RELATION_TERMS | 
            self.JOB_TERMS |
            {"tuổi", "·", "-", "\u2022"}
        )
```
3. Cập nhật `extract_candidates(self, line: str, skip_known: bool | None = None)`:
Thay thế vòng lặp tuần tự `for src, tgt in self.loader.known_characters.items():` bằng `self.known_trie.find_matches(line_lower)` và `self.deconvert_trie.find_matches(line_lower)` ($O(N)$ tức thời).
Thêm bộ lọc nhanh:
```python
        # Fast-Path Line Screening:
        # Nếu dòng không có chữ hoa VÀ không chứa bất kỳ từ khóa họ / mỏ neo nào -> Bỏ qua ngay
        has_upper = any(c.isupper() for c in line)
        if not has_upper and not any(kw in line_lower for kw in self.fast_cue_words):
            return results
```
4. Cập nhật `_extract_lowercase_action_candidates`:
Thay vòng lặp 61 `for act in self.LOWERCASE_ACTION_TERMS` bằng:
```python
        m_act = self.lowercase_action_regex.match(after_text_lower)
        if m_act:
            matched_action = m_act.group(0)
```

- [ ] **Step 4: Chạy test để xác nhận hoàn tất**

Run: `pytest tests/test_candidate_extractor_optimization.py tests/test_scanner_noise_and_dedup_e2e.py -v`
Expected: PASS

- [ ] **Step 5: Chạy toàn bộ test suite để đảm bảo không lỗi**

Run: `pytest tests/ -k "extractor or scanner" -v`
Expected: PASS

- [ ] **Step 6: Commit Task 2**

```bash
git add src/scanner/candidate_extractor.py tests/test_candidate_extractor_optimization.py
git commit -m "perf(scanner): optimize CandidateExtractor with TrieMatcher, Regex Trie, and line pre-screening"
```

---

### Task 3: Tối ưu hóa `ReplaceEngine` với I/O Chunk Streaming & Đếm Dòng Nhanh (Giai đoạn 1)

**Files:**
- Modify: `src/replacer/replace_engine.py:316-350`
- Test: `tests/test_replace_engine_optimization.py`

**Interfaces:**
- Consumes: Binary block reader
- Produces:
  - `ReplaceEngine.replace_file`: Đọc và ghi theo buffer chunks 64KB (thay vì từng dòng) kết hợp đếm dòng nhanh trong 1 pass nhị phân.
  - Tăng tốc thay thế dòng từ 5.000 dòng/s lên 25.000 - 30.000 dòng/s trên 1 core CPU.

- [ ] **Step 1: Viết test kiểm tra tính tương đương của `ReplaceEngine` tối ưu**

Tạo file `tests/test_replace_engine_optimization.py`:
```python
from pathlib import Path
import pytest
from src.replacer.replace_engine import ReplaceEngine

def test_replace_file_parity_and_stats(tmp_path: Path):
    in_file = tmp_path / "input.txt"
    out_file = tmp_path / "output.txt"
    
    mapping = {
        "tiêu viêm": "Tiêu Viêm",
        "dược lão": "Dược Lão",
        "long kiếm phi": "Long Kiếm Phi",
        "kiếm phi": "Long Kiếm Phi"  # prefix guard test
    }
    engine = ReplaceEngine(custom_mapping=mapping)

    content = (
        "tiêu viêm nhìn thấy dược lão.\n"
        "Long kiếm phi rút kiếm ra.\n"
        "kiếm phi cũng mỉm cười.\n"
    )
    in_file.write_text(content, encoding="utf-8")

    stats = engine.replace_file(in_file, out_file, show_progress=False)
    
    res = out_file.read_text(encoding="utf-8")
    assert "Tiêu Viêm nhìn thấy Dược Lão.\n" in res
    assert "Long Kiếm Phi rút kiếm ra.\n" in res
    assert "Long Kiếm Phi cũng mỉm cười.\n" in res
    assert stats.total_lines == 3
    assert stats.total_replacements >= 3
```

- [ ] **Step 2: Chạy test để xác nhận thất bại hoặc cần điều chỉnh**

Run: `pytest tests/test_replace_engine_optimization.py -v`
Expected: PASS hoặc sẵn sàng tối ưu.

- [ ] **Step 3: Triển khai Chunked Buffered I/O và Đếm dòng nhanh trong `src/replacer/replace_engine.py`**

Tối ưu hàm `replace_file`:
- Đếm dòng nhanh bằng đọc nhị phân 1MB (như đã làm tốt trong scanner).
- Đọc/ghi theo block dòng (buffer size 1.000 dòng) để giảm thiểu I/O syscall:
```python
        BUFFER_LINES = 1000
        line_buffer = []
        replaced_lines = []
        
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f_in, \
             open(tmp_output_path, "w", encoding="utf-8", buffering=64*1024) as f_out:
            for line_idx, line in enumerate(f_in, start=1):
                new_line = self.replace_line(line, track_stats=track_stats)
                line_buffer.append(new_line)
                
                if len(line_buffer) >= BUFFER_LINES:
                    f_out.writelines(line_buffer)
                    line_buffer.clear()
                    if progress and line_idx % 2000 == 0:
                        current_reps = sum(self.stats_counter.values()) if track_stats else 0
                        progress.update(line_idx, current_reps)
                        
            if line_buffer:
                f_out.writelines(line_buffer)
                line_buffer.clear()
```

- [ ] **Step 4: Chạy test để xác nhận kết quả**

Run: `pytest tests/test_replace_engine_optimization.py tests/test_replace_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit Task 3**

```bash
git add src/replacer/replace_engine.py tests/test_replace_engine_optimization.py
git commit -m "perf(replacer): optimize ReplaceEngine with chunked buffered IO and fast binary line count"
```

---

### Task 4: Module Phân Đoạn Khối An Toàn `chunk_splitter.py` và Song Song Hóa Quét `ScannerEngine` (Giai đoạn 2)

**Files:**
- Create: `src/utils/chunk_splitter.py`
- Modify: `src/scanner/scanner_engine.py:329-472`
- Test: `tests/test_parallel_scanner.py`

**Interfaces:**
- Consumes: File path, `num_chunks: int`
- Produces:
  - `split_file_line_chunks(filepath: Path, num_chunks: int) -> list[tuple[int, int]]` (trả về danh sách `[start_line, end_line]` hoặc byte offsets an toàn căn lề `\n`)
  - `ScannerEngine.scan_file(..., workers: int = 1)`: Khi `workers > 1`, tự động phân chia các chunk và chạy `multiprocessing` trên CPU đa nhân.

- [ ] **Step 1: Viết test cho `chunk_splitter` và `parallel scan`**

Tạo file `tests/test_parallel_scanner.py`:
```python
from pathlib import Path
import pytest
from src.utils.chunk_splitter import split_file_line_ranges
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine

def test_split_file_line_ranges(tmp_path: Path):
    f = tmp_path / "test.txt"
    lines = [f"Dòng thứ {i}\n" for i in range(1, 101)]
    f.writelines(lines)
    
    ranges = split_file_line_ranges(f, num_chunks=4)
    assert len(ranges) == 4
    assert ranges[0][0] == 1
    assert ranges[-1][1] == 100
    # Đảm bảo các dải dòng liên tục, không bị chồng chéo hay rỗng
    for i in range(len(ranges) - 1):
        assert ranges[i][1] + 1 == ranges[i+1][0]

def test_scanner_parallel_parity_with_sequential(tmp_path: Path):
    sample = tmp_path / "novel.txt"
    sample.write_text(
        "Tần Khả Cầm bước vào phòng khách.\n"
        "Âu Dương Như Tuyết đi ra ngoài ngắm tuyết rơi.\n"
        "Trương Tử Mạnh gật đầu tán thành lời nói của mọi người.\n"
        "Tần Khả Phi thở dài ngồi xuống ghế.\n"
        "Trần Ngọc Ánh Tuyết mỉm cười nhẹ nhàng.\n",
        encoding="utf-8"
    )

    loader = ResourceLoader(base_dir=tmp_path)
    # Khởi tạo tối thiểu
    loader.single_surnames = {"tần", "trương", "trần"}
    loader.compound_surnames = {"âu dương"}

    engine = ScannerEngine(loader=loader, skip_known=False)
    
    # Quét tuần tự (1 worker)
    seq_res = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    # Quét song song (2 workers)
    par_res = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=2)

    seq_targets = sorted([b.target for b in seq_res])
    par_targets = sorted([b.target for b in par_res])

    assert seq_targets == par_targets
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

Run: `pytest tests/test_parallel_scanner.py -v`
Expected: FAIL với `ModuleNotFoundError: No module named 'src.utils.chunk_splitter'`

- [ ] **Step 3: Triển khai `src/utils/chunk_splitter.py`**

```python
from pathlib import Path
from typing import List, Tuple

def split_file_line_ranges(filepath: Path, num_chunks: int) -> List[Tuple[int, int]]:
    """
    Chia tổng số dòng của file thành các khoảng dòng [start_line, end_line] liên tục (1-indexed).
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return [(1, 1)]
    
    total = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            total += chunk.count(b"\n")
    total_lines = max(1, total)

    if num_chunks <= 1 or total_lines <= num_chunks:
        return [(1, total_lines)]

    chunk_size = total_lines // num_chunks
    ranges = []
    curr_start = 1
    for i in range(num_chunks):
        if i == num_chunks - 1:
            curr_end = total_lines
        else:
            curr_end = curr_start + chunk_size - 1
        ranges.append((curr_start, curr_end))
        curr_start = curr_end + 1

    return ranges
```

- [ ] **Step 4: Cập nhật `ScannerEngine.scan_file` để hỗ trợ `workers > 1`**

Trong `src/scanner/scanner_engine.py`:
- Thêm tham số `workers: int = 1`.
- Nếu `workers > 1`:
  Sử dụng `concurrent.futures.ProcessPoolExecutor` (hoặc `multiprocessing.Pool`) để chạy hàm phụ trợ `_scan_chunk_worker` quét các dải dòng.
- Mỗi worker trả về danh sách `(name_key, cand_raw, cand_name, cand_reason, cand_conf, line_idx, context)`.
- Main process merge các kết quả vào `tracked: dict[str, CharacterBlock]`.
- Chạy `self.cluster_aliases(list(tracked.values()))` để chuẩn hóa cuối cùng.

- [ ] **Step 5: Chạy test để xác nhận kiểm tra**

Run: `pytest tests/test_parallel_scanner.py -v`
Expected: PASS

- [ ] **Step 6: Commit Task 4**

```bash
git add src/utils/chunk_splitter.py src/scanner/scanner_engine.py tests/test_parallel_scanner.py
git commit -m "feat(scanner): add parallel chunk scanning with ProcessPoolExecutor"
```

---

### Task 5: Song Song Hóa Thay Thế Tài Liệu `ReplaceEngine` (Giai đoạn 2)

**Files:**
- Modify: `src/replacer/replace_engine.py:297-371`
- Test: `tests/test_parallel_replacer.py`

**Interfaces:**
- Consumes: `workers: int`
- Produces:
  - `ReplaceEngine.replace_file(..., workers: int = 1)`:
    - Khi `workers > 1`: chia file thành $K$ chunk theo byte offset căn lề `\n`.
    - Mỗi worker ghi ra một chunk file tạm thời `.part_N`.
    - Sau khi hoàn tất, ghép các file tạm nhị phân thành file đích nguyên tử.
    - Tốc độ tăng vọt lên 80.000 – 120.000 dòng/s.

- [ ] **Step 1: Viết test cho `parallel replace`**

Tạo file `tests/test_parallel_replacer.py`:
```python
from pathlib import Path
import pytest
from src.replacer/replace_engine import ReplaceEngine

def test_parallel_replace_matches_sequential(tmp_path: Path):
    in_file = tmp_path / "large_input.txt"
    out_seq = tmp_path / "out_seq.txt"
    out_par = tmp_path / "out_par.txt"

    lines = []
    for i in range(1000):
        lines.append(f"Dòng {i}: tiêu viêm nói chuyện với dược lão tại thành phố.\n")
    in_file.writelines(lines)

    mapping = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    engine = ReplaceEngine(custom_mapping=mapping)

    stats_seq = engine.replace_file(in_file, out_seq, show_progress=False, workers=1)
    stats_par = engine.replace_file(in_file, out_par, show_progress=False, workers=4)

    assert out_seq.read_text(encoding="utf-8") == out_par.read_text(encoding="utf-8")
    assert stats_seq.total_replacements == stats_par.total_replacements
```

- [ ] **Step 2: Chạy test để xác nhận thất bại hoặc cần điều chỉnh**

Run: `pytest tests/test_parallel_replacer.py -v`
Expected: PASS nếu đã hỗ trợ workers hoặc FAIL nếu chưa nhận `workers`.

- [ ] **Step 3: Triển khai song song hóa cho `ReplaceEngine`**

1. Thêm hàm helper mức module `_replace_chunk_worker(input_path, out_part_path, start_line, end_line, dict_map, custom_mapping)`:
   - Worker chỉ đọc các dòng từ `start_line` đến `end_line`.
   - Thực hiện `replace_line` và ghi trực tiếp vào `out_part_path`.
   - Trả về `Counter(local_stats)`.
2. Trong `ReplaceEngine.replace_file`:
   - Nếu `workers > 1` và `total_lines >= 2000`:
     - Phân chia `line_ranges` bằng `split_file_line_ranges`.
     - Chạy qua `ProcessPoolExecutor`.
     - Sau khi các worker hoàn tất, nối các file `.part_N` vào `tmp_output_path` bằng binary copy chunk 1MB.
     - Xóa các file `.part_N`.
     - Hợp nhất `stats_counter`.

- [ ] **Step 4: Chạy test kiểm tra tính toàn vẹn**

Run: `pytest tests/test_parallel_replacer.py tests/test_replace_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit Task 5**

```bash
git add src/replacer/replace_engine.py tests/test_parallel_replacer.py
git commit -m "feat(replacer): add multi-worker parallel file replacement with binary chunk assembly"
```

---

### Task 6: Kiểm Thử Tương Đương 100% (Bit-for-bit Parity) & Benchmark Đo Lường Tốc Độ

**Files:**
- Create: `tests/test_performance_parity_e2e.py`
- Create: `tools/benchmark_scanner_replacer.py`
- Test: Toàn bộ test suite `pytest`

**Interfaces:**
- Consumes: File thực tế `samples/exam.txt`
- Produces:
  - Báo cáo đo lường tốc độ chi tiết (dòng/giây và thời gian hoàn thành).
  - Khẳng định tính tương đương 100% về số lượng nhân vật, tên nhân vật, số lần xuất hiện và nội dung thay thế giữa bản tuần tự và bản song song tối ưu.

- [ ] **Step 1: Viết test parity trên toàn bộ test suite**

Tạo file `tests/test_performance_parity_e2e.py`:
```python
from pathlib import Path
import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine
from src.replacer.replace_engine import ReplaceEngine

def test_full_scanner_and_replacer_parity(tmp_path: Path):
    sample = Path("samples/exam.txt")
    if not sample.exists():
        pytest.skip("Không có file samples/exam.txt để kiểm thử parity")

    # 1. Parity Kiểm tra Scanner
    loader = ResourceLoader()
    loader.load_all()
    engine = ScannerEngine(loader=loader, skip_known=True)

    res_seq = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    res_par = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=4)

    assert len(res_seq) == len(res_par)
    for b_s, b_p in zip(res_seq, res_par):
        assert b_s.target == b_p.target
        assert b_s.so_lan_xuat_hien == b_p.so_lan_xuat_hien

    # 2. Parity Kiểm tra Replacer
    out_seq = tmp_path / "out_seq.txt"
    out_par = tmp_path / "out_par.txt"

    replacer = ReplaceEngine()
    stats_seq = replacer.replace_file(sample, out_seq, show_progress=False, workers=1)
    stats_par = replacer.replace_file(sample, out_par, show_progress=False, workers=4)

    assert stats_seq.total_replacements == stats_par.total_replacements
    assert out_seq.read_text(encoding="utf-8") == out_par.read_text(encoding="utf-8")
```

- [ ] **Step 2: Viết script benchmark đo lường tốc độ thực tế `tools/benchmark_scanner_replacer.py`**

Tạo file `tools/benchmark_scanner_replacer.py`:
```python
import time
from pathlib import Path
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine
from src.replacer.replace_engine import ReplaceEngine

def run_benchmark():
    sample = Path("samples/exam.txt")
    if not sample.exists():
        print("[!] Không tìm thấy file samples/exam.txt!")
        return

    print("==================================================")
    print(" BẮT ĐẦU BENCHMARK HIỆU NĂNG SCANNER VÀ REPLACER")
    print("==================================================")
    
    # 1. Benchmark Scanner
    loader = ResourceLoader()
    loader.load_all()
    engine = ScannerEngine(loader=loader, skip_known=True)

    print("\n[*] Đang đo Scanner (1 worker - Tối ưu thuật toán)...")
    t0 = time.time()
    res_1 = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    t_seq = max(0.001, time.time() - t0)
    lines = 13486
    print(f" -> Scanner (1 worker): {lines/t_seq:,.0f} dòng/s ({t_seq:.2f}s) - {len(res_1)} nhân vật")

    print("[*] Đang đo Scanner (4 workers - Đa tiến trình)...")
    t0 = time.time()
    res_4 = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=4)
    t_par = max(0.001, time.time() - t0)
    print(f" -> Scanner (4 workers): {lines/t_par:,.0f} dòng/s ({t_par:.2f}s) - {len(res_4)} nhân vật")

    # 2. Benchmark Replacer
    replacer = ReplaceEngine()
    tmp_out = Path("samples/benchmark_out.txt")

    print("\n[*] Đang đo Replacer (1 worker - Tối ưu Buffer IO)...")
    t0 = time.time()
    s_1 = replacer.replace_file(sample, tmp_out, show_progress=False, workers=1)
    t_rep_seq = max(0.001, time.time() - t0)
    print(f" -> Replacer (1 worker): {lines/t_rep_seq:,.0f} dòng/s ({t_rep_seq:.2f}s) - {s_1.total_replacements:,} lượt thay")

    print("[*] Đang đo Replacer (4 workers - Đa tiến trình)...")
    t0 = time.time()
    s_4 = replacer.replace_file(sample, tmp_out, show_progress=False, workers=4)
    t_rep_par = max(0.001, time.time() - t0)
    print(f" -> Replacer (4 workers): {lines/t_rep_par:,.0f} dòng/s ({t_rep_par:.2f}s) - {s_4.total_replacements:,} lượt thay")

    if tmp_out.exists():
        tmp_out.unlink()

if __name__ == "__main__":
    run_benchmark()
```

- [ ] **Step 3: Chạy toàn bộ test suite để đảm bảo 100% tests PASS**

Run: `pytest -v`
Expected: Tất cả các test cũ (124) và toàn bộ test mới đều PASS 100%.

- [ ] **Step 4: Chạy script benchmark để kiểm chứng tốc độ thực tế**

Run: `python tools/benchmark_scanner_replacer.py`
Expected: Tốc độ Scanner đạt > 25.000 dòng/s, Replacer đạt > 60.000 dòng/s.

- [ ] **Step 5: Commit Task 6**

```bash
git add tests/test_performance_parity_e2e.py tools/benchmark_scanner_replacer.py
git commit -m "test(perf): add parity verification test and benchmark script for scan and replace"
```
