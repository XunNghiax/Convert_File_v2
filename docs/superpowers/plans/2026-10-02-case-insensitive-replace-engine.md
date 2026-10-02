# Case-Insensitive Matching and Entity Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable case-insensitive dictionary matching (`re.IGNORECASE`) and automatic Title-Case entity normalization in `ReplaceEngine`, ensuring character names like `"kiều ngọc"` are properly converted to `"Kiều Ngọc"` even when the dictionary entry has identical source and target (`"Kiều Ngọc" -> "Kiều Ngọc"`).

**Architecture:**
- Dictionary loading stores canonical lowercased keys in `dict_map[source.lower()] = target`.
- `character_dict` entries are Title-Cased and loaded without filtering out `source == target`.
- Regex patterns are compiled with `re.IGNORECASE` while retaining negative lookbehind guards.
- Replacement in `replace_line` retrieves normalized target via `m.group(0).lower()`, performs replacement when casing differs, and only increments stats on actual text modifications.

**Tech Stack:** Python 3.12, `re` (built-in regex with Unicode and case-folding), `pytest`.

## Global Constraints
- Target platform: Windows / Python 3.12.
- Backward compatibility: All existing test cases in `tests/` must remain passing.
- High performance: Streaming I/O and single-pass regex matching must be preserved.

---

### Task 1: Dictionary Loading & Key Canonicalization in `ReplaceEngine`

**Files:**
- Modify: `src/replacer/replace_engine.py:114-184`
- Test: `tests/test_replace_engine.py`

**Interfaces:**
- Consumes: JSON files (`character_dict.json`, `hanviet_dict.json`, `common_dict.json`) or custom mapping dict.
- Produces: `self.dict_map: Dict[str, str]` where keys are lowercased strings (`k.lower()`) and values are their normalized targets.

- [ ] **Step 1: Write failing test for pre-normalized character dictionary entries**

Add to `tests/test_replace_engine.py`:
```python
def test_character_dict_loads_pre_normalized_entries(tmp_path: Path):
    """Kiểm tra các mục tên nhân vật đã chuẩn hóa (source == target) vẫn được nạp vào dict_map."""
    char_dict = tmp_path / "char_dict.json"
    char_dict.write_text(json.dumps([
        {"id": "ch-264", "source": "Kiều Ngọc", "target": "Kiều Ngọc"},
        {"id": "ch-265", "source": "tô tư văn", "target": "Tô Tư Văn"}
    ], ensure_ascii=False), encoding="utf-8")

    engine = ReplaceEngine(char_dict_path=char_dict, common_dict_path=None, hanviet_dict_path=None)
    assert "kiều ngọc" in engine.dict_map
    assert engine.dict_map["kiều ngọc"] == "Kiều Ngọc"
    assert "tô tư văn" in engine.dict_map
    assert engine.dict_map["tô tư văn"] == "Tô Tư Văn"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replace_engine.py::test_character_dict_loads_pre_normalized_entries -v`
Expected: FAIL (assertion error because `"kiều ngọc"` is not in `dict_map` due to `src != tgt` check and case mismatch).

- [ ] **Step 3: Update `load_dictionaries` and `load_custom_mapping` in `replace_engine.py`**

