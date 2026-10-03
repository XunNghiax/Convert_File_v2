from pathlib import Path
from src.translator.chapter_splitter import ChapterSplitter, Chapter

def test_split_chapters_basic(tmp_path):
    content = """第一卷 闯荡都市
    
第一章 公车南下
龙剑飞的心情象这春末夏初的天气多少有些烦躁。

第二章 英雄救美
炎河是黄河的一个小支流，虽然不阔，却水深流急。
"""
    file_path = tmp_path / "test_raw.txt"
    file_path.write_text(content, encoding="utf-8")

    splitter = ChapterSplitter()
    chapters = splitter.split_file(file_path)

    assert len(chapters) == 2
    assert chapters[0].index == 1
    assert "第一章" in chapters[0].title
    assert "龙剑飞" in chapters[0].content
    assert chapters[1].index == 2
    assert "第二章" in chapters[1].title
    assert "炎河" in chapters[1].content

def test_split_long_chapter(tmp_path):
    # Kiểm tra tự động tách sub-chunk nếu chương quá dài (> max_chars)
    long_para = "龙剑飞在河中奋力游动。" * 200 # ~2400 ký tự
    content = f"第一章 长章节\n\n{long_para}\n\n{long_para}"
    file_path = tmp_path / "long_raw.txt"
    file_path.write_text(content, encoding="utf-8")

    splitter = ChapterSplitter()
    chapters = splitter.split_file(file_path, max_chars=3000)
    assert len(chapters) >= 2
    assert chapters[0].title.startswith("第一章")
    assert chapters[0].index == 1
    assert chapters[1].index == 2

def test_split_raw_without_standard_headers(tmp_path):
    # Kiểm tra fallback khi file chỉ có các đoạn văn ngắt bởi \n\n
    content = "Đoạn 1 nội dung ngắn.\n\nĐoạn 2 nội dung tiếp theo."
    file_path = tmp_path / "no_header.txt"
    file_path.write_text(content, encoding="utf-8")

    splitter = ChapterSplitter()
    chapters = splitter.split_file(file_path, max_chars=1000)
    assert len(chapters) >= 1
    assert "Đoạn 1" in chapters[0].content
