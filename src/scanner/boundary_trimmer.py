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
        "cao hứng", "an ủi", "an bài", "tò mò", "tưởng tượng", "hầu hạ",
        "là của ngài", "là của", "tự mình", "có thể", "nghe nói"
    ]

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
                s = " ".join(words[1:]).strip()
                changed = True
        return s

    def trim(self, text: str) -> tuple[str, str]:
        s = self.trim_leading(text)
        words = s.strip().split()
        removed = []
        while len(words) > 1 and words[-1].lower() in self.trailing_stopwords:
            removed.insert(0, words.pop())
        return " ".join(words), " ".join(removed)

    def normalize_name(self, text: str) -> str:
        words = text.strip().split()
        return " ".join(w.capitalize() for w in words)

