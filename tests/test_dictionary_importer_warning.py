import json
from pathlib import Path
from src.importer.dictionary_importer import (
    check_word_count_alignment,
    filter_and_export_warnings,
    distribute_and_import
)

def test_check_word_count_alignment():
    # Trường hợp khớp số từ
    ok, ws, wt, _ = check_word_count_alignment("Trương Tử Kiến", "Trương Tử Kiến")
    assert ok is True
    assert ws == 3 and wt == 3

    ok, ws, wt, _ = check_word_count_alignment("Lâm Thi Âm", "Lâm Thi Âm")
    assert ok is True
    assert ws == 3 and wt == 3

    # Trường hợp lệch số từ (thêm họ/tiền tố)
    ok, ws, wt, reason = check_word_count_alignment("Kiếm Phi", "Long Kiếm Phi")
    assert ok is False
    assert ws == 2 and wt == 3
    assert "Target (3 từ) dài hơn Source (2 từ)" in reason

    # Trường hợp lệch số từ (rút gọn cụm từ)
    ok, ws, wt, reason = check_word_count_alignment("bóng hình xinh đẹp", "Thiến Ảnh")
    assert ok is False
    assert ws == 4 and wt == 2
    assert "Target (2 từ) ngắn hơn Source (4 từ)" in reason

def test_filter_and_export_warnings(tmp_path: Path):
    warning_file = tmp_path / "warning.json"
    items = [
        {"id": "ch-1", "source": "Trương Tử Kiến", "target": "Trương Tử Kiến", "is_character": True},
        {"id": "ch-2", "source": "Kiếm Phi", "target": "Long Kiếm Phi", "is_character": True},
        {"id": "ch-3", "source": "bóng hình xinh đẹp", "target": "Thiến Ảnh", "is_character": True},
        {"id": "ch-4", "source": "Lâm Thi Âm", "target": "Lâm Thi Âm", "is_character": True}
    ]

    valid, warnings = filter_and_export_warnings(items, warning_path=warning_file)

    assert len(valid) == 2
    assert [x["source"] for x in valid] == ["Trương Tử Kiến", "Lâm Thi Âm"]

    assert len(warnings) == 2
    assert [x["source"] for x in warnings] == ["Kiếm Phi", "bóng hình xinh đẹp"]

    assert warning_file.exists()
    w_data = json.loads(warning_file.read_text(encoding="utf-8"))
    assert len(w_data) == 2
    assert w_data[0]["source"] == "Kiếm Phi"
    assert w_data[0]["words_source"] == 2
    assert w_data[0]["words_target"] == 3

def test_distribute_and_import_with_word_count_validation(tmp_path: Path):
    char_dict = tmp_path / "char_dict.json"
    common_dict = tmp_path / "common_dict.json"
    warning_file = tmp_path / "warning.json"

    items = [
        {"id": "ch-1", "source": "Long Kiếm Phi", "target": "Long Kiếm Phi", "is_character": True},
        {"id": "ch-2", "source": "Kiếm Phi", "target": "Long Kiếm Phi", "is_character": True}, # Lệch từ
        {"id": "co-1", "source": "tất chân", "target": "Tất Chân", "is_character": False},
        {"id": "co-2", "source": "bóng hình xinh đẹp", "target": "Thiến Ảnh", "is_character": False} # Lệch từ
    ]

    res = distribute_and_import(
        items,
        char_dict_path=char_dict,
        common_dict_path=common_dict,
        warning_path=warning_file,
        validate_word_count=True
    )

    assert res["warning_count"] == 2
    assert warning_file.exists()

    # Chỉ có 1 nhân vật hợp lệ (Long Kiếm Phi) và 1 từ chung hợp lệ (tất chân)
    assert res["character"]["added"] == 1
    assert res["common"]["added"] == 1

    char_data = json.loads(char_dict.read_text(encoding="utf-8"))
    assert len(char_data) == 1
    assert char_data["long kiếm phi"] == "Long Kiếm Phi"

    comm_data = json.loads(common_dict.read_text(encoding="utf-8"))
    assert len(comm_data) == 1
    assert comm_data["tất chân"] == "tất chân"
