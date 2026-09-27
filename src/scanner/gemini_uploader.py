import os
import time
from pathlib import Path
from typing import Callable, Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page
from .json_extractor import JSONExtractor

def resolve_profile_path(profile_path: Path | str) -> Path:
    p = Path(profile_path)
    if p.is_dir() and (p / "Default").exists():
        return p
    if (p / "chrome_data_1" / "Default").exists():
        return p / "chrome_data_1"
    
    # 1. Kiểm tra trong runtime/chrome_profiles
    runtime_profiles = Path("runtime") / "chrome_profiles"
    if runtime_profiles.exists():
        if (runtime_profiles / p.name / "Default").exists():
            return runtime_profiles / p.name
        if (runtime_profiles / "chrome_data_1" / "Default").exists() and (str(p) in ("chrome_profiles", "runtime/chrome_profiles", "runtime\\chrome_profiles", ".")):
            return runtime_profiles / "chrome_data_1"
        if (runtime_profiles / "chrome_data_1" / "Default").exists():
            return runtime_profiles / "chrome_data_1"

    # 2. Tương thích ngược với chrome_profiles ở thư mục gốc
    base_profiles = Path("chrome_profiles")
    if (base_profiles / str(profile_path) / "Default").exists():
        return base_profiles / str(profile_path)
    if (base_profiles / "chrome_data_1" / "Default").exists():
        return base_profiles / "chrome_data_1"
    return p

class GeminiUploader:
    CHAT_BOX_LOCATOR = 'div[contenteditable="true"]'
    RESPONSE_TEXT_LOCATOR = '.model-response-text'
    SEND_BUTTON_SELECTORS = [
        'button[aria-label*="gửi tin nhắn" i]',
        'button[aria-label*="send message" i]',
        'button[aria-label*="gửi" i]:not([aria-label*="phản hồi"])',
        'button[aria-label*="send" i]:not([aria-label*="feedback"])',
        '[data-testid="send-button"]',
        'button:has(svg):right-of(div[contenteditable="true"])'
    ]
    NEW_CHAT_SELECTORS = [
        'button[aria-label*="cuộc trò chuyện mới" i]',
        'button[aria-label*="new chat" i]',
        'a[aria-label*="cuộc trò chuyện mới" i]',
        'a[aria-label*="new chat" i]',
        'a[href="/app"]',
        'button:has-text("Cuộc trò chuyện mới")',
        'button:has-text("New chat")',
        '[data-test-id="new-chat-button"]'
    ]

    def __init__(self, profile_dir: Path | str, log_cb: Callable = print, headless: bool = False):
        self.profile_dir = resolve_profile_path(profile_dir)
        self.log_cb = log_cb
        self.headless = headless
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.json_extractor = JSONExtractor()

    def start(self):
        self.log_cb(f"[*] Khởi động Google Chrome với Profile: {self.profile_dir}...")
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir.resolve()),
            headless=self.headless,
            channel="chrome",
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
        )
        self.page = self.context.new_page()
        self.log_cb("[*] Đang truy cập https://gemini.google.com/app...")
        self.page.goto("https://gemini.google.com/app", timeout=60000)
        self.page.wait_for_load_state("load")
        time.sleep(3)
        self.log_cb("[+] Kết nối tới Gemini Web thành công!")

    def send_and_extract(self, text_payload: str, max_wait: int = 150) -> list[dict]:
        if not self.page:
            raise RuntimeError("Trình duyệt chưa được khởi động. Hãy gọi start() trước!")

        initial_count = self.page.locator(self.RESPONSE_TEXT_LOCATOR).count()
        chat_box = self.page.locator(self.CHAT_BOX_LOCATOR).first
        chat_box.wait_for(state="visible", timeout=10000)
        chat_box.click()
        time.sleep(0.5)

        # Fill text
        try:
            chat_box.fill(text_payload, timeout=15000)
        except Exception:
            self.page.evaluate("""
                ([el, text]) => {
                    el.innerText = text;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
            """, [chat_box.element_handle(), text_payload])
        time.sleep(1)

        # Gửi
        chat_box.focus()
        self.page.keyboard.press("Control+Enter")
        time.sleep(0.5)

        clicked_send = False
        for sel in self.SEND_BUTTON_SELECTORS:
            elements = self.page.locator(sel).all()
            for el in elements:
                if el.is_visible() and el.is_enabled():
                    try:
                        el.click(timeout=1500)
                        clicked_send = True
                        break
                    except Exception:
                        pass
            if clicked_send:
                break

        if not clicked_send:
            self.page.keyboard.press("Enter")

        self.log_cb("🚀 Đã gửi nội dung lên Gemini. Đang chờ phản hồi...")

        # Chờ phản hồi
        start_time = time.time()
        previous_text = ""
        stable_count = 0

        while time.time() - start_time < max_wait:
            time.sleep(2)
            current_count = self.page.locator(self.RESPONSE_TEXT_LOCATOR).count()
            if current_count > initial_count:
                responses = self.page.locator(self.RESPONSE_TEXT_LOCATOR).all_inner_texts()
                if responses:
                    current_text = responses[-1].strip()
                    if current_text == previous_text and len(current_text) > 20:
                        stable_count += 1
                        if stable_count >= 3:
                            self.log_cb("✓ Gemini đã hoàn tất phản hồi!")
                            break
                    else:
                        stable_count = 0
                        previous_text = current_text

        # Trích xuất
        responses = self.page.locator(self.RESPONSE_TEXT_LOCATOR).all_inner_texts()
        raw_output = responses[-1] if responses else ""
        extracted = self.json_extractor.extract_json(raw_output)
        return extracted

    def new_chat(self, timeout: int = 30000):
        """Khởi tạo đoạn chat mới trên giao diện Gemini Web."""
        if not self.page:
            raise RuntimeError("Trình duyệt chưa được khởi động. Hãy gọi start() trước!")

        self.log_cb("[*] Đang tạo đoạn chat mới trên Gemini...")
        clicked_new_chat = False
        for sel in self.NEW_CHAT_SELECTORS:
            try:
                elements = self.page.locator(sel).all()
                for el in elements:
                    if el.is_visible():
                        el.click(timeout=2000)
                        clicked_new_chat = True
                        break
                if clicked_new_chat:
                    break
            except Exception:
                pass

        if not clicked_new_chat:
            self.log_cb("[*] Điều hướng tới https://gemini.google.com/app để mở chat mới...")
            self.page.goto("https://gemini.google.com/app", timeout=timeout)
            self.page.wait_for_load_state("load")

        try:
            chat_box = self.page.locator(self.CHAT_BOX_LOCATOR).first
            chat_box.wait_for(state="visible", timeout=timeout)
            time.sleep(1.5)
            self.log_cb("[+] Đã chuyển sang đoạn chat mới thành công!")
        except Exception as e:
            self.log_cb(f"[-] Cảnh báo khi chờ khung chat mới: {e}")

    def close(self):
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
            self.log_cb("[*] Đã đóng trình duyệt Playwright an toàn.")
        except Exception:
            pass
