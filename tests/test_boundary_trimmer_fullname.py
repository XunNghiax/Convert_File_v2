from src.scanner.boundary_trimmer import BoundaryTrimmer

def test_protects_tu_surname():
    trimmer = BoundaryTrimmer(trailing_stopwords={"hai", "người", "thân"})
    # "Từ Tân Đồng" không được bị cắt chữ "Từ"
    trimmed, rem = trimmer.trim("Từ Tân Đồng")
    assert trimmed == "Từ Tân Đồng"
    
    # "Từ Linh San" không được bị cắt chữ "Từ"
    trimmed, rem = trimmer.trim("Từ Linh San")
    assert trimmed == "Từ Linh San"

    # "từ vân tuyết" không được bị cắt chữ "từ"
    trimmed, rem = trimmer.trim("từ vân tuyết")
    assert trimmed.lower() == "từ vân tuyết"

def test_protects_third_word_in_three_word_names():
    trimmer = BoundaryTrimmer(trailing_stopwords={"y", "di", "mai", "thân", "người"})
    # Chữ "Sương", "Y", "Di", "Văn" ở cuối không được bị cắt
    assert trimmer.trim("Tôn Như Sương")[0] == "Tôn Như Sương"
    assert trimmer.trim("Đường Thiền Y")[0] == "Đường Thiền Y"
    assert trimmer.trim("Trần Mộng Di")[0] == "Trần Mộng Di"
    assert trimmer.trim("Diệp Mạn Văn")[0] == "Diệp Mạn Văn"
