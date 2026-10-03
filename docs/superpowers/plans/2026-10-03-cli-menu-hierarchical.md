# Kế Hoạch Triển Khai Menu Phân Cấp (Hierarchical CLI Menu) Cho `run_cli.py`

> **Dành cho Agent thực thi:** BẮT BUỘC SỬ DỤNG SUB-SKILL: Sử dụng `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans` để triển khai kế hoạch này theo từng task. Các bước sử dụng cú pháp checkbox (`- [ ]`) để theo dõi tiến độ.

**Mục tiêu:** Tái cấu trúc giao diện dòng lệnh `run_cli.py` từ menu phẳng 16 chức năng rối mắt sang mô hình **Menu Phân Cấp 2 Tầng** (1 Menu Cha điều hướng 6 Menu Con theo chuyên đề), giữ nguyên 100% logic và tham số hiện có.

**Kiến trúc:**
- **Menu Chính (`main_menu`):** Hiển thị thống kê từ điển và 6 Nhóm chức năng cha (`[1]` đến `[6]`, `[0]` Thoát).
- **Các Menu Con (`menu_*`):** Tách thành 6 hàm độc lập (`menu_ai_translation`, `menu_character_scanner`, `menu_hanviet_scanner`, `menu_dictionary_manager`, `menu_replace_engine`, `menu_system_tools`), mỗi menu con có banner riêng và tùy chọn `[0] Quay lại menu chính`.
- **Kiểm thử tự động (`tests/test_run_cli.py`):** Kiểm thử khả năng điều hướng, thoát và tính sẵn sàng của tất cả các hàm sub-menu bằng mock input.

**Công nghệ sử dụng:** Python 3.12, Pytest, Subprocess, Unittest Mock.

## Ràng buộc chung (Global Constraints)
- **Bảo toàn chức năng:** Không sửa đổi các lệnh subprocess hay đường dẫn file mặc định của các chức năng hiện có.
- **Hỗ trợ Windows UTF-8:** Giữ nguyên thiết lập `sys.stdout.reconfigure(encoding="utf-8")`.
- **Bắt phím an toàn:** Giữ khối `try...except KeyboardInterrupt` để người dùng bấm Ctrl+C luôn quay lại an toàn, không văng lỗi terminal.

---

### Task 1: Viết Unit Tests Cho Cấu Trúc Menu Mới (`tests/test_run_cli.py`)

**Files:**
- Create: `tests/test_run_cli.py`

**Interfaces:**
- Consumes: `run_cli.py`
- Produces: Test các hàm `menu_ai_translation`, `menu_character_scanner`, `menu_hanviet_scanner`, `menu_dictionary_manager`, `menu_replace_engine`, `menu_system_tools`, `main_menu`.

- [x] **Bước 1: Viết test cho các hàm Menu Con**
  Tạo `tests/test_run_cli.py`:
  ```python
  from unittest.mock import patch
  import run_cli

  def test_menu_functions_exist():
      assert hasattr(run_cli, "menu_ai_translation")
      assert hasattr(run_cli, "menu_character_scanner")
      assert hasattr(run_cli, "menu_hanviet_scanner")
      assert hasattr(run_cli, "menu_dictionary_manager")
      assert hasattr(run_cli, "menu_replace_engine")
      assert hasattr(run_cli, "menu_system_tools")
      assert hasattr(run_cli, "main_menu")

  def test_submenus_exit_on_zero():
      # Test khi người dùng nhập '0' thì menu con kết thúc và quay lại ngay
      with patch("builtins.input", return_value="0"), patch("run_cli.clear_screen"):
          run_cli.menu_ai_translation()
          run_cli.menu_character_scanner()
          run_cli.menu_hanviet_scanner()
          run_cli.menu_dictionary_manager()
          run_cli.menu_replace_engine()
          run_cli.menu_system_tools()

  def test_main_menu_exit_on_zero():
      with patch("builtins.input", return_value="0"), patch("run_cli.clear_screen"):
          run_cli.main_menu()
  ```

- [x] **Bước 2: Chạy test để xác nhận test chạy và FAIL (chưa có các hàm sub-menu)**
  Chạy: `pytest tests/test_run_cli.py`
  Kỳ vọng: FAIL vì chưa định nghĩa các hàm `menu_*`.

---

### Task 2: Triển khai 6 Hàm Menu Con Độc Lập Trong `run_cli.py`

**Files:**
- Modify: `run_cli.py`

**Interfaces:**
- Produces:
  - `print_sub_banner(title: str)`
  - `menu_ai_translation()`: Chứa chức năng Dịch raw bằng Ollama Colab và kiểm tra kết nối.
  - `menu_character_scanner()`: Chứa 5 chức năng quét nhân vật cũ (`[1], [2], [3], [4], [5]`).
  - `menu_hanviet_scanner()`: Chứa 4 chức năng quét Hán Việt cũ (`[10], [11], [12], [13]`).
  - `menu_dictionary_manager()`: Chứa các chức năng import & nhập từ điển cũ (`[6], [14], [7]` + nạp từ gợi ý).
  - `menu_replace_engine()`: Chứa chức năng replace bằng từ điển cũ (`[9]` + hậu kỳ de-convert).
  - `menu_system_tools()`: Chứa chức năng chạy Unit Tests (`[8]`).

- [x] **Bước 1: Cài đặt `print_sub_banner` và 6 hàm `menu_*`**
- [x] **Bước 2: Chạy test xác nhận Task 1 PASS một phần**
  Chạy: `pytest tests/test_run_cli.py`

---

### Task 3: Tái Cấu Trúc `main_menu()` Thành Menu Cha Điều Hướng

**Files:**
- Modify: `run_cli.py`

**Interfaces:**
- Chuyển `main_menu()` thành vòng lặp gọi 6 menu con:
  - `1`: `menu_ai_translation()`
  - `2`: `menu_character_scanner()`
  - `3`: `menu_hanviet_scanner()`
  - `4`: `menu_dictionary_manager()`
  - `5`: `menu_replace_engine()`
  - `6`: `menu_system_tools()`
  - `0`: Thoát chương trình

- [x] **Bước 1: Cập nhật `main_menu()`**
- [x] **Bước 2: Chạy test `tests/test_run_cli.py` xác nhận 100% PASS**
  Chạy: `pytest tests/test_run_cli.py`
- [x] **Bước 3: Commit code**
  `git add run_cli.py tests/test_run_cli.py`
  `git commit -m "feat(cli): refactor run_cli into clean 2-tier hierarchical sub-menus"`

---

### Task 4: Kiểm Thử Toàn Diện Hệ Thống (Regression Testing)

**Files:**
- Run: `pytest tests/`

- [x] **Bước 1: Chạy toàn bộ test suite**
  Chạy: `pytest tests/` (Tất cả 95+ tests phải PASS hoàn toàn).
- [x] **Bước 2: Chạy thử CLI và báo cáo cho người dùng**
