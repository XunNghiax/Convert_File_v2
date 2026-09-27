import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple

# Đường dẫn mặc định chuẩn của dự án
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_IMPORT_JSON = DEFAULT_PROJECT_ROOT / "samples" / "import.json"
DEFAULT_DICTIONARIES_DIR = DEFAULT_PROJECT_ROOT / "resources" / "dictionaries"
DEFAULT_CHARACTER_DICT = DEFAULT_DICTIONARIES_DIR / "character_dict.json"
DEFAULT_COMMON_DICT = DEFAULT_DICTIONARIES_DIR / "common_dict.json"

# Để tương thích ngược
DEFAULT_TARGET_DICT = DEFAULT_CHARACTER_DICT

def get_next_id(entries: List[Dict[str, str]], default_prefix: str = "ch-") -> str:
    """Tìm ID số lớn nhất hiện tại (vd: ch-55 hoặc co-1106) và trả về ID tiếp theo."""
    prefix = default_prefix
    if entries:
        for entry in reversed(entries):
            item_id = str(entry.get("id", "")).strip()
            match = re.match(r"^([a-zA-Z]+-?)(\d+)$", item_id)
            if match:
                prefix = match.group(1)
                break

    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    for entry in entries:
        item_id = str(entry.get("id", "")).strip()
        match = pattern.match(item_id)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"{prefix}{max_num + 1}"

def load_dictionary(path: Path) -> List[Dict[str, str]]:
    """Tải file từ điển JSON."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception as e:
        print(f"[!] Cảnh báo: Không thể đọc file từ điển {path}: {e}")
        return []

def save_dictionary(entries: List[Dict[str, str]], path: Path, indent: int = 4) -> bool:
    """Lưu lại từ điển với chuẩn UTF-8 và cơ chế atomic write chống hỏng file khi bị ngắt."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=indent)
            f.write("\n")
        temp_path.replace(path)
        return True
    except Exception as e:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        print(f"[X] Lỗi khi lưu file từ điển {path}: {e}")
        return False

def normalize_character_entry(raw_item: Dict[str, any]) -> Optional[Dict[str, str]]:
    """Chuẩn hóa một mục nhân vật cho character_dict.json (dùng Tag)."""
    if not isinstance(raw_item, dict):
        return None

    source = str(raw_item.get("source", "")).strip()
    target = str(raw_item.get("target") or raw_item.get("suggested_target", "")).strip()
    tag = raw_item.get("Tag", raw_item.get("tag", raw_item.get("yeu_to_nhan_biet", "")))
    tag = str(tag).strip() if tag is not None else ""
    custom_id = str(raw_item.get("id", "")).strip()

    if not source or not target:
        return None

    return {
        "id": custom_id,
        "source": source,
        "target": target,
        "Tag": tag
    }

def normalize_common_entry(raw_item: Dict[str, any]) -> Optional[Dict[str, str]]:
    """Chuẩn hóa một mục từ thông dụng / nhận diện nhầm cho common_dict.json (dùng category)."""
    if not isinstance(raw_item, dict):
        return None

    source = str(raw_item.get("source", "")).strip()
    target = str(raw_item.get("target") or raw_item.get("suggested_target", "")).strip()
    cat = raw_item.get("category", raw_item.get("yeu_to_nhan_biet", raw_item.get("Tag", "Cụm từ chung")))
    cat = str(cat).strip() if cat is not None else "Cụm từ chung"
    custom_id = str(raw_item.get("id", "")).strip()

    if not source or not target:
        return None

    return {
        "id": custom_id,
        "source": source,
        "target": target,
        "category": cat
    }

def normalize_entry(
    raw_item: Dict[str, any],
    filter_characters: bool = True
) -> Optional[Dict[str, str]]:
    """Hàm chuẩn hóa tương thích ngược."""
    if not isinstance(raw_item, dict):
        return None

    if filter_characters and "is_character" in raw_item:
        if not raw_item.get("is_character", False):
            return None

    return normalize_character_entry(raw_item)

def import_character_dict(
    items: List[Dict[str, any]],
    dict_path: Union[str, Path] = DEFAULT_CHARACTER_DICT,
    overwrite_existing: bool = True,
    id_prefix: str = "ch-",
    filter_characters: bool = True,
    keep_id: bool = False
) -> Dict[str, any]:
    """Import các mục nhân vật vào character_dict.json."""
    dict_path = Path(dict_path)
    entries = load_dictionary(dict_path)

    existing_map = {}
    for idx, entry in enumerate(entries):
        src = str(entry.get("source", "")).strip().lower()
        if src:
            existing_map[src] = idx

    added_count = 0
    updated_count = 0
    skipped_count = 0

    id_pattern = re.compile(rf"^{re.escape(id_prefix)}\d+$", re.IGNORECASE)

    for raw in items:
        if filter_characters and isinstance(raw, dict) and "is_character" in raw:
            if not raw.get("is_character", False):
                skipped_count += 1
                continue

        norm = normalize_character_entry(raw)
        if not norm:
            skipped_count += 1
            continue

        src_key = norm["source"].lower()
        custom_id = norm["id"]

        if src_key in existing_map:
            if overwrite_existing:
                idx = existing_map[src_key]
                entries[idx]["target"] = norm["target"]
                if norm["Tag"] != "":
                    entries[idx]["Tag"] = norm["Tag"]
                if custom_id and (keep_id or id_pattern.match(custom_id)):
                    entries[idx]["id"] = custom_id
                updated_count += 1
            else:
                skipped_count += 1
        else:
            if custom_id and (keep_id or id_pattern.match(custom_id)):
                item_id = custom_id
            else:
                item_id = get_next_id(entries, default_prefix=id_prefix)

            new_entry = {
                "id": item_id,
                "source": norm["source"],
                "target": norm["target"],
                "Tag": norm["Tag"]
            }
            entries.append(new_entry)
            existing_map[src_key] = len(entries) - 1
            added_count += 1

    if added_count > 0 or updated_count > 0:
        save_dictionary(entries, dict_path, indent=4)

    return {
        "added": added_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": len(entries),
        "target_file": str(dict_path)
    }

