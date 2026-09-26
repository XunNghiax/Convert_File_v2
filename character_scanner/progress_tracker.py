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
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
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

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(all_blocks, ensure_ascii=False, indent=2), encoding="utf-8")
        return len(all_blocks)
