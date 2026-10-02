from src.scanner.resource_loader import ResourceLoader
from src.scanner.boundary_trimmer import BoundaryTrimmer
from src.scanner.candidate_extractor import CandidateExtractor

def test_extract_profile_candidate():
    loader = ResourceLoader()
    loader.single_surnames = {"trương", "lâm", "mã"}
    trimmer = BoundaryTrimmer({"hai", "người", "thân"})
    extractor = CandidateExtractor(loader, trimmer)

    line = "Trương Tử Kiến, nam, 30 tuổi."
    candidates = extractor.extract_candidates(line)
    assert any(c.name == "Trương Tử Kiến" and c.confidence >= 0.5 for c in candidates)

def test_extract_lowercase_intro_candidate():
    loader = ResourceLoader()
    loader.single_surnames = {"lâm"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = "Lâm bằng tường, 53 tuổi, Nam Phương tỉnh tỉnh trưởng"
    candidates = extractor.extract_candidates(line)
    assert any(c.name == "Lâm Bằng Tường" for c in candidates)

def test_filter_non_person():
    loader = ResourceLoader()
    loader.single_surnames = {"hoàng"}
    loader.non_person = {"hoàng hà"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = "Sông Viêm là Hoàng Hà một cái tiểu nhánh sông"
    candidates = extractor.extract_candidates(line)
    assert not any(c.name.lower() == "hoàng hà" for c in candidates)

def test_skip_known_characters():
    loader = ResourceLoader()
    loader.single_surnames = {"vệ", "lâm"}
    loader.known_characters = {"vệ đông": "Vệ Đông"}
    trimmer = BoundaryTrimmer(set())

    line = "Vệ Đông và Lâm Bằng Tường cùng nhau bước vào phòng."

    # Chế độ skip_known=True (mặc định): Không liệt kê Vệ Đông, nhưng vẫn bắt nhân vật mới Lâm Bằng Tường
    extractor_skip = CandidateExtractor(loader, trimmer, skip_known=True)
    cands_skip = extractor_skip.extract_candidates(line)
    names_skip = [c.name for c in cands_skip]
    assert "Vệ Đông" not in names_skip
    assert "Lâm Bằng Tường" in names_skip

    # Chế độ skip_known=False: Liệt kê cả Vệ Đông
    extractor_include = CandidateExtractor(loader, trimmer, skip_known=False)
    cands_include = extractor_include.extract_candidates(line)
    names_include = [c.name for c in cands_include]
    assert "Vệ Đông" in names_include
    assert "Lâm Bằng Tường" in names_include

def test_extract_lowercase_anchor_name():
    loader = ResourceLoader()
    loader.single_surnames = {"tôn", "kiều", "từ"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = "Người này mới đến bảo mẫu tên là tôn như sương, ba mươi chín tuổi."
    candidates = extractor.extract_candidates(line)
    assert any(c.name == "Tôn Như Sương" for c in candidates)

def test_extract_dialogue_speaker():
    loader = ResourceLoader()
    loader.single_surnames = {"tần", "từ"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = 'Tần Vận khẽ mỉm cười nói: "Từ Thanh, ngươi mạnh khỏe!"'
    candidates = extractor.extract_candidates(line)
    assert any(c.name == "Tần Vận" for c in candidates)

def test_prevent_anatomy_caching():
    loader = ResourceLoader()
    loader.single_surnames = {"dương"}
    loader.non_person = {"dương vật"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = "hắn đại dương vật hung hăng đỉnh vào."
    candidates = extractor.extract_candidates(line)
    assert not any("Dương Vật" in c.name for c in candidates)
    assert "dương vật" not in [s.lower() for s in extractor.session_cache]

def test_extract_deconvert_name():
    loader = ResourceLoader()
    loader.deconvert_dict = {"tô cũng có thể": "Tô Diệc Khả"}
    trimmer = BoundaryTrimmer(set())
    extractor = CandidateExtractor(loader, trimmer)

    line = "Nhìn đến gần chính mình Từ Thanh, tô cũng có thể tỉ mỉ trang điểm."
    candidates = extractor.extract_candidates(line)
    assert any(c.name == "Tô Diệc Khả" for c in candidates)

