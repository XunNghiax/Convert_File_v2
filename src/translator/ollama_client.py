import json
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


class OllamaTranslatorClient:
    """
    Communicates with Ollama server running on Google Colab or local machine
    using standard library urllib (zero external dependency).
    """

    SYSTEM_PROMPT = """Bạn là một dịch giả tiểu thuyết Trung - Việt chuyên nghiệp với hơn 10 năm kinh nghiệm.
Nhiệm vụ của bạn là dịch nguyên văn đoạn văn bản tiếng Trung (raw) sang tiếng Việt với tiêu chí:
1. Độ chính xác cao: Giữ đúng ngữ cảnh, danh xưng nhân vật, bối cảnh cốt truyện.
2. Văn phong tự nhiên, thuần Việt, mượt mà nhưng không tự ý thêm thắt hoặc cắt bớt nội dung.
3. Tên nhân vật, địa danh, chiêu thức, tên tổ chức: Ưu tiên phiên âm chuẩn Hán Việt, KHÔNG dịch thoát nghĩa đen ngô nghê.
4. Bắt buộc tuân thủ danh mục Glossary được cung cấp bên dưới (nếu có).

CẤU TRÚC KẾT QUẢ ĐẦU RA BẮT BUỘC:
=== BẢN DỊCH ===
(Toàn bộ nội dung chương dịch sang tiếng Việt)

=== TỪ ĐIỂN MỚI ===
(Danh sách các danh từ riêng, nhân vật, địa danh Hán Việt xuất hiện trong đoạn mà bạn đã định danh chuẩn xác, định dạng mỗi dòng:
- [chữ Hán] => [Hán Việt chuẩn] (Loại: Nhân vật/Địa danh/Thuật ngữ)
Nếu không có từ mới đáng chú ý, để trống phần này)"""

    def __init__(
        self,
        base_url: str,
        model_name: str = "qwen2.5:7b-instruct",
        timeout: int = 180,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

    def check_health(self) -> bool:
        """Checks if Ollama server is reachable and active."""
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"User-Agent": "ConvertFileV2/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False

    def translate_chapter(self, chapter_text: str, glossary_prompt: str = "") -> str:
        """
        Sends chapter text to Ollama and returns the raw AI response.
        Retries up to max_retries on transient failure with backoff.
        """
        user_prompt = ""
        if glossary_prompt and glossary_prompt.strip():
            user_prompt += f"DANH MỤC GLOSSARY THAM KHẢO:\n{glossary_prompt.strip()}\n\n"
        user_prompt += f"VĂN BẢN TIẾNG TRUNG CẦN DỊCH:\n{chapter_text}"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192,
            },
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ConvertFileV2/1.0"
            },
            method="POST"
        )

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status == 200:
                        resp_bytes = resp.read()
                        data = json.loads(resp_bytes.decode("utf-8"))
                        return data.get("message", {}).get("content", "")
                    else:
                        last_err = RuntimeError(f"HTTP {resp.status}")
            except Exception as e:
                last_err = e

            if attempt < self.max_retries:
                time.sleep(2 * attempt)

        raise RuntimeError(f"Translation request failed after {self.max_retries} attempts: {last_err}")