def import_common_dict(
    items: List[Dict[str, any]],
    dict_path: Union[str, Path] = DEFAULT_COMMON_DICT,
    overwrite_existing: bool = True,
    id_prefix: str = "co-",
    keep_id: bool = False
) -> Dict[str, any]:
    """Import các mục từ ngữ chung vào common_dict.json."""
    dict_path = Path(dict_path)
    entries = load_dictionary(dict_path)

    existing_map = {}
    for idx, entry in enumerate(entries):
        src = str(entry.get("source", "")).strip().lower()
        if src:
            existing_map[src] = idx

    added_count = 0
    updated_count = 0
    skipped_count = 0

    id_pattern = re.compile(rf"^{re.escape(id_prefix)}\d+$", re.IGNORECASE)

    for raw in items:
        norm = normalize_common_entry(raw)
        if not norm:
            skipped_count += 1
            continue

        src_key = norm["source"].lower()
        custom_id = norm["id"]

        if src_key in existing_map:
            if overwrite_existing:
                idx = existing_map[src_key]
                entries[idx]["target"] = norm["target"]
                if norm["category"] != "":
                    entries[idx]["category"] = norm["category"]
                if custom_id and (keep_id or id_pattern.match(custom_id)):
                    entries[idx]["id"] = custom_id
                updated_count += 1
            else:
                skipped_count += 1
        else:
            if custom_id and (keep_id or id_pattern.match(custom_id)):
                item_id = custom_id
            else:
                item_id = get_next_id(entries, default_prefix=id_prefix)

            new_entry = {
                "id": item_id,
                "source": norm["source"],
                "target": norm["target"],
                "category": norm["category"]
            }
            entries.append(new_entry)
            existing_map[src_key] = len(entries) - 1
            added_count += 1

    if added_count > 0 or updated_count > 0:
        save_dictionary(entries, dict_path, indent=2)

    return {
        "added": added_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": len(entries),
        "target_file": str(dict_path)
    }

def distribute_and_import(
    items: List[Dict[str, any]],
    char_dict_path: Union[str, Path] = DEFAULT_CHARACTER_DICT,
    common_dict_path: Union[str, Path] = DEFAULT_COMMON_DICT,
    overwrite_existing: bool = True,
    keep_id: bool = False
) -> Dict[str, any]:
    """
    Phân bổ các mục dựa vào trường 'is_character':
    - 'is_character': true -> nạp vào character_dict.json (ID: ch-XX, Tag)
    - 'is_character': false -> nạp vào common_dict.json (ID: co-XX, category)
    """
    char_items = []
    common_items = []

    for item in items:
        if not isinstance(item, dict):
            continue
        is_char = item.get("is_character", True)
        if is_char:
            char_items.append(item)
        else:
            common_items.append(item)

    char_result = import_character_dict(
        char_items,
        dict_path=char_dict_path,
        overwrite_existing=overwrite_existing,
        id_prefix="ch-",
        keep_id=keep_id
    )

    common_result = import_common_dict(
        common_items,
        dict_path=common_dict_path,
        overwrite_existing=overwrite_existing,
        id_prefix="co-",
        keep_id=keep_id
    )

    return {
        "character": char_result,
        "common": common_result,
        "total_processed": len(items)
    }

def import_entries(
    items: List[Dict[str, any]],
    dict_path: Union[str, Path] = DEFAULT_TARGET_DICT,
    overwrite_existing: bool = True,
    id_prefix: str = "ch-",
    filter_characters: bool = True,
    keep_id: bool = False
) -> Dict[str, any]:
    """
    Import danh sách mục vào một file từ điển chỉ định.
    Nếu target là common_dict.json, sẽ tự động áp dụng định dạng common_dict.
    Nếu target là character_dict.json và filter_characters=True, sẽ lọc bỏ is_character == False.
    """
    dict_path = Path(dict_path)
    if "common_dict" in dict_path.name:
        return import_common_dict(
            items,
            dict_path=dict_path,
            overwrite_existing=overwrite_existing,
            id_prefix=id_prefix if id_prefix != "ch-" else "co-",
            keep_id=keep_id
        )

    return import_character_dict(
        items,
        dict_path=dict_path,
        overwrite_existing=overwrite_existing,
        id_prefix=id_prefix,
        filter_characters=filter_characters,
        keep_id=keep_id
    )

def parse_source_file(file_path: Union[str, Path]) -> List[Dict[str, any]]:
    """Phân tích dữ liệu từ file JSON, TXT hoặc CSV/TSV."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file nguồn: {file_path}")

    ext = file_path.suffix.lower()
    items = []

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = [data]
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = []
                for delimiter in ["\t", "|", "=", ","]:
                    if delimiter in line:
                        parts = [p.strip() for p in line.split(delimiter)]
                        break
                if len(parts) >= 2:
                    items.append({
                        "source": parts[0],
                        "target": parts[1],
                        "Tag": parts[2] if len(parts) > 2 else ""
                    })
    return items
