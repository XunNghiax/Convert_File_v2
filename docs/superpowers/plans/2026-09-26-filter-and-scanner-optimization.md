# Kế Hoạch Tối Ưu Bộ Lọc (Filters) & Heuristics Cho Character Scanner

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Loại bỏ triệt để các thực thể sai (địa danh, tổ chức, danh từ miêu tả, cụm từ dính ngữ pháp, nhân vật lịch sử ngoài truyện) xuất hiện trong `scanner/scanner_master.json`, đồng thời bảo toàn 100% các nhân vật truyện hợp lệ.

**Architecture:** 
1. Cập nhật dữ liệu từ điển: Thêm các địa danh, tổ chức, chức danh vào `filters/non_person.txt`; sửa lỗi định dạng và thêm cụm từ nhiễu/cảm thán vào `filters/blacklist.txt` và `filters/trailing_stopwords.txt`.
2. Thắt chặt heuristics trích xuất: Profile regex bắt buộc ứng viên trước `,\s*(nam|nữ|thiếu phụ|...)` phải là TitleCase và bắt đầu bằng họ hợp lệ; lọc từ quan hệ không cho dính động từ hành vi (`an ủi`, `an bài`, `cao hứng`, `tò mò`); và bảo vệ `session_cache` chỉ lưu nhân vật có độ tin cậy cao (`confidence >= 0.88` và có họ).

**Tech Stack:** Python 3.12+, `pytest`, Regex, JSON, Trie.

## Global Constraints

- Không làm mất hoặc suy giảm khả năng nhận diện các nhân vật truyện có thật trong `exam.txt`.
- Giữ vững cấu trúc 6 trường dữ liệu chuẩn của `scanner_master.json`: `id`, `is_character`, `source`, `target`, `context`, `yeu_to_nhan_biet`, `so_lan_xuat_hien`.
- Toàn bộ 16 test hiện tại trong `tests/` và các test mới đều phải vượt qua (`100% PASS`).

---

### Task 1: Cập nhật Danh từ Phi Nhân Vật vào `filters/non_person.txt`

**Files:**
- Modify: `filters/non_person.txt`
- Test: `tests/test_filters_non_person.py`

**Interfaces:**
- Consumes: `ResourceLoader.load_word_set()`
- Produces: `ResourceLoader.non_person: set[str]` với đầy đủ các địa danh, tổ chức, tác phẩm, đồ vật.

- [ ] **Step 1: Viết test kiểm tra các từ phi nhân vật mới đã được nạp**

```python
# tests/test_filters_non_person.py
from character_scanner.resource_loader import ResourceLoader

def test_non_person_expanded_list():
    loader = ResourceLoader()
    loader.load_all()
    samples = [
        "tô châu", "cổ hy lạp", "thổ nhĩ kỳ", "đông hải", "hà đông",
        "thái sơn", "lương sơn", "tây môn", "cao hùng", "vũ hoa",
        "lạc dương nam cung", "lam điền", "la mã", "bách linh", "vân long",
        "đại trung hoa", "hoa hạ thần châu", "hồng lâu mộng", "kim bình mai",
        "kim bôi", "thái thản ni khắc", "kim lợi", "lưu ly cung", "tống triều",
        "bóng hình xinh đẹp", "da thịt", "thái hư", "hầu vương", "hồng hà",
        "phương hoa", "loan phượng", "bảo bối nhi", "hoa cốc", "thái hòa"
    ]
    for word in samples:
        assert word in loader.non_person, f"Thiếu từ phi nhân vật: {word}"
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `pytest tests/test_filters_non_person.py -v`
Expected: FAIL vì các từ mới chưa có trong `filters/non_person.txt`.

- [ ] **Step 3: Bổ sung từ vào `filters/non_person.txt`**

Thêm các nhóm từ (chuyển chữ thường):
- Địa danh / Quốc gia: `tô châu`, `cổ hy lạp`, `thổ nhĩ kỳ`, `đông hải`, `hà đông`, `thái sơn`, `lương sơn`, `tây môn`, `cao hùng`, `vũ hoa`, `hàn quốc nhật bản`, `lạc dương nam cung`, `lam điền`, `la mã`, `bách linh`.
- Tổ chức / Tác phẩm: `vân long`, `đại trung hoa`, `hoa hạ thần châu`, `phong điền`, `lăng vân`, `hồng lâu mộng`, `kim bình mai`, `kim bôi`, `thái thản ni khắc`, `kim lợi`, `lưu ly cung`, `tống triều`.
- Danh từ / Khái niệm / Đồ vật: `bóng hình xinh đẹp`, `da thịt`, `thái hư`, `hầu vương`, `hồng hà`, `phương hoa`, `loan phượng`, `bảo bối nhi`, `hoa cốc`, `thái hòa`.
- Tước xưng nhầm lẫn: `hoàng hậu nữ nhi`, `vương phi nữ nhi`, `văn nhân thân vương`, `thủ tướng`, `ngoại tướng`, `vương quý phi`.

- [ ] **Step 4: Chạy test để xác nhận test vượt qua**

Run: `pytest tests/test_filters_non_person.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add filters/non_person.txt tests/test_filters_non_person.py
git commit -m "feat(filters): expand non_person.txt with locations, organizations and non-character concepts"
```

---

### Task 2: Chuẩn Hóa `blacklist.txt` & Mở Rộng `trailing_stopwords.txt`

**Files:**
- Modify: `filters/blacklist.txt`
- Modify: `filters/trailing_stopwords.txt`
- Test: `tests/test_filters_blacklist.py`

**Interfaces:**
- Consumes: `ResourceLoader.blacklist`, `ResourceLoader.trailing_stopwords`
- Produces: Bộ từ khóa blacklist và stopword sạch, sửa lỗi format dính dòng.

- [ ] **Step 1: Viết test kiểm tra blacklist và trailing stopwords**

```python
# tests/test_filters_blacklist.py
from character_scanner.resource_loader import ResourceLoader