In `src/replacer/replace_engine.py`:
```python
    def load_dictionaries(self):
        """Nạp và hợp nhất từ điển nhân vật, từ điển Hán Việt và từ điển chung."""
        merged: Dict[str, str] = {}

        # 1. Nạp từ điển chung (Ưu tiên cơ bản)
        if self.common_dict_path and self.common_dict_path.exists():
            try:
                data = json.loads(self.common_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        src = str(item.get("source", "")).strip()
                        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
                        tgt = tgt.lower()
                        if src and tgt:
                            merged[src.lower()] = tgt
                elif isinstance(data, dict):
                    for k, v in data.items():
                        src = str(k).strip()
                        tgt = str(v).strip().lower()
                        if src and tgt:
                            merged[src.lower()] = tgt
            except Exception as e:
                print(f"[!] Cảnh báo: Không thể nạp common_dict: {e}")

        # 2. Nạp từ điển Hán Việt (Ưu tiên cao hơn từ điển chung)
        if self.hanviet_dict_path and self.hanviet_dict_path.exists():
            try:
                data = json.loads(self.hanviet_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        src = str(item.get("source", "")).strip()
                        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
                        if src and tgt:
                            merged[src.lower()] = tgt
                elif isinstance(data, dict):
                    for k, v in data.items():
                        src = str(k).strip()
                        tgt = str(v).strip()
                        if src and tgt:
                            merged[src.lower()] = tgt
            except Exception as e:
                print(f"[!] Cảnh báo: Không thể nạp hanviet_dict: {e}")

        # 3. Nạp từ điển nhân vật (Ghi đè, ưu tiên cao nhất)
        if self.char_dict_path and self.char_dict_path.exists():
            try:
                data = json.loads(self.char_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        src = str(item.get("source", "")).strip()
                        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
                        # Chuẩn hóa: Tên nhân vật luôn upcase chữ cái đầu mỗi từ
                        words = tgt.split()
                        tgt = " ".join(w[:1].upper() + w[1:] for w in words)
                        if src and tgt:
                            merged[src.lower()] = tgt
            except Exception as e:
                print(f"[!] Cảnh báo: Không thể nạp character_dict: {e}")

        self._compile_from_dict(merged)

    def load_custom_mapping(self, mapping: Dict[str, str]):
        """Nạp trực tiếp mapping từ điển thủ công (dùng cho testing hoặc mở rộng)."""
        clean_map = {
            str(k).strip().lower(): str(v).strip()
            for k, v in mapping.items()
            if str(k).strip() and str(v).strip()
        }
        self._compile_from_dict(clean_map)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_replace_engine.py::test_character_dict_loads_pre_normalized_entries -v`
Expected: PASS.

- [ ] **Step 5: Commit Task 1 changes**

```bash
git add src/replacer/replace_engine.py tests/test_replace_engine.py
git commit -m "feat(replacer): load pre-normalized character entries and canonicalize keys to lowercase"
```

---

### Task 2: Case-Insensitive Regex Pattern Compilation with Guards

**Files:**
- Modify: `src/replacer/replace_engine.py:185-220`
- Test: `tests/test_replace_guards.py`

**Interfaces:**
- Consumes: `self.dict_map` with lowercase keys.
- Produces: `self.pattern: re.Pattern` compiled with `re.IGNORECASE` and case-insensitive lookbehinds.

- [ ] **Step 1: Write failing test for case-insensitive guards**

Add to `tests/test_replace_guards.py`:
```python
def test_prefix_guard_case_insensitive():
    """Kiểm tra Prefix Guard hoạt động chính xác khi tiền tố xuất hiện ở bất kỳ định dạng hoa thường nào."""
    custom_map = {
        "kiếm phi": "Long Kiếm Phi"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    # 1. Đứng độc lập với chữ thường
    assert engine.replace_line("kiếm phi xuất chiêu.") == "Long Kiếm Phi xuất chiêu."

    # 2. Đã có họ 'long' viết thường đi trước -> không biến thành 'long Long Kiếm Phi'
    assert engine.replace_line("long kiếm phi xuất chiêu.") == "long kiếm phi xuất chiêu."

    # 3. Đã có họ 'Long' viết hoa đi trước -> không biến thành 'Long Long Kiếm Phi'
    assert engine.replace_line("Long kiếm phi xuất chiêu.") == "Long kiếm phi xuất chiêu."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replace_guards.py::test_prefix_guard_case_insensitive -v`
Expected: FAIL (because regex compilation currently lacks `re.IGNORECASE` and prefix lookbehind matching).

- [ ] **Step 3: Update `_compile_from_dict` in `replace_engine.py`**

