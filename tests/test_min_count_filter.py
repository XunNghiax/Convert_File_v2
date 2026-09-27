from src.scanner.scanner_engine import CharacterBlock
from src.scanner.output_packager import OutputPackager
import json

def test_min_count_filtering(tmp_path):
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("prompt content", encoding="utf-8")
    output_dir = tmp_path / "scanner"

    # Tạo 5 nhân vật với số lần xuất hiện khác nhau
    blocks = [
        CharacterBlock(id="ch_0001", source="A", target="A", context="ctx A", yeu_to_nhan_biet="c1", so_lan_xuat_hien=1),
        CharacterBlock(id="ch_0002", source="B", target="B", context="ctx B", yeu_to_nhan_biet="c2", so_lan_xuat_hien=3),
        CharacterBlock(id="ch_0003", source="C", target="C", context="ctx C", yeu_to_nhan_biet="c3", so_lan_xuat_hien=5),
        CharacterBlock(id="ch_0004", source="D", target="D", context="ctx D", yeu_to_nhan_biet="c4", so_lan_xuat_hien=2),
        CharacterBlock(id="ch_0005", source="E", target="E", context="ctx E", yeu_to_nhan_biet="c5", so_lan_xuat_hien=1),
    ]

    # Lọc với min_count = 3
    filtered = [b for b in blocks if b.so_lan_xuat_hien >= 3]
    for idx, b in enumerate(filtered, start=1):
        b.id = f"ch_{idx:04d}"

    assert len(filtered) == 2
    assert filtered[0].target == "B"
    assert filtered[0].id == "ch_0001"
    assert filtered[1].target == "C"
    assert filtered[1].id == "ch_0002"

    packager = OutputPackager(prompt_file)
    packager.package(filtered, output_dir, chunk_size=10)

    master = json.loads((output_dir / "scanner_master.json").read_text(encoding="utf-8"))
    assert len(master) == 2
    assert master[0]["id"] == "ch_0001"
    assert master[0]["target"] == "B"
    assert master[1]["id"] == "ch_0002"
    assert master[1]["target"] == "C"
