from pathlib import Path
from src.scanner.resource_loader import ResourceLoader

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

def test_load_deconvert_dict(tmp_path):
    dict_dir = tmp_path / "resources" / "dictionaries"
    dict_dir.mkdir(parents=True)
    deconvert_file = dict_dir / "deconvert_dict.json"
    deconvert_file.write_text('{"tô cũng có thể": "Tô Diệc Khả", "mực đầu hạ": "Mặc Đầu Hạ"}', encoding="utf-8")
    
    loader = ResourceLoader(base_dir=tmp_path)
    loader.load_all()
    assert loader.deconvert_dict.get("tô cũng có thể") == "Tô Diệc Khả"
    assert loader.deconvert_dict.get("mực đầu hạ") == "Mặc Đầu Hạ"

