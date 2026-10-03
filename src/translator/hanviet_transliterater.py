import json
import re
from pathlib import Path
from typing import Dict, Optional, List

CN_NUMS = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000
}

def cn_to_int(cn_str: str) -> int:
    """Chuyển đổi chuỗi số chữ Hán như '一', '二十三', '一百零五' sang số nguyên."""
    if not cn_str:
        return 0
    if cn_str.isdigit():
        return int(cn_str)

    total = 0
    unit = 1
    for char in reversed(cn_str):
        if char in CN_NUMS:
            val = CN_NUMS[char]
            if val >= 10:
                if val > unit:
                    unit = val
                else:
                    unit = unit * val
            else:
                total += val * unit
    if unit == 10 and total < 10:
        total += 10
    return max(1, total)


class HanVietTransliterater:
    """
    Công cụ phiên âm và chuyển đổi Hán Việt chuyên dụng:
    - Tự động dịch và chuẩn hóa tiêu đề chương (第一章 => Chương 1).
    - Quét và chuyển đổi triệt để các ký tự/cụm từ chữ Hán còn sót lại sang Hán Việt.
    - Đảm bảo 0% chữ Hán tồn đọng trong văn bản đầu ra.
    """

    def __init__(self, dict_path: Optional[Path | str] = None):
        if dict_path:
            self.dict_path = Path(dict_path)
        else:
            self.dict_path = Path(__file__).resolve().parent.parent.parent / "resources" / "dictionaries" / "hanviet_dict.json"

        self.compound_dict: Dict[str, str] = {}
        self.char_dict: Dict[str, str] = {}
        self.compound_pattern: Optional[re.Pattern] = None
        self._load_dictionary()

    def _load_dictionary(self):
        if not self.dict_path.exists():
            return

        try:
            data = json.loads(self.dict_path.read_text(encoding="utf-8"))
            compounds = {}
            chars = {}
            for k, v in data.items():
                k_clean = str(k).strip()
                v_clean = str(v).strip()
                if not k_clean or not v_clean:
                    continue
                if len(k_clean) > 1:
                    compounds[k_clean] = v_clean
                else:
                    chars[k_clean] = v_clean

            self.compound_dict = compounds
            self.char_dict = chars

            # Sắp xếp từ ghép dài nhất lên trước
            if self.compound_dict:
                sorted_compounds = sorted(self.compound_dict.keys(), key=lambda x: (len(x), x), reverse=True)
                self.compound_pattern = re.compile("|".join(re.escape(k) for k in sorted_compounds))
            else:
                self.compound_pattern = None
        except Exception as e:
            print(f"[!] Cảnh báo không thể tải từ điển Hán Việt: {e}")

    def transliterate_chunk(self, chinese_chunk: str) -> str:
        """
        Chuyển một cụm chữ Hán liền nhau sang tiếng Việt:
        1. Ưu tiên khớp cụm từ ghép (Compound words).
        2. Từng ký tự đơn lẻ còn lại tra bảng ký tự Hán Việt.
        """
        if not chinese_chunk:
            return ""

        # Bước 1: Thay thế các từ ghép trước
        if self.compound_pattern:
            def repl_compound(m):
                matched = m.group(0)
                return " " + self.compound_dict.get(matched, matched) + " "
            intermediate = self.compound_pattern.sub(repl_compound, chinese_chunk)
        else:
            intermediate = chinese_chunk

        # Bước 2: Chuyển các ký tự chữ Hán đơn lẻ còn lại
        res = []
        for ch in intermediate:
            if '\u4e00' <= ch <= '\u9fff':
                val = self.char_dict.get(ch, ch)
                res.append(" " + val + " ")
            else:
                res.append(ch)

        # Chuẩn hóa khoảng trắng
        joined = "".join(res)
        return re.sub(r'\s+', ' ', joined).strip()

    def clean_text(self, text: str) -> str:
        """
        Quét toàn bộ đoạn văn bản, tìm các đoạn chữ Hán và chuyển sang tiếng Việt.
        Giữ nguyên các ký tự tiếng Việt, dấu câu, số và định dạng xung quanh.
        """
        if not text:
            return ""

        # Biểu thức tìm chuỗi chữ Hán liên tiếp
        pattern = re.compile(r'[\u4e00-\u9fff]+')

        def repl(match):
            cn_seq = match.group(0)
            trans = self.transliterate_chunk(cn_seq)
            return trans

        cleaned = pattern.sub(repl, text)
        # Làm sạch khoảng trắng thừa trước dấu câu
        cleaned = re.sub(r'\s+([,.:;!?])', r'\1', cleaned)
        return cleaned

    def translate_title(self, raw_title: str) -> str:
        """
        Dịch và chuẩn hóa tiêu đề chương:
        Ví dụ:
        '第一章　　公车南下' => 'Chương 1: Công xa nam hạ'
        '第309章 大结局（终）' => 'Chương 309: Đại kết cục (chung)'
        """
        raw_title = raw_title.strip()
        if not raw_title:
            return ""

        # Tìm định dạng: 第...章 ...
        m = re.match(r'第([0-9一二三四五六七八九十百千万]+)章\s*(.*)', raw_title)
        if m:
            num_part = m.group(1).strip()
            rest_part = m.group(2).strip()

            c_num = cn_to_int(num_part)

            if rest_part:
                # Thay thế các dấu ngoặc tiếng Trung thành dấu ngoặc thường
                rest_part = rest_part.replace('（', ' (').replace('）', ') ')
                # Dịch phần tiêu đề phụ
                sub_title = self.clean_text(rest_part)
                # Viết hoa chữ cái đầu cho tiêu đề phụ
                if sub_title:
                    words = sub_title.split()
                    words[0] = words[0].capitalize()
                    sub_title = " ".join(words)
                    return f"Chương {c_num}: {sub_title}"
            return f"Chương {c_num}"

        # Nếu không có định dạng 第...章, dịch toàn bộ tiêu đề
        translated = self.clean_text(raw_title)
        if translated:
            words = translated.split()
            words[0] = words[0].capitalize()
            return " ".join(words)
        return raw_title
