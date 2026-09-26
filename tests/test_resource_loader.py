from pathlib import Path
from character_scanner.resource_loader import ResourceLoader

def test_load_surnames(tmp_path):
    f = tmp_path / "surnames.txt"
    f.write_text("# Surnames\ntrương\nlâm\nâu dương\n", encoding="utf-8")
    loader = ResourceLoader()
    single, compound = loader.load_surnames(f)
    assert "trương" in single
    assert "lâm" in single
    assert "âu dương" in compound

def test_load_word_set(tmp_path):
    f = tmp_path / "pronouns.txt"
    f.write_text("# Pronouns\nchúng ta\nbọn họ\n", encoding="utf-8")
    loader = ResourceLoader()
    words = loader.load_word_set(f)
    assert "chúng ta" in words
    assert "bọn họ" in words
