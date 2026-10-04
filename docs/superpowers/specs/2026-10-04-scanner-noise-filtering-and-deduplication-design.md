# Thiết kế Kỹ thuật: Bộ lọc Nhiễu, Làm sạch Từ Rác và Khử Trùng Lặp Nâng Cao cho Scanner

- **Ngày tạo:** 2026-10-04
- **Dự án:** Convert_File_V2
- **Thư mục mục tiêu:** `src/scanner/`
- **Mục đích:** Khắc phục triệt để tình trạng trích xuất từ rác, giữ lại tên viết thường hợp lệ, lọc bỏ từ điển tiếng Việt 2 từ (như "xoáy thuận"), xử lý chuẩn xác họ kép/tên 4 chữ, và gộp biến thể source chính xác.

---

## 1. Vấn đề Hiện tại & Nguyên nhân

1. **Từ điển đã biết bị bỏ sót**:
   - `ResourceLoader` chỉ nạp `character_dict.json` vào `known_characters`, bỏ qua `chinese_names_dict.json` và chưa đối chiếu đầy đủ cả `source` lẫn `target`.
   - Kết quả: Các nhân vật đã được dịch/chuẩn hóa vẫn bị quét lại nhiều lần.

2. **Quét tên viết thường sinh ra hàng ngàn từ rác**:
   - `_extract_lowercase_action_candidates()` trong `candidate_extractor.py` cho phép mọi từ bắt đầu bằng một từ trong danh sách họ (ví dụ: "thân", "đường", "phương", "hoa"...) kết hợp với động từ thông dụng ("đi", "chạy", "nhìn", "nói"...) được nhận là tên nhân vật.
   - Các từ thông dụng tiếng Việt như `thân tay gạt` (duỗi tay gạt), `phương tâm hươu` (phương tâm hươu chạy), `đường có mỹ nữ`... bị trích xuất hàng trăm lần với độ tin cậy giả tạo 0.95.

3. **Chưa tận dụng từ điển tiếng Việt 2 từ**:
   - File `resources/dictionaries/vietnamese_words.txt` có hơn 31.000 từ ghép 2 từ (như `xoáy thuận`, `từ chối`, `cổ kính`, `cổ nhân`, `thân thể`, `du lịch`...).
   - Hiện tại bộ trích xuất không kiểm tra danh sách này, dẫn đến các từ ghép tiếng Việt thông dụng bị gán nhầm thành tên người.

4. **Dính động từ/từ rác ở đuôi tên**:
   - Các cụm như `tần khả cầm đi`, `tần khả phi thở`, `âu dương như tuyết đi` bị dính động từ `đi`, `thở` vào tên.
   - Cần cơ chế bóc tách động từ tự động dựa trên độ dài họ (họ đơn vs họ kép) và kiểm tra danh mục động từ hành động.

5. **File `scanner_all.json` lưu rác bừa bãi**:
   - Hiện tại toàn bộ ứng viên thô được lưu vào `scanner_all.json`, khiến người dùng nhầm lẫn giữa dữ liệu rác thô và dữ liệu sạch.

---

## 2. Mục tiêu Thiết kế (Design Goals)

1. **Chỉ lấy nhân vật mới**:
   - Bỏ qua 100% các từ/tên đã tồn tại trong `character_dict.json`, `chinese_names_dict.json` và `common_dict.json` (kiểm tra cả `source` và `target`).
2. **Bảo tồn tên viết thường hợp lệ**:
   - Vẫn nhận diện tên nhân vật viết thường (như `tần khả cầm`, `tần khả phi`, `la mẫn`, `tô tuyết nghi`...) nhưng loại bỏ các cụm từ ngữ thông thường.
3. **Lọc bỏ và cắt bớt theo từ điển tiếng Việt 2 từ (`vn_2word_set`)**:
   - **Loại bỏ (Reject)**: Nếu ứng viên có đúng 2 từ và nằm trong `vietnamese_words.txt` 2 từ (ví dụ `xoáy thuận`, `từ chối`, `cổ kính`...) $\rightarrow$ Loại bỏ ngay lập tức.
   - **Cắt bớt (Trim)**: Nếu ứng viên dính từ ghép 2 từ ở đuôi (ví dụ `vũ mỹ vương phi` $\rightarrow$ cắt `vương phi` thành `Vũ Mỹ`).
4. **Loại bỏ từ chức năng/ngữ pháp ở giữa tên**:
   - Tên người không thể chứa các từ: `có`, `của`, `được`, `bị`, `đang`, `đã`, `sẽ`, `lại`, `rất`, `quá`, `một`, `hai`... (loại bỏ `đường có mỹ nữ`, `lại ra vẻ`...).
