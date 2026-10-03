# Thiết kế Chuyển đổi Từ điển sang Cấu trúc Key-Value Thuần túy (Plain Dictionary)

## 1. Bối cảnh & Vấn đề
Hiện tại, các từ điển trong `resources/dictionaries/` (`character_dict.json`, `common_dict.json`, `hanviet_dict.json`) đang được lưu dưới dạng mảng các đối tượng JSON:
```json
[
  {
    "id": "ch-1",
    "source": "Ung nhân",
    "target": "Yasuhito",
    "Tag": "Thiên hoàng"
  }
]
```
Nhược điểm thực tế:
- `id` hoàn toàn không được sử dụng trong engine thay thế (`replace_engine.py`) hay bộ quét (`resource_loader.py`). Phép tra cứu tự nhiên trong NLP dựa trên `source.lower()`.
- Trường `Tag` và `category` bị ô nhiễm dữ liệu khi import tự động từ scanner/Gemini (lý do quét heuristics bị ghi đè vào nhãn phân loại).
- Dung lượng file phình to hơn 60-70% không cần thiết.
- Code importer phải duy trì các hàm phức tạp như `get_next_id()`, duyệt mảng tìm chỉ mục cập nhật $O(N)$.

## 2. Mục tiêu thiết kế
- Chuyển đổi `character_dict.json`, `common_dict.json`, `hanviet_dict.json` sang cấu trúc Key-Value thuần túy:
  ```json
  {
    "ung nhân": "Yasuhito"
  }
  ```
- Khóa (`source`) luôn ở dạng chữ thường (`.strip().lower()`) để đảm bảo tính duy nhất và tra cứu $O(1)$.
- Giá trị (`target`):
  - Nhân vật (`character_dict`): Title Case (viết hoa chữ cái đầu mỗi từ).
  - Từ chung (`common_dict`): Lowercase.
- Đơn giản hóa toàn bộ `src/importer/dictionary_importer.py` và `src/importer/main.py`.
- Nâng cấp `src/scanner/resource_loader.py` và `src/replacer/replace_engine.py` để nạp từ điển dạng dict trực tiếp, đồng thời giữ fallback cho dạng list (tương thích ngược).
- Giữ nguyên `hanviet_markers.json` (chứa quy tắc ngữ pháp `pattern`, `suggestion`, `category`) và `vietnamese_words.txt`.
- Giữ nguyên định dạng các file giao tiếp tạm thời với Gemini (`scanner_master.json`, `samples/import.json`) có chứa `id` và `context` phục vụ AI.

## 3. Kiến trúc các thành phần sau chuyển đổi

### 3.1 Định dạng dữ liệu lưu trữ
- `resources/dictionaries/character_dict.json`: `Dict[str, str]` (key: lowercase source, value: Title Case target).
- `resources/dictionaries/common_dict.json`: `Dict[str, str]` (key: lowercase source, value: lowercase target).
- `resources/dictionaries/hanviet_dict.json`: `Dict[str, str]` (rỗng ban đầu `{}`).

### 3.2 Bộ nạp tài nguyên (`src/scanner/resource_loader.py`)
- `load_common_dict(path)`:
  - Nếu `isinstance(data, dict)`: lấy `set(data.keys())`.
  - Fallback nếu `isinstance(data, list)`: đọc `item.get("source")`.
- `load_character_dict(path)`:
  - Nếu `isinstance(data, dict)`: lấy `{k.lower(): v for k, v in data.items()}`.
  - Fallback nếu `isinstance(data, list)`: đọc `item.get("source")`, `item.get("target")`.

### 3.3 Động cơ thay thế (`src/replacer/replace_engine.py`)
- `load_dictionaries()`:
  - Bổ sung nhánh xử lý `isinstance(data, dict)` cho `character_dict`.
  - Tự động chuẩn hóa Title Case cho giá trị khi nạp vào `merged`.

### 3.4 Module Importer (`src/importer/dictionary_importer.py` & `main.py`)
- `load_dictionary(path)`: Trả về `Dict[str, str]`.
- `save_dictionary(entries: Dict[str, str], path)`: Lưu JSON dạng `Dict[str, str]`, sắp xếp key hoặc giữ thứ tự chèn, format `indent=2`.
- `import_character_dict(items, dict_path, ...)`:
  - Nhận danh sách mục (từ `samples/import.json` hoặc CLI).
  - Lọc `is_character == True`.
  - Thêm / cập nhật trực tiếp vào dictionary: `entries[src_key] = target_title_case`.
  - Trả về thống kê `{ "added": int, "updated": int, "total": int }`.
- `import_common_dict(items, dict_path, ...)`:
  - Tương tự, lọc `is_character == False`, lưu với `target_lowercase`.
- Loại bỏ logic sinh ID thừa (`get_next_id`), bỏ kiểm tra prefix `ch-`, `co-`.
- CLI (`src/importer/main.py`):
  - Chế độ `--interactive` chỉ hỏi `source` và `target`.
  - Bỏ cờ bắt buộc liên quan đến `id` / `tag`.

## 4. Kế hoạch kiểm thử & Tiêu chí nghiệm thu
- Chuyển đổi thành công dữ liệu hiện tại, có bản backup an toàn `.json.bak`.
- Toàn bộ unit tests liên quan đến dictionary, casing rules, loader, replacer đều pass.
- Dung lượng file `character_dict.json` và `common_dict.json` giảm đáng kể.
- Chạy thử nghiệm thành công toàn bộ pipeline: `src/scanner/main.py` -> `src/importer/main.py` -> `src/replacer/main.py`.
