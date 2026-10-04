import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.boundary_trimmer import BoundaryTrimmer
from src.scanner.candidate_extractor import CandidateExtractor

@pytest.fixture
def extractor():
    loader = ResourceLoader()
    loader.single_surnames = {"tần", "trần", "lâm", "đường", "hoa", "vũ"}
    loader.compound_surnames = {"âu dương"}
    loader.known_characters = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    loader.common_dict = {"không có": "không có"}
    loader.vn_2word_set = {"xoáy thuận", "từ chối", "cổ kính", "vương phi", "phương tâm"}
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames=loader.single_surnames | loader.compound_surnames)
    return CandidateExtractor(loader=loader, trimmer=trimmer, skip_known=True)

def test_is_negative_rejects_vn_2word_set(extractor):
    # Các từ ghép 2 từ tiếng Việt thông thường phải bị từ chối 100%
    assert extractor._is_negative("xoáy thuận") is True
    assert extractor._is_negative("từ chối") is True
    assert extractor._is_negative("cổ kính") is True
    assert extractor._is_negative("phương tâm") is True

def test_is_negative_rejects_grammar_connectors(extractor):
    # Cụm chứa từ chức năng ngữ pháp ở giữa tên phải bị loại
    assert extractor._is_negative("đường có mỹ nữ") is True
    assert extractor._is_negative("lâm lại chạy") is True
    assert extractor._is_negative("trần được cứu") is True

def test_is_negative_rejects_known_characters_when_skip_known(extractor):
    assert extractor._is_negative("Tiêu Viêm", skip_known=True) is True
    assert extractor._is_negative("tiêu viêm", skip_known=True) is True
    assert extractor._is_negative("Dược Lão", skip_known=True) is True

def test_is_negative_accepts_valid_names(extractor):
    # Tên nhân vật hợp lệ không nằm trong từ điển rác
    assert extractor._is_negative("tần khả cầm") is False
    assert extractor._is_negative("tần khả phi") is False
    assert extractor._is_negative("âu dương như tuyết") is False

def test_extract_lowercase_action_candidates_trims_verb(extractor):
    line = "tần khả cầm đi tới phòng khách, tần khả phi thở dài một tiếng."
    matches = extractor._extract_lowercase_action_candidates(line, skip_known=True)
    names = [m.name for m in matches]
    
    assert "Tần Khả Cầm" in names
    assert "Tần Khả Phi" in names
    assert not any("Đi" in n for n in names)
    assert not any("Thở" in n for n in names)
