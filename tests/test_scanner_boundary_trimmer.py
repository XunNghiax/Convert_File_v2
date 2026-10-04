import pytest
from src.scanner.boundary_trimmer import BoundaryTrimmer

def test_trim_action_suffix_single_surname():
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames={"tần", "trần", "lâm"})
    
    # Họ đơn + 2 từ tên + 1 động từ hành động = 4 từ -> Cắt động từ
    trimmed, removed = trimmer.trim_action_suffix("tần khả cầm đi")
    assert trimmed == "tần khả cầm"
    assert removed == "đi"

    trimmed, removed = trimmer.trim_action_suffix("tần khả phi thở")
    assert trimmed == "tần khả phi"
    assert removed == "thở"

    # Họ đơn + 2 từ tên (không có động từ thừa) -> Không cắt
    trimmed, removed = trimmer.trim_action_suffix("tần khả cầm")
    assert trimmed == "tần khả cầm"
    assert removed == ""

    # Họ đơn + từ cuối nằm trong PROTECTED_NAME_WORDS (vd: y, lan, ngọc) -> Không cắt
    trimmed, removed = trimmer.trim_action_suffix("tần khả lan")
    assert trimmed == "tần khả lan"
    assert removed == ""

def test_trim_action_suffix_compound_surname():
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames={"âu dương", "thượng quan"})
    
    # Họ kép + 2 từ tên + 1 động từ = 5 từ -> Cắt động từ
    trimmed, removed = trimmer.trim_action_suffix("âu dương như tuyết đi")
    assert trimmed == "âu dương như tuyết"
    assert removed == "đi"

    # Họ kép + 2 từ tên = 4 từ -> Không cắt
    trimmed, removed = trimmer.trim_action_suffix("âu dương như tuyết")
    assert trimmed == "âu dương như tuyết"
    assert removed == ""

def test_trim_vn_compound_suffix():
    trimmer = BoundaryTrimmer(trailing_stopwords=set(), surnames={"vũ", "trần"})
    vn_2word = {"vương phi", "chủ tịch", "bác sĩ"}

    # 4 từ, kết thúc bằng "vương phi" -> Cắt còn "vũ mỹ"
    trimmed, removed = trimmer.trim_vn_compound_suffix("vũ mỹ vương phi", vn_2word)
    assert trimmed == "vũ mỹ"
    assert removed == "vương phi"

    # Tên chỉ có 2 từ ("vũ mỹ") -> Không cắt dù có trong từ điển hay không
    trimmed, removed = trimmer.trim_vn_compound_suffix("vũ mỹ", vn_2word)
    assert trimmed == "vũ mỹ"
    assert removed == ""

def test_clean_candidate():
    trimmer = BoundaryTrimmer(trailing_stopwords={"này", "của"}, surnames={"tần", "vũ"})
    vn_2word = {"vương phi"}
    
    assert trimmer.clean_candidate("tần khả cầm đi", vn_2word) == "tần khả cầm"
    assert trimmer.clean_candidate("vũ mỹ vương phi", vn_2word) == "vũ mỹ"