5. **Xử lý chuẩn xác Họ kép và Tên 4 chữ**:
   - Họ kép 2 chữ (`Âu Dương`, `Thượng Quan`...): Tên tối đa 4 chữ. Nếu có chữ thứ 5 là động từ (`âu dương như tuyết đi` $\rightarrow$ cắt thành `Âu Dương Như Tuyết`).
   - Họ đơn 1 chữ: Tên tối đa 3 chữ. Nếu có chữ thứ 4 là động từ (`tần khả cầm đi` $\rightarrow$ cắt thành `Tần Khả Cầm`, `tần khả phi thở` $\rightarrow$ cắt thành `Tần Khả Phi`).
6. **Khử trùng lặp & Gộp biến thể chính xác (Safe Merging)**:
   - Gộp biến thể viết thường vào viết hoa (`tần khả cầm` $\rightarrow$ `Tần Khả Cầm`).
   - Bóc tách tiền tố/hậu tố dính kèm (`hoa Mã Lan` $\rightarrow$ gộp vào `Mã Lan`).
   - Gộp tên ngắn vào tên dài khi và chỉ khi **CÙNG HỌ** và **CÙNG TÊN CHÍNH CUỐI CÙNG**. Tuyệt đối không gộp `Tần Khả Cầm` và `Tần Khả Phi` vì khác tên chính ("Cầm" vs "Phi").
7. **Làm sạch `scanner_all.json`**:
   - Chỉ lưu các ứng viên đã vượt qua bộ lọc làm sạch.

---

## 3. Kiến trúc & Chi tiết Kỹ thuật

### 3.1. Nâng cấp `ResourceLoader` (`src/scanner/resource_loader.py`)

- **Nạp từ điển tên chuẩn**:
  - Đọc cả `character_dict.json` và `chinese_names_dict.json`.
  - Lưu vào `self.known_characters`: lưu cả khóa viết thường lẫn giá trị đích viết thường để đối soát đa chiều.
- **Nạp tập từ ghép 2 từ tiếng Việt (`vn_2word_set`)**:
  - Đọc file `resources/dictionaries/vietnamese_words.txt`.
  - Chỉ lọc lấy các dòng có `len(line.split()) == 2`.
  - Khởi tạo tập `self.vn_2word_set: set[str]`.

```python
# Pseudo-code trong ResourceLoader
def load_vn_2word_set(self, path: Path) -> set[str]:
    words = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip().lower()
            if line and not line.startswith("#") and len(line.split()) == 2:
                words.add(line)
    return words
```

### 3.2. Nâng cấp `BoundaryTrimmer` (`src/scanner/boundary_trimmer.py`)

- Mở rộng danh mục động từ hành động đơn âm tiết (`SINGLE_ACTION_VERBS`):
  `{"đi", "thở", "nói", "hỏi", "cười", "quát", "nghĩ", "nhìn", "bước", "chạy", "ngồi", "đứng", "ôm", "hôn", "đáp", "kêu", "hét", "lẩm", "bẩm", "gật", "lắc"}`
- Thêm phương thức `trim_action_suffix(text: str) -> str`:
  - Phân tích từ đầu tiên:
    - Nếu 2 từ đầu là Họ kép trong `compound_surnames` (độ dài họ = 2):
      - Nếu độ dài $\ge 5$ và từ thứ 5 nằm trong `SINGLE_ACTION_VERBS` $\rightarrow$ Cắt bỏ từ thứ 5.
    - Nếu từ đầu là Họ đơn (độ dài họ = 1):
      - Nếu độ dài $\ge 4$ và từ thứ 4 nằm trong `SINGLE_ACTION_VERBS` $\rightarrow$ Cắt bỏ từ thứ 4.
- Thêm phương thức `trim_vn_compound_suffix(text: str, vn_2word_set: set[str]) -> str`:
  - Nếu cụm từ có độ dài $\ge 4$:
    - Kiểm tra nếu 2 từ cuối tạo thành 1 cụm trong `vn_2word_set` (ví dụ `vương phi`, `bác sĩ`, `chủ tịch`...):
      - Cắt bỏ 2 từ cuối nếu phần còn lại vẫn bắt đầu bằng họ hợp lệ và có độ dài $\ge 2$.
      - Ví dụ: `vũ mỹ vương phi` (4 từ) $\rightarrow$ 2 từ cuối là `vương phi` $\rightarrow$ cắt còn `vũ mỹ`.

### 3.3. Nâng cấp `CandidateExtractor` (`src/scanner/candidate_extractor.py`)

