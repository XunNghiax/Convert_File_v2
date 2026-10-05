import json
from io import BytesIO
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
from src.translator.ollama_client import OllamaTranslatorClient
from src.translator.translator_engine import TranslatorEngine

def test_ollama_client_health_check():
    client = OllamaTranslatorClient(base_url="https://fake-tunnel.trycloudflare.com")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert client.check_health() is True

def test_ollama_client_health_check_retries_on_transient_failure():
    client = OllamaTranslatorClient(base_url="https://fake-tunnel.trycloudflare.com")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    # First call raises URLError, second call returns mock_resp
    from urllib.error import URLError
    with patch("urllib.request.urlopen", side_effect=[URLError("Connection reset"), mock_resp]):
        with patch("time.sleep", return_value=None):
            assert client.check_health(retries=2) is True

def test_ollama_client_translate_chapter_streaming():
    client = OllamaTranslatorClient(base_url="https://fake-tunnel.trycloudflare.com")
    mock_resp = MagicMock()
    mock_resp.status = 200

    chunk1 = json.dumps({"message": {"content": "=== BẢN DỊCH ===\n"}}).encode("utf-8") + b"\n"
    chunk2 = json.dumps({"message": {"content": "Long Kiếm Phi."}}).encode("utf-8") + b"\n"
    mock_resp.__iter__.return_value = [chunk1, chunk2]
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    captured_payload = {}
    def mock_urlopen(req, *args, **kwargs):
        nonlocal captured_payload
        captured_payload = json.loads(req.data.decode("utf-8"))
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        result = client.translate_chapter("龙剑飞。")
        assert captured_payload.get("stream") is True
        assert "Long Kiếm Phi" in result

def test_ollama_client_translate_chapter():
    client = OllamaTranslatorClient(base_url="https://fake-tunnel.trycloudflare.com")
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_payload = {
        "message": {
            "role": "assistant",
            "content": "=== BẢN DỊCH ===\nXin chào thế giới."
        }
    }
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = client.translate_chapter("你好，世界。")
        assert "Xin chào thế giới" in result

def test_ollama_client_translate_chapter_retries_on_error():
    client = OllamaTranslatorClient(base_url="https://fake-tunnel.trycloudflare.com", max_retries=3)
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_payload = {
        "message": {
            "role": "assistant",
            "content": "Thành công sau khi thử lại."
        }
    }
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = None

    from urllib.error import URLError
    with patch("urllib.request.urlopen", side_effect=[URLError("524 Gateway Timeout"), mock_resp]):
        with patch("time.sleep", return_value=None):
            result = client.translate_chapter("你好")
            assert "Thành công" in result

def test_translator_engine_mock_run(tmp_path):
    raw_file = tmp_path / "raw.txt"
    raw_file.write_text("第一章 试运行\n\n龙剑飞走进了校园。", encoding="utf-8")
    out_file = tmp_path / "out.txt"

    engine = TranslatorEngine(
        colab_url="https://fake-tunnel.trycloudflare.com",
        base_dir=tmp_path
    )

    with patch.object(engine.client, "translate_chapter") as mock_translate:
        mock_translate.return_value = """=== BẢN DỊCH ===
Chương 1: Chạy thử
Long Kiếm Phi bước vào khuôn viên trường học.

=== TỪ ĐIỂN MỚI ===
- 龙剑飞 => Long Kiếm Phi
"""
        success = engine.translate_novel(
            raw_filepath=raw_file,
            output_filepath=out_file,
            max_chapters=1,
            run_post_processing=False
        )
        assert success is True
        assert out_file.exists()
        assert "Long Kiếm Phi bước vào" in out_file.read_text(encoding="utf-8")

def test_translator_engine_post_processing(tmp_path):
    dict_dir = tmp_path / "resources" / "dictionaries"
    dict_dir.mkdir(parents=True)
    (dict_dir / "character_dict.json").write_text("{}", encoding="utf-8")
    (dict_dir / "common_dict.json").write_text("{}", encoding="utf-8")
    (dict_dir / "deconvert_dict.json").write_text(json.dumps({
        "tô cũng có thể": "Tô Diệc Khả"
    }), encoding="utf-8")

    raw_file = tmp_path / "raw.txt"
    raw_file.write_text("第一章\n\n苏亦可来了。", encoding="utf-8")
    out_file = tmp_path / "out.txt"

    engine = TranslatorEngine(
        colab_url="https://fake-tunnel.trycloudflare.com",
        base_dir=tmp_path
    )

    with patch.object(engine.client, "translate_chapter") as mock_translate:
        mock_translate.return_value = """=== BẢN DỊCH ===
Chương 1
Tô cũng có thể đã đến rồi.
"""
        success = engine.translate_novel(
            raw_filepath=raw_file,
            output_filepath=out_file,
            max_chapters=1,
            run_post_processing=True
        )
        assert success is True
        content = out_file.read_text(encoding="utf-8")
        assert "Tô Diệc Khả đã đến rồi" in content
        assert "Tô cũng có thể" not in content

