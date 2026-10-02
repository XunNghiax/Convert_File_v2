import re

class BoundaryTrimmer:
    DEFAULT_TRAILING = {
        "hai", "người", "thân", "con", "của", "đích", "này", "kia", "đó",
        "đệ", "huynh", "tỷ", "muội", "thê", "mẫu", "phụ", "dì", "chú", "bác",
        "cô", "ông", "bà", "anh", "chị", "em", "cùng", "và", "với"
    }

    DEFAULT_LEADING = {
        "thật", "rất", "lấy", "tự", "mình", "cùng", "và", "với", "cho",
        "cấp", "được", "bị", "đem", "khiến", "làm", "thấy", "nghe",
        "biết", "nghĩ", "bảo", "nói", "hỏi", "kêu", "hướng", "đối",
        "tại", "ở", "từ", "trên", "dưới", "trong", "ngoài", "một",
        "hai", "ba", "vị", "những", "các", "mọi", "mỗi", "là", "của", "ngài"
    }

    DEFAULT_LEADING_PHRASES = [
        "đối phương là", "đối phương", "người này là", "người này", "vị này là", "vị này",
        "chính mình", "người khác", "bản thân", "nhìn thấy", "trông thấy", "nghe thấy",
        "cao hứng", "an ủi", "an bài", "tò mò", "tưởng tượng", "hầu hạ",
        "là của ngài", "là của", "tự mình", "có thể", "nghe nói"
    ]

    INTERNAL_CONNECTORS = {
        "là", "của", "tại", "ở", "với", "cho", "cùng", "và", "bị", "được", "đem", "làm", "khiến"
    }

    def __init__(self, trailing_stopwords: set[str]):
        self.trailing_stopwords = set(trailing_stopwords) | self.DEFAULT_TRAILING

    def trim_leading(self, text: str) -> str:
        s = text.strip()
        changed = True
        while changed and s:
            changed = False
            s_lower = s.lower()
            for phrase in self.DEFAULT_LEADING_PHRASES:
                if s_lower.startswith(phrase + " "):
                    s = s[len(phrase):].strip()
                    changed = True
                    break
            words = s.split()
            if len(words) > 1 and words[0].lower() in self.DEFAULT_LEADING:
                if words[0].lower() == "từ" and len(words) <= 3 and words[1].lower() in self.PROTECTED_NAME_WORDS:
                    break
                s = " ".join(words[1:]).strip()
                changed = True
            elif len(words) >= 3 and words[1].lower() in self.INTERNAL_CONNECTORS:
                s = " ".join(words[2:]).strip()
                changed = True
        return s

    PROTECTED_NAME_WORDS = {
        "tâm", "y", "lan", "phương", "ngọc", "đồng", "hoa", "quân",
        "hương", "sương", "thanh", "vận", "nhã", "di", "lâm", "thủy",
        "tử", "cảnh", "bạch", "trì", "nguyệt", "san", "hân", "ninh",
        "oánh", "tuyết", "du", "hải", "kiệt", "long", "an", "hưng",
        "dũng", "hạ", "văn", "cương", "đào", "huy", "nghĩa", "dương",
        "chấn", "dung", "vũ", "ương", "yến", "mai", "thảo", "khê",
        "quảng", "kỳ"
    }

    def trim(self, text: str) -> tuple[str, str]:
        s = self.trim_leading(text)
        words = s.strip().split()
        removed = []
        while len(words) > 1 and words[-1].lower() in self.trailing_stopwords:
            if len(words) <= 3 and words[-1].lower() in self.PROTECTED_NAME_WORDS:
                break
            removed.insert(0, words.pop())
        return " ".join(words), " ".join(removed)


    def normalize_name(self, text: str) -> str:
        words = text.strip().split()
        return " ".join(w.capitalize() for w in words)

