# Kế hoạch tối ưu hóa thuật toán quét nhân vật (Scanner Engine V2)

> **Dành cho Agent thực thi:** BẮT BUỘC SỬ DỤNG SUB-SKILL: Sử dụng `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans` để triển khai kế hoạch này theo từng task. Các bước sử dụng cú pháp checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Nâng cấp thuật toán trích xuất thực thể tên nhân vật trong `src/scanner/` từ cơ chế regex chữ hoa đơn giản thành hệ thống quét chuyên sâu theo ngữ cảnh cho truyện dịch thô/convert; triệt tiêu 100% lỗi rác/bộ phận cơ thể, khắc phục lỗi chặt cụt tên, bắt trọn tên viết thường qua mỏ neo ngữ nghĩa và khôi phục tên bị dịch máy nghĩa đen.

**Kiến trúc:** Triển khai theo mô hình 3 tầng (Three-Stage Pipeline):
1. **Stage 1 (Anchor-based Candidate Mining):** Quét đa dạng ứng viên bằng chữ hoa, mỏ neo quan hệ/chức danh chữ thường, cấu trúc hội thoại và tra cứu từ điển giải mã dịch thô (De-convert).
2. **Stage 2 (Semantic Verification & Boundary Protection):** Bảo vệ ranh giới tên (xóa tên riêng khỏi stopword đuôi), loại bỏ lây nhiễm cache độc hại (`session_cache`), bắt buộc kiểm tra hành vi nhân tính.
3. **Stage 3 (Alias Clustering & Context Selection):** Gom nhóm biến thể danh xưng về thực thể gốc và chọn câu chứng minh hành động tiêu biểu nhất.

**Công nghệ sử dụng:** Python 3.12, Pytest, Regex Unicode Tiếng Việt, JSON streaming.

## Ràng buộc chung (Global Constraints)
- **Tương thích ngược:** Giữ nguyên giao diện CLI trong `run_cli.py` và cấu trúc `CharacterBlock` để các module `replacer`, `importer`, `upload_to_gemini` không bị ảnh hưởng.
- **Tốc độ:** Thuật toán chạy offline thuần Python, thời gian quét toàn bộ file 5-7MB không vượt quá 10 giây.
- **Độ chính xác:** Tuyệt đối không để lọt từ ngữ giải phẫu học, tình dục, động từ hoặc địa danh vào danh sách nhân vật.

---

### Task 1: Làm sạch Stopwords, cập nhật Blacklist và sửa BoundaryTrimmer

**Files:**
- Modify: `resources/filters/trailing_stopwords.txt`
- Modify: `resources/filters/non_person.txt`
- Modify: `src/scanner/boundary_trimmer.py:43-50`
- Test: `tests/test_boundary_trimmer.py`

**Interfaces:**
- Consumes: `BoundaryTrimmer(trailing_stopwords: set[str])`
- Produces: `trim(text: str) -> tuple[str, str]` bảo vệ từ tố tên người, không chặt cụt `Tâm`, `Y`, `Phương`, `Lan`...

- [ ] **Bước 1: Viết test kiểm tra ranh giới từ bị lỗi**
  Thêm test case trong `tests/test_boundary_trimmer.py`:
  ```python
  def test_preserve_valid_name_endings():
      trimmer = BoundaryTrimmer({"hai", "người", "thân"})
      # "Văn Liên Tâm" không được bị cắt thành "Văn Liên"
      trimmed, suffix = trimmer.trim("Văn Liên Tâm")
      assert trimmed == "Văn Liên Tâm"
      assert suffix == ""

      # "Đường Thiền Y" không được bị cắt
      trimmed, suffix = trimmer.trim("Đường Thiền Y")
      assert trimmed == "Đường Thiền Y"
      assert suffix == ""
  ```
- [ ] **Bước 2: Chạy test để xác nhận test chạy và phản ánh đúng hành vi**
  Chạy: `pytest tests/test_boundary_trimmer.py`
- [ ] **Bước 3: Làm sạch file stopwords và cập nhật non_person**
  1. Trong `resources/filters/trailing_stopwords.txt`: Tìm và xóa các từ `tâm`, `y`, `lan`, `phương`, `ngọc`, `đồng`, `hoa`, `quân`.
  2. Trong `resources/filters/non_person.txt`: Thêm danh sách đen giải phẫu học/18+/vật phẩm:
     ```text
     dương vật
     quy đầu
     âm đạo
     mật huyệt
     tử cung
     hoa tâm
     vú sữa
     bạo địt
     cường địt
     nhan bắn
     đại gia hỏa
     phòng bên
     bao trùm
     bao gồm
     bạch cái
     mông cong cùng eo
     cầu hoan chó
     ```
