import json
from pathlib import Path
import pytest

from src.importer.dictionary_importer import (
    normalize_character_entry,
    normalize_common_entry,
    distribute_and_import,
    capitalize_first_letters,
    lowercase_all
)
from src.replacer.replace_engine import ReplaceEngine

def test_capitalize_first_letters_helper():
    assert capitalize_first_letters("lâm thi âm") == "Lâm Thi Âm"
    assert capitalize_first_letters("dương ngọc khanh") == "Dương Ngọc Khanh"
    assert capitalize_first_letters("Trương Mẫn mẫn") == "Trương Mẫn Mẫn"
    assert capitalize_first_letters("Jikko Sayuri") == "Jikko Sayuri"
    assert capitalize_first_letters("") == ""

def test_lowercase_all_helper():
    assert lowercase_all("Hoa Nhị") == "hoa nhị"
    assert lowercase_all("hoàng triều Hoa Cúc") == "hoàng triều hoa cúc"
    assert lowercase_all("Nhà Họ Dương") == "nhà họ dương"
    assert lowercase_all("CẢNH SÁT") == "cảnh sát"
    assert lowercase_all("") == ""

def test_normalize_character_entry_upcases_first_letters():
    raw = {
        "id": "ch_001",
        "source": "lâm thi âm",
        "target": "lâm thi âm",
        "Tag": "Nhân vật nữ"
    }
    norm = normalize_character_entry(raw)
    assert norm is not None
    assert norm["source"] == "lâm thi âm"
    assert norm["target"] == "Lâm Thi Âm"

def test_normalize_common_entry_lowercases_all():
    raw = {
        "id": "co_001",
        "source": "Hoa Nhị",
        "target": "Hoa Nhị",
        "category": "Cụm từ"
    }
    norm = normalize_common_entry(raw)
    assert norm is not None
    assert norm["source"] == "Hoa Nhị"
    assert norm["target"] == "hoa nhị"

def test_distribute_and_import_applies_casing_rules(tmp_path: Path):
    char_dict = tmp_path / "character_dict.json"
    common_dict = tmp_path / "common_dict.json"
    warning_path = tmp_path / "warning.json"

    char_dict.write_text("[]", encoding="utf-8")
    common_dict.write_text("[]", encoding="utf-8")

    items = [
        {
            "id": "item-1",
            "is_character": True,
            "source": "dương ngọc khanh",
            "target": "dương ngọc khanh",
            "yeu_to_nhan_biet": "Nữ chính"
        },
        {
            "id": "item-2",
            "is_character": False,
            "source": "Cảnh Sát",
            "target": "Cảnh Sát",
            "yeu_to_nhan_biet": "Nghề nghiệp"
        }
    ]

    res = distribute_and_import(
        items,
        char_dict_path=char_dict,
        common_dict_path=common_dict,
        warning_path=warning_path,
        validate_word_count=True
    )

    assert res["character"]["added"] == 1
    assert res["common"]["added"] == 1

    char_data = json.loads(char_dict.read_text(encoding="utf-8"))
    assert char_data[0]["target"] == "Dương Ngọc Khanh"

    common_data = json.loads(common_dict.read_text(encoding="utf-8"))
    assert common_data[0]["target"] == "cảnh sát"
