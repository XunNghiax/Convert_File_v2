# Design Specification: Project Structure Optimization & Path Migration

- **Date:** 2026-09-27
- **Project:** Convert_File_v2
- **Topic:** Clean Directory Restructuring & Path Re-linking

## 1. Problem Statement
The current `Convert_File_v2` project has several structural pain points:
1. Static resources (`data/` dictionaries and `filters/` text sets) are split across multiple top-level directories.
2. Runtime generated output (`scanner/`) and large browser profile cache (`chrome_profiles/`) clutter the project root.
3. Test/sample data (`exam.txt`, `Thiếu Long .txt`, `file_nhan_vat.json`, `prompt.md`) are placed loose at the root.
4. Redundant documentation folders (`superpowers/` and `docs/superpowers/`).
5. Missing `pytest.ini`, leading to `ModuleNotFoundError` when running standard `pytest` command.

## 2. Target Directory Architecture
```text
Convert_File_v2/
├── run.bat
├── run_cli.py
├── pytest.ini
├── .gitignore
│
├── character_scanner/
│   ├── __init__.py
│   ├── benchmark.py
│   ├── boundary_trimmer.py
│   ├── candidate_extractor.py
│   ├── context_expander.py
│   ├── gemini_uploader.py
│   ├── json_extractor.py
│   ├── main.py
│   ├── output_packager.py
│   ├── progress_tracker.py
│   ├── resource_loader.py
│   ├── scanner_engine.py
│   └── upload_to_gemini.py
│
├── resources/
│   ├── dictionaries/
│   │   ├── character_dict.json
│   │   └── common_dict.json
│   ├── filters/
│   │   ├── blacklist.txt
│   │   ├── non_person.txt
│   │   ├── pronouns.txt
│   │   ├── surnames.txt
│   │   └── trailing_stopwords.txt
│   └── prompts/
│       └── prompt.md
│
├── samples/
│   ├── exam.txt
│   ├── "Thiếu Long .txt"
│   └── file_nhan_vat.json
│
├── output/
│   ├── scanner/
│   │   ├── scanner_1.md
│   │   ├── scanner_master.json
│   │   └── .gemini_progress.json
│   └── import.json
│
├── runtime/
│   └── chrome_profiles/
│       ├── chrome_data_1/
│       ├── chrome_data_2/
│       └── chrome_data_3/
│
├── tests/
│   └── (all test_*.py files)
│
├── docs/
│   ├── designs/
│   │   ├── design_character_scanner.md
│   │   └── design_gemini_uploader.md
│   ├── plans/
│   └── superpowers/
│
└── tools/
    ├── analyze_targets.py
    ├── categorize_all.py
    └── analyzed_summary.txt
```

## 3. Path Migration Contract
1. **`ResourceLoader.load_all(base_dir=Path("."))`**:
   - Searches `resources/filters` first; falls back to `filters/` if not found.
   - Searches `resources/dictionaries` first; falls back to `data/` if not found.
2. **`GeminiUploader.resolve_profile_path(profile_path)`**:
   - Checks `runtime/chrome_profiles/` before `chrome_profiles/`.
3. **`character_scanner.main` defaults**:
   - `--input`: defaults to `samples/exam.txt` (or checks root `exam.txt`).
   - `--output`: defaults to `output/scanner`.
   - `--prompt`: defaults to `resources/prompts/prompt.md` (or checks root `prompt.md`).
   - `--ground-truth`: defaults to `samples/file_nhan_vat.json`.
   - `--profile-dir`: defaults to `runtime/chrome_profiles`.
   - `--output-import-json`: defaults to `output/import.json`.
4. **`run_cli.py` & `run.bat`**:
   - Matches the updated defaults above.
5. **Testing**:
   - `pytest.ini` with `pythonpath = .` ensures both `pytest` and `python -m pytest` pass cleanly.
