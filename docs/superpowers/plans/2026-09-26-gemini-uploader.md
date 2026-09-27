# Gemini Uploader & import.json Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây dựng tính năng tự động nạp các file markdown trong thư mục `scanner/` lên Google Gemini Web UI bằng Playwright, sử dụng Profile Chrome lưu sẵn, trích xuất kết quả JSON trả về, lưu tiến trình checkpoint và xuất file `import.json` hoàn chỉnh.

**Architecture:**
1. `JSONExtractor`: Trích xuất khối ```json ... ``` từ phản hồi thô của Gemini, fallback tìm mảng `[...]` và parse kiểm tra hợp lệ.
2. `ProgressTracker`: Quản lý lưu/đọc file `.gemini_progress.json`, bỏ qua file đã xử lý và gộp kết quả ra `import.json`.
3. `GeminiUploader`: Điều khiển Playwright với persistent context của Chrome Profile, định vị DOM selectors, gửi prompt và chờ phản hồi ổn định.
4. `CLI Entrypoint`: Script thực thi cho phép chạy tự động qua dòng lệnh với các tham số linh hoạt.

**Tech Stack:** Python 3.12+, `playwright`, `pytest`, `json`, `pathlib`, `re`.

## Global Constraints
- Profile Chrome mặc định đặt tại `user_data/chrome_profiles/chrome_data_1`.
- Tất cả các file đọc/ghi sử dụng encoding `utf-8`.
- Kết quả cuối cùng được gộp và ghi vào file `import.json`.

---

### Task 1: JSONExtractor

**Files:**
- Create: `character_scanner/json_extractor.py`
- Test: `tests/test_json_extractor.py`

**Interfaces:**
- Produces: `JSONExtractor` class:
  - `extract_json(text: str) -> list[dict]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_json_extractor.py
from character_scanner.json_extractor import JSONExtractor

def test_extract_code_block_json():
    raw = """Dưới đây là kết quả đã biên tập:
```json
[
  {
    "id": "ch_0001",
    "is_character": true,
    "source": "Trương Tử Kiến",
    "target": "Trương Tử Kiến"
  }
]
```
Hy vọng bạn hài lòng!"""
    extractor = JSONExtractor()
    data = extractor.extract_json(raw)
    assert len(data) == 1
    assert data[0]["source"] == "Trương Tử Kiến"

def test_extract_fallback_brackets():
    raw = """Đây là kết quả:
[
  {"id": "ch_0001", "is_character": true, "source": "Lâm Ngọc Chi", "target": "Lâm Ngọc Chi"}
]"""
    extractor = JSONExtractor()
    data = extractor.extract_json(raw)
    assert len(data) == 1
    assert data[0]["target"] == "Lâm Ngọc Chi"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_json_extractor.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/json_extractor.py
import json
import re

class JSONExtractor:
    def extract_json(self, text: str) -> list[dict]:
        if not text:
            return []

        # 1. Thử tìm khối code block ```json ... ``` hoặc ``` ... ```
        code_blocks = re.findall(r'```(?:json)?\s*\n(.*?)\n\s*```', text, re.DOTALL | re.IGNORECASE)
        for block in code_blocks:
            clean = block.strip()
            try:
                parsed = json.loads(clean)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass

        # 2. Fallback: Tìm mảng JSON từ dấu '[' đầu tiên đến ']' cuối cùng
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = text[start_idx:end_idx + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass

        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_json_extractor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/json_extractor.py tests/test_json_extractor.py
git commit -m "feat(uploader): add JSONExtractor for parsing Gemini responses"
```

---

### Task 2: ProgressTracker & import.json Aggregator

**Files:**
- Create: `character_scanner/progress_tracker.py`
- Test: `tests/test_progress_tracker.py`

**Interfaces:**
- Produces: `ProgressTracker` class:
  - `is_completed(file_name: str) -> bool`
  - `save_file_result(file_name: str, blocks: list[dict])`
  - `export_to_import_json(output_path: Path) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_progress_tracker.py
from pathlib import Path
from character_scanner.progress_tracker import ProgressTracker

def test_progress_tracker(tmp_path):
    progress_file = tmp_path / ".gemini_progress.json"
    import_file = tmp_path / "import.json"

    tracker = ProgressTracker(progress_file)
    assert not tracker.is_completed("scanner_1.md")

    sample_blocks_1 = [{"id": "ch_0001", "target": "Nhân Vật 1"}]
    sample_blocks_2 = [{"id": "ch_0002", "target": "Nhân Vật 2"}]

    tracker.save_file_result("scanner_1.md", sample_blocks_1)
    assert tracker.is_completed("scanner_1.md")

    tracker.save_file_result("scanner_2.md", sample_blocks_2)
    assert tracker.is_completed("scanner_2.md")

    total = tracker.export_to_import_json(import_file)
    assert total == 2
    assert import_file.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_progress_tracker.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# character_scanner/progress_tracker.py
import json
from pathlib import Path
import re

class ProgressTracker:
    def __init__(self, progress_path: Path):
        self.progress_path = progress_path
        self.completed_files: list[str] = []
        self.results: dict[str, list[dict]] = {}
        self.load()

    def load(self):
        if self.progress_path.exists():
            try:
                data = json.loads(self.progress_path.read_text(encoding="utf-8"))
                self.completed_files = data.get("completed_files", [])
                self.results = data.get("results", {})
            except Exception:
                pass

    def save(self):
        data = {
            "completed_files": self.completed_files,
            "results": self.results
        }
        self.progress_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def is_completed(self, file_name: str) -> bool:
        return file_name in self.completed_files

    def save_file_result(self, file_name: str, blocks: list[dict]):
        if file_name not in self.completed_files:
            self.completed_files.append(file_name)
        self.results[file_name] = blocks
        self.save()

    def export_to_import_json(self, output_path: Path) -> int:
        def extract_num(fname: str) -> int:
            m = re.search(r'(\d+)', fname)
            return int(m.group(1)) if m else 0

        sorted_files = sorted(self.completed_files, key=extract_num)
        all_blocks = []
        for fname in sorted_files:
            all_blocks.extend(self.results.get(fname, []))

        output_path.write_text(json.dumps(all_blocks, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(all_blocks)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_progress_tracker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add character_scanner/progress_tracker.py tests/test_progress_tracker.py
git commit -m "feat(uploader): add ProgressTracker and import.json exporter"
```

---

### Task 3: GeminiUploader Automation Controller

**Files:**
- Create: `character_scanner/gemini_uploader.py`

**Interfaces:**
- Produces: `GeminiUploader` class:
  - `start()`
  - `send_markdown_and_get_response(file_path: Path) -> list[dict]`
  - `close()`

- [ ] **Step 1: Write implementation for `character_scanner/gemini_uploader.py`**
- [ ] **Step 2: Add unit test with mock in `tests/test_gemini_uploader.py`**
- [ ] **Step 3: Run pytest to verify**
- [ ] **Step 4: Commit**

---

### Task 4: CLI Runner `character_scanner/upload_to_gemini.py`

**Files:**
- Create: `character_scanner/upload_to_gemini.py`

**Interfaces:**
- Accepts arguments: `--scanner-dir`, `--profile-dir`, `--output-json`, `--delay`.
- Automates complete scanning, checkpointing, and `import.json` creation.

- [ ] **Step 1: Write CLI implementation**
- [ ] **Step 2: Verify CLI help and args**
- [ ] **Step 3: Commit**
