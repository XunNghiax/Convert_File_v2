from pathlib import Path
from typing import Union

def count_file_lines(filepath: Union[str, Path]) -> int:
    """
    Đếm nhanh và chính xác tổng số dòng trong file bằng cách đọc nhị phân theo khối 1MB.
    Xử lý an toàn file không tồn tại (trả về 0) và dòng cuối cùng không có ký tự xuống dòng.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        return 0
    total = 0
    last_byte = b""
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            total += chunk.count(b"\n")
            if chunk:
                last_byte = chunk[-1:]
    if last_byte and last_byte != b"\n":
        total += 1
    return total
