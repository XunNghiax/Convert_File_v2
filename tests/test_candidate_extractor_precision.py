from character_scanner.resource_loader import ResourceLoader
from character_scanner.boundary_trimmer import BoundaryTrimmer
from character_scanner.candidate_extractor import CandidateExtractor

def test_extract_profile_with_age_translated_name():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    extractor = CandidateExtractor(loader, trimmer)

    line = "Thẩm bóng hình xinh đẹp, 39 tuổi, chủ quản y tá, Long Kiếm Phi dì, thành thục mỹ phụ"
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    # Phải bắt được trọn vẹn cả họ lẫn tên, hoặc đã quy chuẩn qua character_dict
    assert "Thẩm Thiến Ảnh" in names or "Thẩm Bóng Hình Xinh Đẹp" in names
    # Tuyệt đối không được cắt cụt mất họ Thẩm thành 'Bóng Hình Xinh Đẹp'
    assert "Bóng Hình Xinh Đẹp" not in names

def test_reject_false_positive_clauses():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    extractor = CandidateExtractor(loader, trimmer)

    line1 = "nam nhân đàm luận bóng đá thời điểm, nữ nhân luôn bị xem nhẹ."
    cands1 = extractor.extract_candidates(line1)
    names1 = [c.name for c in cands1]
    assert "Bóng Đá Thời Điểm" not in names1
    assert "Thời Thượng Thời Điểm" not in names1

    line2 = "như khói chuyện cũ, nữ nhân ở thở dài dung nhan Dịch lão, nam nhân đâu?"
    cands2 = extractor.extract_candidates(line2)
    names2 = [c.name for c in cands2]
    assert "Như Khói Chuyện Cũ" not in names2
    assert "Dung Nhan Dịch Lão" not in names2

def test_trim_leading_action_in_relations():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    extractor = CandidateExtractor(loader, trimmer)

    line = "Tần Xảo Xảo cười nói: 'Ta thật cao hứng Nguyên Xuân tỷ tỷ như thế duy trì.'"
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    assert "Cao Hứng Nguyên Xuân" not in names
    assert "Nguyên Xuân" in names or "Tô Nguyên Xuân" in names

def test_reject_object_relation_verb():
    loader = ResourceLoader()
    loader.load_all()
    trimmer = BoundaryTrimmer(loader.trailing_stopwords)
    extractor = CandidateExtractor(loader, trimmer)

    line = "Tiểu Lệ hồng tò mò nhìn mẹ cùng Long Kiếm Phi đấu võ mồm."
    cands = extractor.extract_candidates(line)
    names = [c.name for c in cands]
    assert "Hồng Tò Mò" not in names
    assert "Tò Mò Nhìn" not in names