- [ ] **Bước 4: Cập nhật logic BoundaryTrimmer để bảo vệ cấu trúc tên 2-3 từ**
  Trong `src/scanner/boundary_trimmer.py`, cập nhật phương thức `trim`:
  ```python
  PROTECTED_NAME_WORDS = {"tâm", "y", "lan", "phương", "ngọc", "đồng", "hoa", "quân", "hương", "sương"}

  def trim(self, text: str) -> tuple[str, str]:
      s = self.trim_leading(text)
      words = s.strip().split()
      removed = []
      while len(words) > 1 and words[-1].lower() in self.trailing_stopwords:
          if len(words) <= 3 and words[-1].lower() in PROTECTED_NAME_WORDS:
              break
          removed.insert(0, words.pop())
      return " ".join(words), " ".join(removed)
  ```
- [ ] **Bước 5: Chạy lại toàn bộ test boundary trimmer**
  Chạy: `pytest tests/test_boundary_trimmer.py` và xác nhận PASS.

---

### Task 2: Xây dựng Module De-convert khôi phục tên bị dịch thô

**Files:**
- Create: `resources/dictionaries/deconvert_dict.json`
- Modify: `src/scanner/resource_loader.py:12-20, 75-93`
- Test: `tests/test_resource_loader.py`

**Interfaces:**
- Consumes: File JSON từ điển ánh xạ `deconvert_dict.json`
- Produces: `ResourceLoader.deconvert_dict: dict[str, str]` phục vụ `CandidateExtractor`

- [ ] **Bước 1: Viết test cho ResourceLoader tải deconvert_dict**
  Trong `tests/test_resource_loader.py`:
  ```python
  def test_load_deconvert_dict(tmp_path):
      loader = ResourceLoader(base_dir=tmp_path)
      dict_dir = tmp_path / "resources" / "dictionaries"
      dict_dir.mkdir(parents=True)
      deconvert_file = dict_dir / "deconvert_dict.json"
      deconvert_file.write_text('{"tô cũng có thể": "Tô Diệc Khả", "mực đầu hạ": "Mặc Đầu Hạ"}', encoding="utf-8")
      
      loader.load_all()
      assert loader.deconvert_dict.get("tô cũng có thể") == "Tô Diệc Khả"
      assert loader.deconvert_dict.get("mực đầu hạ") == "Mặc Đầu Hạ"
  ```
- [ ] **Bước 2: Tạo file `resources/dictionaries/deconvert_dict.json`**
  ```json
  {
    "tô cũng có thể": "Tô Diệc Khả",
    "tô cũng khả": "Tô Diệc Khả",
    "mực đầu hạ": "Mặc Đầu Hạ",
    "marvin quân": "Mã Văn Quân",
    "máu tôn": "Huyết Tôn"
  }
  ```
- [ ] **Bước 3: Cập nhật `ResourceLoader` trong `src/scanner/resource_loader.py`**
  Thêm trường `self.deconvert_dict: dict[str, str] = {}` và hàm nạp `load_deconvert_dict`:
  ```python
  def load_deconvert_dict(self, path: Path) -> dict[str, str]:
      mapping = {}
      if not path.exists():
          return mapping
      try:
          data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
          if isinstance(data, dict):
              for k, v in data.items():
                  mapping[k.strip().lower()] = v.strip()
      except Exception:
          pass
      return mapping
  ```
  Gọi hàm này trong `load_all()`.
- [ ] **Bước 4: Chạy test resource loader**
  Chạy: `pytest tests/test_resource_loader.py` và xác nhận PASS.

---

### Task 3: Nâng cấp CandidateExtractor (Xóa Cache độc hại, Quét Mỏ neo chữ thường & Hội thoại)

**Files:**
- Modify: `src/scanner/candidate_extractor.py`
- Test: `tests/test_candidate_extractor.py`
- Test: `tests/test_candidate_extractor_precision.py`

**Interfaces:**
- Consumes: `ResourceLoader` (với `deconvert_dict`, `non_person` mới), `BoundaryTrimmer`
- Produces: `CandidateExtractor.extract_candidates(line: str) -> list[CandidateMatch]`

