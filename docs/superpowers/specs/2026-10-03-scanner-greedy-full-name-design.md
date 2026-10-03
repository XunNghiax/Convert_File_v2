# Thiết kế Cải tiến Thuật toán Scanner: Tối đa hóa Bắt Đủ Họ và Tên (Greedy Full-Name Extraction)

## 1. Bối cảnh & Vấn đề thực tế
Khi đối chiếu kết quả quét `scanner_master.json` / `scanner_all.json` với danh sách nhân vật chuẩn `danh_sach_nhan_vat.md` (91 nhân vật từ tiểu thuyết "Mỹ mẫu cám dỗ"), thuật toán quét hiện tại gặp 5 vấn đề nghiêm trọng:
1. **Cắt cụt tên 3-4 từ thành 2 từ (Truncation):** Do `BoundaryTrimmer` tự ý xóa từ thứ 3 nếu nó nằm trong `trailing_stopwords` (ví dụ `Tôn Như Sương` bị cắt thành `tôn như`, `Đường Thiền Y` thành `đường thiền`, `Trần Mộng Di` thành `trần mộng`, `Diệp Mạn Văn` thành `diệp mạn`).
2. **Cắt mất họ "Từ":** Do chữ "Từ" bị xếp vào danh sách từ thừa đầu câu (`DEFAULT_LEADING`), khiến các tên như `Từ Tân Đồng`, `Từ Linh San`, `Từ Vân Tuyết` bị gọt cụt mất họ.
3. **Bỏ sót tên viết thường:** Tiểu thuyết convert có nhiều tên nhân vật viết thường (`từ nguyệt`, `từ ninh`, `kiều chước hoa`, `ngu triệu hưng`, `lỗ du`...). Scanner hiện tại chỉ bắt tên viết thường nếu đứng sát sau một số ít mỏ neo xưng hô.
4. **Thiếu từ điển Họ:** Thiếu các họ phổ biến như `Liêu` (廖), `Mặc` (墨), `Ngả` (艾), họ kép `Thiên Diệp` (千叶), `Tây Xuyên` (西川), `Nạp Lan` (纳兰).
5. **Gãy tên phiên âm / Tên nước ngoài:** Không hỗ trợ dấu chấm giữa `·` hoặc dấu gạch nối trong tên Latinh/phiên âm (`Đại Na · Hải Ngũ Đức`, `An Cát Lệ Na · Rockefeller`, `Joanna`).

## 2. Mục tiêu thiết kế
- **Nguyên tắc:** Bắt dư hơn bỏ sót (High Recall). Chấp nhận có thể kèm từ rác hoặc động từ dính đuôi, nhưng **phải giữ trọn vẹn Họ và Tên (2-4 từ)** để khâu AI (Gemini) hoặc quy trình lọc tiếp theo có đủ dữ liệu xử lý.
- Tăng tỷ lệ bắt trọn vẹn đủ họ tên các nhân vật trong truyện từ ~11% lên trên 90%.
- Không làm suy giảm tốc độ xử lý dòng (duy trì >10,000 dòng/giây).

## 3. Các thay đổi kiến trúc

### 3.1 Bổ sung Họ & Mỏ neo tài nguyên (`resources/filters/`)
- Cập nhật `resources/filters/surnames.txt`:
  - Thêm họ đơn: `liêu`, `mặc`, `ngả`, `cừu`, `phí`, `khưu`, `khuất`, `chúc`, `trang`, `nhiếp`.
  - Thêm họ kép / phiên âm: `thiên diệp`, `tây xuyên`, `nạp lan`, `đông phương`, `nam cung`, `âu dương`, `tư mã`, `độc cô`, `gia cát`, `hoàng phủ`.
- Mở rộng tập mỏ neo xưng hô gia đình/quan hệ trong `CandidateExtractor.ANCHOR_TERMS`:
  - Thêm: `ba ba`, `bố`, `ông ngoại`, `bà ngoại`, `mẹ kế`, `mẹ ruột`, `chủ tịch`, `giám đốc`, `thích khách`, `nha đầu`, `tiểu nha đầu`, `tên là`, `ta gọi`, `gọi là`, `tự xưng là`.