In `src/replacer/replace_engine.py`:
```python
    def _compile_from_dict(self, mapping: Dict[str, str]):
        """Sắp xếp từ điển theo độ dài giảm dần và biên dịch Regex Pattern kèm Guard an toàn."""
        self.dict_map = mapping
        # Sắp xếp: Ưu tiên chuỗi dài nhất trước (Longest Match First)
        self.sorted_keys = sorted(
            self.dict_map.keys(),
            key=lambda x: (len(x), x),
            reverse=True
        )

        if self.sorted_keys:
            pattern_parts = []
            for k in self.sorted_keys:
                tgt = self.dict_map[k]
                guards = []

                # 1. Prefix Guard: Ngăn chặn lỗi lặp họ (ví dụ Kiếm Phi -> Long Kiếm Phi khi đã có 'Long ')
                if tgt.lower().endswith(k.lower()) and len(tgt) > len(k):
                    prefix = tgt[:-len(k)].strip()
                    if prefix:
                        guards.append(f"(?<!{re.escape(prefix)}\\s)")

                # 2. Negative Context Guard: Ngăn chặn thay thế từ miêu tả vóc dáng
                if k.lower() in AMBIGUOUS_DESCRIPTIVE_WORDS:
                    for dp in DESCRIPTIVE_PREFIXES:
                        guards.append(f"(?<!{re.escape(dp)}\\s)")

                if guards:
                    pattern_parts.append(f"(?:{''.join(guards)}{re.escape(k)})")
                else:
                    pattern_parts.append(re.escape(k))

            self.pattern = re.compile("|".join(pattern_parts), flags=re.IGNORECASE)
        else:
            self.pattern = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_replace_guards.py::test_prefix_guard_case_insensitive -v`
Expected: PASS.

- [ ] **Step 5: Commit Task 2 changes**

```bash
git add src/replacer/replace_engine.py tests/test_replace_guards.py
git commit -m "feat(replacer): compile regex with re.IGNORECASE and case-insensitive guards"
```

---

### Task 3: Intelligent Single-Pass Replacement & Stats Tracking

**Files:**
- Modify: `src/replacer/replace_engine.py:221-308`
- Test: `tests/test_replace_engine.py`

**Interfaces:**
- Consumes: `line: str`, `self.pattern`, `self.dict_map`.
- Produces: Replaced string where character names are converted to standard Title Case, without unnecessary replacements or inflated stats when text already matches target.

- [ ] **Step 1: Write failing test for user's exact issue and stats no-op**

Add to `tests/test_replace_engine.py`:
```python
def test_user_scenario_kieu_ngoc_normalization():
    """Kiểm tra trường hợp thực tế của người dùng: 'kiều ngọc' được chuẩn hóa thành 'Kiều Ngọc'."""
    custom_map = {
        "Kiều Ngọc": "Kiều Ngọc"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    line = "ví dụ tượng kiều ngọc làm Từ Thanh mẹ kế."
    result = engine.replace_line(line, track_stats=True)
    assert result == "ví dụ tượng Kiều Ngọc làm Từ Thanh mẹ kế."
    assert engine.stats_counter["kiều ngọc"] == 1

def test_noop_exact_target_does_not_increment_stats():
    """Nếu từ trong văn bản đã đúng chuẩn (Kiều Ngọc == Kiều Ngọc), không tính là lượt thay thế."""
    custom_map = {
        "Kiều Ngọc": "Kiều Ngọc"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    line = "Từ Thanh gặp Kiều Ngọc tại hoa viên."
    result = engine.replace_line(line, track_stats=True)
    assert result == "Từ Thanh gặp Kiều Ngọc tại hoa viên."
    assert sum(engine.stats_counter.values()) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_replace_engine.py::test_user_scenario_kieu_ngoc_normalization -v`
Expected: FAIL (because `replace_line` currently looks up `matched_str` directly in `dict_map` without `.lower()` and without no-op checking).