- [ ] **Bước 1: Viết test cho các trường hợp quét mới**
  Trong `tests/test_candidate_extractor.py`:
  ```python
  def test_extract_lowercase_anchor_name():
      loader = ResourceLoader()
      loader.single_surnames = {"tôn", "kiều", "từ"}
      trimmer = BoundaryTrimmer(set())
      extractor = CandidateExtractor(loader, trimmer)

      line = "Người này mới đến bảo mẫu tên là tôn như sương, ba mươi chín tuổi."
      candidates = extractor.extract_candidates(line)
      assert any(c.name == "Tôn Như Sương" for c in candidates)

  def test_extract_dialogue_speaker():
      loader = ResourceLoader()
      loader.single_surnames = {"tần", "từ"}
      trimmer = BoundaryTrimmer(set())
      extractor = CandidateExtractor(loader, trimmer)

      line = 'Tần Vận khẽ mỉm cười nói: "Từ Thanh, ngươi mạnh khỏe!"'
      candidates = extractor.extract_candidates(line)
      assert any(c.name == "Tần Vận" for c in candidates)

  def test_prevent_anatomy_caching():
      loader = ResourceLoader()
      loader.single_surnames = {"dương"}
      loader.non_person = {"dương vật"}
      trimmer = BoundaryTrimmer(set())
      extractor = CandidateExtractor(loader, trimmer)

      line = "hắn đại dương vật hung hăng đỉnh vào."
      candidates = extractor.extract_candidates(line)
      assert not any("Dương Vật" in c.name for c in candidates)
      assert "dương vật" not in [s.lower() for s in extractor.session_cache]
  ```
- [ ] **Bước 2: Xóa bỏ việc tự động add bừa bãi vào `session_cache`**
  Trong `src/scanner/candidate_extractor.py`:
  Xóa bỏ đoạn code tự động thêm mọi ứng viên `confidence >= 0.88` vào `session_cache` ở cuối hàm `extract_candidates`. Thay vào đó, chỉ cache những tên xuất hiện cùng hồ sơ rõ ràng (`tuổi`, `nam/nữ`) hoặc cấu trúc đối thoại phát ngôn và **bắt buộc không nằm trong `non_person`**.
- [ ] **Bước 3: Thêm Regex Mỏ neo quan hệ bắt chữ thường (Anchor Patterns)**
  Thêm mẫu nhận diện tên đứng sau các từ mỏ neo (bảo mẫu, mẹ kế, tiểu di, cô cô, lão sư, bạn học, chủ nhiệm...):
  ```python
  self.anchor_rel_pattern = re.compile(
      rf'(?i:\b(bảo mẫu|mẹ kế|mẫu thân|mẹ ruột|tiểu di|cô cô|tỷ tỷ|muội muội|biểu tỷ|biểu muội|lão sư|thầy giáo|cô giáo|chủ nhiệm|bạn học|đồng học)\s+)'
      rf'([{VN_UPPER}{VN_LOWER}]+(?:\s+[{VN_UPPER}{VN_LOWER}]+){{1,3}})\b'
  )
  ```
- [ ] **Bước 4: Thêm Regex Cấu trúc hội thoại (Dialogue Attribution)**
  Thêm mẫu nhận diện người nói trước dấu `:` hoặc sau lời thoại:
  ```python
  self.dialogue_speaker_pattern = re.compile(
      rf'\b([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\s+(?:nói|hỏi|cười|quát|thở dài|lẩm bẩm|thầm nghĩ)\s*:\s*["“]'
  )
  self.dialogue_after_pattern = re.compile(
      rf'["”]\s*([{VN_UPPER}][{VN_LOWER}]+(?:\s+[{VN_UPPER}][{VN_LOWER}]+){{1,3}})\s+(?:nói|hỏi|cười|quát|thở dài|lẩm bẩm|đáp)\b'
  )
  ```
- [ ] **Bước 5: Tích hợp tra cứu De-convert mapping trực tiếp**
  Trong `extract_candidates`: Nếu dòng văn bản chứa cụm từ trong `self.loader.deconvert_dict`, ưu tiên trích xuất ngay với confidence `1.0`.
- [ ] **Bước 6: Chạy test candidate extractor**
  Chạy: `pytest tests/test_candidate_extractor.py tests/test_candidate_extractor_precision.py` và xác nhận tất cả PASS.

---

### Task 4: Nâng cấp ScannerEngine (Thẩm định hành vi nhân tính & Gom nhóm biến thể)

**Files:**
- Modify: `src/scanner/scanner_engine.py:116-120, 250-335`
- Test: `tests/test_deduplication.py`

