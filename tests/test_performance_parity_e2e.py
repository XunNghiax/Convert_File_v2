from pathlib import Path
import pytest
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine
from src.replacer.replace_engine import ReplaceEngine

def test_full_scanner_and_replacer_parity(tmp_path: Path):
    sample = Path("samples/exam.txt")
    if not sample.exists():
        pytest.skip("Không có file samples/exam.txt để kiểm thử parity")

    # 1. Parity Kiểm tra Scanner
    loader = ResourceLoader()
    loader.load_all()
    engine = ScannerEngine(loader=loader, skip_known=True)

    res_seq = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    res_par = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=4)

    assert len(res_seq) == len(res_par)
    for b_s, b_p in zip(res_seq, res_par):
        assert b_s.target == b_p.target
        assert b_s.so_lan_xuat_hien == b_p.so_lan_xuat_hien
        assert b_s.cac_dong_xuat_hien == b_p.cac_dong_xuat_hien

    # 2. Parity Kiểm tra Replacer
    out_seq = tmp_path / "out_seq.txt"
    out_par = tmp_path / "out_par.txt"

    replacer = ReplaceEngine()
    stats_seq = replacer.replace_file(sample, out_seq, show_progress=False, workers=1)
    stats_par = replacer.replace_file(sample, out_par, show_progress=False, workers=4)

    assert stats_seq.total_replacements == stats_par.total_replacements
    assert out_seq.read_text(encoding="utf-8") == out_par.read_text(encoding="utf-8")
