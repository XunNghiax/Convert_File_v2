# TÀI LIỆU THIẾT KẾ KỸ THUẬT: GEMINI UPLOADER & IMPORT.JSON GENERATOR

- **Dự án**: Convert_File_v2
- **Thư mục nguồn cần xử lý**: `scanner/` (`scanner_1.md`, `scanner_2.md`... `scanner_N.md`)
- **Profile Chrome**: `user_data/chrome_profiles/chrome_data_1`
- **File đích cuối cùng**: `import.json`
- **File lưu tiến trình**: `scanner/.gemini_progress.json`

---

## 1. Mục tiêu và Kiến trúc Tổng thể

### 1.1 Mục tiêu
1. Tự động hóa việc nạp từng file markdown phân mảnh (`scanner_1.md` -> `scanner_7.md`) lên Google Gemini Web UI (`https://gemini.google.com/app`).
2. Tận dụng trực tiếp session đăng nhập của Profile Google Chrome (`user_data/chrome_profiles/chrome_data_1`).
3. Chờ đợi phản hồi của Gemini ổn định, trích xuất chính xác khối dữ liệu JSON biên tập từ phản hồi.
4. Ghi nhận tiến trình (Resume checkpoint): Nếu gặp sự cố mạng hoặc dừng đột ngột, lần sau chạy sẽ tự động tiếp tục từ file chưa hoàn thành mà không phải chạy lại từ đầu.
5. Khi hoàn thành 1 file, ghi vào file  **`import.json`**. và các file tiếp theo cứ dán tiếp tục sau đó

### 1.2 Kiến trúc Hệ thống

```
┌────────────────────────────────────────────────────────┐
│ 1. Scanner Directory Reader                            │
│    - Quét danh sách file: scanner_1.md -> scanner_N.md │
│    - Đọc file .gemini_progress.json để lọc file đã xong│
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. Playwright Browser Controller                       │
│    - Nạp profile: user_data/chrome_profiles/chrome_data_1
│    - Mở https://gemini.google.com/app (channel="chrome")│
│    - Kiểm tra trạng thái giao diện và khung chat       │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. Automated File Dispatcher & Response Poller         │
│    - Điền nội dung file markdown vào chatbox           │
│    - Bấm Gửi & Theo dõi phản hồi (.model-response-text)│
│    - Chờ ổn định nội dung (stable count >= 3 chu kỳ)   │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 4. Response Parser & Checkpoint Saver                  │
│    - Trích xuất khối ```json ... ```                   │
│    - Parse JSON an toàn                                │
│    - Lưu kết quả của file vào .gemini_progress.json    │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│ 5. Master Aggregator & Import.json Exporter            │
│    - Gộp kết quả của toàn bộ các file                  │
│    - Xuất file import.json hoàn chỉnh                  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Chi Tiết Tương Tác Giao Diện Gemini (DOM Selectors & Flow)

Kế thừa các selector đã kiểm nghiệm thực tế từ `NewInject/src/gemini_bot.py`:
1. **Khung nhập chat (Chat Box)**:
   - Selector: `div[contenteditable="true"]`
   - Phương thức: `fill()` hoặc `innerText` injection kèm dispatch event `input`.
2. **Nút Gửi (Send Button)**:
   - Các selector ưu tiên:
     - `button[aria-label*="Gửi tin nhắn" i]`
     - `button[aria-label*="Send message" i]`
     - `button[aria-label*="Gửi" i]:not([aria-label*="phản hồi"])`
     - `[data-testid="send-button"]`
3. **Phần tử câu trả lời (Response Text)**:
   - Selector: `.model-response-text`
   - Thuật toán đợi:
     - Đếm số lượng response ban đầu: `initial_count`.
     - Lặp kiểm tra mỗi 2 giây: Nếu số response tăng, lấy văn bản phản hồi cuối cùng.
     - So sánh văn bản qua các chu kỳ: Khi văn bản không thay đổi và có độ dài hợp lý trong 3 lần liên tiếp (khoảng 6 giây), kết luận Gemini đã sinh xong.

---

## 3. Trích Xuất và Xử Lý JSON (JSON Parser)
- Sử dụng Regex tìm khối code block: `r'```(?:json)?\s*\n(.*?)\n\s*```'`.
- Fallback: Nếu Gemini quên đóng ```` ``` ````, tìm từ vị trí dấu mở ngoặc vuông `[` đầu tiên đến dấu đóng `]` cuối cùng.
- Parse `json.loads(extracted_text)` để kiểm tra tính toàn vẹn của danh sách đối tượng.

---

## 4. Cơ Chế Lưu Tiến Trình & Gộp `import.json`
1. **File tiến trình `scanner/.gemini_progress.json`**:
   ```json
   {
     "completed_files": ["scanner_1.md", "scanner_2.md"],
     "results": {
       "scanner_1.md": [ ... các block đã sửa ... ],
       "scanner_2.md": [ ... các block đã sửa ... ]
     }
   }
   ```
2. **File tổng hợp cuối cùng `import.json`**:
   - Khi `len(completed_files) == total_files`:
   - Gộp tất cả các mảng theo đúng thứ tự file `scanner_1.md`, `scanner_2.md`...
   - Ghi file `import.json` với encoding `utf-8`, format JSON đẹp mắt.
