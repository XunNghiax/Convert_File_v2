import json
import pytest
from pathlib import Path
from src.importer.dictionary_importer import get_next_id, import_entries, load_dictionary, normalize_entry

def test_get_next_id():
    entries = [
        {"id": "ch-1", "source": "a", "target": "b"},
        {"id": "ch-10", "source": "c", "target": "d"},
        {"id": "ch-5", "source": "e", "target": "f"}
    ]
    assert get_next_id(entries) == "ch-11"

def test_import_entries(tmp_path):
    dict_file = tmp_path / "character_dict.json"
    initial_data = [
        {"id": "ch-1", "source": "Hồng Lâu", "target": "Hong Lou", "Tag": "Old"}
    ]
    dict_file.write_text(json.dumps(initial_data, ensure_ascii=False), encoding="utf-8")

    # Thêm mới
    new_items = [
        {"id": "ch-51", "source": "Gavin Tĩnh", "target": "Giả Văn tĩnh", "Tag": ""}
    ]
    res = import_entries(new_items, dict_path=dict_file)
    assert res["added"] == 1
    assert res["total"] == 2

    # Đọc lại và kiểm tra
    data = load_dictionary(dict_file)
    assert len(data) == 2
    assert data[1]["id"] == "ch-51"
    assert data[1]["source"] == "Gavin Tĩnh"
    assert data[1]["target"] == "Giả Văn tĩnh"
    assert data[1]["Tag"] == ""

    # Cập nhật mục đã có
    update_items = [
        {"source": "Gavin Tĩnh", "target": "Giả Văn Tĩnh Mới", "Tag": "Updated"}
    ]
    res_update = import_entries(update_items, dict_path=dict_file, overwrite_existing=True)
    assert res_update["updated"] == 1

    data = load_dictionary(dict_file)
    assert len(data) == 2
    assert data[1]["target"] == "Giả Văn Tĩnh Mới"
    assert data[1]["Tag"] == "Updated"

def test_normalize_and_import_scanner_json(tmp_path):
    dict_file = tmp_path / "character_dict.json"
    dict_file.write_text("[]", encoding="utf-8")

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
    assert data[0]["source"] == "Trương Tử Kiến"
    assert data[0]["Tag"] == "Họ Trương"
    assert data[0]["id"] == "ch-1"

def test_distribute_and_import(tmp_path):
    char_dict = tmp_path / "character_dict.json"
    common_dict = tmp_path / "common_dict.json"
    char_dict.write_text("[]", encoding="utf-8")
    common_dict.write_text("[]", encoding="utf-8")

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
            "target": "haha",
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

    from src.importer.dictionary_importer import distribute_and_import
    res = distribute_and_import(
        mixed_items,
        char_dict_path=char_dict,
        common_dict_path=common_dict
    )

    assert res["character"]["added"] == 2
    assert res["common"]["added"] == 1

    char_data = load_dictionary(char_dict)
    assert len(char_data) == 2
    assert char_data[0]["source"] == "Lâm Ngọc Chi"
    assert char_data[0]["id"] == "ch-1"
    assert char_data[0]["Tag"] == "Nhân vật nữ"
    assert char_data[1]["source"] == "Tần Xảo Xảo"
    assert char_data[1]["id"] == "ch-2"

    common_data = load_dictionary(common_dict)
    assert len(common_data) == 1
    assert common_data[0]["source"] == "Ha Ha"
    assert common_data[0]["target"] == "haha"
    assert common_data[0]["id"] == "co-1"
    assert common_data[0]["category"] == "Từ cảm thán"

