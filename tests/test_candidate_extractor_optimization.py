import pytest
import re
from src.scanner.resource_loader import ResourceLoader
from src.scanner.boundary_trimmer import BoundaryTrimmer
from src.scanner.candidate_extractor import CandidateExtractor
from src.utils.trie_matcher import TrieMatcher


@pytest.fixture
def extractor():
    loader = ResourceLoader()
    loader.single_surnames = {"tần", "trần", "lâm", "tiêu"}
    loader.compound_surnames = {"âu dương"}
    loader.known_characters = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    loader.deconvert_dict = {"dược lão": "Dược Lão"}
    loader.vn_2word_set = {"xoáy thuận", "từ chối"}
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames=loader.single_surnames | loader.compound_surnames)
    return CandidateExtractor(loader=loader, trimmer=trimmer, skip_known=False)


def test_extractor_attributes_initialized(extractor):
    assert isinstance(extractor.known_trie, TrieMatcher)
    assert isinstance(extractor.deconvert_trie, TrieMatcher)
    assert isinstance(extractor.lowercase_action_regex, re.Pattern)
    assert hasattr(extractor, "fast_cue_words")


def test_fast_line_screening_skips_empty_or_plain_lines(extractor):
    # Dòng chỉ có chữ thường thông thường không mang họ, không mỏ neo -> Bỏ qua
    plain_line = "trời hôm nay nhiều mây và có gió nhẹ thổi qua thung lũng."
    matches = extractor.extract_candidates(plain_line)
    assert len(matches) == 0


def test_trie_matcher_replaces_slow_loop_for_known_chars(extractor):
    line = "Lúc này tiêu viêm nhìn thấy dược lão đang mỉm cười."
    matches = extractor.extract_candidates(line, skip_known=False)
    targets = [m.name for m in matches]
    assert "Tiêu Viêm" in targets
    assert "Dược Lão" in targets


def test_lowercase_action_regex_matches_all_actions(extractor):
    line = "tần khả cầm đi tới chiếc bàn, khẽ mỉm cười."
    matches = extractor.extract_candidates(line, skip_known=True)
    names = [m.name for m in matches]
    assert "Tần Khả Cầm" in names
    assert not any("Đi" in n for n in names)
