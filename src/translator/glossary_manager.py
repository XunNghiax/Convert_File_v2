import json
import re
from pathlib import Path
from typing import Optional, Dict, Tuple


from src.translator.hanviet_transliterater import HanVietTransliterater


class GlossaryManager:
    """
    Manages translation dictionaries, prompt glossary injection,
    and automatic harvesting of new Sino-Vietnamese terms.
    """

    def __init__(
        self,
        base_dir: Optional[Path | str] = None,
        suggested_file: Optional[Path | str] = None,
    ):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(__file__).resolve().parent.parent.parent

        self.dict_dir = self.base_dir / "resources" / "dictionaries"
        if suggested_file:
            self.suggested_file = Path(suggested_file)
        else:
            self.suggested_file = self.base_dir / "samples" / "suggested_terms.json"

        self.character_dict: dict[str, str] = {}
        self.common_dict: dict[str, str] = {}
        self.deconvert_dict: dict[str, str] = {}
        self.chinese_names_dict: dict[str, str] = {}

        dict_path = self.dict_dir / "hanviet_dict.json"
        self.transliterater = HanVietTransliterater(dict_path=dict_path) if dict_path.exists() else None

    def _load_json_file(self, path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}

    def load_dictionaries(self) -> None:
        """Loads character_dict, common_dict, deconvert_dict, and chinese_names_dict from disk."""
        self.character_dict = self._load_json_file(self.dict_dir / "character_dict.json")
        self.common_dict = self._load_json_file(self.dict_dir / "common_dict.json")
        self.deconvert_dict = self._load_json_file(self.dict_dir / "deconvert_dict.json")
        self.chinese_names_dict = self._load_json_file(self.dict_dir / "chinese_names_dict.json")

    @staticmethod
    def is_pinyin_or_invalid(text: str) -> bool:
        """
        Detects if text contains Pinyin, foreign letters (w, j, z, f),
        or obvious non-Vietnamese phonetic patterns.
        """
        if not text or not text.strip():
            return True
        clean = text.strip()

        # 1. Letters that never appear in standard Vietnamese alphabet
        if re.search(r'[wjzf]', clean, re.IGNORECASE):
            return True

        # 2. 'q' not followed by 'u' (in Vietnamese q is always qu)
        if re.search(r'q(?!u)', clean, re.IGNORECASE):
            return True

        # 3. Known Pinyin syllables that may lack foreign consonants
        pinyin_syllables = {
            'yuxuan', 'xuan', 'liu', 'chen', 'sun', 'xue', 'chun', 'meng', 'de', 'yuan',
            'tang', 'shao', 'feng', 'dong', 'ling', 'xiang'
        }
        words = re.findall(r'[a-zA-ZÀ-ỹ]+', clean.lower())
        for w in words:
            if w in pinyin_syllables:
                return True

        return False

    def build_prompt_glossary(self, chapter_text: str) -> str:
        """
        Builds a concise glossary prompt section containing only terms
        that actually appear in the chapter text to save context window tokens.
        """
        matched_characters: dict[str, str] = {}
        matched_common: dict[str, str] = {}
        deconvert_notes: list[str] = []

        chapter_lower = chapter_text.lower()

        # Chinese names (Direct Chinese substring match)
        for k, v in self.chinese_names_dict.items():
            if k in chapter_text:
                matched_characters[k] = v

        # Characters
        for k, v in self.character_dict.items():
            if k in chapter_text or k.lower() in chapter_lower or v.lower() in chapter_lower:
                matched_characters[k] = v

        # Common terms
        for k, v in self.common_dict.items():
            if k in chapter_text or k.lower() in chapter_lower or v.lower() in chapter_lower:
                matched_common[k] = v

        # Deconvert notes / warnings
        for k, v in self.deconvert_dict.items():
            if k in chapter_text or k.lower() in chapter_lower or v.lower() in chapter_lower:
                deconvert_notes.append(
                    f"- '{k}' / '{v}': ĐÂY LÀ TÊN RIÊNG/TỪ ĐẶC BIỆT, DỊCH LÀ '{v}', TUYỆT ĐỐI KHÔNG dịch nghĩa đen thô thiển."
                )

        lines = []
        if matched_characters:
            lines.append("### Danh sách Nhân vật / Tên riêng (BẮT BUỘC DỊCH CHUẨN HÁN VIỆT):")
            for k, v in matched_characters.items():
                lines.append(f"- {k} => {v}")

        if matched_common:
            lines.append("### Danh sách Thuật ngữ / Địa danh:")
            for k, v in matched_common.items():
                lines.append(f"- {k} => {v}")

        if deconvert_notes:
            lines.append("### Quy tắc chống dịch sai tên riêng (De-convert Protection):")
            lines.extend(deconvert_notes)

        return "\n".join(lines)

    def parse_dual_output(self, ai_output: str) -> Tuple[str, dict[str, str]]:
        """
        Parses AI response containing dual output:
        === BẢN DỊCH ===
        ...
        === TỪ ĐIỂN MỚI ===
        - term => translation
        """
        translation = ai_output
        new_terms: dict[str, str] = {}

        dict_marker_pattern = re.compile(
            r'===\s*TỪ\s*ĐIỂN\s*MỚI\s*===', re.IGNORECASE
        )
        trans_marker_pattern = re.compile(
            r'===\s*BẢN\s*DỊCH\s*===', re.IGNORECASE
        )

        dict_split = dict_marker_pattern.split(ai_output, maxsplit=1)
        if len(dict_split) > 1:
            trans_part = dict_split[0]
            terms_part = dict_split[1]

            # Parse terms
            term_line_pattern = re.compile(
                r'^\s*[-*•]?\s*([^=\->:\n]+?)\s*(?:=>|->|:)\s*([^(\n\r]+?)(?:\s*\(.*?\))?\s*$',
                re.MULTILINE
            )
            for m in term_line_pattern.finditer(terms_part):
                chinese_term = m.group(1).strip().strip("[]")
                viet_meaning = m.group(2).strip()
                if chinese_term and viet_meaning:
                    new_terms[chinese_term] = viet_meaning
        else:
            trans_part = ai_output

        # Clean translation marker
        trans_split = trans_marker_pattern.split(trans_part, maxsplit=1)
        if len(trans_split) > 1:
            translation = trans_split[1].strip()
        else:
            translation = trans_split[0].strip()

        return translation, new_terms

    def integrate_new_terms(self, new_terms: dict[str, str]) -> None:
        """
        Saves discovered terms into suggested_terms.json and keeps
        in-memory cache updated for subsequent chapters.
        Sanitizes Pinyin terms and auto-corrects them via Han-Viet dictionary.
        """
        if not new_terms:
            return

        cleaned_terms: dict[str, str] = {}
        for cn_key, vn_val in new_terms.items():
            cn_key = cn_key.strip().strip("[]")
            vn_val = vn_val.strip()

            # Skip empty or trivially short non-Chinese keys
            if not cn_key or len(cn_key) < 2:
                continue

            if self.is_pinyin_or_invalid(vn_val):
                # Try auto-correcting via Han-Viet transliteration if possible
                if self.transliterater:
                    corrected = self.transliterater.transliterate_chunk(cn_key).title()
                    if corrected and not self.is_pinyin_or_invalid(corrected):
                        cleaned_terms[cn_key] = corrected
                        continue
                # If cannot auto-correct or transliterater not available, reject pinyin
                continue

            cleaned_terms[cn_key] = vn_val

        if not cleaned_terms:
            return

        existing_data = self._load_json_file(self.suggested_file)
        existing_data.update(cleaned_terms)

        self.suggested_file.parent.mkdir(parents=True, exist_ok=True)
        self.suggested_file.write_text(
            json.dumps(existing_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # Update in-memory common dict for the session
        self.common_dict.update(cleaned_terms)
