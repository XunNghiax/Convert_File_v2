# Restructure Output Folders to Convert and Scanner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move `output/scanner` and `output/replaced` to the project root as `scanner/` and `convert/`, delete `output/`, and update all code/CLI references.

**Architecture:** Filesystem restructuring followed by configuration updates (.gitignore) and code refactoring in `src/replacer/main.py`, `src/scanner/main.py`, `src/scanner/upload_to_gemini.py`, and `run_cli.py`.

**Tech Stack:** Python 3.12, pathlib, argparse, pytest.

## Global Constraints
- Target paths: `scanner/` and `convert/` directly under project root `Convert_File_v2/`.
- No lingering `output/` directory.
- Preserve 100% test pass rate across existing unit tests.

---

### Task 1: Move Filesystem Directories and Clean Up Old Output Folder

**Files:**
- Move: `output/scanner` -> `scanner/`
- Move: `output/replaced` -> `convert/`
- Delete: `output/`

- [ ] **Step 1: Move `output/scanner` to `scanner/` and `output/replaced` to `convert/`**
Move directories preserving any existing files. If `output/replaced` does not exist or is empty, create `convert/`.

- [ ] **Step 2: Remove the empty `output/` directory**
Ensure `output/` no longer exists.

- [ ] **Step 3: Verify filesystem state**
Check that `scanner/` and `convert/` exist at root and `output/` is removed.

---

### Task 2: Update `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update `.gitignore`**
Replace `output/` with `convert/` and `scanner/`.

- [ ] **Step 2: Verify git status**
Run `git status` to ensure git is not tracking files inside `convert/` or `scanner/`.

---

### Task 3: Update Core Application Defaults in Replacer and Scanner Modules

**Files:**
- Modify: `src/replacer/main.py`
- Modify: `src/scanner/main.py`
- Modify: `src/scanner/upload_to_gemini.py`

- [ ] **Step 1: Update `src/replacer/main.py`**
Change default output destination from `output/replaced/<stem>_converted<suffix>` to `convert/<stem>_converted<suffix>`.
Update argument help text for `--output`.

- [ ] **Step 2: Update `src/scanner/main.py`**
Change `--output` default from `"output/scanner"` to `"scanner"`.
Update fallback directory resolution logic if `output_dir` does not exist.

- [ ] **Step 3: Update `src/scanner/upload_to_gemini.py`**
Change default `scanner_dir` from `"output/scanner"` to `"scanner"`.
Update argument help text and fallback directory resolution logic.

---

### Task 4: Update Interactive CLI Menu in `run_cli.py`

**Files:**
- Modify: `run_cli.py`

- [ ] **Step 1: Update `run_cli.py`**
Update CLI arguments in menu options [1], [2], [4], [5] from `"output/scanner"` to `"scanner"`.
Update default prompt in option [3] from `"output/scanner"` to `"scanner"`.
Update default replace output path in option [9] from `output/replaced/...` to `convert/...`.

- [ ] **Step 2: Verify test suite**
Run `pytest` to confirm all 47 tests pass.
