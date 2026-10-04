from pathlib import Path
import pytest
from src.utils.chunk_splitter import split_file_line_ranges
from src.scanner.resource_loader import ResourceLoader
from src.scanner.scanner_engine import ScannerEngine

def test_split_file_line_ranges(tmp_path: Path):
    f = tmp_path / "test.txt"
    lines = [f"Dòng thứ {i}\n" for i in range(1, 101)]
    f.write_text("".join(lines), encoding="utf-8")
    
    ranges = split_file_line_ranges(f, num_chunks=4)
    assert len(ranges) == 4
    assert ranges[0][0] == 1
    assert ranges[-1][1] == 100
    # Đảm bảo các dải dòng liên tục, không bị chồng chéo hay rỗng
    for i in range(len(ranges) - 1):
        assert ranges[i][1] + 1 == ranges[i+1][0]

def test_split_file_line_ranges_edge_cases(tmp_path: Path):
    # Non-existent file
    assert split_file_line_ranges(tmp_path / "non_existent.txt", num_chunks=4) == [(1, 1)]

    # Single chunk
    f = tmp_path / "single.txt"
    f.write_text("Dòng 1\nDòng 2\nDòng 3\n", encoding="utf-8")
    assert split_file_line_ranges(f, num_chunks=1) == [(1, 3)]

    # num_chunks > total_lines
    ranges = split_file_line_ranges(f, num_chunks=10)
    assert ranges[0][0] == 1
    assert ranges[-1][1] == 3
    for i in range(len(ranges) - 1):
        assert ranges[i][1] + 1 == ranges[i+1][0]

def test_scanner_parallel_parity_with_sequential(tmp_path: Path):
    sample = tmp_path / "novel.txt"
    sample.write_text(
        "Tần Khả Cầm bước vào phòng khách.\n"
        "Âu Dương Như Tuyết đi ra ngoài ngắm tuyết rơi.\n"
        "Trương Tử Mạnh gật đầu tán thành lời nói của mọi người.\n"
        "Tần Khả Phi thở dài ngồi xuống ghế.\n"
        "Trần Ngọc Ánh Tuyết mỉm cười nhẹ nhàng.\n",
        encoding="utf-8"
    )

    loader = ResourceLoader(base_dir=tmp_path)
    # Khởi tạo tối thiểu
    loader.single_surnames = {"tần", "trương", "trần"}
    loader.compound_surnames = {"âu dương"}

    engine = ScannerEngine(loader=loader, skip_known=False)
    
    # Quét tuần tự (1 worker)
    seq_res = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    # Quét song song (2 workers)
    par_res = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=2)

    seq_targets = sorted([b.target for b in seq_res])
    par_targets = sorted([b.target for b in par_res])

    assert seq_targets == par_targets

def test_scanner_parallel_cross_chunk_dedup_and_stats(tmp_path: Path):
    # Test character appearing across different chunks
    sample = tmp_path / "cross_chunk_novel.txt"
    lines = [
        "Tần Khả Cầm bước vào phòng khách.\n",         # Line 1 (Chunk 1)
        "Một ngày bình thường trôi qua êm đềm.\n",      # Line 2 (Chunk 1)
        "Trương Tử Mạnh gật đầu tán thành ý kiến.\n",   # Line 3 (Chunk 2)
        "Tần Khả Cầm lại lên tiếng giải thích rõ.\n",   # Line 4 (Chunk 2)
        "Mọi người cùng nhau im lặng lắng nghe.\n",     # Line 5 (Chunk 3)
        "Tần Khả Cầm mỉm cười chào tạm biệt.\n",       # Line 6 (Chunk 3)
    ]
    sample.write_text("".join(lines), encoding="utf-8")

    loader = ResourceLoader(base_dir=tmp_path)
    loader.single_surnames = {"tần", "trương"}

    engine = ScannerEngine(loader=loader, skip_known=False)

    seq_res = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    par_res = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=3)

    seq_map = {b.target: b for b in seq_res}
    par_map = {b.target: b for b in par_res}

    assert set(seq_map.keys()) == set(par_map.keys())

    tkc_seq = seq_map["Tần Khả Cầm"]
    tkc_par = par_map["Tần Khả Cầm"]

    assert tkc_seq.so_lan_xuat_hien == tkc_par.so_lan_xuat_hien == 3
    assert tkc_seq.dong_xuat_hien == tkc_par.dong_xuat_hien == 1
    assert tkc_seq.cac_dong_xuat_hien == tkc_par.cac_dong_xuat_hien == [1, 4, 6]
    assert tkc_seq.target == tkc_par.target
    assert tkc_seq.source == tkc_par.source