**Interfaces:**
- Consumes: `CandidateMatch` từ Task 3
- Produces: `ScannerEngine.scan_file()` trả về danh sách `CharacterBlock` sạch, đã gom nhóm biến thể và ngữ cảnh chứng minh chuẩn.

- [ ] **Bước 1: Viết test cho gom nhóm biến thể danh xưng (Alias Clustering)**
  Trong `tests/test_deduplication.py`:
  ```python
  def test_alias_clustering():
      engine = ScannerEngine(ResourceLoader())
      blocks = [
          CharacterBlock(id="ch_1", source="Từ Thanh", target="Từ Thanh", context="Từ Thanh nói.", yeu_to_nhan_biet=""),
          CharacterBlock(id="ch_2", source="Tiểu Thanh", target="Tiểu Thanh", context="Tiểu Thanh cười.", yeu_to_nhan_biet=""),
      ]
      clustered = engine.cluster_aliases(blocks)
      # "Tiểu Thanh" phải được liên kết vào biến thể của "Từ Thanh"
      assert len(clustered) == 1
      assert clustered[0].target == "Từ Thanh"
  ```
- [ ] **Bước 2: Cập nhật hàm chấm điểm `_score_block` trong `ScannerEngine`**
  Ưu tiên tuyệt đối ngữ cảnh có **động từ hành vi nhân tính** (`nói`, `hỏi`, `cười`, `gật đầu`, `bước đi`, `nhìn`, `ôm`, `nghĩ`):
  ```python
  HUMAN_ACTION_VERBS = {"nói", "hỏi", "cười", "quát", "thở dài", "đáp", "gật đầu", "lắc đầu", "ôm", "nhìn", "bước", "đi"}

  @staticmethod
  def _score_block(confidence: float, context: str, line_idx: int) -> tuple:
      has_dialogue = '"' in context or '“' in context
      has_action = any(v in context.lower() for v in HUMAN_ACTION_VERBS)
      has_profile_cue = any(kw in context.lower() for kw in ("tuổi", "thê tử", "mẫu thân", "bảo mẫu", "tiểu di"))
      action_score = (2 if has_dialogue else 0) + (2 if has_action else 0) + (1 if has_profile_cue else 0)
      return (action_score, confidence, len(context), -line_idx)
  ```
- [ ] **Bước 3: Xây dựng thuật toán gom nhóm Alias trong `deduplicate_blocks`**
  Thêm logic liên kết:
  - Nếu thực thể `B` có dạng `Tiểu + [Tên]` hoặc `[Họ] + thiếu gia / tổng / lão sư`, và tồn tại thực thể `A` có dạng `[Họ] + [Tên]`, tự động gộp số lần xuất hiện của `B` vào `A` và bổ sung `B` vào danh sách biến thể.
- [ ] **Bước 4: Chạy test deduplication**
  Chạy: `pytest tests/test_deduplication.py` và xác nhận PASS.

---

### Task 5: Kiểm thử hồi quy hệ thống và Benchmark trên tệp mẫu thực tế

**Files:**
- Test: Toàn bộ suite test trong `tests/`
- Run: Chạy quét file `samples/Mỹ mẫu cám dỗ (1-309 chương kết thúc + phiên ngoại) (mẹ con, hậu cung).txt`
- Output: `scanner/scanner_all.json`

- [ ] **Bước 1: Chạy toàn bộ Unit Tests của dự án**
  Chạy: `pytest tests/` để đảm bảo không có bất kỳ regression nào trong `importer`, `replacer`, `scanner`.
- [ ] **Bước 2: Chạy thử nghiệm quét trên novel thực tế**
  Chạy lệnh:
  ```powershell
  python -m src.scanner.main --input "samples/Mỹ mẫu cám dỗ (1-309 chương kết thúc + phiên ngoại) (mẹ con, hậu cung).txt" --output "scanner" --min-count 2
  ```
- [ ] **Bước 3: Xác minh kết quả đầu ra trong `scanner/scanner_all.json`**
  Viết script đối chiếu tự động kiểm tra:
  1. Số lượng mục rác (`dương vật`, `bạo địt`, `phòng bên`, `bao trùm`...): Phải bằng 0.
  2. Bắt được các nhân vật chữ thường: `Tôn Như Sương`, `Kiều Ngọc`, `Từ Quảng`, `Quan Uyển Bạch`...
  3. Bắt được tên de-convert: `Tô Diệc Khả`, `Mặc Đầu Hạ`, `Mã Văn Quân`...
  4. Tên `Văn Liên Tâm` còn nguyên vẹn, không bị cụt thành `văn Liên`.
