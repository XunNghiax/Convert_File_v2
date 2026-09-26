import re

class BoundaryTrimmer:
    def __init__(self, trailing_stopwords: set[str]):
        self.trailing_stopwords = trailing_stopwords

    def trim(self, text: str) -> tuple[str, str]:
        words = text.strip().split()
        removed = []
        while len(words) > 1 and words[-1].lower() in self.trailing_stopwords:
            removed.insert(0, words.pop())
        return " ".join(words), " ".join(removed)

    def normalize_name(self, text: str) -> str:
        words = text.strip().split()
        return " ".join(w.capitalize() for w in words)
