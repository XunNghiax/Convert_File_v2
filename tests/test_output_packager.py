from pathlib import Path
from character_scanner.scanner_engine import CharacterBlock
from character_scanner.output_packager import OutputPackager

def test_package_outputs(tmp_path):
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("--- PROMPT HUONG DAN ---", encoding="utf-8")
    out_dir = tmp_path / "scanner"

    blocks = [
        CharacterBlock(
            id=f"ch_{i:04d}",
            source=f"Nhân vật {i}",
            target=f"Nhân Vật {i}",
            context=f"Bối cảnh dòng {i}",
            dong_xuat_hien=i,
            confidence=0.85,
            yeu_to_nhan_biet="Thử nghiệm"
        )
        for i in range(1, 45)
    ]

    packager = OutputPackager(prompt_path=prompt_file)
    packager.package(blocks, output_dir=out_dir, chunk_size=30)

    assert (out_dir / "scanner_master.json").exists()
    assert (out_dir / "scanner_1.md").exists()
    assert (out_dir / "scanner_2.md").exists()
