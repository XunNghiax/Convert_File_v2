# TÀI LIỆU THIẾT KẾ KỸ THUẬT: THUẬT TOÁN QUÉT VÀ NHẬN DIỆN TÊN NHÂN VẬT (CHARACTER SCANNER)

- **Dự án**: Convert_File_v2
- **Tập tin dữ liệu mẫu**: `exam.txt`
- **Tập tin đối chiếu cơ sở**: `file_nhan_vat.json`
- **Thư mục bộ lọc**: `filters/` (`surnames.txt`, `pronouns.txt`, `non_person.txt`, `trailing_stopwords.txt`, `blacklist.txt`)
- **Bộ từ điển**: `data/` (`character_dict.json`, `common_dict.json`)
- **Thư mục xuất kết quả**: `scanner/`

---

## 1. Mục tiêu và Kiến trúc Tổng thể

### 1.1 Mục tiêu
1. Tự động tìm kiếm và nhận diện tên nhân vật từ văn bản truyện convert/dịch máy thô (`exam.txt`) với độ bao phủ (Recall) cao và độ chính xác (Precision) tốt.
2. Xử lý được các đặc thù của truyện convert tiếng Trung sang tiếng Việt:
   - Tên viết hoa chuẩn (TitleCase): "Trương Tử Kiến", "Lâm Thi Âm".
   - Tên bị lỗi convert viết thường: "lâm bằng tường", "hứa tiểu điệp", "Lưu tuệ đẹp".
   - Tên dính từ thừa/từ đuôi: "Nguyễn mai hai", "Ngọc Thiến thân".
   - Tên người Nhật/phương Tây bị phiên âm Hán Việt thô.
3. Xuất kết quả vào thư mục `scanner/`:
   - `scanner_master.json`: Toàn bộ dữ liệu trích xuất.
   - Các file `scanner_1.md`, `scanner_2.md`... (mỗi file 30-50 block kèm prompt hướng dẫn AI từ `prompt.md`).

### 1.2 Kiến trúc Hệ thống Pipeline

```
[exam.txt] + [filters/] + [prompt.md]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 1. Resource Loader & Preprocessor                      │
│    - Nạp surnames, pronouns, non_person, blacklist     │
│    - Tối ưu tra cứu bằng Set & Trie (O(1))             │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Line & Sentence Segmenter                           │
│    - Đọc theo dòng (lưu `dong_xuat_hien`)              │
│    - Tách câu thông minh (Sentence boundary)           │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Multi-tier Candidate Extractor & Scorer             │
│    - Nhóm A: Profile intro (tuổi, giới tính, chức vụ)  │
│    - Nhóm B: Họ + Tên (TitleCase & Lowercase do lỗi)   │
│    - Nhóm C: Chủ ngữ tương tác & Ngữ cảnh hội thoại    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Boundary Trimmer & Negative Filter                  │
│    - Cắt từ dính đuôi (trailing stopwords)             │
│    - Lọc bỏ địa danh, môn phái, đại từ, blacklist      │
│    - Tính điểm tin cậy (Confidence Score)              │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Centered Context Expander                           │
│    - Lấy `source` làm trung tâm                        │
│    - Mở rộng trọn vẹn câu (+ câu lân cận nếu quá ngắn) │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 6. Output Packager & Prompt Integrator                 │
│    - scanner/scanner_master.json                       │
│    - scanner/scanner_1.md, scanner_2.md...             │
│      (Mỗi file 30-50 block kèm prompt.md cho AI)       │
└────────────────────────────────────────────────────────┘
```


---

## 2. Chi Tiết Thuật Toán Nhận Diện (Heuristic Rules, Trimming & Scoring)

### 2.1 Bộ quy tắc nhận diện ứng viên (Candidate Extraction Rules)

#### Quy tắc 1: Cấu trúc hồ sơ giới thiệu (Profile Cue Pattern) - Trọng số (+0.45)
- **Mẫu Tuổi & Giới tính**: `<Cụm từ 2-4 từ> [,\s-]+ (\d{1,2}\s*tuổi|nam|nữ)`
  - Hỗ trợ cả tên viết thường do dịch máy (`lâm bằng tường, 53 tuổi`, `Lưu tuệ đẹp, 32 tuổi`).
- **Mẫu Quan hệ nhân thân**: `<Cụm từ> + <từ quan hệ>` hoặc `<từ quan hệ> + của + <Cụm từ>`
  - Từ khóa: `thê tử`, `mẫu thân`, `tỷ tỷ`, `muội muội`, `kế mẫu`, `đệ đệ`, `con`, `nữ nhi`, `ba ba`, `mẹ`, `chị dâu`, `dì`, `vợ trước`...
- **Mẫu Chức danh / Nghề nghiệp**: `<chức vụ> + <Cụm từ>` hoặc ngược lại
  - Từ khóa: `bang chủ`, `đà chủ`, `tỉnh trưởng`, `thị trưởng`, `cục trưởng`, `tổng giám đốc`, `phó quản lý`, `giáo sư`, `y tá trưởng`...

#### Quy tắc 2: Đối chiếu Họ & Cụm từ viết hoa (Surname & TitleCase Pattern) - Trọng số (+0.35)
- Nhận diện cụm 2-4 từ bắt đầu bằng họ trong `filters/surnames.txt`:
  - Họ đơn: `Trương`, `Lâm`, `Trần`, `Lý`, `Vương`, `Mã`, `Tô`, `Kim`, `Diệp`, `Giả`, `Long`, `Tiêu`, `Hàn`...
  - Họ kép: `Âu Dương`, `Đông Phương`, `Gia Cát`, `Tư Mã`, `Thượng Quan`...