def test_blacklist_cleaned_and_expanded():
    loader = ResourceLoader()
    loader.load_all()
    
    # Kiểm tra các từ lỗi format đã được sửa
    corrupted_words = ["hư thếcó thểcó lẽ", "ghĩ thầm"]
    for w in corrupted_words:
        assert w not in loader.blacklist
        
    expected_blacklist = [
        "như vậy", "có thể", "có lẽ", "tuy nhiên", "thế nhưng", "mặc dù",
        "nghĩ thầm", "tính toán", "phải chịu", "chịu trách nhiệm", "giảm biên chế",
        "ha ha", "đúng vậy a", "thật dài rên rỉ", "cả người mềm yếu", "nổi lên phản ứng",
        "thấu xương toan ngứa", "đại từ đại bi", "thổ khí như lan", "nói như",
        "lơ trên mặt đất", "hứa ly", "đại thụy", "nam nhân không xấu", "như thế tán tỉnh",
        "mềm mại", "trắng nõn", "cổ trắng", "bảo đảm", "nhạc nhạc", "đại hòa"
    ]
    for w in expected_blacklist:
        assert w in loader.blacklist, f"Thiếu từ blacklist: {w}"
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `pytest tests/test_filters_blacklist.py -v`
Expected: FAIL

- [ ] **Step 3: Chỉnh sửa `filters/blacklist.txt` và `filters/trailing_stopwords.txt`**

1. Sửa `filters/blacklist.txt`: Tách các từ bị dính dòng (line 3 & line 4) thành từng dòng riêng biệt, thêm danh sách các cụm từ cảm thán / miêu tả trạng thái.
2. Cập nhật `filters/trailing_stopwords.txt`: Bổ sung các từ: `an ủi`, `an bài`, `cao hứng`, `hầu hạ`, `tưởng tượng`, `tò mò`, `đối`, `một`, `mẹ con`, `vợ chồng`, `phu lý`.

- [ ] **Step 4: Chạy test để xác nhận test vượt qua**

Run: `pytest tests/test_filters_blacklist.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add filters/blacklist.txt filters/trailing_stopwords.txt tests/test_filters_blacklist.py
git commit -m "fix(filters): format blacklist and add common descriptive phrases and stopwords"
```

---

### Task 3: Thắt Chặt Heuristics và Session Cache Guard trong `candidate_extractor.py`

**Files:**
- Modify: `character_scanner/candidate_extractor.py`
- Test: `tests/test_candidate_extractor_precision.py`

**Interfaces:**
- Consumes: `CandidateExtractor.extract_candidates(line)`
- Produces: Danh sách `CandidateMatch` đã lọc sạch các cụm dính dấu phẩy, động từ trước từ quan hệ, và không lây nhiễm vào `session_cache`.

- [ ] **Step 1: Viết test cho profile regex, relation trimmer và cache guard**

