import re

class BoundaryTrimmer:
    DEFAULT_TRAILING = {
        "hai", "người", "thân", "con", "của", "đích", "này", "kia", "đó",
        "đệ", "huynh", "tỷ", "muội", "thê", "mẫu", "phụ", "dì", "chú", "bác",
        "cô", "ông", "bà", "anh", "chị", "em", "cùng", "và", "với"
    }

    def __init__(self, trailing_stopwords: set[str]):
        self.trailing_stopwords = set(trailing_stopwords) | self.DEFAULT_TRAILING

    def trim(self, text: str) -> tuple[str, str]:
        words = text.strip().split()
        removed = []
        while len(words) > 1 and words[-1].lower() in self.trailing_stopwords:
            removed.insert(0, words.pop())
        return " ".join(words), " ".join(removed)

    def normalize_name(self, text: str) -> str:
        words = text.strip().split()
        return " ".join(w.capitalize() for w in words)
