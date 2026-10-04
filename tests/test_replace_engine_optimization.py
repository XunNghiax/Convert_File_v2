from pathlib import Path
import pytest
from src.replacer.replace_engine import ReplaceEngine, count_file_lines

def test_replace_file_parity_and_stats(tmp_path: Path):
    in_file = tmp_path / "input.txt"
    out_file = tmp_path / "output.txt"
    
    mapping = {
        "tiêu viêm": "Tiêu Viêm",
        "dược lão": "Dược Lão",
        "long kiếm phi": "Long Kiếm Phi",
        "kiếm phi": "Long Kiếm Phi"  # prefix guard test
    }
    engine = ReplaceEngine(custom_mapping=mapping)

    content = (
        "tiêu viêm nhìn thấy dược lão.\n"
        "Long kiếm phi rút kiếm ra.\n"
        "kiếm phi cũng mỉm cười.\n"
    )
    in_file.write_text(content, encoding="utf-8")

    stats = engine.replace_file(in_file, out_file, show_progress=False)
    
    res = out_file.read_text(encoding="utf-8")
    assert "Tiêu Viêm nhìn thấy Dược Lão.\n" in res
    assert "Long Kiếm Phi rút kiếm ra.\n" in res
    assert "Long Kiếm Phi cũng mỉm cười.\n" in res
    assert stats.total_lines == 3
    assert stats.total_replacements >= 3


def test_replace_file_large_buffer_chunking(tmp_path: Path):
    """Kiểm tra thay thế với số dòng lớn hơn BUFFER_LINES (1000) để đảm bảo chunk flush chính xác."""
    in_file = tmp_path / "large_input.txt"
    out_file = tmp_path / "large_output.txt"

    mapping = {
        "tiêu viêm": "Tiêu Viêm",
        "huân nhi": "Huân Nhi"
    }
    engine = ReplaceEngine(custom_mapping=mapping)

    total_test_lines = 2500
    lines = []
    for i in range(total_test_lines):
        if i % 2 == 0:
            lines.append(f"Dòng {i}: tiêu viêm đang luyện đan.\n")
        else:
            lines.append(f"Dòng {i}: huân nhi đứng chờ bên cạnh.\n")

    in_file.write_text("".join(lines), encoding="utf-8")

    stats = engine.replace_file(in_file, out_file, show_progress=False)

    assert stats.total_lines == total_test_lines
    assert stats.total_replacements == total_test_lines

    out_lines = out_file.read_text(encoding="utf-8").splitlines(keepends=True)
    assert len(out_lines) == total_test_lines
    assert out_lines[0] == "Dòng 0: Tiêu Viêm đang luyện đan.\n"
    assert out_lines[1] == "Dòng 1: Huân Nhi đứng chờ bên cạnh.\n"
    assert out_lines[2499] == "Dòng 2499: Huân Nhi đứng chờ bên cạnh.\n"


def test_fast_line_count(tmp_path: Path):
    """Kiểm tra tính chính xác của hàm count_file_lines với các trường hợp biên."""
    f1 = tmp_path / "f1.txt"
    f1.write_text("a\nb\nc\n", encoding="utf-8")
    assert count_file_lines(f1) == 3

    # File không có newline ở cuối
    f2 = tmp_path / "f2.txt"
    f2.write_text("a\nb\nc", encoding="utf-8")
    assert count_file_lines(f2) == 3

    # File rỗng
    f3 = tmp_path / "f3.txt"
    f3.write_text("", encoding="utf-8")
    assert count_file_lines(f3) == 0

    # File 1 dòng không có newline
    f4 = tmp_path / "f4.txt"
    f4.write_text("hello", encoding="utf-8")
    assert count_file_lines(f4) == 1
