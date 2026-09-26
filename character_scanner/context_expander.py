import re

class ContextExpander:
    def __init__(self, min_length: int = 30):
        self.min_length = min_length
        self.sentence_regex = re.compile(r'[^.!?;\n]+[.!?;\n]*')

    def expand_context(self, line: str, match_start: int, match_end: int) -> str:
        line_clean = line.strip()
        if not line_clean:
            return ""

        matches = list(self.sentence_regex.finditer(line))
        if not matches:
            return line_clean

        target_idx = -1
        for i, m in enumerate(matches):
            if m.start() <= match_start and match_end <= m.end():
                target_idx = i
                break

        if target_idx == -1:
            return line_clean

        ctx = matches[target_idx].group(0).strip()
        if len(ctx) < self.min_length:
            prev_s = matches[target_idx - 1].group(0).strip() if target_idx > 0 else ""
            next_s = matches[target_idx + 1].group(0).strip() if target_idx + 1 < len(matches) else ""
            if prev_s and next_s:
                ctx = f"{prev_s} {ctx} {next_s}"
            elif prev_s:
                ctx = f"{prev_s} {ctx}"
            elif next_s:
                ctx = f"{ctx} {next_s}"

        return ctx.strip()
