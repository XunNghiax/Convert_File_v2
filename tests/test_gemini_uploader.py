from pathlib import Path
from unittest.mock import MagicMock, patch
from src.scanner.gemini_uploader import GeminiUploader

def test_gemini_uploader_init():
    uploader = GeminiUploader("chrome_profiles")
    assert uploader.profile_dir.exists()
    assert (uploader.profile_dir / "Default").exists()
    assert uploader.json_extractor is not None

def test_send_and_extract_dispatches_file_path(tmp_path: Path):
    uploader = GeminiUploader("chrome_profiles")
    f = tmp_path / "test.md"
    f.write_text("# Test", encoding="utf-8")

    uploader.send_file_and_extract = MagicMock(return_value=[{"id": "ch_0001"}])
    res = uploader.send_and_extract(f)

    assert res == [{"id": "ch_0001"}]
    uploader.send_file_and_extract.assert_called_once_with(f, max_wait=150)

def test_send_and_extract_dispatches_str_path(tmp_path: Path):
    uploader = GeminiUploader("chrome_profiles")
    f = tmp_path / "test2.md"
    f.write_text("# Test 2", encoding="utf-8")

    uploader.send_file_and_extract = MagicMock(return_value=[{"id": "ch_0002"}])
    res = uploader.send_and_extract(str(f))

    assert res == [{"id": "ch_0002"}]
    uploader.send_file_and_extract.assert_called_once_with(f, max_wait=150)

def test_send_and_extract_raw_content_creates_temp_file_no_paste():
    uploader = GeminiUploader("chrome_profiles")
    raw_content = "# Raw Markdown Content\n```json\n[]\n```"

    recorded_path = []
    def fake_send_file(file_path: Path, max_wait: int = 150):
        recorded_path.append(file_path)
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == raw_content
        return [{"id": "ch_0003"}]

    uploader.send_file_and_extract = fake_send_file
    res = uploader.send_and_extract(raw_content)

    assert res == [{"id": "ch_0003"}]
    assert len(recorded_path) == 1
    # Sau khi xong, file tạm phải được dọn dẹp (unlink)
    assert not recorded_path[0].exists()

def test_log_cb_never_contains_file_content(tmp_path: Path):
    logged_messages = []
    uploader = GeminiUploader("chrome_profiles", log_cb=logged_messages.append)

    secret_content = "TUYET_MAT_NOI_DUNG_FILE_12345_KHONG_DUOC_LOG"
    f = tmp_path / "sensitive_scanner.md"
    f.write_text(secret_content, encoding="utf-8")

    uploader.upload_file = MagicMock(return_value=True)
    mock_page = MagicMock()
    # 0 ở initial_count, sau đó luôn là 1 để phát hiện response mới
    mock_page.locator.return_value.count.side_effect = lambda: 1 if getattr(mock_page, "_counted", False) else (setattr(mock_page, "_counted", True) or 0)
    # Trả về text > 20 ký tự để stable_count đạt 3 nhanh chóng
    dummy_resp = '```json\n[{"id": "ch_0001", "target": "Nhân vật bí mật"}]\n```'
    mock_page.locator.return_value.all_inner_texts.return_value = [dummy_resp]
    mock_btn = MagicMock()
    mock_btn.is_visible.return_value = True
    mock_btn.is_enabled.return_value = True
    mock_page.locator.return_value.all.return_value = [mock_btn]
    uploader.page = mock_page

    # Chạy với max_wait ngắn
    uploader.send_file_and_extract(f, max_wait=10)

    # Đảm bảo file name xuất hiện trong log
    assert any(f.name in msg for msg in logged_messages)
    # Tuyệt đối không có nội dung file trong bất kỳ log message nào
    assert not any(secret_content in msg for msg in logged_messages)


