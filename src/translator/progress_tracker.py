import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any


class TranslatorProgressTracker:
    """
    Manages translation checkpointing, atomic persistence,
    incremental file output appending, and ETA statistics.
    """

    def __init__(
        self,
        progress_file: Path | str,
        output_file: Path | str,
        total_chapters: int,
    ):
        self.progress_file = Path(progress_file)
        self.output_file = Path(output_file)
        self.total_chapters = total_chapters
        self.completed_chapters: Set[int] = set()
        self.chapter_durations: List[float] = []

        self._load_checkpoint()

    def _load_checkpoint(self) -> None:
        if not self.progress_file.exists():
            return
        try:
            data = json.loads(self.progress_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                saved_completed = data.get("completed_chapters", [])
                self.completed_chapters = set(saved_completed)
                self.chapter_durations = data.get("chapter_durations", [])
                if "total_chapters" in data and not self.total_chapters:
                    self.total_chapters = data["total_chapters"]
        except Exception:
            pass

    def _save_checkpoint(self) -> None:
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.progress_file.with_suffix(".tmp")
        payload = {
            "total_chapters": self.total_chapters,
            "completed_chapters": sorted(list(self.completed_chapters)),
            "chapter_durations": self.chapter_durations,
            "last_updated": datetime.now().isoformat()
        }
        tmp_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        os.replace(tmp_file, self.progress_file)

    def is_completed(self, chapter_index: int) -> bool:
        """Checks if a chapter has already been successfully translated."""
        return chapter_index in self.completed_chapters

    def get_resume_index(self) -> int:
        """Returns the first chapter index (1-based) that hasn't been completed."""
        for idx in range(1, self.total_chapters + 1):
            if idx not in self.completed_chapters:
                return idx
        return self.total_chapters + 1

    def mark_completed(
        self,
        chapter_index: int,
        chapter_title: str,
        translated_text: str,
        elapsed_seconds: float = 0.0,
    ) -> None:
        """
        Appends the translated chapter to the output text file
        and updates the checkpoint atomically.
        """
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if self.output_file.exists() and self.output_file.stat().st_size > 0 else "w"
        with open(self.output_file, mode, encoding="utf-8") as f:
            if mode == "a":
                f.write(f"\n\n=== {chapter_title} ===\n\n{translated_text}\n")
            else:
                f.write(f"=== {chapter_title} ===\n\n{translated_text}\n")
            f.flush()

        self.completed_chapters.add(chapter_index)
        if elapsed_seconds > 0:
            self.chapter_durations.append(elapsed_seconds)

        self._save_checkpoint()

    def get_stats(self) -> Dict[str, Any]:
        """Calculates progress statistics, completion rate, and estimated time remaining."""
        completed_count = len(self.completed_chapters)
        percent = (completed_count / self.total_chapters * 100.0) if self.total_chapters > 0 else 0.0

        avg_sec = (sum(self.chapter_durations) / len(self.chapter_durations)) if self.chapter_durations else 0.0
        remaining_count = max(0, self.total_chapters - completed_count)
        estimated_remaining_sec = remaining_count * avg_sec

        return {
            "completed": completed_count,
            "total": self.total_chapters,
            "percent": round(percent, 2),
            "avg_seconds_per_chapter": round(avg_sec, 2),
            "estimated_remaining_seconds": round(estimated_remaining_sec, 2)
        }
