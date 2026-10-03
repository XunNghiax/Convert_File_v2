from src.scanner.scanner_engine import ScannerEngine, CharacterBlock

def test_consolidates_shorter_name_into_longer_full_name():
    engine = ScannerEngine(loader=None)
    b1 = CharacterBlock(id="ch_1", source="Đường Thiền", target="Đường Thiền", context="ctx1", yeu_to_nhan_biet="rel", so_lan_xuat_hien=10)
    b2 = CharacterBlock(id="ch_2", source="Đường Thiền Y", target="Đường Thiền Y", context="ctx2", yeu_to_nhan_biet="rel", so_lan_xuat_hien=50)
    
    result = engine.cluster_aliases([b1, b2])
    targets = [b.target for b in result]
    # Phải giữ lại "Đường Thiền Y", gộp "Đường Thiền" vào biến thể
    assert "Đường Thiền Y" in targets
    main_block = next(b for b in result if b.target == "Đường Thiền Y")
    assert "Đường Thiền" in main_block.bien_the
    assert main_block.so_lan_xuat_hien == 60

def test_action_verb_cleanup_merges_into_base_name():
    engine = ScannerEngine(loader=None)
    b1 = CharacterBlock(id="ch_1", source="Từ Thanh", target="Từ Thanh", context="ctx1", yeu_to_nhan_biet="rel", so_lan_xuat_hien=20, cac_dong_xuat_hien=[10])
    b2 = CharacterBlock(id="ch_2", source="Từ Thanh khiêu", target="Từ Thanh khiêu", context="ctx2", yeu_to_nhan_biet="act", so_lan_xuat_hien=3, cac_dong_xuat_hien=[15])
    b3 = CharacterBlock(id="ch_3", source="Từ Thanh dùng", target="Từ Thanh dùng", context="ctx3", yeu_to_nhan_biet="act", so_lan_xuat_hien=2, cac_dong_xuat_hien=[20])

    result = engine.cluster_aliases([b1, b2, b3])
    targets = [b.target for b in result]
    assert targets == ["Từ Thanh"]
    main_block = result[0]
    assert main_block.so_lan_xuat_hien == 25
    assert main_block.cac_dong_xuat_hien == [10, 15, 20]
    # Động từ dính đuôi không làm ô nhiễm bien_the
    assert "Từ Thanh khiêu" not in main_block.bien_the
    assert "Từ Thanh dùng" not in main_block.bien_the

def test_superstring_consolidation_with_alias():
    engine = ScannerEngine(loader=None)
    b1 = CharacterBlock(id="ch_1", source="Đường Thiền", target="Đường Thiền", context="ctx1", yeu_to_nhan_biet="rel", so_lan_xuat_hien=10, cac_dong_xuat_hien=[10])
    b2 = CharacterBlock(id="ch_2", source="Đường Thiền Y", target="Đường Thiền Y", context="ctx2", yeu_to_nhan_biet="rel", so_lan_xuat_hien=50, cac_dong_xuat_hien=[50])
    b3 = CharacterBlock(id="ch_3", source="Tiểu Thiền", target="Tiểu Thiền", context="ctx3", yeu_to_nhan_biet="rel", so_lan_xuat_hien=5, cac_dong_xuat_hien=[25])

    result = engine.cluster_aliases([b1, b2, b3])
    targets = [b.target for b in result]
    assert targets == ["Đường Thiền Y"]
    main_block = result[0]
    assert main_block.so_lan_xuat_hien == 65
    assert "Đường Thiền" in main_block.bien_the
    assert "Tiểu Thiền" in main_block.bien_the

def test_compound_surname_superstring():
    engine = ScannerEngine(loader=None)
    b1 = CharacterBlock(id="ch_1", source="Hoàng Phủ Thiền", target="Hoàng Phủ Thiền", context="ctx1", yeu_to_nhan_biet="rel", so_lan_xuat_hien=5, cac_dong_xuat_hien=[5])
    b2 = CharacterBlock(id="ch_2", source="Hoàng Phủ Thiền Y", target="Hoàng Phủ Thiền Y", context="ctx2", yeu_to_nhan_biet="rel", so_lan_xuat_hien=20, cac_dong_xuat_hien=[20])

    result = engine.cluster_aliases([b1, b2])
    assert len(result) == 1
    assert result[0].target == "Hoàng Phủ Thiền Y"
    assert "Hoàng Phủ Thiền" in result[0].bien_the
    assert result[0].so_lan_xuat_hien == 25
    assert result[0].cac_dong_xuat_hien == [5, 20]

def test_deduplicate_blocks_with_superstring():
    engine = ScannerEngine(loader=None)
    b1_a = CharacterBlock(id="ch_1", source="Đường Thiền", target="Đường Thiền", context="ctx1", yeu_to_nhan_biet="rel", so_lan_xuat_hien=10, dong_xuat_hien=10)
    b1_b = CharacterBlock(id="ch_2", source="Đường Thiền", target="Đường Thiền", context="ctx2", yeu_to_nhan_biet="rel", so_lan_xuat_hien=5, dong_xuat_hien=12)
    b2 = CharacterBlock(id="ch_3", source="Đường Thiền Y", target="Đường Thiền Y", context="ctx3", yeu_to_nhan_biet="rel", so_lan_xuat_hien=50, dong_xuat_hien=50)

    result = engine.deduplicate_blocks([b1_a, b1_b, b2])
    assert len(result) == 1
    assert result[0].target == "Đường Thiền Y"
    assert result[0].so_lan_xuat_hien == 65
    assert "Đường Thiền" in result[0].bien_the

