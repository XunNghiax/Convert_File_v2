import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple, Any

# Đường dẫn mặc định chuẩn của dự án
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_IMPORT_JSON = DEFAULT_PROJECT_ROOT / "samples" / "import.json"
DEFAULT_DICTIONARIES_DIR = DEFAULT_PROJECT_ROOT / "resources" / "dictionaries"
DEFAULT_CHARACTER_DICT = DEFAULT_DICTIONARIES_DIR / "character_dict.json"
DEFAULT_COMMON_DICT = DEFAULT_DICTIONARIES_DIR / "common_dict.json"
DEFAULT_WARNING_JSON = DEFAULT_PROJECT_ROOT / "samples" / "warning.json"

# Để tương thích ngược
DEFAULT_TARGET_DICT = DEFAULT_CHARACTER_DICT

def deduplicate_by_suggested_target(
    items: List[Dict[str, Any]],
    max_occurrences: int = 2
) -> List[Dict[str, Any]]:
    """
    Loại bỏ các block có suggested_target (hoặc target) trùng nhau,
    chỉ giữ lại tối đa max_occurrences cái (mặc định là 2).
    """
    if max_occurrences is None or max_occurrences <= 0:
        return list(items)

    seen_counts: Dict[str, int] = {}
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = str(item.get("suggested_target") or item.get("target") or item.get("source", "")).strip().lower()
        if not key:
            result.append(item)
            continue
        cnt = seen_counts.get(key, 0)
        if cnt < max_occurrences:
            seen_counts[key] = cnt + 1
            result.append(item)
        else:
            # Bỏ qua từ lần xuất hiện thứ (max_occurrences + 1) trở đi
            continue
    return result

def check_word_count_alignment(source: str, target: str) -> Tuple[bool, int, int, str]:
    """
    Kiểm tra số từ giữa source và target.
    Nếu lệch nhau (ví dụ 2 từ -> 3 từ), trả về False kèm nguyên nhân.
    """
    words_s = [w for w in source.strip().split() if w]
    words_t = [w for w in target.strip().split() if w]
    cnt_s = len(words_s)
    cnt_t = len(words_t)

    if cnt_s == cnt_t:
        return True, cnt_s, cnt_t, ""

    diff = cnt_t - cnt_s
    if diff > 0:
        reason = f"Lệch số từ (+{diff}): Target ({cnt_t} từ) dài hơn Source ({cnt_s} từ), nguy cơ lặp họ/tiền tố khi replace"
    else:
        reason = f"Lệch số từ ({diff}): Target ({cnt_t} từ) ngắn hơn Source ({cnt_s} từ), nguy cơ xung đột từ miêu tả/tên rút gọn"

    return False, cnt_s, cnt_t, reason

