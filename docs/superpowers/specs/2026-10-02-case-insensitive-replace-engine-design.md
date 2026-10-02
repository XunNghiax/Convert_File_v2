# Design Spec: Case-Insensitive Matching & Entity Normalization in ReplaceEngine

- **Date**: 2026-10-02
- **Topic**: Case-Insensitive Matching & Title-Case Auto-Normalization in ReplaceEngine
- **Status**: Approved by User

---

## 1. Problem Statement

In web novel translation and conversion workflows, character names in raw text often appear with inconsistent casing (e.g., `kiều ngọc`, `Kiều ngọc`, `KIỀU NGỌC`, or `Kiều Ngọc`).

In `character_dict.json`, many entries have been pre-normalized into standard Title Case where `source` and `target` are identical (e.g. `"source": "Kiều Ngọc", "target": "Kiều Ngọc"`).

Currently, `ReplaceEngine` suffers from two limitations:
1. **Filtering out identical source/target**: In `load_dictionaries`, entries are only accepted if `src != tgt`. Consequently, pre-normalized character entries (e.g. `ch-264` `"Kiều Ngọc": "Kiều Ngọc"`) are dropped and never loaded.
2. **Strict case-sensitive matching**: `re.compile("|".join(pattern_parts))` compiles without `re.IGNORECASE`. As a result, even if an entry exists, lowercase occurrences like `"kiều ngọc"` in raw sentences fail to match.

---

## 2. Requirements & Goals

1. **Case-Insensitive Regex Matching**:
   The engine must match words regardless of casing in the input text (`"kiều ngọc"`, `"Kiều ngọc"`, `"KIỀU NGỌC"`).

2. **Entity Title-Case Auto-Normalization**:
   Whenever a character name appears in the input text, it must be normalized to its canonical Title-Cased target (e.g. `"Kiều Ngọc"`), even if the dictionary entry has identical source and target (`"Kiều Ngọc" -> "Kiều Ngọc"`).

3. **Canonical Lowercase Lookup Key**:
   All dictionary mappings in `self.dict_map` use lowercased keys (`key.lower()`) to guarantee $O(1)$ uniform retrieval regardless of the casing matched by regex.

4. **Multi-tier Dictionary Priority**:
   Priority hierarchy must remain strictly enforced across case variants:
   - `character_dict` (Highest, overrides all, targets formatted as Title Case)
   - `hanviet_dict` (Medium)
   - `common_dict` (Base, targets formatted as lowercase)

5. **Case-Insensitive Guards**:
   - **Prefix Guard**: Negative lookbehind `(?<!{prefix}\s)` must prevent duplicate prefixes regardless of case (e.g., `"long kiều ngọc"` or `"Long kiều ngọc"` will not turn into `"Long Long Kiều Ngọc"`).
   - **Negative Context Guard**: Phrases in `AMBIGUOUS_DESCRIPTIVE_WORDS` preceded by prefixes like `"một"`, `"những"`, `"vóc dáng"` must be preserved regardless of casing.

6. **Intelligent Stats & No-Op Handling**:
   - If the text already has the exact target string (e.g. `"Kiều Ngọc"` == `"Kiều Ngọc"`), it remains unchanged and does not count as a replacement.
   - Only true changes (`matched_str != target`) increment `self.stats_counter`.
   - Stats are aggregated by canonical key so that all casing variations count towards the same word item in top rankings.

7. **Zero Regression**:
   All existing core tests and guards must continue to pass cleanly.

---

## 3. Detailed Architecture & Implementation

### 3.1 `load_dictionaries` in `ReplaceEngine`
```python
merged: Dict[str, str] = {}

# 1. common_dict (Base)
# For common_dict: tgt is lowercased.
# Map merged[src.lower()] = tgt.lower() if src.strip() and tgt.strip()

# 2. hanviet_dict (Medium)
# Map merged[src.lower()] = tgt if src.strip() and tgt.strip()

# 3. character_dict (Highest)
# Target is Title Cased: words = tgt.split(); tgt = " ".join(w[:1].upper() + w[1:] for w in words)
# Map merged[src.lower()] = tgt if src.strip() and tgt.strip()
# (Do NOT filter by src != tgt for character entries!)
```

### 3.2 `_compile_from_dict`
- Keys in `dict_map` are lowercased strings.
- Keys are sorted by `(len(k), k)` descending for Longest-Match First.
- Regex compiled with `re.IGNORECASE`:
  ```python
  self.pattern = re.compile("|".join(pattern_parts), flags=re.IGNORECASE)
  ```
- Prefix guard calculation:
  ```python
  if tgt.lower().endswith(k) and len(tgt) > len(k):
      prefix = tgt[:-len(k)].strip()
      if prefix:
          guards.append(f"(?<!{re.escape(prefix)}\\s)")
  ```

### 3.3 `replace_line`
```python
def replace_line(self, line: str, track_stats: bool = True) -> str:
    if not self.pattern or not line:
        return line

    def _repl(m: re.Match) -> str:
        matched_str = m.group(0)
        matched_key = matched_str.lower()
        target = self.dict_map.get(matched_key, matched_str)
        if matched_str != target:
            if track_stats:
                self.stats_counter[matched_key] += 1
            return target
        return matched_str

    return self.pattern.sub(_repl, line)
```

### 3.4 `replace_file` Stats Output
In `replace_file`, top replacements display:
```python
top_list = [
    (key, self.dict_map.get(key, ""), count)
    for key, count in self.stats_counter.most_common(20)
]
```

---

## 4. Verification & Testing Strategy

1. **Unit Tests in `test_replace_engine.py`**:
   - `test_case_insensitive_character_normalization`:
     Input: `"ví dụ tượng kiều ngọc làm Từ Thanh mẹ kế."`
     With dict containing `"Kiều Ngọc" -> "Kiều Ngọc"`
     Output: `"ví dụ tượng Kiều Ngọc làm Từ Thanh mẹ kế."`
   - `test_mixed_casing_variants`:
     Verify `"kiều ngọc"`, `"Kiều ngọc"`, `"KIỀU NGỌC"` all convert to `"Kiều Ngọc"`.
   - `test_noop_does_not_increment_stats`:
     If text already contains `"Kiều Ngọc"`, stats counter remains 0.
   - `test_prefix_guard_case_insensitive`:
     Verify `"long kiếm phi"` does not become `"Long Long Kiếm Phi"` when rule is `"kiếm phi" -> "Long Kiếm Phi"`.

2. **Full Regression Test**:
   Execute `pytest tests/` to confirm all 55+ tests pass without errors.
