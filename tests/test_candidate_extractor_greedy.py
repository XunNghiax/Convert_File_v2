import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.boundary_trimmer import BoundaryTrimmer
from src.scanner.candidate_extractor import CandidateExtractor

@pytest.fixture
def extractor():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    return CandidateExtractor(loader, trimmer, skip_known=False)

def test_extract_three_word_names_after_anchor(extractor):
    line = "bảo mẫu tôn như sương bưng hoa quả đi vào phòng khách."
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    assert "Tôn Như Sương" in names

def test_extract_lowercase_name_with_action(extractor):
    line = "Nhìn phụ thân như thế cưng chìu mẫu thân, từ vân tuyết trong lòng có một chút ghen tị."
    cands = extractor.extract_candidates(line)
    names = [c.name.lower() for c in cands]
    assert "từ vân tuyết" in names

def test_extract_foreign_name_with_middle_dot(extractor):
    line = "Mà ngồi tại Ngả Lâm Na bên người Đại Na · Hải Ngũ Đức ánh mắt quyến rũ nhìn chính mình."
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    assert any("Đại Na" in n and "Hải Ngũ Đức" in n for n in names)

def test_extract_latin_name_after_anchor_or_speaker(extractor):
    line = 'Cô giáo Joanna cười nói: "Chào các em!"'
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    assert "Joanna" in names
