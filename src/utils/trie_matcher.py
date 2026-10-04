from typing import Dict, List, Tuple, Optional

class TrieNode:
    __slots__ = ('children', 'is_end', 'keyword', 'value')
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_end: bool = False
        self.keyword: str = ""
        self.value: str = ""

class TrieMatcher:
    """
    Bộ so khớp đa chuỗi hiệu năng cao dựa trên Trie (Longest-Match-First):
    - Độ phức tạp tìm kiếm: O(N) theo chiều dài chuỗi văn bản.
    - Không bị ảnh hưởng bởi kích thước từ điển (1.000 hay 50.000 từ tốc độ như nhau).
    - Thuần Python chuẩn, không phụ thuộc C compiler.
    """
    def __init__(self, mapping: Optional[Dict[str, str]] = None):
        self.root = TrieNode()
        self.longest_len: int = 0
        self.word_count: int = 0
        if mapping:
            for k, v in mapping.items():
                self.add_keyword(k, v)
            self.build()

    def add_keyword(self, keyword: str, value: str = ""):
        kw = keyword.strip()
        if not kw:
            return
        node = self.root
        for char in kw:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        if not node.is_end:
            self.word_count += 1
        node.is_end = True
        node.keyword = kw
        node.value = value if value else kw
        if len(kw) > self.longest_len:
            self.longest_len = len(kw)

    def build(self):
        # Có thể mở rộng failure links nếu triển khai đầy đủ Aho-Corasick
        pass

    def find_matches(self, text: str) -> List[Tuple[int, int, str, str]]:
        """
        Tìm tất cả các match trong chuỗi (ưu tiên Longest-Match-First tại mỗi vị trí).
        Trả về danh sách (start, end, keyword, value).
        """
        matches = []
        n = len(text)
        i = 0
        while i < n:
            curr = self.root
            longest_match = None
            j = i
            while j < n and text[j] in curr.children:
                curr = curr.children[text[j]]
                j += 1
                if curr.is_end:
                    longest_match = (i, j, curr.keyword, curr.value)
            
            if longest_match:
                matches.append(longest_match)
                i = longest_match[1]  # Nhảy qua phần đã khớp để tránh trùng lặp
            else:
                i += 1
        return matches

    def replace_all(self, text: str) -> str:
        """Thay thế tất cả các match trong text theo Longest-Match-First."""
        if not self.word_count or not text:
            return text
        matches = self.find_matches(text)
        if not matches:
            return text

        parts = []
        last_idx = 0
        for start, end, _, val in matches:
            parts.append(text[last_idx:start])
            parts.append(val)
            last_idx = end
        parts.append(text[last_idx:])
        return "".join(parts)
