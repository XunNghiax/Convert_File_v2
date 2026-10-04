from pathlib import Path
import json
import pytest
from src.scanner.resource_loader import ResourceLoader

def test_load_vn_2word_set(tmp_path: Path):
    dict_file = tmp_path / "vietnamese_words.txt"
    dict_file.write_text(
        "hoa\n"              # 1 từ -> bỏ qua
        "xoáy thuận\n"       # 2 từ -> nhận
        "từ chối\n"          # 2 từ -> nhận
        "cổ kính\n"          # 2 từ -> nhận
        "bác sĩ gia đình\n"  # 3 từ -> bỏ qua
        "# ghi chú\n"        # comment -> bỏ qua
        "\n",
        encoding="utf-8"
    )
    loader = ResourceLoader(base_dir=tmp_path)
    words = loader.load_vn_2word_set(dict_file)
    
    assert "xoáy thuận" in words
    assert "từ chối" in words
    assert "cổ kính" in words
    assert "hoa" not in words
    assert "bác sĩ gia đình" not in words
    assert len(words) == 3

def test_load_all_includes_chinese_names_and_vn_2word(tmp_path: Path):
    resources_dir = tmp_path / "resources"
    dict_dir = resources_dir / "dictionaries"
    filters_dir = resources_dir / "filters"
    dict_dir.mkdir(parents=True)
    filters_dir.mkdir(parents=True)

    (filters_dir / "surnames.txt").write_text("tần\nâu dương\n", encoding="utf-8")
    (dict_dir / "character_dict.json").write_text(json.dumps({"Tiêu Viêm": "Tiêu Viêm"}), encoding="utf-8")
    (dict_dir / "chinese_names_dict.json").write_text(json.dumps({"Dược Lão": "Dược Lão"}), encoding="utf-8")
    (dict_dir / "vietnamese_words.txt").write_text("xoáy thuận\nhoa\n", encoding="utf-8")

    loader = ResourceLoader(base_dir=tmp_path)
    loader.load_all()

    assert "tiêu viêm" in loader.known_characters
    assert "dược lão" in loader.known_characters
    assert "xoáy thuận" in loader.vn_2word_set
    assert "hoa" not in loader.vn_2word_set
