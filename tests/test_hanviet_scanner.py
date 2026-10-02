import json
import pytest
from pathlib import Path
from src.scanner.hanviet_scanner import (
    HanVietBlock,
    HanVietScanner,
    HanVietPackager,
    load_vietnamese_words,
    load_hanviet_markers
)
from src.replacer.replace_engine import ReplaceEngine

def test_load_vietnamese_words(tmp_path):
    dict_file = tmp_path / "words.txt"
    dict_file.write_text("xin chào\nbạn bè\ncon mèo\n", encoding="utf-8")
    words = load_vietnamese_words(dict_file)
    assert "xin chào" in words
    assert "bạn bè" in words
    assert "con mèo" in words
    assert "chó con" not in words

def test_load_hanviet_markers(tmp_path):
    markers_file = tmp_path / "markers.json"
    markers_data = [
        {"pattern": "thập phần", "suggestion": "vô cùng", "category": "adverb"},
        {"pattern": "đáo để", "suggestion": "rốt cuộc", "category": "adverb"}
    ]
    markers_file.write_text(json.dumps(markers_data, ensure_ascii=False), encoding="utf-8")
    loaded = load_hanviet_markers(markers_file)
    assert len(loaded) == 2
    assert loaded[0]["pattern"] == "thập phần"

def test_hanviet_scanner_markers_detection(tmp_path):
    words_file = tmp_path / "words.txt"
    words_file.write_text("hắn\nrất\ntức giận\nngười\n", encoding="utf-8")

    markers_file = tmp_path / "markers.json"
    markers_data = [
        {"pattern": "thập phần", "suggestion": "vô cùng", "category": "adverb"},
        {"pattern": "đáo để", "suggestion": "rốt cuộc", "category": "adverb"}
    ]
    markers_file.write_text(json.dumps(markers_data, ensure_ascii=False), encoding="utf-8")

    scanner = HanVietScanner(words_path=words_file, markers_path=markers_file)
    sample_text = (
        "Hắn thập phần tức giận khi nghe tin. "
        "Ngươi đáo để muốn làm cái gì? "
        "Hắn thập phần bình tĩnh bước đi."
    )

    blocks = scanner.scan_text(sample_text, scan_anomalies=False)
    sources = {b.source: b for b in blocks}

    assert "thập phần" in sources
    assert sources["thập phần"].so_lan_xuat_hien == 2
    assert sources["thập phần"].suggested_target == "vô cùng"
    assert "tức giận" in sources["thập phần"].context

    assert "đáo để" in sources
    assert sources["đáo để"].so_lan_xuat_hien == 1
    assert sources["đáo để"].suggested_target == "rốt cuộc"

def test_hanviet_scanner_anomaly_detection(tmp_path):
    words_file = tmp_path / "words.txt"
    # Chỉ có các từ này trong từ điển
    words_file.write_text("hắn\nđi\nvề\nnhà\n", encoding="utf-8")

    markers_file = tmp_path / "markers.json"
    markers_file.write_text("[]", encoding="utf-8")

    scanner = HanVietScanner(words_path=words_file, markers_path=markers_file)
    # Cụm "chước tửu" không có trong từ điển
    sample_text = "Hắn chước tửu một ly rồi uống cạn. Hắn chước tửu tiếp ly thứ hai."

    blocks = scanner.scan_text(sample_text, scan_anomalies=True)
    sources = {b.source: b for b in blocks}

    assert "chước tửu" in sources
    assert sources["chước tửu"].so_lan_xuat_hien == 2
    assert "Cụm từ ngoài từ điển" in sources["chước tửu"].yeu_to_nhan_biet

def test_hanviet_packager(tmp_path):
    prompt_file = tmp_path / "prompt_hanviet.md"
    prompt_file.write_text("PROMPT TEST HEADER", encoding="utf-8")

    blocks = [
        HanVietBlock(
            id=f"hv_{i:04d}",
            source=f"source_{i}",
            suggested_target=f"target_{i}",
            context=f"context_{i}",
            yeu_to_nhan_biet="test",
            so_lan_xuat_hien=i
        )
        for i in range(1, 15)
    ]

    out_dir = tmp_path / "hanviet_output"
    packager = HanVietPackager(prompt_path=prompt_file)
    total = packager.package(blocks, output_dir=out_dir, chunk_size=5)

    assert total == 14
    master_file = out_dir / "hanviet_output_master.json"
    assert master_file.exists()
    master_data = json.loads(master_file.read_text(encoding="utf-8"))
    assert len(master_data) == 14

    # 14 items với chunk_size=5 -> 3 files markdown con
    md_files = sorted(list(out_dir.glob("hanviet_output_*.md")))
    assert len(md_files) == 3
    content = md_files[0].read_text(encoding="utf-8")
    assert "PROMPT TEST HEADER" in content
    assert "source_1" in content