- [ ] **Step 3: Update `replace_line` and `replace_file` in `replace_engine.py`**

In `src/replacer/replace_engine.py`:
```python
    def replace_line(self, line: str, track_stats: bool = True) -> str:
        """Thay thế một dòng văn bản trong một lượt duy nhất (Single-Pass) với hỗ trợ không phân biệt hoa thường."""
        if not self.pattern or not line:
            return line

        def _repl(m: re.Match) -> str:
            matched_str = m.group(0)
            canonical_key = matched_str.lower()
            target = self.dict_map.get(canonical_key, matched_str)
            if matched_str != target:
                if track_stats:
                    self.stats_counter[canonical_key] += 1
                return target
            return matched_str

        return self.pattern.sub(_repl, line)
```

In `replace_file`:
```python
        top_list = [
            (src_key, self.dict_map.get(src_key, ""), count)
            for src_key, count in self.stats_counter.most_common(20)
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_replace_engine.py::test_user_scenario_kieu_ngoc_normalization tests/test_replace_engine.py::test_noop_exact_target_does_not_increment_stats -v`
Expected: PASS.

- [ ] **Step 5: Commit Task 3 changes**

```bash
git add src/replacer/replace_engine.py tests/test_replace_engine.py
git commit -m "feat(replacer): case-insensitive lookup in replace_line and no-op stats tracking"
```

---

### Task 4: Full Regression Testing & Existing Test Adjustment

**Files:**
- Modify: `tests/test_replace_engine.py` (update `test_empty_or_same_source_target` to match the new semantics).
- Test: All tests in `tests/`

**Interfaces:**
- Consumes: Full test suite.
- Produces: 100% green test suite across 55+ test cases.

- [ ] **Step 1: Check existing `test_empty_or_same_source_target` test**

Review `test_empty_or_same_source_target` in `tests/test_replace_engine.py`:
In the old code:
`"Vương Bá Đao": "Vương Bá Đao"` was asserted to be excluded from `sorted_keys`.
Under the new requirement:
Pre-normalized names like `"Vương Bá Đao": "Vương Bá Đao"` ARE kept so that `"vương bá đao"` (lowercase) in text gets normalized to `"Vương Bá Đao"`. Empty keys `""` are still discarded.

Update the test in `tests/test_replace_engine.py`:
```python
def test_empty_or_same_source_target():
    """Kiểm tra các mục rỗng được lọc bỏ, còn mục chuẩn hóa thực thể (Vương Bá Đao -> Vương Bá Đao) vẫn chuẩn hóa được chữ thường."""
    custom_map = {
        "Vương Bá Đao": "Vương Bá Đao",
        "": "Không tên",
        "Trương Tam": "Trương Tam Phong"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    # Mục rỗng bị loại bỏ, chỉ còn 2 mục hợp lệ
    assert len(engine.sorted_keys) == 2
    assert "vương bá đao" in engine.sorted_keys
    assert "trương tam" in engine.sorted_keys

    # Kiểm tra chuẩn hóa chữ thường thành Title Case
    text = "vương bá đao nói chuyện với Trương Tam."
    result = engine.replace_line(text)
    assert result == "Vương Bá Đao nói chuyện với Trương Tam Phong."
```

- [ ] **Step 2: Run all tests in the project**

Run: `pytest tests/`
Expected: All tests PASS with 0 failures.

- [ ] **Step 3: Test with real character dictionary from project resources**

Run verification command:
```bash
python -c "from src.replacer.replace_engine import ReplaceEngine; e = ReplaceEngine(); print(e.replace_line('ví dụ tượng kiều ngọc làm Từ Thanh mẹ kế.'))"
```
Expected output:
`ví dụ tượng Kiều Ngọc làm Từ Thanh mẹ kế.`

- [ ] **Step 4: Commit Task 4 changes**

```bash
git add tests/test_replace_engine.py
git commit -m "test(replacer): update regression tests and verify full suite passes"
```