def test_split_file_line_chunks_alias(tmp_path: Path):
    from src.utils.chunk_splitter import split_file_line_chunks
    f = tmp_path / "test_alias.txt"
    f.write_text("1\n2\n3\n4\n", encoding="utf-8")
    assert split_file_line_chunks(f, num_chunks=2) == [(1, 2), (3, 4)]

def test_scanner_parallel_session_cache_synchronization(tmp_path: Path):
    """
    Kiểm tra đồng bộ hóa session_cache giữa các chunk:
    - Chunk 1: Định nghĩa nhân vật với hội thoại (conf 0.96 -> session_cache).
    - Chunk 2: Nhắc tới nhân vật bằng chữ thường không có động từ hành động (chỉ match qua session_cache).
    - Chunk 3: Định nghĩa nhân vật thứ hai (Hồ Phi Tuyết).
    - Chunk 4: Nhắc tới cả hai nhân vật.
    Đảm bảo workers=1 và workers=4 hoàn toàn trùng khớp 100%.
    """
    sample = tmp_path / "session_cache_novel.txt"
    lines = [
        'Âu Dương Tiêu Dao nói: "Hôm nay thời tiết thật đẹp."\n',          # Dòng 1 (Chunk 1) - Dialogue cue (conf 0.96)
        "Mọi người chung quanh đều gật đầu tán thành.\n",                  # Dòng 2 (Chunk 1)
        "Trời bắt đầu đổ một cơn mưa rào bất chợt.\n",                    # Dòng 3 (Chunk 1)
        "Vẻ mặt của âu dương tiêu dao luôn giữ nét thản nhiên.\n",        # Dòng 4 (Chunk 2) - Lowercase, chỉ match qua session_cache!
        "Gió lạnh thổi qua từng đợt buốt giá.\n",                          # Dòng 5 (Chunk 2)
        "Một tiếng sấm rền vang rạch ngang bầu trời.\n",                  # Dòng 6 (Chunk 2)
        "Hồ Phi Tuyết, 20 tuổi, từ trên lầu chậm rãi bước xuống.\n",        # Dòng 7 (Chunk 3) - Age profile cue (conf 0.95)
        "Nàng nhìn mọi người với vẻ mặt lạnh lùng.\n",                    # Dòng 8 (Chunk 3)
        "Không một ai dám lên tiếng trước mặt nàng.\n",                    # Dòng 9 (Chunk 3)
        "Tâm tư của hồ phi tuyết không ai có thể đoán trước.\n",           # Dòng 10 (Chunk 4) - Lowercase, chỉ match qua session_cache!
        "Âu Dương Tiêu Dao mỉm cười chào nàng một câu.\n",                 # Dòng 11 (Chunk 4) - Cap
        "Hồ Phi Tuyết khẽ gật đầu đáp lễ rồi quay đi.\n",                  # Dòng 12 (Chunk 4) - Cap
    ]
    sample.write_text("".join(lines), encoding="utf-8")

    loader = ResourceLoader(base_dir=tmp_path)
    loader.single_surnames = {"hồ"}
    loader.compound_surnames = {"âu dương"}

    engine = ScannerEngine(loader=loader, skip_known=False)

    progress_events = []
    def on_progress(done, total, found):
        progress_events.append((done, total, found))

    seq_res = engine.scan_file(sample, deduplicate=True, show_progress=False, workers=1)
    par_res = engine.scan_file(
        sample,
        deduplicate=True,
        show_progress=False,
        workers=4,
        progress_callback=on_progress
    )

    # Kiểm tra progress_callback được gọi trong quá trình song song
    assert len(progress_events) > 0
    assert progress_events[-1][0] == 12  # Total lines

    seq_map = {b.target: b for b in seq_res}
    par_map = {b.target: b for b in par_res}

    assert set(seq_map.keys()) == set(par_map.keys())
    assert "Âu Dương Tiêu Dao" in seq_map
    assert "Hồ Phi Tuyết" in seq_map

    adt = seq_map["Âu Dương Tiêu Dao"]
    adt_par = par_map["Âu Dương Tiêu Dao"]
    assert adt.so_lan_xuat_hien == adt_par.so_lan_xuat_hien == 3
    assert adt.cac_dong_xuat_hien == adt_par.cac_dong_xuat_hien == [1, 4, 11]
    assert adt.dong_xuat_hien == adt_par.dong_xuat_hien == 1

    hpt = seq_map["Hồ Phi Tuyết"]
    hpt_par = par_map["Hồ Phi Tuyết"]
    assert hpt.so_lan_xuat_hien == hpt_par.so_lan_xuat_hien == 3
    assert hpt.cac_dong_xuat_hien == hpt_par.cac_dong_xuat_hien == [7, 10, 12]
    assert hpt.dong_xuat_hien == hpt_par.dong_xuat_hien == 7

