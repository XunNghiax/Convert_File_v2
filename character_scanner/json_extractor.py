import json
import re

class JSONExtractor:
    def extract_json(self, text: str) -> list[dict]:
        if not text:
            return []

        # 1. Thử tìm khối code block ```json ... ``` hoặc ``` ... ```
        code_blocks = re.findall(r'```(?:json)?\s*\n(.*?)\n\s*```', text, re.DOTALL | re.IGNORECASE)
        for block in code_blocks:
            clean = block.strip()
            try:
                parsed = json.loads(clean)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass

        # 2. Fallback: Tìm mảng JSON từ dấu '[' đầu tiên đến ']' cuối cùng
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = text[start_idx:end_idx + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass

        return []
