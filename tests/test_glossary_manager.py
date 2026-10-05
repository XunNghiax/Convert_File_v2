import json
from pathlib import Path
from src.translator.glossary_manager import GlossaryManager

def test_build_prompt_glossary(tmp_path):
    dict_dir = tmp_path / "resources" / "dictionaries"
    dict_dir.mkdir(parents=True)
    (dict_dir / "character_dict.json").write_text(json.dumps({
        "long kiếm phi": "Long Kiếm Phi",
        "thẩm thiến ảnh": "Thẩm Thiến Ảnh",
        "tô diệc khả": "Tô Diệc Khả"
    }), encoding="utf-8")
    (dict_dir / "common_dict.json").write_text(json.dumps({
        "sông viêm": "Sông Viêm"
    }), encoding="utf-8")
    (dict_dir / "deconvert_dict.json").write_text(json.dumps({
        "tô cũng có thể": "Tô Diệc Khả"
    }), encoding="utf-8")

    gm = GlossaryManager(base_dir=tmp_path)
    gm.load_dictionaries()

    chapter_text = "Long Kiếm Phi và Tô Diệc Khả cùng nhau đi dạo bên Sông Viêm."
    glossary = gm.build_prompt_glossary(chapter_text)

    assert "Long Kiếm Phi" in glossary
    assert "Tô Diệc Khả" in glossary
    assert "Sông Viêm" in glossary
    assert "Thẩm Thiến Ảnh" not in glossary  # Không xuất hiện trong chương thì không nhồi vào prompt

def test_parse_dual_output(tmp_path):
    gm = GlossaryManager(base_dir=tmp_path)
    ai_output = """=== BẢN DỊCH ===
Long Kiếm Phi bước nhanh về phía bờ sông Viêm.

=== TỪ ĐIỂN MỚI ===
- 炎河 => Sông Viêm (Loại: Địa danh)
- 稷下村 => Tắc Hạ thôn (Loại: Địa danh)
"""
    translation, new_terms = gm.parse_dual_output(ai_output)
    assert "Long Kiếm Phi bước nhanh" in translation
    assert "=== TỪ ĐIỂN MỚI ===" not in translation
    assert new_terms.get("炎河") == "Sông Viêm"
    assert new_terms.get("稷下村") == "Tắc Hạ thôn"

def test_integrate_new_terms(tmp_path):
    suggested_file = tmp_path / "samples" / "suggested_terms.json"
    gm = GlossaryManager(base_dir=tmp_path, suggested_file=suggested_file)
    
    terms = {
        "炎河": "Sông Viêm",
        "稷下村": "Tắc Hạ thôn"
    }
    gm.integrate_new_terms(terms)
    
    assert suggested_file.exists()
    saved = json.loads(suggested_file.read_text(encoding="utf-8"))
    assert saved.get("炎河") == "Sông Viêm"
    assert saved.get("稷下村") == "Tắc Hạ thôn"

def test_integrate_new_terms_filters_pinyin_and_invalid_terms(tmp_path):
    suggested_file = tmp_path / "samples" / "suggested_terms.json"
    gm = GlossaryManager(base_dir=tmp_path, suggested_file=suggested_file)
    
    dirty_terms = {
        "梅玉萱": "Mai Yuxuan",
        "邱玉贞": "Qiu Yuzhen",
        "阿飞": "A Fei",
        "炎帝": "Viêm Đế",
        "华夏神州": "Đại Hạ Trung Hoa"
    }
    gm.integrate_new_terms(dirty_terms)
    
    saved = json.loads(suggested_file.read_text(encoding="utf-8"))
    assert "炎帝" in saved
    assert saved["炎帝"] == "Viêm Đế"
    # Pinyin terms must be rejected or sanitized
    assert "Mai Yuxuan" not in saved.values()
    assert "Qiu Yuzhen" not in saved.values()
    assert "A Fei" not in saved.values()
    assert "Mai Yuxuan" not in gm.common_dict.values()

def test_build_prompt_glossary_chinese_keys(tmp_path):
    dict_dir = tmp_path / "resources" / "dictionaries"
    dict_dir.mkdir(parents=True)
    (dict_dir / "character_dict.json").write_text("{}", encoding="utf-8")
    (dict_dir / "common_dict.json").write_text("{}", encoding="utf-8")
    (dict_dir / "deconvert_dict.json").write_text("{}", encoding="utf-8")
    (dict_dir / "chinese_names_dict.json").write_text(json.dumps({
        "梅玉萱": "Mai Ngọc Huyên",
        "邱玉贞": "Khâu Ngọc Trinh",
        "阿飞": "A Phi"
    }), encoding="utf-8")

    gm = GlossaryManager(base_dir=tmp_path)
    gm.load_dictionaries()

    raw_chapter = "梅玉萱和阿飞坐在出租车上，旁边没有别人。"
    glossary = gm.build_prompt_glossary(raw_chapter)

    assert "梅玉萱 => Mai Ngọc Huyên" in glossary
    assert "阿飞 => A Phi" in glossary
    assert "邱玉贞" not in glossary
