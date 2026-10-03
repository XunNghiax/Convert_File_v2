import json
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def capitalize_words(text: str) -> str:
    words = text.strip().split()
    return " ".join(w[:1].upper() + w[1:] for w in words)

def convert_dict_list_to_kv(items: List[Dict[str, Any]], is_character: bool = True) -> Dict[str, str]:
    kv = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source", "")).strip().lower()
        tgt = str(item.get("target") or item.get("suggested_target", "")).strip()
        if not src or not tgt:
            continue
        if is_character:
            tgt = capitalize_words(tgt)
        else:
            tgt = tgt.lower()
        kv[src] = tgt
    return kv

def migrate_file(file_path: Path, is_character: bool):
    if not file_path.exists():
        print(f"[-] File không tồn tại: {file_path}")
        return
    backup_path = file_path.with_suffix(f"{file_path.suffix}.bak")
    shutil.copy2(file_path, backup_path)
    print(f"[+] Đã backup vào: {backup_path}")

    data = json.loads(file_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        kv = convert_dict_list_to_kv(data, is_character=is_character)
    elif isinstance(data, dict):
        kv = {k.strip().lower(): (capitalize_words(v) if is_character else str(v).strip().lower()) for k, v in data.items()}
    else:
        kv = {}

    file_path.write_text(json.dumps(kv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[+] Đã chuyển đổi {file_path}: {len(kv)} mục")

def main():
    root = Path(__file__).resolve().parent.parent
    dict_dir = root / "resources" / "dictionaries"
    
    migrate_file(dict_dir / "character_dict.json", is_character=True)
    migrate_file(dict_dir / "common_dict.json", is_character=False)
    
    hanviet_path = dict_dir / "hanviet_dict.json"
    if hanviet_path.exists():
        migrate_file(hanviet_path, is_character=False)
    else:
        hanviet_path.write_text("{}\n", encoding="utf-8")

if __name__ == "__main__":
    main()
