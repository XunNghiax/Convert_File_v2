import re
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Chapter:
    index: int
    title: str
    content: str
    char_count: int

class ChapterSplitter:
    CHAPTER_PATTERN = re.compile(
        r'^\s*(?:第\s*[0-9一二三四五六七八九十百千万]+\s*[章卷回节]|===|\d+[\.\s]+).*$',
        re.MULTILINE
    )

    def split_text(self, text: str, max_chars: int = 4000) -> list[Chapter]:
        matches = list(self.CHAPTER_PATTERN.finditer(text))
        raw_chapters = []

        if not matches:
            # Fallback nếu file không có header chương rõ ràng
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]
            cur_chunk, cur_len, idx = [], 0, 1
            for p in paras:
                if cur_len + len(p) > max_chars and cur_chunk:
                    raw_chapters.append((f"Phần {idx}", "\n\n".join(cur_chunk)))
                    idx += 1
                    cur_chunk, cur_len = [p], len(p)
                else:
                    cur_chunk.append(p)
                    cur_len += len(p)
            if cur_chunk:
                raw_chapters.append((f"Phần {idx}", "\n\n".join(cur_chunk)))
        else:
            for i, m in enumerate(matches):
                title = m.group(0).strip()
                start_pos = m.end()
                end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start_pos:end_pos].strip()
                if content:
                    raw_chapters.append((title, content))

        # Phân tách sub-chunk cho các chương dài
        final_chapters: list[Chapter] = []
        chap_idx = 1
        for title, body in raw_chapters:
            if len(body) <= max_chars:
                final_chapters.append(Chapter(
                    index=chap_idx,
                    title=title,
                    content=body,
                    char_count=len(body)
                ))
                chap_idx += 1
            else:
                paras = [p.strip() for p in body.split("\n\n") if p.strip()]
                sub_idx = 1
                cur_chunk, cur_len = [], 0
                for p in paras:
                    if cur_len + len(p) > max_chars and cur_chunk:
                        final_chapters.append(Chapter(
                            index=chap_idx,
                            title=f"{title} (Phần {sub_idx})",
                            content="\n\n".join(cur_chunk),
                            char_count=cur_len
                        ))
                        chap_idx += 1
                        sub_idx += 1
                        cur_chunk, cur_len = [p], len(p)
                    else:
                        cur_chunk.append(p)
                        cur_len += len(p)
                if cur_chunk:
                    final_chapters.append(Chapter(
                        index=chap_idx,
                        title=f"{title} (Phần {sub_idx})" if sub_idx > 1 else title,
                        content="\n\n".join(cur_chunk),
                        char_count=cur_len
                    ))
                    chap_idx += 1

        return final_chapters

    def split_file(self, filepath: Path, max_chars: int = 4000) -> list[Chapter]:
        text = Path(filepath).read_text(encoding="utf-8", errors="ignore")
        return self.split_text(text, max_chars=max_chars)
