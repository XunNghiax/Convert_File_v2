# Abnormal Han-Viet Scanner and Dedicated Dictionary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a dedicated Han-Viet and abnormal phrase scanner module that detects raw Sino-Vietnamese / awkward convert expressions, outputs to `scanner/hanviet/`, integrates with Gemini uploading / editing, maintains an independent `hanviet_dict.json`, and ties into the Replace Engine and CLI menu.

**Architecture:**
- Resources: `vietnamese_words.txt`, `hanviet_markers.json`, `hanviet_dict.json`, `prompt_hanviet.md`.
- Scanner: `src/scanner/hanviet_scanner.py` with hybrid detection (known markers + dictionary anomaly).
- Packaging: Outputs `hanviet_all.json`, `hanviet_master.json`, and `hanviet_*.md` chunks into `scanner/hanviet/`.
- Uploader: Extend `src/scanner/upload_to_gemini.py` to handle `hanviet_*.md` chunks.
- Replacer: Update `ReplaceEngine` and `src/replacer/main.py` to compile `hanviet_dict.json` alongside character and common dictionaries.
- CLI: Add menu options [10]–[14] in `run_cli.py`.

**Tech Stack:** Python 3.12, pathlib, json, regex, urllib, pytest.

## Global Constraints
- Han-Viet outputs must be stored in `scanner/hanviet/`.
- Dedicated dictionary file is `resources/dictionaries/hanviet_dict.json`.
- Preserve 100% test pass rate across existing 47 unit tests.

---

### Task 1: Resources & Dictionary Acquisition

**Files:**
- Create: `tools/download_wordlist.py`
- Create: `resources/dictionaries/vietnamese_words.txt`
- Create: `resources/dictionaries/hanviet_markers.json`
- Create: `resources/dictionaries/hanviet_dict.json`
- Create: `resources/prompts/prompt_hanviet.md`

- [ ] **Step 1: Create download script and fetch `vietnamese_words.txt`**
Download standard Vietnamese wordlist from VNTK GitHub raw repository and store in `resources/dictionaries/vietnamese_words.txt`.

- [ ] **Step 2: Create `resources/dictionaries/hanviet_markers.json`**
Curate a comprehensive list of classic raw Han-Viet / convert marker expressions (e.g., *thập phần, đáo để, hảo tượng, dĩ kinh, chích thị, vô pháp, thảng như, nhược thị, hồi sự, nhất tràng, bị... cấp, đem... cấp*).

- [ ] **Step 3: Create initial `resources/dictionaries/hanviet_dict.json`**
Initialize with empty dictionary `{}` or sample baseline mappings.

- [ ] **Step 4: Create prompt template `resources/prompts/prompt_hanviet.md`**
Define instructions for Gemini to review Han-Viet expressions with context and propose natural Vietnamese translations.

---

### Task 2: Implement Han-Viet Scanner Module (`src/scanner/hanviet_scanner.py`)

**Files:**
- Create: `src/scanner/hanviet_scanner.py`

- [ ] **Step 1: Implement data models and resource loaders**
Implement `HanVietBlock`, `load_vietnamese_words(path)`, and `load_hanviet_markers(path)`.

- [ ] **Step 2: Implement scanning logic (Hybrid Detection)**
Scan text for:
1. Exact and regex matches of known markers in `hanviet_markers.json`.
2. Multi-word phrases (2-3 words) not found in `vietnamese_words.txt` (filtering numbers, punctuation, and known words).
Extract context sentences and count occurrences.

- [ ] **Step 3: Implement Output Packager for Han-Viet**
Stream `hanviet_master.json` and chunked markdown files `hanviet_*.md` into `scanner/hanviet/`.
Save `hanviet_all.json`.

- [ ] **Step 4: Implement CLI interface and `--filter-only` mode**
Enable running `python -m src.scanner.hanviet_scanner` with `--input`, `--output`, `--min-count`, `--chunk-size`, and `--filter-only`.

---

### Task 3: Adapt Gemini Uploader for Han-Viet Chunks

**Files:**
- Modify: `src/scanner/upload_to_gemini.py`

- [ ] **Step 1: Support pattern matching for both `scanner_*.md` and `hanviet_*.md`**
Update `s_dir.glob("*.md")` or dynamic prefix matching so that `scanner_dir="scanner/hanviet"` finds `hanviet_*.md`.

---

### Task 4: Integrate Han-Viet Dictionary into Replace Engine

**Files:**
- Modify: `src/replacer/replace_engine.py`
- Modify: `src/replacer/main.py`

- [ ] **Step 1: Update `ReplaceEngine`**
Add `hanviet_dict_path` parameter to `ReplaceEngine.__init__`. Load and compile entries alongside character and common dictionaries.

- [ ] **Step 2: Update `src/replacer/main.py`**
Add `--hanviet-dict` argument with default `resources/dictionaries/hanviet_dict.json`.

---

### Task 5: Add Han-Viet Options to Interactive CLI Menu in `run_cli.py`

**Files:**
- Modify: `run_cli.py`

- [ ] **Step 1: Add Han-Viet workflow options [10] - [14]**
Options:
- [10] Toàn trình quét Hán Việt (Quét + Tự động gửi Gemini -> `samples/import_hanviet.json`).
- [11] Chỉ quét từ Hán Việt (Xuất `scanner/hanviet/`).
- [12] Chỉ gửi các file `scanner/hanviet/` lên Gemini -> `samples/import_hanviet.json`.
- [13] Lọc nhanh `scanner/hanviet/` theo số lần xuất hiện (min-count).
- [14] Nạp kết quả Hán Việt vào `hanviet_dict.json`.

- [ ] **Step 2: Update option [9] (Replace Engine)**
Ensure `run_cli.py` invokes `src.replacer.main` with `hanviet_dict.json` included.

---

### Task 6: Unit Testing & Verification

**Files:**
- Create: `tests/test_hanviet_scanner.py`

- [ ] **Step 1: Write unit tests for Han-Viet scanner and dictionaries**
Test marker detection, unknown phrase detection, output packaging to `scanner/hanviet/`, and ReplaceEngine integration.

- [ ] **Step 2: Run pytest across the entire test suite**
Ensure all existing tests plus new tests pass (100% PASS).
