from pathlib import Path
import pytest
from src.replacer.replace_engine import ReplaceEngine

def test_parallel_replace_matches_sequential(tmp_path: Path):
    in_file = tmp_path / "large_input.txt"
    out_seq = tmp_path / "out_seq.txt"
    out_par = tmp_path / "out_par.txt"

    lines = []
    for i in range(1000):
        lines.append(f"Dòng {i}: tiêu viêm nói chuyện với dược lão tại thành phố.\n")
    in_file.write_text("".join(lines), encoding="utf-8")

    mapping = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    engine = ReplaceEngine(custom_mapping=mapping)

    stats_seq = engine.replace_file(in_file, out_seq, show_progress=False, workers=1)
    stats_par = engine.replace_file(in_file, out_par, show_progress=False, workers=4)

    assert out_seq.read_text(encoding="utf-8") == out_par.read_text(encoding="utf-8")
    assert stats_seq.total_replacements == stats_par.total_replacements
    assert stats_seq.total_lines == stats_par.total_lines == 1000


def test_parallel_replace_large_file_and_stats_parity(tmp_path: Path):
    """Kiểm tra thay thế song song với file lớn (3.000 dòng) và kiểm tra thống kê top_replacements."""
    in_file = tmp_path / "large_3000.txt"
    out_seq = tmp_path / "out_seq_3000.txt"
    out_par = tmp_path / "out_par_3000.txt"

    lines = []
    for i in range(3000):
        if i % 3 == 0:
            lines.append(f"Dòng {i}: tiêu viêm mỉm cười chào dược lão.\n")
        elif i % 3 == 1:
            lines.append(f"Dòng {i}: huân nhi bước tới nắm tay tiêu viêm.\n")
        else:
            lines.append(f"Dòng {i}: mỹ đỗ toa lạnh lùng nhìn dược lão.\n")
    in_file.write_text("".join(lines), encoding="utf-8")

    mapping = {
        "tiêu viêm": "Tiêu Viêm",
        "dược lão": "Dược Lão",
        "huân nhi": "Huân Nhi",
        "mỹ đỗ toa": "Mỹ Đỗ Toa"
    }
    engine = ReplaceEngine(custom_mapping=mapping)

    stats_seq = engine.replace_file(in_file, out_seq, show_progress=False, workers=1)
    stats_par = engine.replace_file(in_file, out_par, show_progress=False, workers=4)

    assert out_seq.read_text(encoding="utf-8") == out_par.read_text(encoding="utf-8")
    assert stats_par.total_lines == stats_seq.total_lines == 3000
    assert stats_par.total_replacements == stats_seq.total_replacements
    assert stats_par.top_replacements == stats_seq.top_replacements


def test_parallel_replace_with_guards(tmp_path: Path):
    """Đảm bảo các guard (prefix guard, descriptive guard) hoạt động chính xác khi chạy song song."""
    in_file = tmp_path / "guards_input.txt"
    out_seq = tmp_path / "out_seq_guards.txt"
    out_par = tmp_path / "out_par_guards.txt"

    lines = []
    for i in range(1200):
        lines.append(
            f"Dòng {i}: Long kiếm phi xuất chiêu, kiếm phi sắc bén; vóc dáng bóng hình xinh đẹp.\n"
        )
    in_file.write_text("".join(lines), encoding="utf-8")

    mapping = {
        "long kiếm phi": "Long Kiếm Phi",
        "kiếm phi": "Long Kiếm Phi",
        "bóng hình xinh đẹp": "Bóng Hình Xinh Đẹp"
    }
    engine = ReplaceEngine(custom_mapping=mapping)

    stats_seq = engine.replace_file(in_file, out_seq, show_progress=False, workers=1)
    stats_par = engine.replace_file(in_file, out_par, show_progress=False, workers=4)

    assert out_seq.read_text(encoding="utf-8") == out_par.read_text(encoding="utf-8")
    assert stats_par.total_replacements == stats_seq.total_replacements
    # Kiểm tra prefix guard: không lặp thành Long Long Kiếm Phi
    par_content = out_par.read_text(encoding="utf-8")
    assert "Long Long Kiếm Phi" not in par_content
    # Kiểm tra context guard: vóc dáng bóng hình xinh đẹp không bị thay
    assert "vóc dáng bóng hình xinh đẹp" in par_content


