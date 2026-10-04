from pathlib import Path
import json
import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine


def test_scanner_noise_filtering_and_dedup_e2e(tmp_path: Path):
    # Chuẩn bị dữ liệu mẫu
    resources_dir = tmp_path / "resources"
    dict_dir = resources_dir / "dictionaries"
    filters_dir = resources_dir / "filters"
    dict_dir.mkdir(parents=True)
    filters_dir.mkdir(parents=True)

    (filters_dir / "surnames.txt").write_text("tần\nâu dương\ntrần\n", encoding="utf-8")
    (dict_dir / "character_dict.json").write_text(json.dumps({"Tiêu Viêm": "Tiêu Viêm"}), encoding="utf-8")
    (dict_dir / "chinese_names_dict.json").write_text(json.dumps({"Hàn Lập": "Hàn Lập"}), encoding="utf-8")
    (dict_dir / "vietnamese_words.txt").write_text("xoáy thuận\ntừ chối\ncổ kính\nvương phi\n", encoding="utf-8")

    sample_text = (
        "Trong căn phòng có một hiện tượng xoáy thuận kỳ lạ. Cổ kính phản chiếu ánh trăng.\n"
        "tần khả cầm đi tới chiếc bàn, khẽ mỉm cười.\n"
        "tần khả phi thở dài một hơi rồi ngồi xuống bên cạnh.\n"
        "âu dương như tuyết đi vào với vẻ mặt lạnh lùng.\n"
        "trần ngọc ánh tuyết cười nói vui vẻ cùng mọi người.\n"
        "Tiêu Viêm và Hàn Lập cũng đứng ở đằng xa quan sát.\n"
    )

    test_file = tmp_path / "test_novel.txt"
    test_file.write_text(sample_text, encoding="utf-8")

    loader = ResourceLoader(base_dir=tmp_path)
    loader.load_all()

    engine = ScannerEngine(loader=loader, skip_known=True)
    results = engine.scan_file(test_file, deduplicate=True, show_progress=False)
    targets = [b.target for b in results]

    # 1. Từ rác 2 từ trong từ điển tiếng Việt PHẢI BỊ LOẠI BỎ
    assert "Xoáy Thuận" not in targets
    assert "Cổ Kính" not in targets
    assert "Từ Chối" not in targets

    # 2. Nhân vật đã biết trong character_dict và chinese_names_dict PHẢI BỊ BỎ QUA khi skip_known=True
    assert "Tiêu Viêm" not in targets
    assert "Hàn Lập" not in targets

    # 3. Hai nhân vật cùng họ dính động từ đuôi phải được bóc tách và giữ riêng biệt
    assert "Tần Khả Cầm" in targets
    assert "Tần Khả Phi" in targets
    assert not any("Đi" in t for t in targets)
    assert not any("Thở" in t for t in targets)

    # 4. Họ kép 2 chữ (Âu Dương) và Tên 4 chữ (Trần Ngọc Ánh Tuyết) trích xuất chính xác
    assert "Âu Dương Như Tuyết" in targets
    assert "Trần Ngọc Ánh Tuyết" in targets
