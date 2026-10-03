import json
from pathlib import Path
import time
from src.translator.progress_tracker import TranslatorProgressTracker

def test_progress_tracking_and_resume(tmp_path):
    progress_file = tmp_path / "progress.json"
    output_file = tmp_path / "translated.txt"

    tracker = TranslatorProgressTracker(
        progress_file=progress_file,
        output_file=output_file,
        total_chapters=10
    )

    assert tracker.get_resume_index() == 1
    assert not tracker.is_completed(1)

    tracker.mark_completed(1, "Chương 1: Khởi đầu", "Nội dung chương 1 dịch.")
    assert tracker.is_completed(1)
    assert tracker.get_resume_index() == 2
    
    out_content = output_file.read_text(encoding="utf-8")
    assert "Chương 1: Khởi đầu" in out_content
    assert "Nội dung chương 1 dịch." in out_content

    # Khởi tạo lại tracker từ file checkpoint cũ để kiểm tra resume
    tracker_resume = TranslatorProgressTracker(
        progress_file=progress_file,
        output_file=output_file,
        total_chapters=10
    )
    assert tracker_resume.get_resume_index() == 2
    assert tracker_resume.is_completed(1)
    assert not tracker_resume.is_completed(2)

def test_progress_stats_and_eta(tmp_path):
    progress_file = tmp_path / "progress.json"
    output_file = tmp_path / "translated.txt"

    tracker = TranslatorProgressTracker(
        progress_file=progress_file,
        output_file=output_file,
        total_chapters=5
    )
    
    tracker.mark_completed(1, "Chương 1", "Dịch 1", elapsed_seconds=2.0)
    tracker.mark_completed(2, "Chương 2", "Dịch 2", elapsed_seconds=4.0)

    stats = tracker.get_stats()
    assert stats["completed"] == 2
    assert stats["total"] == 5
    assert stats["percent"] == 40.0
    assert stats["avg_seconds_per_chapter"] == 3.0
    assert stats["estimated_remaining_seconds"] == 9.0  # 3 remaining * 3.0s
