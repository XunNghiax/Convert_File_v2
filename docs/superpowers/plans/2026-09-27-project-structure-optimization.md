# Project Structure Optimization & Path Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the `Convert_File_v2` project into a clean, modular directory layout and update all code, resource, profile, output, and test paths without breaking existing workflows.

**Architecture:** 
1. Group all static resources (`dictionaries`, `filters`, `prompts`) into a unified `resources/` folder.
2. Group samples and ground-truth data into `samples/`.
3. Separate runtime outputs (`output/scanner/`, `output/import.json`) and runtime browser cache (`runtime/chrome_profiles/`) from source code.
4. Add backwards-compatible path resolution in `ResourceLoader` and `GeminiUploader`.
5. Update `character_scanner.main`, `upload_to_gemini.py`, and `run_cli.py` to point to the new paths.
6. Configure `pytest.ini` so test execution works seamlessly.

**Tech Stack:** Python 3.12, Pytest, Playwright, Windows Batch / PowerShell.

## Global Constraints
- Must maintain 100% backward compatibility: if a user or test references the old paths or passes explicit paths, the application must still work.
- All 21 existing unit tests in `tests/` must pass cleanly.
- `run.bat` and `run_cli.py` must execute without error from the project root.

---

### Task 1: Create Directory Skeleton & Relocate Resources and Samples

**Files:**
- Create directories: `resources/dictionaries`, `resources/filters`, `resources/prompts`, `samples`, `output/scanner`, `runtime`
- Move files:
  - `data/*.json` -> `resources/dictionaries/`
  - `filters/*.txt` -> `resources/filters/`
  - `prompt.md` -> `resources/prompts/`
  - `exam.txt`, `Thiếu Long .txt`, `file_nhan_vat.json` -> `samples/`
  - `chrome_profiles` -> `runtime/chrome_profiles`
  - `scanner/*` -> `output/scanner/`

- [ ] **Step 1: Create target directory folders**
- [ ] **Step 2: Copy/Move files to the new target directories**
- [ ] **Step 3: Verify all files are in place**

---

### Task 2: Configure Pytest & Update Gitignore

**Files:**
- Create: `pytest.ini`
- Modify: `.gitignore`

- [ ] **Step 1: Create `pytest.ini` with `pythonpath = .`**
- [ ] **Step 2: Update `.gitignore` to ignore `output/`, `runtime/`, and remove legacy rules**
- [ ] **Step 3: Run `pytest` directly to verify configuration works**

---

### Task 3: Update Core Resource & Profile Path Resolution

**Files:**
- Modify: `character_scanner/resource_loader.py`
- Modify: `character_scanner/gemini_uploader.py`
- Test: `tests/test_resource_loader.py`, `tests/test_gemini_uploader.py`

- [ ] **Step 1: Update `ResourceLoader.load_all` to support `resources/` with fallback**
- [ ] **Step 2: Update `resolve_profile_path` to support `runtime/chrome_profiles/`**
- [ ] **Step 3: Run unit tests to confirm passing**
  Run: `pytest tests/test_resource_loader.py tests/test_gemini_uploader.py -v`

---

### Task 4: Update CLI & Workflow Defaults

**Files:**
- Modify: `character_scanner/main.py`
- Modify: `character_scanner/upload_to_gemini.py`
- Modify: `run_cli.py`

- [ ] **Step 1: Update default arguments in `character_scanner/main.py`**
- [ ] **Step 2: Update default arguments in `character_scanner/upload_to_gemini.py`**
- [ ] **Step 3: Update prompts and defaults in `run_cli.py`**
- [ ] **Step 4: Run CLI help command to verify argument defaults**
  Run: `python -m character_scanner.main --help`

---

### Task 5: Consolidate Documentation and Tools

**Files:**
- Move: `superpowers/*` -> `docs/`
- Move: `scratch/*` -> `tools/`
- Remove empty/redundant directories

- [ ] **Step 1: Move `superpowers/` contents into `docs/` and clean up duplicates**
- [ ] **Step 2: Move `scratch/` to `tools/`**
- [ ] **Step 3: Verify directory cleanliness**

---

### Task 6: Full Verification & End-to-End Test

**Files:**
- Test all components: `tests/`
- End-to-end scanner execution on `samples/exam.txt`

- [ ] **Step 1: Run all unit tests with `pytest`**
  Run: `pytest -v`
- [ ] **Step 2: Test scanner CLI on `samples/exam.txt`**
  Run: `python -m character_scanner.main --input samples/exam.txt --output output/scanner`
- [ ] **Step 3: Verify output files generated in `output/scanner`**
