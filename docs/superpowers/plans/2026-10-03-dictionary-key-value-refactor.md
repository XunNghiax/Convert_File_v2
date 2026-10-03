# Kế hoạch Thực hiện: Chuyển đổi Từ điển sang Key-Value Dict Thuần túy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Chuyển đổi định dạng lưu trữ của `character_dict.json`, `common_dict.json` và `hanviet_dict.json` sang dạng key-value JSON (`{"nguồn": "đích"}`), loại bỏ hoàn toàn các trường `id`, `Tag`, `category` trong từ điển lưu trữ, đơn giản hóa bộ importer, loader và engine thay thế.

**Architecture:** 
1. Di chuyển dữ liệu hiện có từ dạng mảng object sang dictionary key-value, backup bản gốc `.bak`.
2. Cập nhật `ResourceLoader` và `ReplaceEngine` để nạp dữ liệu từ cấu trúc dict trực tiếp $O(1)$.
3. Đơn giản hóa `DictionaryImporter` từ thao tác mảng phức tạp sang cập nhật dictionary thuần túy, tương thích với đầu ra `samples/import.json` của scanner/Gemini.
4. Cập nhật toàn bộ unit tests và kiểm thử end-to-end pipeline.

**Tech Stack:** Python 3.12, Pytest, JSON.

## Global Constraints
- `character_dict.json`, `common_dict.json`, `hanviet_dict.json` phải là JSON Object (`dict[str, str]`).
- Khóa (`source`) luôn ở dạng chữ thường `.strip().lower()`.
- Giá trị (`target`): Title Case cho nhân vật, Lowercase cho từ chung.
- Giữ nguyên `hanviet_markers.json` và `vietnamese_words.txt`.
- Giữ nguyên cấu trúc trao đổi của `samples/import.json` (dạng block chứa `id`, `source`, `target`, `context` cho Gemini).
- Luôn sử dụng mã hóa UTF-8 khi đọc/ghi file.

---

### Task 1: Migration Script & Data Conversion

**Files:**
- Create: `tools/migrate_dictionaries_to_kv.py`
- Modify: `resources/dictionaries/character_dict.json`, `resources/dictionaries/common_dict.json`, `resources/dictionaries/hanviet_dict.json`
- Test: `tests/test_migration.py`

**Interfaces:**
- Consumes: Existing array-based JSON dictionaries.
- Produces: `tools.migrate_dictionaries_to_kv.convert_dict_list_to_kv(items: list[dict], is_character: bool = True) -> dict[str, str]` and updated JSON files.

- [ ] **Step 1: Write test for migration function**

```python
# tests/test_migration.py
from tools.migrate_dictionaries_to_kv import convert_dict_list_to_kv

def test_convert_character_dict_to_kv():
    raw_list = [
        {"id": "ch-1", "source": "Ung nhân", "target": "Yasuhito", "Tag": "Thiên hoàng"},
        {"id": "ch-2", "source": "thực hạnh tiểu bách hợp", "target": "jikko sayuri", "Tag": ""}
    ]
    result = convert_dict_list_to_kv(raw_list, is_character=True)
    assert result == {
        "ung nhân": "Yasuhito",
        "thực hạnh tiểu bách hợp": "Jikko Sayuri"
    }

def test_convert_common_dict_to_kv():
    raw_list = [
        {"id": "co-1", "source": "Đông Phương", "target": "phương đông", "category": "Khớp"}
    ]
    result = convert_dict_list_to_kv(raw_list, is_character=False)
    assert result == {
        "đông phương": "phương đông"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_migration.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'tools.migrate_dictionaries_to_kv')

- [ ] **Step 3: Implement migration script**

```python
# tools/migrate_dictionaries_to_kv.py
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any

def capitalize_words(text: str) -> str:
    words = text.strip().split()
    return " ".join(w[:1].upper() + w[1:] for w in words)

def convert_dict_list_to_kv(items: List[Dict[str, Any]], is_character: bool = True) -> Dict[str, str]:
    kv = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source", "")).strip().lower()
        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
        if not src or not tgt:
            continue
        if is_character:
            tgt = capitalize_words(tgt)
        else:
            tgt = tgt.lower()
        kv[src] = tgt
    return kv

