from pathlib import Path
import json

class ResourceLoader:
    def __init__(self, base_dir: Path | None = None):
        if base_dir is not None:
            self.base_dir = base_dir
        elif (Path(".") / "resources").exists():
            self.base_dir = Path(".")
        else:
            self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.single_surnames: set[str] = set()
        self.compound_surnames: set[str] = set()
        self.pronouns: set[str] = set()
        self.non_person: set[str] = set()
        self.trailing_stopwords: set[str] = set()
        self.blacklist: set[str] = set()
        self.common_dict: set[str] = set()
        self.known_characters: dict[str, str] = {}
        self.deconvert_dict: dict[str, str] = {}
        self.vn_2word_set: set[str] = set()

    def load_deconvert_dict(self, path: Path) -> dict[str, str]:
        mapping = {}
        if not path.exists():
            return mapping
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, dict):
                for k, v in data.items():
                    mapping[k.strip().lower()] = v.strip()
        except Exception:
            pass
        return mapping

    def load_surnames(self, path: Path) -> tuple[set[str], set[str]]:
        single, compound = set(), set()
        if not path.exists():
            return single, compound
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            if " " in line:
                compound.add(line)
            else:
                single.add(line)
        return single, compound

    def load_word_set(self, path: Path) -> set[str]:
        words = set()
        if not path.exists():
            return words
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            words.add(line)
        return words

    def load_common_dict(self, path: Path) -> set[str]:
        words = set()
        if not path.exists():
            return words
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, dict):
                for k in data.keys():
                    src = str(k).strip().lower()
                    if src:
                        words.add(src)
            elif isinstance(data, list):
                for item in data:
                    src = item.get("source", "").strip().lower()
                    if src:
                        words.add(src)
        except Exception:
            pass
        return words

    def load_character_dict(self, path: Path) -> dict[str, str]:
        chars = {}
        if not path.exists():
            return chars
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data, dict):
                for k, v in data.items():
                    src = str(k).strip().lower()
                    tgt = str(v).strip()
                    if src and tgt:
                        chars[src] = tgt
            elif isinstance(data, list):
                for item in data:
                    src = item.get("source", "").strip().lower()
                    tgt = item.get("target", "").strip()
                    if src and tgt:
                        chars[src] = tgt
        except Exception:
            pass
        return chars

    def load_vn_2word_set(self, path: Path) -> set[str]:
        words = set()
        if not path.exists():
            return words
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) == 2:
                        words.add(line)
        except Exception:
            pass
        return words

    def load_all(self):
        # 1. Tìm thư mục bộ lọc (filters)
        filters_dir = self.base_dir / "resources" / "filters"
        if not filters_dir.exists():
            filters_dir = self.base_dir / "filters"

        # 2. Tìm thư mục từ điển (dictionaries)
        data_dir = self.base_dir / "resources" / "dictionaries"
        if not data_dir.exists():
            data_dir = self.base_dir / "data"

        self.single_surnames, self.compound_surnames = self.load_surnames(filters_dir / "surnames.txt")
        self.pronouns = self.load_word_set(filters_dir / "pronouns.txt")
        self.non_person = self.load_word_set(filters_dir / "non_person.txt")
        self.trailing_stopwords = self.load_word_set(filters_dir / "trailing_stopwords.txt")
        self.blacklist = self.load_word_set(filters_dir / "blacklist.txt")
        self.common_dict = self.load_common_dict(data_dir / "common_dict.json")
        self.known_characters = self.load_character_dict(data_dir / "character_dict.json")
        chinese_names = self.load_character_dict(data_dir / "chinese_names_dict.json")
        self.known_characters.update(chinese_names)
        self.deconvert_dict = self.load_deconvert_dict(data_dir / "deconvert_dict.json")

        vn_words_path = data_dir / "vietnamese_words.txt"
        if not vn_words_path.exists():
            vn_words_path = self.base_dir / "resources" / "dictionaries" / "vietnamese_words.txt"
        self.vn_2word_set = self.load_vn_2word_set(vn_words_path)


