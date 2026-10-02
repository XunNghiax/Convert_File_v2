# Design Specification: Abnormal Han-Viet Scanner and Dedicated Dictionary System

## 1. Context & Motivation
In machine-translated / converted web novels (truyện convert từ tiếng Trung sang tiếng Việt), raw Sino-Vietnamese words (từ Hán Việt thô/sượng, hư từ, ngữ pháp tiếng Hán) frequently appear without natural Vietnamese localization (e.g., *thập phần*, *đáo để*, *hảo tượng*, *dĩ kinh*, *chích thị*, *vô pháp*, *nhất tràng*, *đem... cấp...*).

After scanning character names, the system needs a dedicated pipeline to scan, detect, review/edit, and replace these abnormal Han-Viet words. This pipeline operates symmetrically to the character scanner system.

## 2. Structural & Architectural Design

### 2.1. Resources & Dictionaries
1. **Standard Vietnamese Wordlist (`resources/dictionaries/vietnamese_words.txt`)**:
   - ~39,000 standard Vietnamese words downloaded from open-source VNTK repo.
   - Used as a reference baseline to identify unnatural non-standard multi-word combinations.
2. **Han-Viet Raw Markers (`resources/dictionaries/hanviet_markers.json`)**:
   - Curated list of classic raw Han-Viet / convert marker phrases, adverbials, and awkward conjunctions.
3. **Dedicated Han-Viet Dictionary (`resources/dictionaries/hanviet_dict.json`)**:
   - Independent dictionary storing `{ "source_hanviet": "target_vietnamese", ... }`.
   - Populated after reviewing scanner outputs or AI Gemini results.
4. **Prompt Template (`resources/prompts/prompt_hanviet.md`)**:
   - Markdown prompt tailored for Gemini to analyze abnormal Han-Viet expressions with context and propose natural Vietnamese translations.

### 2.2. Scanner Engine (`src/scanner/hanviet_scanner.py`)
- **Input**: Source text file (e.g. `samples/exam.txt`), min-count threshold, chunk size.
- **Scanning Logic**:
  1. *Known Markers Matching*: Searches for known awkward Han-Viet patterns in the text.
  2. *Lexical Anomaly Extraction*: Detects 2-3 word sequences not found in `vietnamese_words.txt`, ignoring pure punctuation, numbers, and known common words.
  3. *Context Extraction*: Captures the sentence/paragraph context for each occurrence.
  4. *Deduplication & Frequency Aggregation*: Aggregates counts and sample contexts.
- **Output Packager**:
  - Outputs directly to `scanner/hanviet/`:
    - `hanviet_all.json`: All candidates before filtering.
    - `hanviet_master.json`: Filtered candidates meeting `min_count`.
    - `hanviet_1.md`, `hanviet_2.md`, ...: Segmented chunks formatted with `prompt_hanviet.md` for Gemini submission or manual review.

### 2.3. Gemini Uploader & Importer Integration
- **Uploader**:
  - Reusable workflow sending markdown files in `scanner/hanviet/` to Gemini, tracking progress in `scanner/hanviet/.gemini_progress.json`, and writing results to `samples/import_hanviet.json`.
- **Importer (`src/importer/main.py`)**:
  - Supports `--dict resources/dictionaries/hanviet_dict.json` or automatic routing.
- **Replace Engine (`src/replacer/replace_engine.py` & `src/replacer/main.py`)**:
  - Accepts `--hanviet-dict` (default: `resources/dictionaries/hanviet_dict.json`).
  - Combines character dictionary, Han-Viet dictionary, and common dictionary in a unified longest-match single-pass compiler.

### 2.4. Interactive CLI (`run_cli.py`)
- Add a new menu group for Han-Viet workflow:
  - Option [10]: Full workflow (Scan + Upload Gemini -> `samples/import_hanviet.json`).
  - Option [11]: Scan text only -> `scanner/hanviet/`.
  - Option [12]: Upload existing `scanner/hanviet/` chunks to Gemini.
  - Option [13]: Fast filter `scanner/hanviet/` by min-count.
  - Option [14]: Import `samples/import_hanviet.json` into `hanviet_dict.json`.
  - Option [9] (Replace Engine): Automatically includes `hanviet_dict.json` in replacement rules.

## 3. Testing & Verification
- Unit test for standard wordlist loader.
- Unit test for Han-Viet scanner (marker detection, unknown phrase detection, context expansion, packaging).
- Unit test for ReplaceEngine loading character + Han-Viet + common dictionaries simultaneously.
- Verify full test suite pass rate (100%).
