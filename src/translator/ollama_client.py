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
1. BẮT BUỘC DỊCH 100% SANG TIẾNG VIỆT: Tuyệt đối không để sót bất kỳ chữ Hán nào trong bản dịch.
2. TÊN NHÂN VẬT & ĐỊA DANH: BẮT BUỘC phiên âm 100% theo âm HÁN VIỆT CHUẨN (Sino-Vietnamese).
   - Ví dụ chuẩn: 龙剑飞 -> Long Kiếm Phi, 梅玉萱 -> Mai Ngọc Huyên, 邱玉贞 -> Khâu Ngọc Trinh, 阿飞 -> A Phi, 杨玉雅 -> Dương Ngọc Nhã, 杨玉卿 -> Dương Ngọc Khanh, 孟德 -> Mạnh Đức, 谢国华 -> Tạ Quốc Hoa, 朱卫东 -> Chu Vệ Đông.
   - CHỮ "玉" trong tên riêng luôn là "NGỌC" (Ví dụ: 玉贞 -> Ngọc Trinh, 玉雅 -> Ngọc Nhã, 玉茹 -> Ngọc Như). TUYỆT ĐỐI KHÔNG dịch thành "Ý" hay "Úy".
3. TUYỆT ĐỐI CẤM SỬ DỤNG BÍNH ÂM (PINYIN) HOẶC TIẾNG ANH CHO TÊN RIÊNG:
   - CẤM các từ dạng: Mei Yuxuan, Qiu Yuzhen, A Fei, Yuzhen, Zhu Weidong, Sun Lina, Xue Liyi... Phải dùng Mai Ngọc Huyên, Khâu Ngọc Trinh, A Phi, Chu Vệ Đông, Tôn Lệ Na, Tiết Lệ Di.
4. NGỮ PHÁP TỰ NHIÊN: Cấu trúc tính từ + 的 + tên người (ví dụ: 美丽的玉贞) phải dịch xuôi theo ngữ pháp tiếng Việt: "Ngọc Trinh xinh đẹp" (hoặc "nàng Ngọc Trinh xinh đẹp"), TUYỆT ĐỐI KHÔNG dịch ngược kiểu máy móc "Xinh đẹp Yuzhen".
5. TUÂN THỦ TỪ ĐIỂN: Ưu tiên áp dụng triệt để danh sách từ điển tham khảo (REFERENCE GLOSSARY) được cung cấp bên dưới.

OUTPUT FORMAT REQUIREMENTS:
=== BẢN DỊCH ===
(Full Vietnamese translation here)

=== TỪ ĐIỂN MỚI ===
(List newly identified character names, locations, and Sino-Vietnamese terms in this format:
- [Chinese] => [Vietnamese] (Type)
Chỉ ghi từ có âm Hán Việt chuẩn, tuyệt đối không ghi từ Pinyin. Nếu không có từ mới, để trống phần này)"""

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

    def check_health(self, timeout: int = 25, retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Checks if Ollama server is reachable and active.
        Retries up to `retries` times to withstand transient proxy/DNS glitches.
        """
        for attempt in range(1, retries + 1):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/api/tags",
                    headers={"User-Agent": "ConvertFileV2/1.0"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass

            if attempt < retries:
                time.sleep(retry_delay)

        return False

    def translate_chapter(self, chapter_text: str, glossary_prompt: str = "") -> str:
        """
        Sends chapter text to Ollama and returns the raw AI response.
        Uses stream=True to prevent Cloudflare Tunnel 100s idle timeout.
        Retries up to max_retries on transient failure with exponential backoff.
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
            "stream": True,
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192,
                "num_predict": 4096,
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
                        chunks = []
                        # 1. Attempt streaming read line-by-line (NDJSON)
                        try:
                            for line in resp:
                                if isinstance(line, (bytes, bytearray)):
                                    line_str = line.decode("utf-8", errors="replace").strip()
                                else:
                                    line_str = str(line).strip()
                                if not line_str:
                                    continue
                                try:
                                    data = json.loads(line_str)
                                    content = data.get("message", {}).get("content", "")
                                    if content:
                                        chunks.append(content)
                                except json.JSONDecodeError:
                                    pass
                        except TypeError:
                            pass

                        # 2. Fallback if streaming iterator was not consumed or returned empty
                        if not chunks and hasattr(resp, "read"):
                            raw_content = resp.read()
                            if raw_content:
                                if isinstance(raw_content, (bytes, bytearray)):
                                    raw_str = raw_content.decode("utf-8", errors="replace")
                                else:
                                    raw_str = str(raw_content)
                                for line_str in raw_str.strip().splitlines():
                                    line_str = line_str.strip()
                                    if not line_str:
                                        continue
                                    try:
                                        data = json.loads(line_str)
                                        content = data.get("message", {}).get("content", "")
                                        if content:
                                            chunks.append(content)
                                    except json.JSONDecodeError:
                                        pass

                        if chunks:
                            return "".join(chunks)
                    else:
                        last_err = RuntimeError(f"HTTP {resp.status}")
            except Exception as e:
                last_err = e

            if attempt < self.max_retries:
                time.sleep(3 * attempt)

        raise RuntimeError(f"Translation request failed after {self.max_retries} attempts: {last_err}")
