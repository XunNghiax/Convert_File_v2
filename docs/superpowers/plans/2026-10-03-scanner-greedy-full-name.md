# Kế hoạch Thực hiện: Cải tiến Thuật toán Scanner Tối đa hóa Bắt Đủ Họ và Tên

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cải tiến thuật toán Scanner trong `src/scanner/` để ưu tiên tối đa độ bao phủ (High Recall), bắt trọn vẹn đủ cả họ và tên (2 đến 4 từ) của nhân vật kể cả khi viết thường, viết lẫn hoa thường hoặc là tên phiên âm nước ngoài, khắc phục triệt để lỗi cắt cụt họ "Từ" và lỗi cắt mất từ thứ 3.

**Architecture:**
1. Cập nhật `surnames.txt` với các họ đơn, họ kép và phiên âm còn thiếu.
2. Sửa `BoundaryTrimmer` để không bao giờ cắt bỏ họ ở đầu hoặc từ thứ 3 trong cụm tên 3 từ.
3. Mở rộng `CandidateExtractor` với cơ chế bắt tham lam (Greedy Match), nhận diện tên viết thường qua mỏ neo mở rộng và cấu trúc cú pháp `[Họ] + [tên] + [động từ hành động]`, hỗ trợ tên nước ngoài kèm dấu `·` hoặc `-`.
4. Nâng cấp `ScannerEngine` với giải thuật gộp chuỗi mẹ (Super-string consolidation) để hợp nhất biến thể ngắn vào tên đầy đủ nhất.
5. Kiểm thử toàn diện và đo lường độ phủ thực tế với 91 nhân vật trong `danh_sach_nhan_vat.md`.

**Tech Stack:** Python 3.12, Pytest, Regex.

## Global Constraints
- Ưu tiên bắt đủ Họ và Tên (2-4 từ) hơn là cắt gọt quá sớm; chấp nhận có thể dính từ ngữ cảnh để AI/Gemini xử lý sau.
- Tuyệt đối không xóa họ "Từ" hoặc các họ hợp lệ ở đầu cụm từ 2-4 từ.
- Tuyệt đối không xóa từ thứ 3 nếu cụm từ có họ hợp lệ hoặc đứng sau mỏ neo.
- Tất cả file đọc/ghi bằng mã UTF-8.
- Duy trì tốc độ quét cao (>10,000 dòng/giây).

---

### Task 1: Cải tiến BoundaryTrimmer & Bổ sung Từ điển Họ

**Files:**
- Modify: `resources/filters/surnames.txt`
- Modify: `src/scanner/boundary_trimmer.py`
- Test: `tests/test_boundary_trimmer_fullname.py`

**Interfaces:**
- `BoundaryTrimmer.trim(text: str) -> tuple[str, str]`
- `BoundaryTrimmer.trim_leading(text: str) -> str`

- [ ] **Step 1: Write test for BoundaryTrimmer protecting full names and surnames**

```python
# tests/test_boundary_trimmer_fullname.py
from src.scanner.boundary_trimmer import BoundaryTrimmer

def test_protects_tu_surname():
    trimmer = BoundaryTrimmer(trailing_stopwords={"hai", "người", "thân"})
    # "Từ Tân Đồng" không được bị cắt chữ "Từ"
    trimmed, rem = trimmer.trim("Từ Tân Đồng")
    assert trimmed == "Từ Tân Đồng"
    
    # "Từ Linh San" không được bị cắt chữ "Từ"
    trimmed, rem = trimmer.trim("Từ Linh San")
    assert trimmed == "Từ Linh San"

    # "từ vân tuyết" không được bị cắt chữ "từ"
    trimmed, rem = trimmer.trim("từ vân tuyết")
    assert trimmed.lower() == "từ vân tuyết"

def test_protects_third_word_in_three_word_names():
    trimmer = BoundaryTrimmer(trailing_stopwords={"y", "di", "mai", "thân", "người"})
    # Chữ "Sương", "Y", "Di", "Văn" ở cuối không được bị cắt
    assert trimmer.trim("Tôn Như Sương")[0] == "Tôn Như Sương"
    assert trimmer.trim("Đường Thiền Y")[0] == "Đường Thiền Y"
    assert trimmer.trim("Trần Mộng Di")[0] == "Trần Mộng Di"
    assert trimmer.trim("Diệp Mạn Văn")[0] == "Diệp Mạn Văn"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_boundary_trimmer_fullname.py -v`
