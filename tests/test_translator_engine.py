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