def test_parallel_replace_fallback_small_file(tmp_path: Path):
    """File nhỏ hơn ngưỡng song song (ví dụ 10 dòng) vẫn hoạt động an toàn và chính xác khi workers=4."""
    in_file = tmp_path / "small.txt"
    out_file = tmp_path / "small_out.txt"

    lines = [f"Dòng {i}: tiêu viêm chào dược lão.\n" for i in range(10)]
    in_file.write_text("".join(lines), encoding="utf-8")

    mapping = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    engine = ReplaceEngine(custom_mapping=mapping)

    stats = engine.replace_file(in_file, out_file, show_progress=False, workers=4)
    assert stats.total_lines == 10
    assert stats.total_replacements == 20
    assert "Tiêu Viêm chào Dược Lão." in out_file.read_text(encoding="utf-8")


def test_parallel_replace_no_track_stats(tmp_path: Path):
    """Kiểm tra track_stats=False trên chế độ song song."""
    in_file = tmp_path / "no_stats.txt"
    out_file = tmp_path / "no_stats_out.txt"

    lines = [f"Dòng {i}: tiêu viêm chào dược lão.\n" for i in range(1000)]
    in_file.write_text("".join(lines), encoding="utf-8")

    mapping = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    engine = ReplaceEngine(custom_mapping=mapping)

    stats = engine.replace_file(in_file, out_file, show_progress=False, track_stats=False, workers=4)
    assert stats.total_lines == 1000
    assert stats.total_replacements == 0
    assert "Tiêu Viêm chào Dược Lão." in out_file.read_text(encoding="utf-8")


def test_replace_chunk_worker_direct(tmp_path: Path):
    """Kiểm tra gọi trực tiếp _replace_chunk_worker ở module-level với cả 2 cách truyền tham số."""
    from src.replacer.replace_engine import _replace_chunk_worker

    in_file = tmp_path / "worker_in.txt"
    in_file.write_text("dòng 1: tiêu viêm\ndòng 2: dược lão\ndòng 3: tiêu viêm\n", encoding="utf-8")

    out_part1 = tmp_path / "part1.txt"
    mapping = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    engine = ReplaceEngine(custom_mapping=mapping)

    # Cách 1: truyền compiled pattern và dict_map
    stats1 = _replace_chunk_worker(
        input_path=in_file,
        out_part_path=out_part1,
        start_line=1,
        end_line=2,
        pattern_or_dict=engine.pattern,
        dict_map_or_custom=engine.dict_map,
        track_stats=True
    )
    assert stats1["tiêu viêm"] == 1
    assert stats1["dược lão"] == 1
    assert out_part1.read_text(encoding="utf-8") == "dòng 1: Tiêu Viêm\ndòng 2: Dược Lão\n"

    # Cách 2: truyền dict_map và custom_mapping
    out_part2 = tmp_path / "part2.txt"
    stats2 = _replace_chunk_worker(
        input_path=in_file,
        out_part_path=out_part2,
        start_line=2,
        end_line=3,
        pattern_or_dict=mapping,
        dict_map_or_custom=None,
        track_stats=True
    )
    assert stats2["tiêu viêm"] == 1
    assert stats2["dược lão"] == 1
    assert out_part2.read_text(encoding="utf-8") == "dòng 2: Dược Lão\ndòng 3: Tiêu Viêm\n"


def _faulty_worker_for_test(*args, **kwargs):
    raise RuntimeError("Cố tình gây lỗi worker")

def test_parallel_replace_cleanup_on_error(tmp_path: Path, monkeypatch):
    """Đảm bảo try...finally dọn dẹp sạch sẽ các part file và progress printer nếu xảy ra ngoại lệ."""
    in_file = tmp_path / "err_in.txt"
    out_file = tmp_path / "err_out.txt"

    lines = [f"Dòng {i}: tiêu viêm chào dược lão.\n" for i in range(1000)]
    in_file.write_text("".join(lines), encoding="utf-8")

    mapping = {"tiêu viêm": "Tiêu Viêm", "dược lão": "Dược Lão"}
    engine = ReplaceEngine(custom_mapping=mapping)

    monkeypatch.setattr("src.replacer.replace_engine._replace_chunk_worker", _faulty_worker_for_test)

    with pytest.raises(RuntimeError, match="Cố tình gây lỗi worker"):
        engine.replace_file(in_file, out_file, show_progress=True, workers=4)

    # Đảm bảo không còn part file hoặc tmp file nào vương vãi
    remaining_files = list(tmp_path.glob("err_out.*"))
    assert len(remaining_files) == 0

