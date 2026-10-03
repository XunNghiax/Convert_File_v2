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

    SYSTEM_PROMPT = """You are a master Chinese-to-Vietnamese literary translator with deep expertise in web novels.
Your ONLY mission is to translate the provided raw Chinese text into fluent, natural, expressive Vietnamese (Tiếng Việt).

STRICT MANDATORY RULES:
1. Every single sentence MUST be translated into Vietnamese. DO NOT leave Chinese sentences or paragraphs in the translation.
2. Character names, locations, and novel terms MUST be translated into standard Sino-Vietnamese (Hán Việt). For example: 龙剑飞 -> Long Kiếm Phi, 稷下村 -> Thôn Tắc Hạ, 炎河 -> Sông Viêm, 炎帝 -> Viêm Đế.
3. Keep the tone natural, vivid, and culturally appropriate for Vietnamese readers.
4. Strictly adhere to the reference glossary provided below.

OUTPUT FORMAT REQUIREMENTS:
=== BẢN DỊCH ===
(Full Vietnamese translation here)

=== TỪ ĐIỂN MỚI ===
(List newly identified character names, locations, and Sino-Vietnamese terms in this format:
- [Chinese] => [Vietnamese] (Type)
If none, leave this section empty)"""

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
        user_prompt = "Please translate the following Chinese novel chapter into natural, fluent Vietnamese (Tiếng Việt):\n\n"
        if glossary_prompt and glossary_prompt.strip():
            user_prompt += f"REFERENCE GLOSSARY:\n{glossary_prompt.strip()}\n\n"
        user_prompt += f"CHINESE TEXT TO TRANSLATE:\n{chapter_text}"

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