- Kiểm tra viết hoa: TitleCase toàn phần tăng điểm; viết thường hoặc lẫn từ miêu tả vẫn được giữ nếu khớp Quy tắc 1.

#### Quy tắc 3: Dấu hiệu dẫn thoại và hành vi chủ ngữ (Narrative & Dialogue Cue) - Trọng số (+0.25)
- Động từ phát ngôn: `nói:`, `hỏi:`, `la lớn:`, `thở dài`, `cười khẩy`, `nghĩ thầm`, `quát to`...
- Danh xưng kính ngữ: `tiểu thư`, `công tử`, `đại hiệp`, `sư huynh`, `sư muội`, `tiền bối`, `chú`, `bác`...

#### Quy tắc 4: Bộ nhớ đệm thực thể động (Dynamic Session Cache) - Trọng số (+0.40)
- Tên nhân vật đã xác nhận tin cậy ở các dòng trước (hoặc có sẵn trong `data/character_dict.json`) được nạp vào cache phiên làm việc để nhận diện tức thì ở các dòng tiếp theo.

### 2.2 Thuật toán cắt tỉa ranh giới từ thừa (Boundary Trimmer)
- Kiểm tra token cuối cùng trong `filters/trailing_stopwords.txt` (`hai`, `người`, `thân`, `con`, `của`, `đích`, `kia`, `này`...).
- Lặp cắt tỉa cho đến khi token cuối hợp lệ, đưa từ bị cắt trả về phần `context`.

### 2.3 Bộ lọc loại trừ âm tính (Negative Filtering)
- Khớp `filters/pronouns.txt` (đại từ).
- Khớp `filters/non_person.txt` (địa danh, tổ chức, môn phái).
- Khớp `data/common_dict.json` (từ ngữ miêu tả thông thường).
- Khớp `filters/blacklist.txt`.
- Cấu trúc không hợp lệ (chứa số, ký tự đặc biệt, dài hơn 5 từ).

### 2.4 Công thức tính điểm tin cậy (Confidence Scoring)
- `Confidence = Base_Score + Sum(Feature_Weights) - Negative_Penalties`
- Ngưỡng đạt chuẩn: $\ge 0.50$.
- Ngưỡng nghi ngờ (cần AI thẩm định trong file .md): $0.35 - 0.49$.
- Dưới $0.35$: Loại bỏ.

---

## 3. Trích Xuất Ngữ Cảnh Trung Tâm & Cơ Chế Xuất File

### 3.1 Mở rộng ngữ cảnh trung tâm (Centered Context Expander)
- **Đầu vào**: Dòng văn bản hiện tại, vị trí xuất hiện của `source`.
- **Giải thuật**:
  1. Phân đoạn ranh giới câu theo dấu câu: `.`, `!`, `?`, `;`.
  2. Lấy trọn vẹn câu chứa `source`.
  3. Kiểm tra độ dài câu: Nếu câu ngắn ($< 30$ ký tự hoặc $< 6$ từ), tự động gộp câu liền kề trước hoặc sau.
  4. Đảm bảo ngữ cảnh cung cấp đủ đại từ xưng hô, mối quan hệ nhân thân hoặc chức vụ để AI hiểu trọn vẹn bối cảnh.

### 3.2 Cơ chế đóng gói đầu ra thư mục `scanner/`
1. **`scanner/scanner_master.json`**:
   - Chứa mảng toàn bộ các đối tượng nhân vật trích xuất được.
2. **`scanner/scanner_<stt>.md`**:
   - Mỗi file chứa từ **30 đến 50 block** (mặc định 40 block/file).
   - Cấu trúc file:
     - **Header**: Toàn bộ nội dung hướng dẫn từ `prompt.md`.
     - **Body**: Khối code block JSON chứa danh sách các block:
       ```json
       [
         {
           "id": "ch_0001",
           "source": "Lâm bằng tường",
           "target": "Lâm Bằng Tường",
           "context": "Lâm bằng tường, 53 tuổi, Nam Phương tỉnh tỉnh trưởng",
           "dong_xuat_hien": 191
         }
       ]
       ```

---

## 4. Xử Lý Ngoại Lệ & Độ Tin Cậy (Error Handling)
- **Xử lý mã hóa văn bản (Encoding)**: Tự động phát hiện và hỗ trợ `utf-8`, `utf-8-sig` để không bị lỗi dấu tiếng Việt.
- **Fallback bộ lọc**: Nếu thiếu bất kỳ file từ điển nào trong `filters/`, hệ thống sử dụng danh sách dự phòng tích hợp sẵn trong code, không gây crash chương trình.
- **Khử trùng lặp (Deduplication)**: Nếu trong 1 dòng văn bản có nhiều quy tắc cùng bắt trúng 1 tên hoặc có các biến thể con/mẹ (ví dụ "Trương Tử Kiến" và "Tử Kiến"), ưu tiên chuỗi dài nhất có điểm tin cậy cao nhất.

---

## 5. Chiến Lược Đánh Giá & Kiểm Thử (Evaluation & Testing)
- **Tập kiểm thử mẫu (Ground Truth)**: Sử dụng 223 thực thể trong `file_nhan_vat.json` làm cơ sở đối chiếu.
- **Chỉ số đo lường**:
  - **Recall**: Tỷ lệ phần trăm nhân vật trong `file_nhan_vat.json` được thuật toán quét trúng.
  - **Precision**: Tỷ lệ phần trăm các tên trích xuất được thực sự là tên người (không dính địa danh, rác).
  - **F1-Score**: Điểm cân bằng giữa Precision và Recall.