def test_replacer_engine_with_hanviet_dict(tmp_path):
    char_dict = tmp_path / "char_dict.json"
    char_dict.write_text(json.dumps([{"source": "tiêu viêm", "target": "Tiêu Viêm"}]), encoding="utf-8")

    hanviet_dict = tmp_path / "hanviet_dict.json"
    hanviet_dict.write_text(json.dumps([{"source": "thập phần", "target": "vô cùng"}]), encoding="utf-8")

    common_dict = tmp_path / "common_dict.json"
    common_dict.write_text(json.dumps([{"source": "cực độ", "target": "hết sức"}]), encoding="utf-8")

    engine = ReplaceEngine(
        char_dict_path=char_dict,
        hanviet_dict_path=hanviet_dict,
        common_dict_path=common_dict
    )

    assert "tiêu viêm" in engine.dict_map
    assert "thập phần" in engine.dict_map
    assert "cực độ" in engine.dict_map

    inp_file = tmp_path / "test.txt"
    inp_file.write_text("tiêu viêm thập phần tức giận và cực độ thất vọng.", encoding="utf-8")
    out_file = tmp_path / "test_converted.txt"

    engine.replace_file(inp_file, out_file, show_progress=False)
    assert out_file.exists()
    converted_text = out_file.read_text(encoding="utf-8")
    assert "Tiêu Viêm vô cùng tức giận và hết sức thất vọng." == converted_text

def test_hanviet_scanner_excludes_existing_dictionaries(tmp_path):
    words_file = tmp_path / "words.txt"
    words_file.write_text("hắn\nrất\nbuồn\n", encoding="utf-8")

    markers_file = tmp_path / "markers.json"
    markers_file.write_text(json.dumps([
        {"pattern": "thập phần", "suggestion": "vô cùng"},
        {"pattern": "đáo để", "suggestion": "rốt cuộc"}
    ]), encoding="utf-8")

    # Giả sử "thập phần" đã có trong hanviet_dict
    hanviet_dict = tmp_path / "hanviet_dict.json"
    hanviet_dict.write_text(json.dumps([{"source": "thập phần", "target": "vô cùng"}]), encoding="utf-8")

    # Giả sử "lưu ngọc" (không có trong từ điển tiếng Việt) đã có trong character_dict
    char_dict = tmp_path / "char_dict.json"
    char_dict.write_text(json.dumps([{"source": "lưu ngọc", "target": "Lưu Ngọc"}]), encoding="utf-8")

    # Giả sử "chước tửu" đã có trong common_dict
    common_dict = tmp_path / "common_dict.json"
    common_dict.write_text(json.dumps([{"source": "chước tửu", "target": "rót rượu"}]), encoding="utf-8")

    scanner = HanVietScanner(
        words_path=words_file,
        markers_path=markers_file,
        char_dict_path=char_dict,
        common_dict_path=common_dict,
        hanviet_dict_path=hanviet_dict
    )

    sample_text = (
        "Hắn thập phần buồn bã. "
        "Lưu ngọc đi vào phòng. "
        "Hắn chước tửu một ly. "
        "Ngươi đáo để muốn gì?"
    )

    blocks = scanner.scan_text(sample_text, scan_anomalies=True)
    sources = {b.source for b in blocks}

    # "thập phần" (có trong hanviet_dict), "lưu ngọc" (có trong char_dict), "chước tửu" (có trong common_dict) PHẢI BỊ LOẠI TRỪ
    assert "thập phần" not in sources
    assert "lưu ngọc" not in sources
    assert "chước tửu" not in sources

    # Chỉ còn "đáo để" (chưa có trong bất kỳ từ điển nào) được phát hiện
    assert "đáo để" in sources


def test_hanviet_scanner_filters_and_stopwords(tmp_path):
    words_file = tmp_path / "words.txt"
    words_file.write_text("tay\ntiếng\nngười\n", encoding="utf-8")

    markers_file = tmp_path / "markers.json"
    markers_file.write_text("[]", encoding="utf-8")

    filters_dir = tmp_path / "filters"
    filters_dir.mkdir()
    (filters_dir / "blacklist.txt").write_text("không có\ncủa hắn\n", encoding="utf-8")
    (filters_dir / "pronouns.txt").write_text("chúng nó\n", encoding="utf-8")
    (filters_dir / "trailing_stopwords.txt").write_text("thế này\n", encoding="utf-8")

    scanner = HanVietScanner(
        words_path=words_file,
        markers_path=markers_file,
        filters_dir=filters_dir
    )

    sample_text = (
        "không có ai ở đây cả. "
        "của hắn rất to lớn. "
        "chúng nó chạy đi đâu. "
        "trong lòng cảm thấy bất an. "
        "hai tay hắn run rẩy. "
        "hắn chước tửu một mình."
    )

    blocks = scanner.scan_text(sample_text, scan_anomalies=True)
    sources = {b.source for b in blocks}

    # Bị loại bởi blacklist: 'không có', 'của hắn'
    assert "không có" not in sources
    assert "của hắn" not in sources

    # Bị loại bởi pronouns: 'chúng nó'
    assert "chúng nó" not in sources

    # Bị loại bởi giới từ đứng đầu ('trong'): 'trong lòng'
    assert "trong lòng" not in sources

    # Bị loại bởi số từ + danh từ thường ('hai' + 'tay'): 'hai tay'
    assert "hai tay" not in sources

    # Cụm từ bất thường hợp lệ 'chước tửu' phải được giữ lại
    assert "chước tửu" in sources