def filter_and_export_warnings(
    items: List[Dict[str, Any]],
    warning_path: Union[str, Path] = DEFAULT_WARNING_JSON
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Lọc các mục bị lệch số từ hoặc nội dung không trùng nhau giữa source và suggested_target (target),
    xuất ra file warning.json để chuẩn hóa.
    Chỉ trả về các mục đạt chuẩn (valid_items) để nạp vào từ điển.
    """
    valid_items = []
    warning_items = []

    for item in items:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", "")).strip()
        # Ưu tiên lấy suggested_target trước, fallback về target
        target = str(item.get("suggested_target") or item.get("target", "")).strip()

        if not source or not target:
            continue

        is_aligned, cnt_s, cnt_t, reason = check_word_count_alignment(source, target)
        if not is_aligned:
            w_entry = {
                "id": str(item.get("id", "")).strip(),
                "is_character": item.get("is_character", True),
                "source": source,
                "target": str(item.get("target", "")).strip() or target,
                "suggested_target": str(item.get("suggested_target", "")).strip() or target,
                "words_source": cnt_s,
                "words_target": cnt_t,
                "diff": cnt_t - cnt_s,
                "reason": reason,
                "context": item.get("context", "")
            }
            warning_items.append(w_entry)
        else:
            valid_items.append(item)

    warning_path = Path(warning_path)
    if warning_items:
        save_dictionary(warning_items, warning_path, indent=2)
        print(f"[!] CẢNH BÁO: Phát hiện {len(warning_items)} mục lệch số từ giữa Source và Suggested Target.")
        print(f"[!] Đã xuất ra '{warning_path}' để bạn kiểm tra và chuẩn hóa lại.")
    else:
        if warning_path.exists():
            try:
                save_dictionary([], warning_path, indent=2)
            except Exception:
                pass

    return valid_items, warning_items

def get_next_id(entries: Any = None, default_prefix: str = "ch-") -> str:
    """[Deprecated] Giữ lại để tương thích ngược. Không còn sử dụng cho từ điển dạng key-value."""
    if not entries or not isinstance(entries, list):
        return ""
    prefix = default_prefix
    for entry in reversed(entries):
        if isinstance(entry, dict):
            item_id = str(entry.get("id", "")).strip()
            match = re.match(r"^([a-zA-Z]+-?)(\d+)$", item_id)
            if match:
                prefix = match.group(1)
                break

    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    for entry in entries:
        if isinstance(entry, dict):
            item_id = str(entry.get("id", "")).strip()
            match = pattern.match(item_id)
            if match:
                max_num = max(max_num, int(match.group(1)))
    return f"{prefix}{max_num + 1}"

def load_dictionary(path: Union[str, Path]) -> Dict[str, str]:
    """Tải file từ điển JSON dưới dạng key-value dict (nguồn: đích). Có fallback cho định dạng mảng cũ."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k).strip().lower(): str(v).strip() for k, v in data.items() if str(k).strip()}
            elif isinstance(data, list):
                result = {}
                for item in data:
                    if isinstance(item, dict):
                        src = str(item.get("source", "")).strip().lower()
                        tgt = str(item.get("suggested_target") or item.get("target", "")).strip()
                        if src and tgt:
                            result[src] = tgt
                return result
            return {}
    except Exception as e:
        print(f"[!] Cảnh báo: Không thể đọc file từ điển {path}: {e}")
        return {}

def save_dictionary(entries: Union[Dict[str, Any], List[Any]], path: Union[str, Path], indent: int = 2) -> bool:
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

def capitalize_first_letters(text: str) -> str:
    """
    Viết hoa chữ cái đầu tiên của mỗi từ trong chuỗi (Title Case cho tên nhân vật).
    Bảo toàn phần còn lại của mỗi từ để không làm hỏng các tên viết hoa đặc thù.
    """
    if not text:
        return text
    words = text.strip().split()
    return " ".join(w[:1].upper() + w[1:] for w in words)

def lowercase_all(text: str) -> str:
    """Chuyển toàn bộ chuỗi thành chữ thường (lowkey toàn bộ cho từ điển chung)."""
    return text.strip().lower() if text else ""

def normalize_character_entry(raw_item: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Chuẩn hóa một mục nhân vật cho character_dict (dùng Tag, tự động upcase chữ cái đầu mỗi từ)."""
    if not isinstance(raw_item, dict):
        return None

    source = str(raw_item.get("source", "")).strip()
    target = str(raw_item.get("suggested_target") or raw_item.get("target", "")).strip()
    tag = raw_item.get("Tag", raw_item.get("tag", raw_item.get("yeu_to_nhan_biet", "")))
    tag = str(tag).strip() if tag is not None else ""
    custom_id = str(raw_item.get("id", "")).strip()

    if not source or not target:
        return None

    # Tự động viết hoa chữ cái đầu tiên của mỗi từ cho tên nhân vật
    target = capitalize_first_letters(target)

    return {
        "id": custom_id,
        "source": source,
        "target": target,
        "Tag": tag
    }

def normalize_common_entry(raw_item: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Chuẩn hóa một mục từ thông dụng cho common_dict (dùng category, tự động lowercase toàn bộ target)."""
    if not isinstance(raw_item, dict):
        return None

    source = str(raw_item.get("source", "")).strip()
    target = str(raw_item.get("suggested_target") or raw_item.get("target", "")).strip()
    cat = raw_item.get("category", raw_item.get("yeu_to_nhan_biet", raw_item.get("Tag", "Cụm từ chung")))
    cat = str(cat).strip() if cat is not None else "Cụm từ chung"
    custom_id = str(raw_item.get("id", "")).strip()

    if not source or not target:
        return None

    # Tự động lowkey (chuyển toàn bộ thành chữ thường) cho từ điển thông dụng
    target = lowercase_all(target)

    return {
        "id": custom_id,
        "source": source,
        "target": target,
        "category": cat
    }

def normalize_entry(
    raw_item: Dict[str, Any],
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
    items: List[Dict[str, Any]],
    dict_path: Union[str, Path] = DEFAULT_CHARACTER_DICT,
    overwrite_existing: bool = True,
    id_prefix: str = "ch-",
    filter_characters: bool = True,
    keep_id: bool = False
) -> Dict[str, Any]:
    """Import các mục nhân vật vào character_dict.json dưới dạng key-value."""
    dict_path = Path(dict_path)
    entries = load_dictionary(dict_path)

    added_count = 0
    updated_count = 0
    skipped_count = 0

    for raw in items:
        if not isinstance(raw, dict):
            skipped_count += 1
            continue

        if filter_characters and "is_character" in raw:
            if not raw.get("is_character", False):
                skipped_count += 1
                continue

        source = str(raw.get("source", "")).strip()
        target = str(raw.get("suggested_target") or raw.get("target", "")).strip()

        if not source or not target:
            skipped_count += 1
            continue

        src_key = source.lower()
        target_val = capitalize_first_letters(target)

        if src_key in entries:
            if overwrite_existing:
                entries[src_key] = target_val
                updated_count += 1
            else:
                skipped_count += 1
        else:
            entries[src_key] = target_val
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

def import_common_dict(
    items: List[Dict[str, Any]],
    dict_path: Union[str, Path] = DEFAULT_COMMON_DICT,
    overwrite_existing: bool = True,
    id_prefix: str = "co-",
    keep_id: bool = False
) -> Dict[str, Any]:
    """Import các mục từ ngữ chung vào common_dict.json dưới dạng key-value."""
    dict_path = Path(dict_path)
    entries = load_dictionary(dict_path)

    added_count = 0
    updated_count = 0
    skipped_count = 0

    for raw in items:
        if not isinstance(raw, dict):
            skipped_count += 1
            continue

        source = str(raw.get("source", "")).strip()
        target = str(raw.get("suggested_target") or raw.get("target", "")).strip()

        if not source or not target:
            skipped_count += 1
            continue

        src_key = source.lower()
        target_val = lowercase_all(target)

        if src_key in entries:
            if overwrite_existing:
                entries[src_key] = target_val
                updated_count += 1
            else:
                skipped_count += 1
        else:
            entries[src_key] = target_val
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
    items: List[Dict[str, Any]],
    char_dict_path: Union[str, Path] = DEFAULT_CHARACTER_DICT,
    common_dict_path: Union[str, Path] = DEFAULT_COMMON_DICT,
    warning_path: Union[str, Path] = DEFAULT_WARNING_JSON,
    overwrite_existing: bool = True,
    keep_id: bool = False,
    validate_word_count: bool = True,
    max_duplicate_suggested_targets: int = 2
) -> Dict[str, Any]:
    """
    Phân bổ các mục dựa vào trường 'is_character':
    - Lọc bỏ các block có suggested_target trùng nhau (giữ tối đa max_duplicate_suggested_targets cái).
    - Nếu validate_word_count=True: Lọc các mục lệch số từ / lệch nội dung ra warning.json trước.
    - 'is_character': true -> nạp vào character_dict.json (Title Case)
    - 'is_character': false -> nạp vào common_dict.json (lowercase)
    """
    if max_duplicate_suggested_targets and max_duplicate_suggested_targets > 0:
        items = deduplicate_by_suggested_target(items, max_occurrences=max_duplicate_suggested_targets)

    warning_count = 0
    if validate_word_count:
        valid_items, warning_items = filter_and_export_warnings(items, warning_path=warning_path)
        warning_count = len(warning_items)
        items_to_process = valid_items
    else:
        items_to_process = items

    char_items = []
    common_items = []

    for item in items_to_process:
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
        overwrite_existing=overwrite_existing
    )

    common_result = import_common_dict(
        common_items,
        dict_path=common_dict_path,
        overwrite_existing=overwrite_existing
    )

    return {
        "character": char_result,
        "common": common_result,
        "warning_count": warning_count,
        "warning_file": str(warning_path) if warning_count > 0 else None,
        "total_processed": len(items_to_process),
        "total_input": len(items)
    }

