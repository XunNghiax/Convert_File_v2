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

def test_import_from_md_sample(tmp_path):
    from tools.import_characters_from_md import main as run_import
    # Verify tools/import_characters_from_md.py can run and loads 91 gold items
    md_file = Path("samples/danh_sach_nhan_vat.md")
    assert md_file.exists()
    
    char_dict = load_dictionary("resources/dictionaries/character_dict.json")
    # Verify all 91 gold items are in character_dict.json
    import re
    md_text = md_file.read_text(encoding="utf-8")
    gold_data = json.loads(re.search(r"```json\s*(\[.*?\])\s*```", md_text, re.DOTALL).group(1))
    
    assert len(gold_data) == 91
    for item in gold_data:
        name = item["ten_han_viet"].strip()
        assert name.lower() in char_dict
        assert char_dict[name.lower()] == name

def test_deduplicate_by_suggested_target_keeps_max_two():
    from src.importer.dictionary_importer import deduplicate_by_suggested_target
    items = [
        {"id": "1", "source": "Lý Vân ôm", "suggested_target": "Lý Vân"},
        {"id": "2", "source": "Lý Vân địt", "suggested_target": "Lý Vân"},
        {"id": "3", "source": "Lý Vân đi", "suggested_target": "Lý Vân"},
        {"id": "4", "source": "Lý Vân đè", "suggested_target": "Lý Vân"},
        {"id": "5", "source": "Trương Ba", "suggested_target": "Trương Ba"},
    ]
    deduped = deduplicate_by_suggested_target(items, max_occurrences=2)
    assert len(deduped) == 3
    # Chỉ giữ 2 cái đầu của "Lý Vân"
    assert [x["id"] for x in deduped] == ["1", "2", "5"]

def test_word_count_check_uses_suggested_target(tmp_path: Path):
    from src.importer.dictionary_importer import filter_and_export_warnings
    warn_file = tmp_path / "warning.json"
    items = [
        # Lệch từ: source 3 từ != suggested_target 2 từ -> vào warning
        {"id": "ch_0014", "source": "Lý Vân địt", "target": "Lý Vân Địt", "suggested_target": "Lý Vân"},
        # Khớp từ: source 2 từ == suggested_target 2 từ -> hợp lệ
        {"id": "ch_0015", "source": "Lý Vân", "target": "Lý Vân", "suggested_target": "Lý Vân"},
    ]
    valid, warnings = filter_and_export_warnings(items, warning_path=warn_file)
    assert len(valid) == 1
    assert valid[0]["id"] == "ch_0015"
    assert len(warnings) == 1
    assert warnings[0]["id"] == "ch_0014"
    assert "Lệch số từ" in warnings[0]["reason"]

def test_content_mismatch_between_source_and_suggested_target_goes_to_warning(tmp_path: Path):
    from src.importer.dictionary_importer import filter_and_export_warnings
    warn_file = tmp_path / "warning.json"
    items = [
        # Cùng 3 từ nhưng nội dung khác nhau -> vào warning
        {"id": "ch_0020", "source": "Thẩm Thần Ảnh", "target": "Thẩm Thiến Ảnh", "suggested_target": "Thẩm Thiến Ảnh"},
        # Cùng 3 từ và nội dung trùng nhau (chỉ khác hoa thường) -> hợp lệ
        {"id": "ch_0021", "source": "thẩm thiến ảnh", "target": "Thẩm Thiến Ảnh", "suggested_target": "Thẩm Thiến Ảnh"},
    ]
    valid, warnings = filter_and_export_warnings(items, warning_path=warn_file)
    assert len(valid) == 1
    assert valid[0]["id"] == "ch_0021"
    assert len(warnings) == 1
    assert warnings[0]["id"] == "ch_0020"
    assert "Nội dung không trùng nhau" in warnings[0]["reason"]

def test_user_scenario_e2e_distribute_and_import(tmp_path: Path):
    char_dict = tmp_path / "character_dict.json"
    common_dict = tmp_path / "common_dict.json"
    warn_file = tmp_path / "warning.json"

    items = [
        # 1. Khớp từ & khớp nội dung -> nạp vào character_dict
        {"id": "ch_0001", "is_character": True, "source": "Lý Vân", "target": "Lý Vân", "suggested_target": "Lý Vân"},
        # 2. Duplicate suggested_target "Lý Vân" thứ 2 -> cùng từ nhưng khác nội dung -> vào warning
        {"id": "ch_0002", "is_character": True, "source": "Lý Lan", "target": "Lý Lan", "suggested_target": "Lý Vân"},
        # 3. Duplicate suggested_target "Lý Vân" thứ 3 -> bị deduplicate loại bỏ sớm, không vào dictionary hay warning
        {"id": "ch_0003", "is_character": True, "source": "Lý Vân đi", "target": "Lý Vân Đi", "suggested_target": "Lý Vân"},
        # 4. Lệch số từ (3 từ != 2 từ) -> vào warning
        {"id": "ch_0014", "is_character": True, "source": "Lý Vân địt", "target": "Lý Vân Địt", "suggested_target": "Lý Vân Tâm"},
        # 5. Khớp từ & khớp nội dung nhân vật khác -> nạp vào character_dict
        {"id": "ch_0005", "is_character": True, "source": "Lâm Ngọc Chi", "target": "Lâm Ngọc Chi", "suggested_target": "Lâm Ngọc Chi"},
    ]

    res = distribute_and_import(
        items,
        char_dict_path=char_dict,
        common_dict_path=common_dict,
        warning_path=warn_file,
        validate_word_count=True,
        max_duplicate_suggested_targets=2
    )

    # ch_0003 bị loại bởi deduplicate (chỉ giữ 2 cái có suggested_target="Lý Vân" là ch_0001, ch_0002)
    # Trong các mục còn lại:
    # ch_0001: hợp lệ -> char_dict
    # ch_0002: lệch nội dung (Lý Lan != Lý Vân) -> warning
    # ch_0014: lệch số từ (3 từ != 3 từ) -> wait: Lý Vân địt (3 từ) vs Lý Vân Tâm (3 từ)?
    # Wait, Lý Vân địt vs Lý Vân Tâm cùng 3 từ nhưng nội dung khác nhau -> warning!
    # ch_0005: hợp lệ -> char_dict
    assert res["character"]["added"] == 2
    char_data = load_dictionary(char_dict)
    assert "lý vân" in char_data
    assert char_data["lý vân"] == "Lý Vân"
    assert "lâm ngọc chi" in char_data
    assert char_data["lâm ngọc chi"] == "Lâm Ngọc Chi"

    assert res["warning_count"] == 2
    w_data = json.loads(warn_file.read_text(encoding="utf-8"))
    assert len(w_data) == 2
    w_ids = [w["id"] for w in w_data]
    assert "ch_0002" in w_ids
    assert "ch_0014" in w_ids



