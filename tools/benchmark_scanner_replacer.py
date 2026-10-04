import sys
import time
from pathlib import Path

# Thêm đường dẫn thư mục gốc dự án để chạy độc lập
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine
from src.replacer.replace_engine import ReplaceEngine
from src.utils.file_utils import count_file_lines

def run_benchmark():
    sample = Path("samples/exam.txt")
    if not sample.exists():
        print("[!] Không tìm thấy file samples/exam.txt!")
        return

    lines = count_file_lines(sample)

    print("==================================================")
    print(" BẮT ĐẦU BENCHMARK HIỆU NĂNG SCANNER VÀ REPLACER")
    print("==================================================")
    
    # 1. Benchmark Scanner
    loader = ResourceLoader()
    loader.load_all()
    engine = ScannerEngine(loader=loader, skip_known=True)

    print("\n[*] Đang đo Scanner (1 worker - Tối ưu thuật toán)...")
    t0 = time.time()
    res_1 = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    t_seq = max(0.001, time.time() - t0)
    print(f" -> Scanner (1 worker): {lines/t_seq:,.0f} dòng/s ({t_seq:.2f}s) - {len(res_1)} nhân vật")

    print("[*] Đang đo Scanner (4 workers - Đa tiến trình)...")
    t0 = time.time()
    res_4 = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=4)
    t_par = max(0.001, time.time() - t0)
    print(f" -> Scanner (4 workers): {lines/t_par:,.0f} dòng/s ({t_par:.2f}s) - {len(res_4)} nhân vật")

    # 2. Benchmark Replacer
    replacer = ReplaceEngine()
    tmp_out = Path("samples/benchmark_out.txt")

    print("\n[*] Đang đo Replacer (1 worker - Tối ưu Buffer IO)...")
    t0 = time.time()
    s_1 = replacer.replace_file(sample, tmp_out, show_progress=False, workers=1)
    t_rep_seq = max(0.001, time.time() - t0)
    print(f" -> Replacer (1 worker): {lines/t_rep_seq:,.0f} dòng/s ({t_rep_seq:.2f}s) - {s_1.total_replacements:,} lượt thay")

    print("[*] Đang đo Replacer (4 workers - Đa tiến trình)...")
    t0 = time.time()
    s_4 = replacer.replace_file(sample, tmp_out, show_progress=False, workers=4)
    t_rep_par = max(0.001, time.time() - t0)
    print(f" -> Replacer (4 workers): {lines/t_rep_par:,.0f} dòng/s ({t_rep_par:.2f}s) - {s_4.total_replacements:,} lượt thay")

    if tmp_out.exists():
        tmp_out.unlink()

if __name__ == "__main__":
    run_benchmark()
