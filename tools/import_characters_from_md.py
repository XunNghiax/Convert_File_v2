import json
import re
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.importer.dictionary_importer import load_dictionary, save_dictionary

sys.stdout.reconfigure(encoding="utf-8")

def main(dry_run: bool = True):
    md_path = PROJECT_ROOT / "samples" / "danh_sach_nhan_vat.md"
    dict_path = PROJECT_ROOT / "resources" / "dictionaries" / "character_dict.json"
    
    if not md_path.exists():
        print(f"[!] Error: {md_path} does not exist!")
        return
        
    char_dict = load_dictionary(dict_path)
    initial_count = len(char_dict)
    print(f"Loaded existing character_dict: {initial_count} entries.")
    
    md_text = md_path.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\[.*?\])\s*```", md_text, re.DOTALL)
    if not match:
        print("[!] Error: No JSON block found in markdown file!")
        return
        
    gold_data = json.loads(match.group(1))
    print(f"Loaded {len(gold_data)} entities from {md_path.name}.")
    
    already_present = []
    added_canonical = []
    updated_entries = []
    added_variants = []
    
    # 1. Process 91 canonical names
    for item in gold_data:
        name = item.get("ten_han_viet", "").strip()
        if not name:
            continue
        key = name.lower()
        if key in char_dict:
            existing_val = char_dict[key]
            if existing_val == name:
                already_present.append((key, name))
            else:
                updated_entries.append((key, existing_val, name))
                char_dict[key] = name
        else:
            added_canonical.append((key, name))
            char_dict[key] = name
            
    # 2. Process specific MT aliases / variants
    mt_aliases = {
        "mực đầu hạ": "Mặc Đầu Hạ",
        "máu tôn": "Huyết Tôn",
        "marvin quân": "Mã Văn Quân",
        "vân trăm sông": "Vân Bách Xuyên",
        "tô cũng khả": "Tô Diệc Khả",
        "văn liền tâm": "Văn Liên Tâm",
        "angelina rockefeller": "Angelina Rockefeller"
    }
    
    for k, v in mt_aliases.items():
        if k in char_dict:
            existing_val = char_dict[k]
            if existing_val != v:
                updated_entries.append((k, existing_val, v))
                char_dict[k] = v
            else:
                already_present.append((k, v))
        else:
            added_variants.append((k, v))
            char_dict[k] = v
            
    final_count = len(char_dict)
    
    print("\n--- IMPORT SUMMARY ---")
    print(f"Already present (unchanged): {len(already_present)}")
    print(f"Updated existing entries:   {len(updated_entries)}")
    for k, old_v, new_v in updated_entries:
        print(f"  * Updated '{k}': '{old_v}' -> '{new_v}'")
        
    print(f"Added canonical names:      {len(added_canonical)}")
    for k, v in added_canonical:
        print(f"  + Added '{k}': '{v}'")
        
    print(f"Added MT / name variants:   {len(added_variants)}")
    for k, v in added_variants:
        print(f"  + Added variant '{k}': '{v}'")
        
    print(f"\nDictionary size: {initial_count} -> {final_count} (+{final_count - initial_count} entries)")
    
    if not dry_run:
        saved = save_dictionary(char_dict, dict_path)
        if saved:
            print(f"[OK] Successfully saved updated character_dict to {dict_path}")
        else:
            print(f"[!] Error saving dictionary!")
    else:
        print("[INFO] DRY RUN ONLY - no changes written to disk.")

if __name__ == "__main__":
    is_dry = "--apply" not in sys.argv
    main(dry_run=is_dry)