```python
# tests/test_candidate_extractor_precision.py
from character_scanner.resource_loader import ResourceLoader
from character_scanner.boundary_trimmer import BoundaryTrimmer
from character_scanner.candidate_extractor import CandidateExtractor

def test_profile_regex_precision():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    extractor = CandidateExtractor(loader, trimmer)
    
    # Đoạn văn có mệnh đề kết thúc bằng dấu phẩy rồi đến 'nữ nhân' hoặc 'nam nhân' -> KHÔNG được nhận diện
    text1 = "nam nhân đàm luận bóng đá thời điểm, nữ nhân luôn bị xem nhẹ."
    cands1 = extractor.extract_candidates(text1)
    names1 = [c.name for c in cands1]
    assert "Bóng Đá Thời Điểm" not in names1
    assert "Thời Thượng Thời Điểm" not in names1
    
    # Đoạn văn giới thiệu thật sự -> BẮT BUỘC nhận diện
    text2 = "Trương Tử Kiến, nam, 30 tuổi, nhân viên văn phòng."
    cands2 = extractor.extract_candidates(text2)
    names2 = [c.name for c in cands2]
    assert "Trương Tử Kiến" in names2

def test_relation_regex_verb_rejection():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    extractor = CandidateExtractor(loader, trimmer)
    
    # Động từ/tính từ đứng trước từ quan hệ -> KHÔNG được nhận diện
    text1 = "Tần Xảo Xảo rất cao hứng Nguyên Xuân tỷ tỷ như thế duy trì."
    cands1 = extractor.extract_candidates(text1)
    names1 = [c.name for c in cands1]
    assert "Cao Hứng Nguyên Xuân" not in names1
    assert "Nguyên Xuân" in names1 or "Tô Nguyên Xuân" in names1 or "Nguyên Xuân" in [c.raw for c in cands1]

def test_session_cache_guard():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    extractor = CandidateExtractor(loader, trimmer)
    
    # Không để các từ vựng thông thường lọt vào cache
    assert "Bóng Hình Xinh Đẹp" not in extractor.session_cache
    assert "Mềm Mại" not in extractor.session_cache
```

- [ ] **Step 2: Chạy test để xác nhận test thất bại**

Run: `pytest tests/test_candidate_extractor_precision.py -v`
Expected: FAIL do các cụm từ ngữ pháp hiện tại vẫn bị regex bắt.

- [ ] **Step 3: Triển khai các cải tiến heuristics trong `character_scanner/candidate_extractor.py`**

1. Trong **Profile regex**:
   - Chỉ xem là hồ sơ hợp lệ nếu ứng viên là TitleCase (ký tự đầu viết hoa) VÀ mang họ hợp lệ (`self._starts_with_surname`).
   - Nếu ứng viên viết thường hoặc từ cuối thuộc danh sách động từ/tính từ/trợ từ -> Bỏ qua.
2. Trong **Relation regex**:
   - Bổ sung kiểm tra tiền tố hành vi: Nếu cụm bắt được bắt đầu bằng động từ/tính từ phổ biến (`cao hứng`, `an ủi`, `an bài`, `tưởng tượng`, `hầu hạ`, `tò mò`) -> Bóc tách chỉ giữ lại tên riêng ở sau nếu có họ hợp lệ.
3. Trong **Session Cache Guard**:
   - Chỉ thêm vào `session_cache` khi `cand.confidence >= 0.88` VÀ `self._starts_with_surname(cand.name)` VÀ không nằm trong `non_person` / `blacklist` / `common_dict`.
   - Ngăn chặn hoàn toàn hiện tượng một từ nhiễu lọt vào cache rồi match lan truyền khắp văn bản.

- [ ] **Step 4: Chạy test để xác nhận test vượt qua**

Run: `pytest tests/test_candidate_extractor_precision.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/candidate_extractor.py tests/test_candidate_extractor_precision.py
git commit -m "fix(scanner): tighten profile/relation regex and guard session cache against pollution"
```

---

### Task 4: Chạy Toàn Bộ Test Suite & Quét Lại `exam.txt` Xác Minh Kết Quả

**Files:**
- Modify: `scanner/scanner_master.json` (tự động qua CLI)
- Test: Chạy toàn bộ test suite

**Interfaces:**
- Consumes: `character_scanner.main`
- Produces: File `scanner/scanner_master.json` mới đã loại bỏ hoàn toàn các mục false positive.

- [ ] **Step 1: Chạy toàn bộ test suite**

Run: `pytest tests/ -v`
Expected: Tất cả các test đều PASS (100%).

- [ ] **Step 2: Chạy quét lại `exam.txt`**

Run: `python -m character_scanner.main --input exam.txt --output scanner/scanner_master.json`
Expected: Quét hoàn tất, ghi file thành công.

- [ ] **Step 3: Kiểm tra định lượng và định tính kết quả mới**

Chạy script kiểm tra:
- Xác nhận các từ: `Bóng Đá Thời Điểm`, `Cao Hứng Nguyên Xuân`, `Bóng Hình Xinh Đẹp`, `Ha Ha`, `Mềm Mại`, `Trắng Nõn`, `Da Thịt`, `Tô Châu`, `Cổ Hy Lạp`, v.v. đã biến mất.
- Xác nhận các nhân vật chính: `Trương Tử Kiến`, `Long Kiếm Phi`, `Lâm Ngọc Chi`, `Tô Nguyên Xuân`, `Tần Xảo Xảo`, `Chung Thục Huệ`, v.v. vẫn xuất hiện đầy đủ 100%.

- [ ] **Step 4: Commit**

```bash
git add scanner/ tests/
git commit -m "chore: re-scan exam.txt with optimized filters and updated scanner master"
```