Expected: FAIL (due to current trimmer cutting "Từ" or 3rd word)

- [ ] **Step 3: Update `resources/filters/surnames.txt`**

Bổ sung các họ:
`liêu`, `mặc`, `ngả`, `thiên diệp`, `tây xuyên`, `nạp lan`, `đông phương`, `nam cung`, `âu dương`, `tư mã`, `độc cô`, `gia cát`, `hoàng phủ`.

- [ ] **Step 4: Update `src/scanner/boundary_trimmer.py`**

- Trong `trim_leading`:
  - Nếu từ đầu tiên là `từ` và cụm từ có 2–4 từ: không cắt `từ`.
  - Không cắt nếu từ đầu tiên là một họ hợp lệ.
- Trong `trim`:
  - Nếu cụm từ có độ dài $\le 3$ từ và từ đầu tiên là một Họ hợp lệ (hoặc không phải hư từ rõ rệt): không dùng `trailing_stopwords` để cắt từ thứ 3 (trừ khi từ thứ 3 là số đếm rõ rệt như `hai người`, `ba người`).

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_boundary_trimmer_fullname.py -v`
Expected: PASS

- [ ] **Step 6: Commit Task 1**

```bash
git add resources/filters/surnames.txt src/scanner/boundary_trimmer.py tests/test_boundary_trimmer_fullname.py
git commit -m "feat: protect full names and surnames in boundary trimmer"
```

---

### Task 2: Mở rộng CandidateExtractor với Greedy Matching và Lowercase Name Patterns

**Files:**
- Modify: `src/scanner/candidate_extractor.py`
- Test: `tests/test_candidate_extractor_greedy.py`

**Interfaces:**
- `CandidateExtractor.extract_candidates(line: str, skip_known: bool | None = None) -> list[CandidateMatch]`

- [ ] **Step 1: Write tests for greedy extraction, lowercase names and foreign names**

```python
# tests/test_candidate_extractor_greedy.py
import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.boundary_trimmer import BoundaryTrimmer
from src.scanner.candidate_extractor import CandidateExtractor

@pytest.fixture
def extractor():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    return CandidateExtractor(loader, trimmer, skip_known=False)

def test_extract_three_word_names_after_anchor(extractor):
    line = "bảo mẫu tôn như sương bưng hoa quả đi vào phòng khách."
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    assert "Tôn Như Sương" in names

def test_extract_lowercase_name_with_action(extractor):
    line = "Nhìn phụ thân như thế cưng chìu mẫu thân, từ vân tuyết trong lòng có một chút ghen tị."
    cands = extractor.extract_candidates(line)
    names = [c.name.lower() for c in cands]
    assert "từ vân tuyết" in names

def test_extract_foreign_name_with_middle_dot(extractor):
    line = "Mà ngồi tại Ngả Lâm Na bên người Đại Na · Hải Ngũ Đức ánh mắt quyến rũ nhìn chính mình."
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    assert any("Đại Na" in n and "Hải Ngũ Đức" in n for n in names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_candidate_extractor_greedy.py -v`
Expected: FAIL

- [ ] **Step 3: Implement updates in `src/scanner/candidate_extractor.py`**
- Mở rộng `ANCHOR_TERMS` với các danh xưng gia đình và chức vụ:
  `ba ba`, `bố`, `ông ngoại`, `bà ngoại`, `mẹ kế`, `mẹ ruột`, `nha đầu`, `tiểu nha đầu`, `thích khách`, `tên là`, `ta gọi`, `chủ tịch`, `giám đốc`, `thê tử`, `tẩu tử`.
- Trong `anchor_pattern`:
  Cập nhật regex để bắt tham lam 2 đến 4 từ sau mỏ neo: `(?i:\b({anchor_group})(?:\s+(?:tên là|gọi là|kêu là|tên gọi là|đích|của ta|của hắn|của nàng))?\s*[:\-—]?\s*)([{VN_UPPER}{VN_LOWER}]+(?:\s+[{VN_UPPER}{VN_LOWER}]+){1,3})\b`.
- Thêm cơ chế nhận diện tên viết thường đi kèm hành động (Lowercase Name with Action):
  Khi dòng chứa một họ trong `single_surnames` hoặc `compound_surnames`, kiểm tra cụm 2-3 từ tiếp theo xem có đi liền với động từ hành động hoặc cảm xúc không.
- Thêm regex hỗ trợ tên phiên âm có dấu chấm nối `[·\-\.]`:
  `rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+)*\s*[·\-]\s*[{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+)*)\b'`