### 3.2 Tái cấu trúc `BoundaryTrimmer` (`src/scanner/boundary_trimmer.py`)
- **Bảo vệ Họ ở đầu:** Không xóa `từ` hoặc bất kỳ họ hợp lệ nào ở đầu cụm từ nếu cụm từ có từ 2 đến 4 từ.
- **Bảo vệ Tên ở cuối:** Tắt hoàn toàn việc xóa từ thứ 3 bằng `trailing_stopwords` nếu cụm từ bắt đầu bằng một Họ hợp lệ hoặc đi sau mỏ neo xưng hô. Chỉ trim các hư từ rõ ràng khi cụm từ dài trên 4 từ.

### 3.3 Mở rộng quy tắc quét trong `CandidateExtractor` (`src/scanner/candidate_extractor.py`)
1. **Quét Tham Lam (Greedy Match cho TitleCase & Mỏ neo):**
   - Khi gặp mỏ neo hoặc viết hoa: Quét lấy cụm 2, 3 và 4 từ liên tiếp.
   - Không vội vàng chốt 2 từ khi từ thứ 3 là từ Hán Việt/tên người.
2. **Bộ quét Tên viết thường (Lowercase Pattern with Action/Subject Cue):**
   - Mẫu: `\b(họ_hợp_lệ)\s+([a-zà-ỹ]+(?:\s+[a-zà-ỹ]+){1,2})\b`
   - Kèm điều kiện xác thực:
     - Đứng làm chủ ngữ của động từ hành động/cảm xúc (`nói`, `hỏi`, `cười`, `nhìn`, `bước`, `ôm`, `nghe`, `trong lòng`, `đưa ra`, `nghĩ`, `thở dài`...).
     - Hoặc đứng sau mỏ neo quan hệ/xưng hô/vai vế.
3. **Bộ quét Tên nước ngoài / Phiên âm đặc thù:**
   - Hỗ trợ ký tự dấu nối/chấm giữa: `[A-ZÀ-Ỹa-zà-ỹ]+(?:\s*[·\-\.]\s*[A-ZÀ-Ỹa-zà-ỹ]+)+`
   - Bắt các tên Latinh độc lập có trong ngữ cảnh đối thoại hoặc giới thiệu (`Joanna`, `Mary`...).

### 3.4 Hợp nhất Mảnh vỡ & Siêu chuỗi (`src/scanner/scanner_engine.py`)
- Nâng cấp `cluster_aliases` và `deduplicate_blocks`:
  - **Super-string consolidation:** Nếu xuất hiện cả `Đường Thiền` và `Đường Thiền Y` (cùng họ `Đường`, cùng xuất hiện trong ngữ cảnh tương đồng), tên dài hơn `Đường Thiền Y` được chọn làm tên đại diện chính (Primary Target), tên ngắn được gộp vào danh sách biến thể (`bien_the`).
  - Tương tự, nếu `Từ Thanh` xuất hiện độc lập và có `Từ Thanh khiêu` (dính từ hành động), hệ thống ưu tiên giữ `Từ Thanh` và tách từ dính.

## 4. Kế hoạch Kiểm thử & Đo lường
- Viết unit tests kiểm tra:
  - Giữ nguyên họ `Từ` (`Từ Tân Đồng`, `Từ Linh San`, `Từ Vân Tuyết`).
  - Giữ nguyên 3 từ (`Tôn Như Sương`, `Đường Thiền Y`, `Trần Mộng Di`, `Diệp Mạn Văn`).
  - Quét được tên viết thường (`từ nguyệt đưa ra...`, `kiều chước hoa nghiêm túc nhìn...`, `ngu triệu hưng nhìn đến...`).
  - Quét tên nước ngoài có dấu chấm giữa (`Đại Na · Hải Ngũ Đức`, `An Cát Lệ Na · Rockefeller`).
- Chạy đối chiếu với 91 nhân vật trong `danh_sach_nhan_vat.md` để đánh giá recall rate.