- Nâng cấp hàm kiểm định phủ định `_is_negative(text, skip_known)`:
  1. **Kiểm tra từ điển đã biết**:
     - Nếu `low in self.loader.known_characters` hoặc `norm_name.lower() in self.loader.known_characters` $\rightarrow$ Bỏ qua (nếu `skip_known=True`).
     - Nếu `low in self.loader.common_dict` $\rightarrow$ Bỏ qua.
  2. **Kiểm tra từ ghép 2 từ tiếng Việt (`vn_2word_set`)**:
     - Nếu ứng viên có đúng 2 từ và `low in self.loader.vn_2word_set` (ví dụ `xoáy thuận`, `từ chối`, `cổ kính`, `cổ nhân`, `chi tử`...) $\rightarrow$ **Return True (Loại bỏ)**.
  3. **Kiểm tra từ chức năng ở giữa tên**:
     - Danh sách từ cấm ngữ pháp: `{"có", "của", "được", "bị", "đang", "đã", "sẽ", "lại", "rất", "quá", "nhiều", "một", "hai", "cái"}`.
     - Nếu bất kỳ từ nào trong số này xuất hiện ở vị trí giữa (không phải họ) $\rightarrow$ **Return True (Loại bỏ)**.
- Nâng cấp `_extract_lowercase_action_candidates()`:
  - Khi bắt được cụm từ viết thường:
    - Chạy qua `trim_action_suffix` để bóc tách các từ như `đi`, `thở`.
    - Kiểm tra `_is_negative` với `vn_2word_set` để không nhận các cụm như `phương tâm hươu` hay `thân tay gạt`.

### 3.4. Nâng cấp `ScannerEngine` (`src/scanner/scanner_engine.py`)

- Trong `scan_file()`:
  - Trước khi thêm vào `tracked`, cho ứng viên chạy qua:
    1. `trim_action_suffix`
    2. `trim_vn_compound_suffix`
    3. `_is_negative`
  - Nếu sau khi cắt còn lại $< 2$ từ hoặc không bắt đầu bằng họ hợp lệ $\rightarrow$ Loại bỏ.
- Trong `cluster_aliases()`:
  - **Khử trùng lặp Tên chính (Given name invariant)**:
    - Khi so sánh 2 khối nhân vật:
      - Bóc tách: `Họ` và `Tên chính` (từ cuối cùng).
      - `tần khả cầm` có Tên chính = `cầm`.
      - `tần khả phi` có Tên chính = `phi`.
      - Vì `cầm != phi` $\rightarrow$ Tuyệt đối không gộp.
  - **Bóc tách tiền tố đơn lẻ (Prefix stripping)**:
    - Nếu gặp `hoa Mã Lan`, kiểm tra thấy `Mã Lan` đã tồn tại với tần suất cao $\rightarrow$ gộp `hoa Mã Lan` vào `Mã Lan`.
  - **Gộp dạng viết thường vào viết hoa**:
    - Khi có cả `tần khả cầm` và `Tần Khả Cầm`, gộp toàn bộ lượt xuất hiện và dòng xuất hiện về `Tần Khả Cầm`.

---

## 4. Kế hoạch Kiểm thử & Xác minh (Verification Plan)

### 4.1. Unit Tests Mới (`tests/test_scanner_noise_and_dedup.py`)
1. **Test loại trừ từ ghép 2 từ tiếng Việt**:
   - `xoáy thuận` $\rightarrow$ Bị loại bỏ, không sinh ra candidate.
   - `từ chối` $\rightarrow$ Bị loại bỏ.
   - `cổ kính` $\rightarrow$ Bị loại bỏ.
2. **Test cắt bớt từ ghép 2 từ dính ở đuôi**:
   - `vũ mỹ vương phi` $\rightarrow$ Cắt thành `Vũ Mỹ`.
3. **Test phân biệt 2 nhân vật cùng họ dính động từ**:
   - Đầu vào văn bản có: `tần khả cầm đi tới...` và `tần khả phi thở dài...`
   - Kết quả phải tạo ra đúng 2 nhân vật:
     - Nhân vật 1: `Tần Khả Cầm` (không còn chữ `đi`).
     - Nhân vật 2: `Tần Khả Phi` (không còn chữ `thở`).
     - Hai nhân vật không được gộp vào nhau.
4. **Test họ kép 2 chữ và tên 4 chữ**:
   - `âu dương như tuyết đi` $\rightarrow$ Trích xuất thành `Âu Dương Như Tuyết`.
   - `trần ngọc ánh tuyết cười` $\rightarrow$ Trích xuất thành `Trần Ngọc Ánh Tuyết`.
5. **Test loại trừ nhân vật đã có trong từ điển**:
   - Nhân vật có trong `character_dict.json` hoặc `chinese_names_dict.json` sẽ không xuất hiện khi `skip_known=True`.

### 4.2. Chạy Kiểm thử Toàn bộ Hệ thống
- Chạy `pytest` đảm bảo toàn bộ bộ 106 tests cũ và các tests mới đều đạt 100%.
- Chạy thử nghiệm quét trên file mẫu `samples/exam.txt` và kiểm tra `scanner_all.json` để xác nhận số lượng từ rác giảm mạnh và dữ liệu trích xuất sạch sẽ.
