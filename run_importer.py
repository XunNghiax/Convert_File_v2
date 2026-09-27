"""
Entry script khởi chạy module Importer.
Mặc định đọc file samples/import.json và import vào resources/dictionaries/character_dict.json
"""
import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc dự án
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.importer.main import main

if __name__ == "__main__":
    main()
