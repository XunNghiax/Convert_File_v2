import json
from pathlib import Path
from src.scanner.scanner_engine import ScannerEngine
from src.scanner.resource_loader import ResourceLoader
from src.scanner.output_packager import OutputPackager

def test_realtime_scanner_and_packaging(tmp_path: Path):
    # Tạo file text mẫu
    sample_text = tmp_path / "sample.txt"
    sample_text.write_text(
        "Long Kiếm Phi, 24 tuổi, thiếu niên tuấn tú bước ra ngoài.\n"
        "Bá phụ Trương Tử Kiến nhìn hắn mỉm cười gật đầu.\n"
        "Long Kiếm Phi nói: Đa tạ bá phụ đã chỉ bảo.\n"
        "Bá phụ Trương Tử Kiến khẽ đáp lời.\n"
        "Vương Bá Đao đứng từ xa theo dõi nhất cử nhất động.\n",
        encoding="utf-8"
    )

    loader = ResourceLoader()
    loader.load_all()
    engine = ScannerEngine(loader, skip_known=False)

    out_dir = tmp_path / "output_test"
    all_path = out_dir / "scanner_all.json"

    # 1. Quét với realtime_all_path
    blocks = engine.scan_file(
        sample_text,
        deduplicate=True,
        show_progress=False,
        skip_known=False,
        realtime_all_path=all_path
    )

    # 2. Kiểm tra scanner_all.json tồn tại và có ID 1, 2, 3...
    assert all_path.exists()
    all_data = json.loads(all_path.read_text(encoding="utf-8"))
    assert len(all_data) == len(blocks)
    assert len(all_data) >= 2

    # Kiểm tra ID tuần tự ch_0001, ch_0002...
    for idx, item in enumerate(all_data, start=1):
        assert item["id"] == f"ch_{idx:04d}"
        assert item["so_lan_xuat_hien"] >= 1

    # Long Kiếm Phi và Trương Tử Kiến xuất hiện 2 lần
    lkp_all = next(item for item in all_data if "Long Kiếm Phi" in item["target"])
    assert lkp_all["so_lan_xuat_hien"] == 2

    ttk_all = next(item for item in all_data if "Trương Tử Kiến" in item["target"])
    assert ttk_all["so_lan_xuat_hien"] == 2

    # 3. Lọc theo min-count = 2 để tạo scanner_master và xuất chunk markdown
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("# Mẫu trích xuất nhân vật", encoding="utf-8")

    filtered = [b for b in blocks if b.so_lan_xuat_hien >= 2]
    assert len(filtered) == 2  # Chỉ có Long Kiếm Phi và Trương Tử Kiến

    for idx, b in enumerate(filtered, start=1):
        b.id = f"ch_{idx:04d}"

    packager = OutputPackager(prompt_path)
    packager.package(filtered, out_dir, chunk_size=1)  # chunk 1 để sinh 2 file md

    master_path = out_dir / "scanner_master.json"
    assert master_path.exists()
    master_data = json.loads(master_path.read_text(encoding="utf-8"))
    assert len(master_data) == 2
    assert master_data[0]["id"] == "ch_0001"
    assert master_data[1]["id"] == "ch_0002"

    # Kiểm tra các file markdown con
    md_files = sorted(list(out_dir.glob("output_test_*.md")))
    assert len(md_files) == 2
    assert "# Mẫu trích xuất nhân vật" in md_files[0].read_text(encoding="utf-8")
