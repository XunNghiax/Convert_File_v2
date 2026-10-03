from unittest.mock import patch
import run_cli


def test_menu_functions_exist():
    """Kiểm tra 6 hàm menu con và menu chính đã được định nghĩa đầy đủ."""
    assert hasattr(run_cli, "menu_ai_translation")
    assert hasattr(run_cli, "menu_character_scanner")
    assert hasattr(run_cli, "menu_hanviet_scanner")
    assert hasattr(run_cli, "menu_dictionary_manager")
    assert hasattr(run_cli, "menu_replace_engine")
    assert hasattr(run_cli, "menu_system_tools")
    assert hasattr(run_cli, "main_menu")


def test_submenus_exit_on_zero():
    """Kiểm tra khi nhập '0' thì mỗi menu con kết thúc và quay lại an toàn mà không lặp vô tận."""
    with patch("builtins.input", return_value="0"), patch("run_cli.clear_screen"):
        run_cli.menu_ai_translation()
        run_cli.menu_character_scanner()
        run_cli.menu_hanviet_scanner()
        run_cli.menu_dictionary_manager()
        run_cli.menu_replace_engine()
        run_cli.menu_system_tools()


def test_main_menu_exit_on_zero():
    """Kiểm tra khi nhập '0' ở main_menu thì chương trình thoát an toàn."""
    with patch("builtins.input", return_value="0"), patch("run_cli.clear_screen"):
        run_cli.main_menu()
