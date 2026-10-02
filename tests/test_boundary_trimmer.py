from src.scanner.boundary_trimmer import BoundaryTrimmer

def test_trim_trailing_stopwords():
    stopwords = {"hai", "người", "thân", "con", "của"}
    trimmer = BoundaryTrimmer(stopwords)

    trimmed, suffix = trimmer.trim("Nguyễn mai hai")
    assert trimmed == "Nguyễn mai"
    assert suffix == "hai"

    trimmed, suffix = trimmer.trim("Ngọc Thiến thân")
    assert trimmed == "Ngọc Thiến"
    assert suffix == "thân"

def test_normalize_name():
    trimmer = BoundaryTrimmer(set())
    assert trimmer.normalize_name("lâm bằng tường") == "Lâm Bằng Tường"
    assert trimmer.normalize_name("Trương Tử Kiến") == "Trương Tử Kiến"

def test_preserve_valid_name_endings():
    # Giả sử stopword có chứa "tâm", "y" do vô tình nạp
    trimmer = BoundaryTrimmer({"hai", "người", "thân", "tâm", "y", "lan"})
    # "Văn Liên Tâm" không được bị cắt thành "Văn Liên"
    trimmed, suffix = trimmer.trim("Văn Liên Tâm")
    assert trimmed == "Văn Liên Tâm"
    assert suffix == ""

    # "Đường Thiền Y" không được bị cắt
    trimmed, suffix = trimmer.trim("Đường Thiền Y")
    assert trimmed == "Đường Thiền Y"
    assert suffix == ""

