import pytest
from src.translator.hanviet_transliterater import HanVietTransliterater

@pytest.fixture
def transliterater():
    return HanVietTransliterater()

def test_translate_chapter_title(transliterater):
    # Test standard Chinese chapter titles
    assert transliterater.translate_title("第一章　　公车南下") == "Chương 1: Công xa nam hạ"
    assert transliterater.translate_title("第二章　　江水春潮") == "Chương 2: Giang thủy xuân triều"
    assert transliterater.translate_title("第三章　　乍遇凶险") == "Chương 3: Sạ ngộ hung hiểm"
    assert transliterater.translate_title("第125章 深入虎穴") == "Chương 125: Thâm nhập hổ huyệt"
    assert transliterater.translate_title("第309章 大结局（终）") == "Chương 309: Đại kết cục (chung)"

def test_transliterate_chinese_words(transliterater):
    text = "Lưu Úy Như mặc một bộ 套装裙 màu hồng."
    cleaned = transliterater.clean_text(text)
    assert "套装裙" not in cleaned
    assert "bộ váy công sở" in cleaned or "sáo trang quần" in cleaned

def test_transliterate_pure_chinese_paragraph(transliterater):
    chinese_para = "清晨，空气怡人，明媚的阳光仿佛龙剑飞的心情。"
    res = transliterater.clean_text(chinese_para)
    assert not any('\u4e00' <= c <= '\u9fff' for c in res)
    assert "Long Kiếm Phi" in res or "long kiếm phi" in res.lower()

def test_zero_chinese_in_cleaned_text(transliterater):
    mixed_text = "Nàng mỉm cười nói: 「你好！」 rồi kéo 丝袜 lên."
    result = transliterater.clean_text(mixed_text)
    # Ensure 0% Chinese characters
    import re
    assert len(re.findall(r'[\u4e00-\u9fff]', result)) == 0
