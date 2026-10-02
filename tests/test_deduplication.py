from src.scanner.scanner_engine import CharacterBlock, ScannerEngine
from src.scanner.resource_loader import ResourceLoader

def test_deduplicate_blocks():
    b1 = CharacterBlock(
        id="ch_0001",
        source="Long Kiếm Phi",
        target="Long Kiếm Phi",
        context="Long Kiếm Phi đi dạo.",
        dong_xuat_hien=300,
        confidence=0.70,
        yeu_to_nhan_biet="Viết hoa"
    )
    b2 = CharacterBlock(
        id="ch_0002",
        source="Long Kiếm Phi",
        target="Long Kiếm Phi",
        context="Long Kiếm Phi, 24 tuổi, thiếu niên tuấn tú.",
        dong_xuat_hien=10,
        confidence=0.95,
        yeu_to_nhan_biet="Hồ sơ giới thiệu"
    )
    b3 = CharacterBlock(
        id="ch_0003",
        source="Trương Tử Kiến",
        target="Trương Tử Kiến",
        context="Trương Tử Kiến, nam, 30 tuổi.",
        dong_xuat_hien=9,
        confidence=0.95,
        yeu_to_nhan_biet="Hồ sơ giới thiệu"
    )

    loader = ResourceLoader()
    engine = ScannerEngine(loader)
    deduped = engine.deduplicate_blocks([b1, b2, b3])

    assert len(deduped) == 2
    # Check that Long Kiếm Phi merged correctly
    lkp = next(b for b in deduped if b.target == "Long Kiếm Phi")
    assert lkp.so_lan_xuat_hien == 2
    assert lkp.cac_dong_xuat_hien == [10, 300]
    # The representative context should be the higher confidence one
    assert "24 tuổi" in lkp.context
    assert lkp.dong_xuat_hien == 10

def test_alias_clustering():
    loader = ResourceLoader()
    engine = ScannerEngine(loader)
    blocks = [
        CharacterBlock(id="ch_1", source="Từ Thanh", target="Từ Thanh", context="Từ Thanh nói.", yeu_to_nhan_biet=""),
        CharacterBlock(id="ch_2", source="Tiểu Thanh", target="Tiểu Thanh", context="Tiểu Thanh cười.", yeu_to_nhan_biet=""),
    ]
    clustered = engine.cluster_aliases(blocks)
    assert len(clustered) == 1
    assert clustered[0].target == "Từ Thanh"
    assert "Tiểu Thanh" in clustered[0].bien_the
    assert clustered[0].so_lan_xuat_hien == 2
