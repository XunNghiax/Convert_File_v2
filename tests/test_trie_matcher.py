import pytest
from src.utils.trie_matcher import TrieMatcher

def test_trie_matcher_basic_find():
    matcher = TrieMatcher()
    matcher.add_keyword("tiêu viêm", "Tiêu Viêm")
    matcher.add_keyword("dược lão", "Dược Lão")
    matcher.build()

    text = "Hôm nay tiêu viêm gặp dược lão tại sơn cốc."
    matches = matcher.find_matches(text.lower())
    
    assert len(matches) == 2
    assert matches[0] == (8, 17, "tiêu viêm", "Tiêu Viêm")
    assert matches[1] == (22, 30, "dược lão", "Dược Lão")

def test_trie_matcher_longest_match_first():
    matcher = TrieMatcher()
    matcher.add_keyword("hàn lập", "Hàn Lập")
    matcher.add_keyword("hàn lập sư huynh", "Hàn Lập Sư Huynh")
    matcher.build()

    text = "hàn lập sư huynh đi vào."
    matches = matcher.find_matches(text.lower())
    
    # Phải ưu tiên chuỗi dài nhất "hàn lập sư huynh"
    assert len(matches) == 1
    assert matches[0][2] == "hàn lập sư huynh"

def test_trie_matcher_replace_all():
    matcher = TrieMatcher()
    matcher.add_keyword("tiêu viêm", "Tiêu Viêm")
    matcher.add_keyword("lão sư", "Thầy giáo")
    matcher.build()

    text = "tiêu viêm chào lão sư của hắn."
    replaced = matcher.replace_all(text.lower())
    assert replaced == "Tiêu Viêm chào Thầy giáo của hắn."

def test_trie_matcher_init_with_mapping():
    mapping = {
        "tiêu viêm": "Tiêu Viêm",
        "dược lão": "Dược Lão",
    }
    matcher = TrieMatcher(mapping)
    assert matcher.word_count == 2
    assert matcher.replace_all("tiêu viêm gặp dược lão") == "Tiêu Viêm gặp Dược Lão"

def test_trie_matcher_empty_and_edge_cases():
    matcher = TrieMatcher()
    matcher.add_keyword("")
    matcher.add_keyword("   ")
    assert matcher.word_count == 0
    assert matcher.find_matches("abc") == []
    assert matcher.replace_all("abc") == "abc"
    assert matcher.replace_all("") == ""
