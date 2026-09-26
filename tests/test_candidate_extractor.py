from character_scanner.resource_loader import ResourceLoader
from character_scanner.boundary_trimmer import BoundaryTrimmer
from character_scanner.candidate_extractor import CandidateExtractor

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
