from pathlib import Path
from character_scanner.progress_tracker import ProgressTracker

def test_progress_tracker(tmp_path):
    progress_file = tmp_path / ".gemini_progress.json"
    import_file = tmp_path / "import.json"

    tracker = ProgressTracker(progress_file)
    assert not tracker.is_completed("scanner_1.md")

    sample_blocks_1 = [{"id": "ch_0001", "target": "Nhân Vật 1"}]
    sample_blocks_2 = [{"id": "ch_0002", "target": "Nhân Vật 2"}]

    tracker.save_file_result("scanner_1.md", sample_blocks_1)
    assert tracker.is_completed("scanner_1.md")

    tracker.save_file_result("scanner_2.md", sample_blocks_2)
    assert tracker.is_completed("scanner_2.md")

    total = tracker.export_to_import_json(import_file)
    assert total == 2
    assert import_file.exists()
