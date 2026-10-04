import re
from pathlib import Path

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

    EXPLICIT_NUMBERS = {
        "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín", "mười",
        "trăm", "ngàn", "nghìn", "vạn", "triệu"
    }

    PROTECTED_NAME_WORDS = {
        "tâm", "y", "lan", "phương", "ngọc", "đồng", "hoa", "quân",
        "hương", "sương", "thanh", "vận", "nhã", "di", "lâm", "thủy",
        "tử", "cảnh", "bạch", "trì", "nguyệt", "san", "hân", "ninh",
        "oánh", "tuyết", "du", "hải", "kiệt", "long", "an", "hưng",
        "dũng", "hạ", "văn", "cương", "đào", "huy", "nghĩa", "dương",
        "chấn", "dung", "vũ", "ương", "yến", "mai", "thảo", "khê",
        "quảng", "kỳ", "linh", "tân", "trúc", "quỳnh", "bình", "phúc",
        "lộc", "thọ", "khang", "minh", "đức", "thành", "cầm", "phi"
    }

    SINGLE_ACTION_VERBS = {
        "đi", "thở", "nói", "hỏi", "cười", "quát", "nghĩ", "nhìn", "bước",
        "chạy", "ngồi", "đứng", "ôm", "hôn", "đáp", "kêu", "hét", "lẩm",
        "bẩm", "gật", "lắc", "la", "nhăn", "nháy", "trừng", "liếc"
    }

    FALLBACK_SURNAMES = {
        "trương", "lâm", "trần", "lý", "vương", "triệu", "tiền", "tôn", "chu", "ngô",
        "trịnh", "phùng", "tô", "mã", "đường", "hứa", "hà", "lã", "mai", "tống",
        "tào", "nghiêm", "hoa", "kim", "ngụy", "đào", "khương", "tạ", "trâu", "dụ",
        "bách", "thủy", "đậu", "chương", "vân", "phan", "cát", "hề", "phạm", "bành",
        "lang", "lỗ", "vi", "xương", "miêu", "phượng", "phương", "du", "nhậm", "viên",
        "liễu", "khưu", "đặng", "bào", "tiêu", "đổng", "lương", "đỗ", "nguyễn", "bạch",
        "đoàn", "tịch", "thái", "hồ", "nhan", "cao", "lô", "ôn", "dương", "hoàng",
        "quách", "diệp", "tăng", "thẩm", "hàn", "dư", "cố", "vũ", "võ", "bùi",
        "đinh", "bàng", "khổng", "thôi", "khang", "doãn", "mao", "lục", "bảo", "cung",
        "viêm", "long", "hầu", "thi", "âu dương", "thượng quan", "quan", "tư mã",
        "gia cát", "hạ hầu", "đông phương", "độc cô", "nam cung", "chúc", "hác", "an",
        "nhạc", "tần", "vưu", "lữ", "thích", "phong", "sử", "phí", "liêm", "sầm",
        "tiết", "lôi", "hạ", "nghê", "thang", "đằng", "ân", "la", "tất", "vu",
        "mục", "khâu", "lạc", "điền", "phàn", "lăng", "hoắc", "ngu", "vạn", "chi",
        "kha", "mẫn", "quản", "mạc", "kinh", "phòng", "cầu", "giải", "ứng", "tông",
        "tuyên", "bôn", "úc", "đơn", "hàng", "hồng", "bao", "chư", "tả", "thạch",
        "nữu", "trình", "khê", "hình", "hoạt", "lam", "mân", "quý", "ma", "cường",
        "cổ", "dịch", "sa", "thổ", "thông", "cừu", "loan", "bạo", "mông", "đại",
        "nhạn", "tương", "lưu", "lê", "từ", "tưởng", "mạnh", "chung", "vệ", "văn",
        "phó", "kiều", "lại", "uông", "thân", "địch", "cảnh", "kỷ", "tề", "công tôn",
        "mộ dung", "hoàng phủ", "lệnh hồ", "vũ văn", "tư đồ", "tư không", "tây môn",
        "trưởng tôn", "uất trì", "bách lý", "liêu", "mặc", "ngả", "khuất", "trang",
        "nhiếp", "thiên diệp", "tây xuyên", "nạp lan", "ước"
    }

    @classmethod
    def _load_default_surnames(cls) -> set[str]:
        candidates = [
            Path("resources/filters/surnames.txt"),
            Path(__file__).resolve().parent.parent.parent / "resources" / "filters" / "surnames.txt",
        ]
        surnames = set()
        for p in candidates:
            if p.exists():
                try:
                    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                        line = line.strip().lower()
                        if line and not line.startswith("#"):
                            surnames.add(line)
                    if surnames:
                        return surnames
                except Exception:
                    pass
        return surnames or set(cls.FALLBACK_SURNAMES)

    def __init__(self, trailing_stopwords: set[str], surnames: set[str] | None = None):
        self.trailing_stopwords = set(trailing_stopwords) | self.DEFAULT_TRAILING
        if surnames is not None:
            self.surnames = set(surnames)
        else:
            self.surnames = self._load_default_surnames()

    def starts_with_surname(self, words: list[str]) -> bool:
        if not words:
            return False
        if len(words) >= 2:
            two_words = f"{words[0]} {words[1]}".lower()
            if two_words in self.surnames:
                return True
        return words[0].lower() in self.surnames

    def is_surname(self, word_or_phrase: str) -> bool:
        return word_or_phrase.lower() in self.surnames

    def is_compound_surname(self, words: list[str]) -> bool:
        if len(words) >= 2:
            return f"{words[0]} {words[1]}".lower() in self.surnames
        return False

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
                # If first word is "từ" or a valid surname, and phrase has 2-4 words:
                # do NOT strip unless second word is clearly a connector/preposition
                if (words[0].lower() == "từ" or self.starts_with_surname(words)) and 2 <= len(words) <= 4:
                    if words[1].lower() not in (self.DEFAULT_LEADING | self.INTERNAL_CONNECTORS | {"khi", "nơi", "lúc", "chỗ"}):
                        break
                s = " ".join(words[1:]).strip()
                changed = True
            elif len(words) >= 3 and words[1].lower() in self.INTERNAL_CONNECTORS:
                s = " ".join(words[2:]).strip()
                changed = True
        return s

    def trim(self, text: str) -> tuple[str, str]:
        s = self.trim_leading(text)
        words = s.strip().split()
        removed = []
        while len(words) > 1 and words[-1].lower() in self.trailing_stopwords:
            # Check if this phrase should be protected from having words[-1] trimmed
            # 1. Protected name words (e.g. tâm, y, lan, sương, di...)
            if len(words) <= 3 and words[-1].lower() in self.PROTECTED_NAME_WORDS:
                break

            # 2. Never strip 3rd word (or 4th word with compound surname) if phrase starts with a valid surname,
            #    unless it is an explicit number / counting word.
            is_valid_structure = False
            if len(words) == 3 and self.starts_with_surname(words):
                is_valid_structure = True
            elif len(words) == 4 and len(words) >= 2 and f"{words[0]} {words[1]}".lower() in self.surnames:
                is_valid_structure = True

            if is_valid_structure and words[-1].lower() not in self.EXPLICIT_NUMBERS:
                break

            removed.insert(0, words.pop())
        return " ".join(words), " ".join(removed)

    def normalize_name(self, text: str) -> str:
        words = text.strip().split()
        return " ".join(w.capitalize() for w in words)

    def trim_action_suffix(self, text: str) -> tuple[str, str]:
        words = text.strip().split()
        if len(words) < 3:
            return text.strip(), ""

        last_word_low = words[-1].lower()
        if last_word_low in self.PROTECTED_NAME_WORDS:
            return text.strip(), ""

        if last_word_low in self.SINGLE_ACTION_VERBS:
            # Trường hợp họ kép: độ dài tiêu chuẩn là 4 từ (2 họ + 2 tên).
            # Nếu có 5 từ trở lên và từ cuối là động từ hành động -> cắt.
            if self.is_compound_surname(words) and len(words) >= 5:
                removed = words.pop()
                return " ".join(words), removed
            # Trường hợp họ đơn: độ dài tiêu chuẩn là 3 từ (1 họ + 2 tên).
            # Nếu có 4 từ trở lên và từ cuối là động từ hành động -> cắt.
            elif not self.is_compound_surname(words) and self.starts_with_surname(words) and len(words) >= 4:
                removed = words.pop()
                return " ".join(words), removed

        return text.strip(), ""

    def trim_vn_compound_suffix(self, text: str, vn_2word_set: set[str]) -> tuple[str, str]:
        words = text.strip().split()
        if len(words) >= 4 and vn_2word_set:
            tail_compound = f"{words[-2]} {words[-1]}".lower()
            if tail_compound in vn_2word_set:
                remaining_words = words[:-2]
                if len(remaining_words) >= 2 and self.starts_with_surname(remaining_words):
                    return " ".join(remaining_words), tail_compound
        return text.strip(), ""

    def clean_candidate(self, text: str, vn_2word_set: set[str] | None = None) -> str:
        s, _ = self.trim(text)
        s, _ = self.trim_action_suffix(s)
        if vn_2word_set:
            s, _ = self.trim_vn_compound_suffix(s, vn_2word_set)
        return s
