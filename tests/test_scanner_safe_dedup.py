import pytest
from src.scanner.scanner_engine import ScannerEngine, CharacterBlock

def test_different_given_names_are_never_merged():
    engine = ScannerEngine()
    b1 = CharacterBlock(
        id="ch_0001",
        source="tần khả cầm",
        target="Tần Khả Cầm",
        context="Tần Khả Cầm bước vào phòng.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=5,
        cac_dong_xuat_hien=[1, 2]
    )
    b2 = CharacterBlock(
        id="ch_0002",
        source="tần khả phi",
        target="Tần Khả Phi",
        context="Tần Khả Phi mỉm cười.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=4,
        cac_dong_xuat_hien=[3, 4]
    )

    result = engine.cluster_aliases([b1, b2])
    targets = [b.target for b in result]

    # Cả hai nhân vật phải được giữ lại riêng biệt, KHÔNG bị gộp
    assert len(result) == 2
    assert "Tần Khả Cầm" in targets
    assert "Tần Khả Phi" in targets

def test_merge_lowercase_into_titlecase():
    engine = ScannerEngine()
    b1 = CharacterBlock(
        id="ch_0001",
        source="Tần Khả Cầm",
        target="Tần Khả Cầm",
        context="Tần Khả Cầm bước vào phòng.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=5,
        cac_dong_xuat_hien=[1, 5]
    )
    b2 = CharacterBlock(
        id="ch_0002",
        source="tần khả cầm",
        target="tần khả cầm",
        context="tần khả cầm nói nhỏ.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=2,
        cac_dong_xuat_hien=[10]
    )

    result = engine.cluster_aliases([b1, b2])
    assert len(result) == 1
    assert result[0].target == "Tần Khả Cầm"
    assert result[0].so_lan_xuat_hien == 7
    assert 10 in result[0].cac_dong_xuat_hien

def test_merge_lowercase_first_into_titlecase():
    engine = ScannerEngine()
    b1 = CharacterBlock(
        id="ch_0001",
        source="tần khả cầm",
        target="tần khả cầm",
        context="tần khả cầm nói nhỏ.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=2,
        cac_dong_xuat_hien=[10]
    )
    b2 = CharacterBlock(
        id="ch_0002",
        source="Tần Khả Cầm",
        target="Tần Khả Cầm",
        context="Tần Khả Cầm bước vào phòng.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=5,
        cac_dong_xuat_hien=[1, 5]
    )

    result = engine.cluster_aliases([b1, b2])
    assert len(result) == 1
    assert result[0].target == "Tần Khả Cầm"
    assert result[0].so_lan_xuat_hien == 7
    assert 10 in result[0].cac_dong_xuat_hien

def test_prefix_stripping_single_word_noise():
    engine = ScannerEngine()
    b_main = CharacterBlock(
        id="ch_0001",
        source="Mã Lan",
        target="Mã Lan",
        context="Mã Lan xuất hiện.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=10,
        cac_dong_xuat_hien=[1, 2, 3]
    )
    b_noise = CharacterBlock(
        id="ch_0002",
        source="hoa Mã Lan",
        target="Hoa Mã Lan",
        context="hoa Mã Lan đang đi.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=1,
        cac_dong_xuat_hien=[15]
    )

    result = engine.cluster_aliases([b_main, b_noise])
    targets = [b.target for b in result]
    assert len(result) == 1
    assert result[0].target == "Mã Lan"
    assert result[0].so_lan_xuat_hien == 11
    assert 15 in result[0].cac_dong_xuat_hien

def test_superstring_conflict_preserves_distinct_characters():
    engine = ScannerEngine()
    b_short = CharacterBlock(
        id="ch_0001",
        source="Tần Khả",
        target="Tần Khả",
        context="Tần Khả nhìn sang.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=3,
        cac_dong_xuat_hien=[1]
    )
    b_cam = CharacterBlock(
        id="ch_0002",
        source="Tần Khả Cầm",
        target="Tần Khả Cầm",
        context="Tần Khả Cầm mỉm cười.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=10,
        cac_dong_xuat_hien=[2]
    )
    b_phi = CharacterBlock(
        id="ch_0003",
        source="Tần Khả Phi",
        target="Tần Khả Phi",
        context="Tần Khả Phi gật đầu.",
        yeu_to_nhan_biet="test",
        so_lan_xuat_hien=8,
        cac_dong_xuat_hien=[3]
    )

    result = engine.cluster_aliases([b_short, b_cam, b_phi])
    targets = [b.target for b in result]
    # Do Tần Khả Cầm và Tần Khả Phi xung đột về tên chính, Tần Khả không được gộp vào ai
    assert len(result) == 3
    assert "Tần Khả" in targets
    assert "Tần Khả Cầm" in targets
    assert "Tần Khả Phi" in targets

def test_realtime_output_filters_negative_candidates(tmp_path):
    import json
    from src.scanner.resource_loader import ResourceLoader

    loader = ResourceLoader()
    loader.load_all()
    engine = ScannerEngine(loader=loader, skip_known=False)

    sample_file = tmp_path / "sample.txt"
    sample_file.write_text(
        "Tần Khả Cầm bước vào phòng mỉm cười.\n"
        "Tần Khả Phi gật đầu chào hỏi.\n",
        encoding="utf-8"
    )

    all_path = tmp_path / "scanner_all.json"
    results = engine.scan_file(sample_file, deduplicate=True, show_progress=False, realtime_all_path=all_path)

    assert all_path.exists()
    saved = json.loads(all_path.read_text(encoding="utf-8"))
    targets = [item["target"] for item in saved]
    assert "Tần Khả Cầm" in targets
    assert "Tần Khả Phi" in targets
    # Đảm bảo không có candidate nào là negative
    for item in saved:
        assert not engine._is_negative(item["target"], skip_known=False)
