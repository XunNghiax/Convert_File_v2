import json
from pathlib import Path
from src.replacer.replace_engine import ReplaceEngine

def test_longest_match_first():
    """Kiểm tra nguyên tắc Longest-Match-First: Từ dài hơn luôn được ưu tiên thay trước."""
    custom_map = {
        "Long Kiếm": "Long Kiem",
        "Long Kiếm Phi": "Long Kiem Phi"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    # Nếu sai thứ tự, "Long Kiếm" sẽ ăn trước làm "Long Kiếm Phi" -> "Long Kiem Phi"
    text = "Đại hiệp Long Kiếm Phi mang theo Long Kiếm hành tẩu giang hồ."
    result = engine.replace_line(text)

    assert result == "Đại hiệp Long Kiem Phi mang theo Long Kiem hành tẩu giang hồ."

def test_non_cascading_replacement():
    """Kiểm tra tính an toàn: Không bị lỗi thay thế vòng lặp / lồng nhau (A -> B -> C)."""
    custom_map = {
        "A": "B",
        "B": "C"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    text = "A gặp B tại quán trà."
    result = engine.replace_line(text)

    # Trong single-pass, A đổi thành B, và B đổi thành C. Ký tự B sinh ra từ A không bị đổi tiếp thành C.
    assert result == "B gặp C tại quán trà."

def test_empty_or_same_source_target():
    """Kiểm tra các mục không cần thay thế (source == target hoặc rỗng) được lọc bỏ sạch sẽ."""
    custom_map = {
        "Vương Bá Đao": "Vương Bá Đao",
        "": "Không tên",
        "Trương Tam": "Trương Tam Phong"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    assert len(engine.sorted_keys) == 1
    assert engine.sorted_keys == ["Trương Tam"]

    text = "Vương Bá Đao nói chuyện với Trương Tam."
    result = engine.replace_line(text)
    assert result == "Vương Bá Đao nói chuyện với Trương Tam Phong."

def test_stats_tracking():
    """Kiểm tra việc đếm chính xác tần suất thay thế của từng từ khóa."""
    custom_map = {
        "Long Kiếm Phi": "Long Kiem Phi",
        "Trương Tử Kiến": "Truong Tu Kien"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    text1 = "Long Kiếm Phi cùng Trương Tử Kiến bước ra."
    text2 = "Long Kiếm Phi mỉm cười gật đầu."

    engine.replace_line(text1)
    engine.replace_line(text2)

    assert engine.stats_counter["Long Kiếm Phi"] == 2
    assert engine.stats_counter["Trương Tử Kiến"] == 1

def test_replace_file_stream_and_atomic(tmp_path: Path):
    """Kiểm tra thay thế file văn bản dạng streaming và tính atomic write."""
    custom_map = {
        "Long ca": "Long đại ca",
        "Muội muội": "Hiền muội"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    input_file = tmp_path / "story.txt"
    input_file.write_text(
        "Long ca nhìn Muội muội nói: Đi thôi.\n"
        "Muội muội đáp: Vâng ạ, Long ca.\n"
        "Không có từ khóa ở dòng này.\n",
        encoding="utf-8"
    )

    output_file = tmp_path / "story_converted.txt"
    stats = engine.replace_file(input_file, output_file, show_progress=False)

    assert output_file.exists()
    assert not (tmp_path / "story_converted.txt.tmp").exists()
    assert stats.total_lines == 3
    assert stats.total_replacements == 4  # 2 lần Long ca + 2 lần Muội muội
    assert stats.lines_per_second > 0

    content = output_file.read_text(encoding="utf-8")
    assert "Long đại ca nhìn Hiền muội nói: Đi thôi." in content
    assert "Hiền muội đáp: Vâng ạ, Long đại ca." in content
    assert "Không có từ khóa ở dòng này." in content

def test_dictionary_loading_and_override_priority(tmp_path: Path):
    """Kiểm tra nạp 2 file từ điển JSON và quy tắc ưu tiên character_dict ghi đè common_dict."""
    common_dict = tmp_path / "common.json"
    common_dict.write_text(json.dumps([
        {"id": "co-1", "source": "Đại ca", "target": "Ca ca"},
        {"id": "co-2", "source": "Long Phi", "target": "Long Phi (Chung)"}
    ], ensure_ascii=False), encoding="utf-8")

    char_dict = tmp_path / "char.json"
    char_dict.write_text(json.dumps([
        {"id": "ch-1", "source": "Long Phi", "target": "Long Kiếm Phi"},
        {"id": "ch-2", "source": "Tử Kiến", "target": "Trương Tử Kiến"}
    ], ensure_ascii=False), encoding="utf-8")

    engine = ReplaceEngine(char_dict_path=char_dict, common_dict_path=common_dict)

    # Long Phi phải lấy theo char_dict ("Long Kiếm Phi") chứ không lấy "Long Phi (Chung)"
    assert engine.dict_map["Long Phi"] == "Long Kiếm Phi"
    assert engine.dict_map["Đại ca"] == "ca ca"
    assert engine.dict_map["Tử Kiến"] == "Trương Tử Kiến"