def migrate_file(file_path: Path, is_character: bool):
    if not file_path.exists():
        print(f"[-] File không tồn tại: {file_path}")
        return
    backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
    shutil.copy2(file_path, backup_path)
    print(f"[+] Đã backup vào: {backup_path}")

    data = json.loads(file_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        kv = convert_dict_list_to_kv(data, is_character=is_character)
    elif isinstance(data, dict):
        kv = {k.strip().lower(): (capitalize_words(v) if is_character else str(v).strip().lower()) for k, v in data.items()}
    else:
        kv = {}

    file_path.write_text(json.dumps(kv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[+] Đã chuyển đổi {file_path}: {len(kv)} mục")

def main():
    root = Path(__file__).resolve().parent.parent
    dict_dir = root / "resources" / "dictionaries"
    
    migrate_file(dict_dir / "character_dict.json", is_character=True)
    migrate_file(dict_dir / "common_dict.json", is_character=False)
    
    hanviet_path = dict_dir / "hanviet_dict.json"
    if hanviet_path.exists():
        migrate_file(hanviet_path, is_character=False)
    else:
        hanviet_path.write_text("{}\n", encoding="utf-8")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_migration.py -v`
Expected: PASS

- [ ] **Step 5: Run migration script on real dictionary files**

Run: `python tools/migrate_dictionaries_to_kv.py`
Expected: `character_dict.json` (~437 mục) và `common_dict.json` (~78 mục) chuyển sang dạng JSON `{ "source": "target" }`.

- [ ] **Step 6: Commit Task 1**

```bash
git add tools/migrate_dictionaries_to_kv.py tests/test_migration.py resources/dictionaries/
git commit -m "refactor: migrate dictionary files to plain key-value format"
```

---

### Task 2: Update ResourceLoader and ReplaceEngine

**Files:**
- Modify: `src/scanner/resource_loader.py`
- Modify: `src/replacer/replace_engine.py`
- Test: `tests/test_resource_loader.py`
- Test: `tests/test_replace_engine.py`

**Interfaces:**
- `ResourceLoader.load_common_dict(path: Path) -> set[str]`
- `ResourceLoader.load_character_dict(path: Path) -> dict[str, str]`
- `ReplaceEngine.load_dictionaries()`

- [ ] **Step 1: Update ResourceLoader tests for dictionary support**

Add to `tests/test_resource_loader.py`:
```python
def test_resource_loader_loads_dict_format(tmp_path):
    loader = ResourceLoader(base_dir=tmp_path)
    char_file = tmp_path / "char.json"
    char_file.write_text(json.dumps({"ung nhân": "Yasuhito"}), encoding="utf-8")
    chars = loader.load_character_dict(char_file)
    assert chars["ung nhân"] == "Yasuhito"

    common_file = tmp_path / "common.json"
    common_file.write_text(json.dumps({"đông phương": "phương đông"}), encoding="utf-8")
    common = loader.load_common_dict(common_file)
    assert "đông phương" in common
```

- [ ] **Step 2: Run test to verify it fails if dict is not handled in load_common_dict / load_character_dict**

Run: `python -m pytest tests/test_resource_loader.py -v`

- [ ] **Step 3: Update `src/scanner/resource_loader.py`**

In `load_common_dict`:
```python
    def load_common_dict(self, path: Path) -> set[str]:
        words = set()
        if not path.exists():
            return words
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, dict):
                for k in data.keys():
                    src = str(k).strip().lower()
                    if src:
                        words.add(src)
            elif isinstance(data, list):
                for item in data:
                    src = item.get("source", "").strip().lower()
                    if src:
                        words.add(src)
        except Exception:
            pass
        return words
```

In `load_character_dict`:
```python
    def load_character_dict(self, path: Path) -> dict[str, str]:
        chars = {}
        if not path.exists():
            return chars
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, dict):
                for k, v in data.items():
                    src = str(k).strip().lower()
                    tgt = str(v).strip()
                    if src and tgt:
                        chars[src] = tgt
            elif isinstance(data, list):
                for item in data:
                    src = item.get("source", "").strip().lower()
                    tgt = item.get("target", "").strip()
                    if src and tgt:
                        chars[src] = tgt
        except Exception:
            pass
        return chars
```

- [ ] **Step 4: Update `src/replacer/replace_engine.py`**

In `load_dictionaries` (handling `char_dict_path`):
```python
        # 3. Nạp từ điển nhân vật (Ghi đè, ưu tiên cao nhất)
        if self.char_dict_path and self.char_dict_path.exists():
            try:
                data = json.loads(self.char_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        src = str(k).strip()
                        tgt = str(v).strip()
                        words = tgt.split()
                        tgt = " ".join(w[:1].upper() + w[1:] for w in words)
                        if src and tgt:
                            merged[src.lower()] = tgt
                elif isinstance(data, list):
                    for item in data:
                        src = str(item.get("source", "")).strip()
                        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
                        words = tgt.split()
                        tgt = " ".join(w[:1].upper() + w[1:] for w in words)
                        if src and tgt:
                            merged[src.lower()] = tgt
            except Exception as e:
                print(f"[!] Cảnh báo: Không thể nạp character_dict: {e}")
```

- [ ] **Step 5: Run tests for ResourceLoader and ReplaceEngine**

Run: `python -m pytest tests/test_resource_loader.py tests/test_replace_engine.py tests/test_replace_guards.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit Task 2**

```bash
git add src/scanner/resource_loader.py src/replacer/replace_engine.py tests/test_resource_loader.py
git commit -m "feat: support key-value dict format in ResourceLoader and ReplaceEngine"
```

---

### Task 3: Refactor Dictionary Importer to Key-Value Dict Model

**Files:**
- Modify: `src/importer/dictionary_importer.py`
- Modify: `src/importer/main.py`
- Test: `tests/test_import_dictionary.py`
- Test: `tests/test_dictionary_casing_rules.py`
- Test: `tests/test_dictionary_importer_warning.py`

**Interfaces:**
- `load_dictionary(path: Path) -> Dict[str, str]`
- `save_dictionary(entries: Dict[str, str], path: Path, indent: int = 2) -> bool`
- `import_character_dict(items: List[Dict[str, Any]], dict_path: Path, overwrite_existing: bool = True) -> Dict[str, Any]`
- `import_common_dict(items: List[Dict[str, Any]], dict_path: Path, overwrite_existing: bool = True) -> Dict[str, Any]`
- `distribute_and_import(items: List[Dict[str, Any]], ...) -> Dict[str, Any]`

- [ ] **Step 1: Update `tests/test_import_dictionary.py` for Key-Value dictionary structure**

Rewrite tests to assert dictionary structure:
```python
def test_import_entries(tmp_path):
    dict_file = tmp_path / "character_dict.json"
    dict_file.write_text(json.dumps({"hồng lâu": "Hong Lou"}, ensure_ascii=False), encoding="utf-8")

    new_items = [
        {"source": "gavin tĩnh", "target": "giả tĩnh"}
    ]
    res = import_character_dict(new_items, dict_path=dict_file)
    assert res["added"] == 1
    assert res["total"] == 2

    data = load_dictionary(dict_file)
    assert data["gavin tĩnh"] == "Giả Tĩnh"

    update_items = [
        {"source": "gavin tĩnh", "target": "giả mới"}
    ]
    res_update = import_character_dict(update_items, dict_path=dict_file, overwrite_existing=True)
    assert res_update["updated"] == 1
    data = load_dictionary(dict_file)
    assert data["gavin tĩnh"] == "Giả Mới"
```

- [ ] **Step 2: Update `src/importer/dictionary_importer.py`**
- Change `load_dictionary` to return `Dict[str, str]` (with fallback if list is encountered).
- Change `save_dictionary` to save `Dict[str, str]`.
- Simplify `import_character_dict`:
  - Load dict `entries = load_dictionary(dict_path)`.
  - For each raw item: extract `source`, `target`.
  - Apply `capitalize_first_letters` to `target`.
  - Check if `src_key` in `entries`: update or add.
  - Save dict with atomic write.
- Simplify `import_common_dict`:
  - Similar, with `lowercase_all` applied to `target`.
- Deprecate `get_next_id` (return `""` or remove callers).
- In `filter_and_export_warnings`: keep alignment check.

- [ ] **Step 3: Update `src/importer/main.py`**
- Interactive mode: prompts only for `Source`, `Target`, and `is_character` (skip prompt for `Tag` and `ID`).
- Keep CLI argument parser compatible with existing `--id` and `--tag` flags without breaking.

- [ ] **Step 4: Run all importer tests**

Run: `python -m pytest tests/test_import_dictionary.py tests/test_dictionary_casing_rules.py tests/test_dictionary_importer_warning.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit Task 3**

```bash
git add src/importer/ tests/
git commit -m "refactor: simplify dictionary_importer to use plain key-value format"
```

---

### Task 4: End-to-End Pipeline Verification & Verification Tests

**Files:**
- Run tests: Full test suite `python -m pytest`
- Verify pipeline: Scanner -> Importer -> Replacer

- [ ] **Step 1: Run full pytest suite**

Run: `python -m pytest -v`
Expected: 66/67 tests passing (the only existing failure being unrelated `test_gemini_uploader_init`).

- [ ] **Step 2: Test importing `samples/import.json` into dictionaries**

Run: `python src/importer/main.py --file samples/import.json`
Verify output counts and check `resources/dictionaries/character_dict.json` and `common_dict.json`.

- [ ] **Step 3: Test replacement engine with converted dictionaries**

Run: `python src/replacer/main.py --input samples/exam.txt --output samples/exam_out.txt`
Verify replace statistics and output correctness.

- [ ] **Step 4: Commit all final changes**

```bash
git add .
git commit -m "feat: complete key-value dictionary refactor"
```