def import_entries(
    items: List[Dict[str, Any]],
    dict_path: Union[str, Path] = DEFAULT_TARGET_DICT,
    warning_path: Union[str, Path] = DEFAULT_WARNING_JSON,
    overwrite_existing: bool = True,
    id_prefix: str = "ch-",
    filter_characters: bool = True,
    keep_id: bool = False,
    validate_word_count: bool = True,
    max_duplicate_suggested_targets: int = 2
) -> Dict[str, Any]:
    """
    Import danh sách mục vào một file từ điển chỉ định dưới dạng key-value.
    - Lọc bỏ các block có suggested_target trùng nhau (giữ tối đa max_duplicate_suggested_targets cái).
    - Nếu target là common_dict.json, sẽ tự động áp dụng định dạng common_dict.
    - Nếu target là character_dict.json và filter_characters=True, sẽ lọc bỏ is_character == False.
    """
    if max_duplicate_suggested_targets and max_duplicate_suggested_targets > 0:
        items = deduplicate_by_suggested_target(items, max_occurrences=max_duplicate_suggested_targets)

    warning_count = 0
    if validate_word_count:
        valid_items, warning_items = filter_and_export_warnings(items, warning_path=warning_path)
        warning_count = len(warning_items)
        items_to_process = valid_items
    else:
        items_to_process = items

    dict_path = Path(dict_path)
    if "common_dict" in dict_path.name:
        res = import_common_dict(
            items_to_process,
            dict_path=dict_path,
            overwrite_existing=overwrite_existing
        )
    else:
        res = import_character_dict(
            items_to_process,
            dict_path=dict_path,
            overwrite_existing=overwrite_existing,
            filter_characters=filter_characters
        )

    res["warning_count"] = warning_count
    res["warning_file"] = str(warning_path) if warning_count > 0 else None
    return res

def parse_source_file(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
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
                if "items" in data and isinstance(data["items"], list):
                    items = data["items"]
                elif all(isinstance(v, str) for v in data.values()):
                    items = [{"source": k, "target": v} for k, v in data.items()]
                else:
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
