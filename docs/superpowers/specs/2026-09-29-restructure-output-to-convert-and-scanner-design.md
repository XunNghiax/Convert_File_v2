# Design Specification: Restructure Output Folders to Root Convert and Scanner

## 1. Context & Motivation
Currently, generated runtime outputs are placed inside `output/`:
- `output/scanner/`: Generated markdown chunks and master/all JSON metadata.
- `output/replaced/`: Converted/replaced text outputs.

The goal is to flatten these directories directly under the project root `Convert_File_v2/`:
- Move `output/scanner` -> `scanner/`
- Move `output/replaced` -> `convert/`
- Delete the old `output/` directory
- Update all associated references in code, CLI menus, and configuration.

## 2. Structural Changes
1. **Directories**:
   - `scanner/`: Top-level folder for scanner chunks and metadata.
   - `convert/`: Top-level folder for converted text files.
   - Remove `output/`.

2. **Git Configuration**:
   - In `.gitignore`, replace `output/` with `convert/` and `scanner/`.

3. **Source Code**:
   - `src/replacer/main.py`: Update default destination to `convert/<stem>_converted<suffix>`.
   - `src/scanner/main.py`: Update default `--output` argument to `scanner`.
   - `src/scanner/upload_to_gemini.py`: Update default `scanner_dir` argument to `scanner`.
   - `run_cli.py`: Update CLI invocation flags and prompts from `output/scanner` -> `scanner` and `output/replaced` -> `convert`.

## 3. Verification
- Verify directories exist at the project root and `output/` is removed.
- Run `pytest` to confirm 100% of unit tests pass.
