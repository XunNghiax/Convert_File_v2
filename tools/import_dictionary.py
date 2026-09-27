"""
Wrapper script gọi src.importer.main để tương thích ngược.
"""
import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc dự án
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.importer.main import main
from src.importer.dictionary_importer import (
    import_entries,
    load_dictionary,
    save_dictionary,
    get_next_id,
    normalize_entry
)

if __name__ == "__main__":
    main()
