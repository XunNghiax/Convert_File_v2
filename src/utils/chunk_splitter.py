from pathlib import Path
from typing import List, Tuple

def split_file_line_ranges(filepath: Path, num_chunks: int) -> List[Tuple[int, int]]:
    """
    Chia tổng số dòng của file thành các khoảng dòng [start_line, end_line] liên tục (1-indexed).
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return [(1, 1)]

    total = 0
    last_char = b""
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            total += chunk.count(b"\n")
            if chunk:
                last_char = chunk[-1:]
    if last_char and last_char != b"\n":
        total += 1
    total_lines = max(1, total)

    if num_chunks <= 1 or total_lines <= 1:
        return [(1, total_lines)]

    num_chunks = min(num_chunks, total_lines)
    chunk_size = total_lines // num_chunks
    ranges = []
    curr_start = 1
    for i in range(num_chunks):
        if i == num_chunks - 1:
            curr_end = total_lines
        else:
            curr_end = curr_start + chunk_size - 1
        ranges.append((curr_start, curr_end))
        curr_start = curr_end + 1

    return ranges

split_file_line_chunks = split_file_line_ranges
