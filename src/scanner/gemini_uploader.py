import time
from pathlib import Path
from typing import Callable, Optional

try:
    from playwright.sync_api import (
        sync_playwright,
        BrowserContext,
        Page,
        TimeoutError as PlaywrightTimeoutError,
    )
except ImportError:
    sync_playwright = None
    BrowserContext = None
    Page = None
    PlaywrightTimeoutError = Exception

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

        if (
            (runtime_profiles / "chrome_data_1" / "Default").exists()
            and str(p) in (
                "chrome_profiles",
                "runtime/chrome_profiles",
                r"runtime\chrome_profiles",
                ".",
            )
        ):
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
    RESPONSE_TEXT_LOCATOR = ".model-response-text"

    # Selector nút gửi
    SEND_BUTTON_SELECTORS = [
        'button[aria-label*="gửi tin nhắn" i]',
        'button[aria-label*="send message" i]',
        'button[aria-label*="gửi" i]:not([aria-label*="phản hồi"])',
        'button[aria-label*="send" i]:not([aria-label*="feedback"])',
        '[data-testid="send-button"]',
        'button[data-test-id="send-button"]',
        'button.send-button',
    ]

    # Các selector có thể dùng để mở chức năng upload/đính kèm.
    # Gemini có thể thay đổi aria-label theo ngôn ngữ/giao diện.
    UPLOAD_BUTTON_SELECTORS = [
        'button[aria-label*="tải tệp" i]',
        'button[aria-label*="tải file" i]',
        'button[aria-label*="mở menu tải tệp" i]',
        'button[aria-label*="mở menu tải" i]',
        'button[aria-label*="thêm tệp" i]',
        'button[aria-label*="đính kèm" i]',
        'button[aria-label*="upload file" i]',
        'button[aria-label*="upload files" i]',
        'button[aria-label*="open upload" i]',
        'button[aria-label*="attach file" i]',
        'button[aria-label*="attach files" i]',
        'button[aria-label*="attach" i]',
        'button[aria-label*="add files" i]',
        'button[aria-label*="add file" i]',
        '[data-testid*="upload" i]',
        '[data-testid*="attach" i]',
        '[data-test-id*="upload" i]',
        '[data-test-id*="attach" i]',
        'button[mattooltip*="tệp" i]',
        'button[mattooltip*="file" i]',
        'button[mattooltip*="upload" i]',
    ]

    # Sau khi bấm nút +/Upload, Gemini có thể hiện menu.
    UPLOAD_MENU_SELECTORS = [
        'button:has-text("Tải tệp lên")',
        'button:has-text("Tải file lên")',
        'button:has-text("Upload files")',
        'button:has-text("Upload file")',
        'button:has-text("Attach files")',
        'button:has-text("Từ thiết bị")',
        'button:has-text("Từ máy tính")',
        '[role="menuitem"]:has-text("Tải tệp lên")',
        '[role="menuitem"]:has-text("Tải file lên")',
        '[role="menuitem"]:has-text("Upload files")',
        '[role="menuitem"]:has-text("Upload file")',
        '[role="menuitem"]:has-text("Attach files")',
        '[role="menuitem"]:has-text("Từ thiết bị")',
        '[role="menuitem"]:has-text("Từ máy tính")',
    ]

    NEW_CHAT_SELECTORS = [
        'button[aria-label*="cuộc trò chuyện mới" i]',
        'button[aria-label*="trò chuyện mới" i]',
        'button[aria-label*="new chat" i]',
        'a[aria-label*="cuộc trò chuyện mới" i]',
        'a[aria-label*="trò chuyện mới" i]',
        'a[aria-label*="new chat" i]',
        '[data-test-id="new-chat-button"]',
        '[data-test-id="chat-history-new-chat-button"]',
        'button:has-text("Cuộc trò chuyện mới")',
        'button:has-text("Trò chuyện mới")',
        'button:has-text("New chat")',
        'a[href="/app"]',
    ]

    def __init__(
        self,
        profile_dir: Path | str,
        log_cb: Callable = print,
        headless: bool = False,
    ):
        self.profile_dir = resolve_profile_path(profile_dir)
        self.log_cb = log_cb
        self.headless = headless

        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.json_extractor = JSONExtractor()

    # ------------------------------------------------------------------
    # START
    # ------------------------------------------------------------------

    def start(self):
        if sync_playwright is None:
            raise RuntimeError(
                "Thư viện 'playwright' chưa được cài đặt trong môi trường Python hiện tại.\n"
                "👉 Vui lòng kích hoạt môi trường ảo (venv):\n"
                "    .\\venv\\Scripts\\activate\n"
                "Hoặc cài đặt:\n"
                "    pip install playwright\n"
                "    playwright install chromium"
            )

        self.log_cb(
            f"[*] Khởi động Google Chrome với Profile: {self.profile_dir}..."
        )

        self.playwright = sync_playwright().start()

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir.resolve()),
            headless=self.headless,
            channel="chrome",
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        # Persistent context có thể đã có page.
        # Ưu tiên dùng page hiện có thay vì tạo tab mới không cần thiết.
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = self.context.new_page()

        self.log_cb(
            "[*] Đang truy cập https://gemini.google.com/app..."
        )

        self.page.goto(
            "https://gemini.google.com/app",
            timeout=60000,
            wait_until="domcontentloaded",
        )

        try:
            self.page.wait_for_load_state(
                "load",
                timeout=30000,
            )
        except Exception:
            pass

        time.sleep(3)

        self.log_cb("[+] Kết nối tới Gemini Web thành công!")

    # ------------------------------------------------------------------
    # HELPER
    # ------------------------------------------------------------------

    def _visible_enabled(self, locator) -> bool:
        try:
            return locator.is_visible() and locator.is_enabled()
        except Exception:
            return False

    def _click_first_matching(self, selectors, timeout: int = 1500) -> bool:
        if not self.page:
            return False

        for selector in selectors:
            try:
                elements = self.page.locator(selector).all()

                for element in elements:
                    if not self._visible_enabled(element):
                        continue

                    try:
                        element.click(timeout=timeout)
                        return True
                    except Exception:
                        continue

            except Exception:
                continue

        return False

    # ------------------------------------------------------------------
    # UPLOAD FILE
    # ------------------------------------------------------------------

    def upload_file(
        self,
        file_path: Path | str,
        timeout: int = 30000,
    ) -> bool:
        """
        Upload file trực tiếp lên Gemini.

        Ưu tiên:
        1. input[type=file] nếu Gemini đã tạo sẵn input trong DOM.
        2. File chooser nếu nút Upload/Attach kích hoạt FileChooser trực tiếp.
        3. Mở menu Upload rồi bắt FileChooser từ mục "Tải tệp lên".
        4. input[type=file] xuất hiện sau khi mở menu.

        Hàm này tuyệt đối KHÔNG đọc nội dung file và KHÔNG copy/paste nội dung file
        vào ô chat.
        """

        if not self.page:
            raise RuntimeError(
                "Trình duyệt chưa được khởi động. Hãy gọi start() trước!"
            )

        file_path = Path(file_path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Đường dẫn không phải file: {file_path}"
            )

        self.log_cb(
            f"[*] Chuẩn bị upload file: {file_path.name}"
        )

        # --------------------------------------------------------------
        # Cách 1: input[type=file] đã tồn tại trong DOM
        # --------------------------------------------------------------

        try:
            file_inputs = self.page.locator(
                'input[type="file"]'
            )

            count = file_inputs.count()

            if count > 0:
                for index in range(count):
                    try:
                        file_input = file_inputs.nth(index)

                        file_input.set_input_files(
                            str(file_path),
                            timeout=5000,
                        )

                        self.log_cb(
                            f"[+] Đã upload file trực tiếp: {file_path.name}"
                        )

                        time.sleep(2)
                        return True

                    except Exception:
                        continue

        except Exception:
            pass

        # --------------------------------------------------------------
        # Cách 2 & 3: Thử tương tác qua nút Upload/Attach (+)
        # Khi click nút Upload, Gemini có thể:
        # a) Mở FileChooser trực tiếp
        # b) Mở dropdown menu chứa tùy chọn "Tải tệp lên"
        # c) Chèn input[type=file] vào DOM
        # --------------------------------------------------------------

        for selector in self.UPLOAD_BUTTON_SELECTORS:
            try:
                elements = self.page.locator(selector).all()

                for element in elements:
                    if not self._visible_enabled(element):
                        continue

                    # 2a. Thử xem click nút có kích hoạt FileChooser trực tiếp không
                    try:
                        with self.page.expect_file_chooser(
                            timeout=2000
                        ) as fc_info:
                            element.click(timeout=1500)

                        file_chooser = fc_info.value

                        file_chooser.set_files(
                            str(file_path),
                            timeout=timeout,
                        )

                        self.log_cb(
                            f"[+] Đã upload file qua FileChooser: {file_path.name}"
                        )

                        time.sleep(2)
                        return True

                    except Exception:
                        pass

                    # 2b. Nếu không mở FileChooser trực tiếp, có thể nút đã mở menu dropdown.
                    # Kiểm tra xem menu item có xuất hiện không
                    time.sleep(0.5)
                    for menu_sel in self.UPLOAD_MENU_SELECTORS:
                        try:
                            menu_items = self.page.locator(menu_sel).all()

                            for item in menu_items:
                                if not self._visible_enabled(item):
                                    continue

                                try:
                                    with self.page.expect_file_chooser(
                                        timeout=3000
                                    ) as fc_info:
                                        item.click(timeout=1500)

                                    file_chooser = fc_info.value

                                    file_chooser.set_files(
                                        str(file_path),
                                        timeout=timeout,
                                    )

                                    self.log_cb(
                                        f"[+] Đã upload file qua menu Upload: {file_path.name}"
                                    )

                                    time.sleep(2)
                                    return True

                                except Exception:
                                    continue

                        except Exception:
                            continue

                    # 2c. Kiểm tra xem input[type=file] có vừa xuất hiện trong DOM sau khi click không
                    try:
                        file_inputs = self.page.locator('input[type="file"]')
                        if file_inputs.count() > 0:
                            for idx in range(file_inputs.count()):
                                try:
                                    file_inputs.nth(idx).set_input_files(
                                        str(file_path),
                                        timeout=5000,
                                    )
                                    self.log_cb(
                                        f"[+] Đã upload file qua input vừa mở: {file_path.name}"
                                    )
                                    time.sleep(2)
                                    return True
                                except Exception:
                                    continue
                    except Exception:
                        pass

            except Exception:
                continue

        # --------------------------------------------------------------
        # Không upload được
        # --------------------------------------------------------------

        self.log_cb(
            "[-] Không thể upload file."
        )

        self.log_cb(
            "[!] Không tìm thấy input[type=file] hoặc nút Upload/Attach "
            "phù hợp trên giao diện Gemini hiện tại."
        )

        return False

    # ------------------------------------------------------------------
    # SEND FILE AND EXTRACT
    # ------------------------------------------------------------------

    def send_file_and_extract(
        self,
        file_path: Path | str,
        max_wait: int = 150,
    ) -> list[dict]:
        """
        Upload nguyên file lên Gemini rồi gửi.

        File phải tự chứa prompt/instruction.

        Không:
        - đọc toàn bộ file vào RAM dưới dạng text;
        - copy/paste nội dung file;
        - gọi chat_box.fill();
        - truyền biến prompt;
        - ghi log nội dung file vào log_cb.

        Chỉ:
        file -> upload -> Send -> chờ response -> extract JSON.
        """

        if not self.page:
            raise RuntimeError(
                "Trình duyệt chưa được khởi động. Hãy gọi start() trước!"
            )

        file_path = Path(file_path).resolve()

        if not file_path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Đường dẫn không phải file: {file_path}"
            )

        self.log_cb(
            f"[*] Bắt đầu xử lý file: {file_path.name}"
        )

        # Đếm response trước khi gửi.
        initial_count = self.page.locator(
            self.RESPONSE_TEXT_LOCATOR
        ).count()

        # --------------------------------------------------------------
        # 1. Upload file trực tiếp (không copy/paste)
        # --------------------------------------------------------------

        uploaded = self.upload_file(file_path)

        if not uploaded:
            raise RuntimeError(
                f"Không thể upload file lên Gemini: {file_path.name}"
            )

        # --------------------------------------------------------------
        # 2. KHÔNG chat_box.fill()
        #
        # File đã chứa prompt nên không nhập thêm nội dung.
        # --------------------------------------------------------------

        self.log_cb(
            f"[+] File {file_path.name} đã được đính kèm vào khung chat."
        )

        # Chờ Gemini hoàn tất việc hiển thị file đính kèm.
        time.sleep(2)

        # --------------------------------------------------------------
        # 3. Chờ nút Send sẵn sàng và click gửi
        # --------------------------------------------------------------

        clicked_send = False
        start_send_wait = time.time()

        while time.time() - start_send_wait < 15:
            for selector in self.SEND_BUTTON_SELECTORS:
                try:
                    elements = self.page.locator(selector).all()

                    for element in elements:
                        if not self._visible_enabled(element):
                            continue

                        try:
                            element.click(timeout=2000)
                            clicked_send = True
                            break

                        except Exception:
                            continue

                    if clicked_send:
                        break

                except Exception:
                    continue

            if clicked_send:
                break

            time.sleep(1)

        # Fallback:
        # Nếu không tìm được selector Send, thử Enter.
        if not clicked_send:
            self.log_cb(
                "[!] Không tìm thấy nút Send bằng selector. "
                "Thử nhấn Enter..."
            )

            try:
                chat_box = self.page.locator(self.CHAT_BOX_LOCATOR).first
                if chat_box.is_visible():
                    chat_box.focus()
                self.page.keyboard.press("Enter")
                clicked_send = True
            except Exception:
                clicked_send = False

        if not clicked_send:
            raise RuntimeError(
                f"Đã upload file {file_path.name} nhưng không thể bấm nút Send."
            )

        self.log_cb(
            f"🚀 Đã gửi file {file_path.name} lên Gemini."
        )

        # --------------------------------------------------------------
        # 4. Chờ Gemini phản hồi
        # --------------------------------------------------------------

        start_time = time.time()

        previous_text = ""
        stable_count = 0
        response_received = False

        while time.time() - start_time < max_wait:

            time.sleep(2)

            try:
                current_count = self.page.locator(
                    self.RESPONSE_TEXT_LOCATOR
                ).count()
            except Exception:
                continue

            if current_count <= initial_count:
                continue

            response_received = True

            try:
                responses = self.page.locator(
                    self.RESPONSE_TEXT_LOCATOR
                ).all_inner_texts()
            except Exception:
                continue

            if not responses:
                continue

            current_text = responses[-1].strip()

            # Response đang tiếp tục được sinh.
            if current_text != previous_text:
                previous_text = current_text
                stable_count = 0
                continue

            # Response không thay đổi.
            if len(current_text) > 20:
                stable_count += 1

                # 3 lần liên tiếp không thay đổi
                # => coi như Gemini đã hoàn tất.
                if stable_count >= 3:
                    self.log_cb(
                        "✓ Gemini đã hoàn tất phản hồi!"
                    )
                    break

        # --------------------------------------------------------------
        # 5. Lấy response cuối cùng
        # --------------------------------------------------------------

        try:
            responses = self.page.locator(
                self.RESPONSE_TEXT_LOCATOR
            ).all_inner_texts()
        except Exception:
            responses = []

        raw_output = responses[-1] if responses else ""

        if not response_received:
            self.log_cb(
                f"[!] Hết thời gian chờ nhưng chưa phát hiện response mới cho {file_path.name}."
            )

        if not raw_output.strip():
            self.log_cb(
                f"[!] Gemini không trả về nội dung cho {file_path.name}."
            )
            return []

        # --------------------------------------------------------------
        # 6. Extract JSON
        # --------------------------------------------------------------

        extracted = self.json_extractor.extract_json(
            raw_output
        )

        return extracted

    # ------------------------------------------------------------------
    # TƯƠNG THÍCH NGƯỢC & HỖ TRỢ ĐA DẠNG THAM SỐ
    # ------------------------------------------------------------------

    def send_and_extract(
        self,
        file_path: Path | str,
        max_wait: int = 150,
    ) -> list[dict]:
        """
        Gửi file lên Gemini và trích xuất JSON.
        Nhận file_path (Path hoặc chuỗi đường dẫn).
        Nếu nhận chuỗi nội dung văn bản (legacy), tự động lưu ra file tạm để upload,
        tuyệt đối KHÔNG paste nội dung vào khung chat gây tràn bộ nhớ/lỗi trang.
        """
        if isinstance(file_path, Path):
            return self.send_file_and_extract(file_path, max_wait=max_wait)

        if isinstance(file_path, str):
            try:
                p = Path(file_path)
                if p.is_file():
                    return self.send_file_and_extract(p, max_wait=max_wait)
            except Exception:
                pass

            # Chuỗi nội dung thô (raw content) -> Lưu ra file tạm rồi upload file
            temp_dir = Path("runtime") / "temp_uploads"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_file = temp_dir / f"upload_{int(time.time() * 1000)}.md"
            try:
                temp_file.write_text(file_path, encoding="utf-8")
                return self.send_file_and_extract(temp_file, max_wait=max_wait)
            finally:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception:
                    pass

        return self.send_file_and_extract(Path(file_path), max_wait=max_wait)

    # ------------------------------------------------------------------
    # NEW CHAT
    # ------------------------------------------------------------------

    def new_chat(self, timeout: int = 15000) -> bool:
        """Khởi tạo đoạn chat mới trên Gemini Web mà không tắt trình duyệt."""

        if not self.page:
            self.log_cb(
                "[-] Cảnh báo: Trình duyệt chưa sẵn sàng!"
            )
            return False

        self.log_cb(
            "[*] Đang tạo đoạn chat mới trên Gemini..."
        )

        clicked_new_chat = False

        # 1. Thử click selector nút New Chat
        for selector in self.NEW_CHAT_SELECTORS:
            try:
                elements = self.page.locator(selector).all()

                for element in elements:
                    if not self._visible_enabled(element):
                        continue

                    try:
                        element.click(timeout=1500)
                        clicked_new_chat = True
                        break
                    except Exception:
                        continue

                if clicked_new_chat:
                    break

            except Exception:
                continue

        # 2. Nếu không click được nút, điều hướng URL.
        if not clicked_new_chat:
            try:
                self.log_cb(
                    "[*] Điều hướng tới "
                    "https://gemini.google.com/app "
                    "để mở chat mới..."
                )

                self.page.goto(
                    "https://gemini.google.com/app",
                    wait_until="domcontentloaded",
                    timeout=timeout,
                )

            except Exception as e:
                self.log_cb(
                    f"[-] Cảnh báo khi điều hướng: {e}"
                )

        # 3. Chờ khung chat sẵn sàng.
        try:
            chat_box = self.page.locator(
                self.CHAT_BOX_LOCATOR
            ).first

            chat_box.wait_for(
                state="visible",
                timeout=timeout,
            )

            time.sleep(1)

            self.log_cb(
                "[+] Đã chuyển sang đoạn chat mới thành công!"
            )

            return True

        except Exception as e:
            self.log_cb(
                f"[-] Cảnh báo khi chờ khung chat mới: {e}"
            )

            return False

    # ------------------------------------------------------------------
    # CLOSE
    # ------------------------------------------------------------------

    def close(self):
        try:
            if self.context:
                self.context.close()

            if self.playwright:
                self.playwright.stop()

            self.log_cb(
                "[*] Đã đóng trình duyệt Playwright an toàn."
            )

        except Exception:
            pass