- Thêm nhận diện tên Latinh độc lập khi đứng sau xưng hô hoặc phát ngôn (như `Joanna`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_candidate_extractor_greedy.py tests/test_candidate_extractor.py tests/test_candidate_extractor_precision.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit Task 2**

```bash
git add src/scanner/candidate_extractor.py tests/test_candidate_extractor_greedy.py
git commit -m "feat: add greedy matching, lowercase action pattern, and foreign name support"
```

---

### Task 3: Nâng cấp ScannerEngine với Hợp nhất Chuỗi Mẹ (Super-string Consolidation)

**Files:**
- Modify: `src/scanner/scanner_engine.py`
- Test: `tests/test_scanner_engine_superstring.py`

**Interfaces:**
- `ScannerEngine.cluster_aliases(blocks: list[CharacterBlock]) -> list[CharacterBlock]`
- `ScannerEngine.deduplicate_blocks(blocks: list[CharacterBlock]) -> list[CharacterBlock]`

- [ ] **Step 1: Write test for super-string consolidation**

```python
# tests/test_scanner_engine_superstring.py
from src.scanner.scanner_engine import ScannerEngine, CharacterBlock

def test_consolidates_shorter_name_into_longer_full_name():
    engine = ScannerEngine(loader=None)
    b1 = CharacterBlock(id="ch_1", source="Đường Thiền", target="Đường Thiền", context="ctx1", yeu_to_nhan_biet="rel", so_lan_xuat_hien=10)
    b2 = CharacterBlock(id="ch_2", source="Đường Thiền Y", target="Đường Thiền Y", context="ctx2", yeu_to_nhan_biet="rel", so_lan_xuat_hien=50)
    
    result = engine.cluster_aliases([b1, b2])
    targets = [b.target for b in result]
    # Phải giữ lại "Đường Thiền Y", gộp "Đường Thiền" vào biến thể
    assert "Đường Thiền Y" in targets
    main_block = next(b for b in result if b.target == "Đường Thiền Y")
    assert "Đường Thiền" in main_block.bien_the
    assert main_block.so_lan_xuat_hien == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scanner_engine_superstring.py -v`
Expected: FAIL

- [ ] **Step 3: Implement super-string consolidation in `src/scanner/scanner_engine.py`**
- Trong `cluster_aliases`:
  - Nhận diện các cặp khối có quan hệ tiền tố họ + tên ngắn vs tên dài:
    Nếu `A` (2 từ: `Họ + X`) và `B` (3 từ: `Họ + X + Y`), gộp `A` vào `B`, coi `A` là biến thể gọi tắt của `B`.
  - Chuyển `so_lan_xuat_hien` và danh sách dòng xuất hiện từ `A` sang `B`.
  - Cắt bỏ các động từ dính đuôi nếu tên gốc đã tồn tại (ví dụ `Từ Thanh khiêu` gộp vào `Từ Thanh`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scanner_engine_superstring.py tests/test_deduplication.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit Task 3**

```bash
git add src/scanner/scanner_engine.py tests/test_scanner_engine_superstring.py
git commit -m "feat: implement super-string consolidation in scanner engine"
```

---

### Task 4: Kiểm thử Toàn trình & Đo lường Recall đối chiếu với `danh_sach_nhan_vat.md`

**Files:**
- Test script: `scratch/evaluate_benchmark.py`
- Command: `python src/scanner/main.py --input samples/exam.txt --include-known`
- Full test suite: `python -m pytest`

- [ ] **Step 1: Run full pytest suite**

Run: `python -m pytest -v`
Expected: All tests pass (except known pre-existing `test_gemini_uploader_init`)

- [ ] **Step 2: Run scanner on `samples/exam.txt` with `--include-known`**

Run: `python src/scanner/main.py --input samples/exam.txt --include-known`

- [ ] **Step 3: Run benchmark evaluation against 91 gold names in `danh_sach_nhan_vat.md`**

Đo lường:
- Số lượng nhân vật trích xuất đủ họ và tên.
- Recall rate so với ban đầu (trước: 10/91 khớp trọn vẹn; mục tiêu sau: > 80/91 khớp trọn vẹn).

- [ ] **Step 4: Commit all final improvements**

```bash
git add .
git commit -m "feat: complete greedy full-name scanner improvements and benchmark"
```
