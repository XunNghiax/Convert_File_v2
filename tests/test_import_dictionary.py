import json
import pytest
from pathlib import Path
from src.importer.dictionary_importer import (
    get_next_id,
    import_character_dict,
    import_common_dict,
    import_entries,
    load_dictionary,
    save_dictionary,
    distribute_and_import
)

def test_get_next_id():
    entries = [
        {"id": "ch-1", "source": "a", "target": "b"},
        {"id": "ch-10", "source": "c", "target": "d"},
        {"id": "ch-5", "source": "e", "target": "f"}
    ]
    assert get_next_id(entries) == "ch-11"
    assert get_next_id({}) == ""

def test_import_entries(tmp_path):
    dict_file = tmp_path / "character_dict.json"
    dict_file.write_text(json.dumps({"hồng lâu": "Hong Lou"}, ensure_ascii=False), encoding="utf-8")

    new_items = [
        {"source": "gavin tĩnh", "target": "giả tĩnh"}
    ]
    res = import_character_dict(new_items, dict_path=dict_file)
    assert res["added"] == 1
    assert res["total"] == 2

    data = load_dictionary(dict_file)
    assert data["gavin tĩnh"] == "Giả Tĩnh"

    update_items = [
        {"source": "gavin tĩnh", "target": "giả mới"}
    ]
    res_update = import_character_dict(update_items, dict_path=dict_file, overwrite_existing=True)
    assert res_update["updated"] == 1
    data = load_dictionary(dict_file)
    assert data["gavin tĩnh"] == "Giả Mới"

def test_normalize_and_import_scanner_json(tmp_path):
    dict_file = tmp_path / "character_dict.json"
    dict_file.write_text("{}", encoding="utf-8")

    scanner_output = [
        {
            "id": "ch_0001",
            "is_character": True,
            "source": "Trương Tử Kiến",
            "target": "Trương Tử Kiến",
            "yeu_to_nhan_biet": "Họ Trương",
            "suggested_target": "Trương Tử Kiến"
        },
        {
            "id": "ch_0002",
            "is_character": False,
            "source": "Ha Ha",
            "target": "Ha Ha",
            "yeu_to_nhan_biet": "Từ cảm thán"
        }
    ]

    res = import_entries(scanner_output, dict_path=dict_file, filter_characters=True)
    assert res["added"] == 1
    assert res["skipped"] == 1  # Mục is_character: False bị bỏ qua
    assert res["total"] == 1

    data = load_dictionary(dict_file)
    assert data["trương tử kiến"] == "Trương Tử Kiến"

def test_distribute_and_import(tmp_path):
    char_dict = tmp_path / "character_dict.json"
    common_dict = tmp_path / "common_dict.json"
    char_dict.write_text("{}", encoding="utf-8")
    common_dict.write_text("{}", encoding="utf-8")

    mixed_items = [
        {
            "id": "ch_0001",
            "is_character": True,
            "source": "Lâm Ngọc Chi",
            "target": "Lâm Ngọc Chi",
            "yeu_to_nhan_biet": "Nhân vật nữ"
        },
        {
            "id": "ch_0002",
            "is_character": False,
            "source": "Ha Ha",
            "target": "Ha Ha",
            "yeu_to_nhan_biet": "Từ cảm thán"
        },
        {
            "id": "ch_0003",
            "is_character": True,
            "source": "Tần Xảo Xảo",
            "target": "Tần Xảo Xảo",
            "yeu_to_nhan_biet": "Thiếu phụ"
        }
    ]

    res = distribute_and_import(
        mixed_items,
        char_dict_path=char_dict,
        common_dict_path=common_dict
    )

    assert res["character"]["added"] == 2
    assert res["common"]["added"] == 1

    char_data = load_dictionary(char_dict)
    assert len(char_data) == 2
    assert char_data["lâm ngọc chi"] == "Lâm Ngọc Chi"
    assert char_data["tần xảo xảo"] == "Tần Xảo Xảo"

    common_data = load_dictionary(common_dict)
    assert len(common_data) == 1
    assert common_data["ha ha"] == "ha ha"
