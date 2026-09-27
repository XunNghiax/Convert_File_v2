import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.scanner.upload_to_gemini import run_upload_workflow
from src.scanner.gemini_uploader import GeminiUploader

def test_gemini_uploader_has_new_chat():
    uploader = GeminiUploader("chrome_profiles")
    assert hasattr(uploader, "new_chat")
    assert callable(uploader.new_chat)
    assert len(uploader.NEW_CHAT_SELECTORS) > 0

def test_upload_workflow_realtime_and_new_chat_cycling(tmp_path: Path):
    scanner_dir = tmp_path / "scanner"
    scanner_dir.mkdir(parents=True, exist_ok=True)
    out_json = tmp_path / "import.json"
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    # Tạo 5 file scanner markdown mẫu
    for i in range(1, 6):
        f = scanner_dir / f"scanner_{i}.md"
        f.write_text(f"# Chunk {i}\n```json\n[]\n```", encoding="utf-8")

    # Giả lập phản hồi từ Gemini cho mỗi file
    mock_responses = {
        "scanner_1.md": [{"id": "ch_0001", "target": "Nhân vật 1"}],
        "scanner_2.md": [{"id": "ch_0002", "target": "Nhân vật 2"}],
        "scanner_3.md": [{"id": "ch_0003", "target": "Nhân vật 3"}],
        "scanner_4.md": [{"id": "ch_0004", "target": "Nhân vật 4"}],
        "scanner_5.md": [{"id": "ch_0005", "target": "Nhân vật 5"}],
    }

    recorded_import_snapshots = []

    def mock_send_and_extract(content: str):
        # Trích xuất số chunk từ content
        for fname, resp in mock_responses.items():
            chunk_num = fname.split("_")[1].split(".")[0]
            if f"# Chunk {chunk_num}" in content:
                # Kiểm tra trạng thái import.json trước khi nhận
                if out_json.exists():
                    recorded_import_snapshots.append(len(json.loads(out_json.read_text(encoding="utf-8"))))
                else:
                    recorded_import_snapshots.append(0)
                return resp
        return []

    mock_uploader_instance = MagicMock()
    mock_uploader_instance.send_and_extract.side_effect = mock_send_and_extract

    with patch("src.scanner.upload_to_gemini.GeminiUploader", return_value=mock_uploader_instance):
        total = run_upload_workflow(
            scanner_dir=scanner_dir,
            profile_dir=profile_dir,
            output_json=out_json,
            delay=0,
            headless=True,
            reset_progress=True,
            files_per_chat=2  # New chat mỗi 2 file: sau file 2 và sau file 4
        )

    assert total == 5
    assert out_json.exists()
    final_data = json.loads(out_json.read_text(encoding="utf-8"))
    assert len(final_data) == 5
    assert [x["target"] for x in final_data] == [f"Nhân vật {i}" for i in range(1, 6)]

    # Kiểm tra tính realtime: import.json tăng dần kích thước
    # Trước file 1: 0 mục -> Sau file 1: 1 mục -> Trước file 2: 1 mục -> Sau file 2: 2 mục...
    assert recorded_import_snapshots == [0, 1, 2, 3, 4]

    # Kiểm tra new_chat được gọi đúng 2 lần (sau file 2 và sau file 4)
    assert mock_uploader_instance.new_chat.call_count == 2

    # Chạy lại lần 2 (Resume) -> Tất cả đã hoàn tất từ trước, không gọi uploader nữa
    with patch("src.scanner.upload_to_gemini.GeminiUploader", return_value=mock_uploader_instance) as mock_cls:
        resumed_total = run_upload_workflow(
            scanner_dir=scanner_dir,
            profile_dir=profile_dir,
            output_json=out_json,
            delay=0,
            headless=True,
            reset_progress=False,
            files_per_chat=2
        )
        assert resumed_total == 5
        # Không khởi tạo GeminiUploader lại vì pending_files rỗng
        mock_cls.assert_not_called()
