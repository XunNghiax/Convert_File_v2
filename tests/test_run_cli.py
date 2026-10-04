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


def test_menu_dictionary_manager_option_5_force_all():
    """Kiểm tra lựa chọn [5] trong menu_dictionary_manager gọi main importer với tham số --force-all."""
    # input sequence: "5" (chọn option 5), "" (file mặc định), "" (dict mặc định), "" (nhấn Enter để tiếp tục), "0" (quay lại)
    inputs = ["5", "", "", "", "0"]
    with patch("builtins.input", side_effect=inputs), \
         patch("run_cli.clear_screen"), \
         patch("run_cli.subprocess.run") as mock_run:
        run_cli.menu_dictionary_manager()
        assert mock_run.called
        cmd_args = mock_run.call_args[0][0]
        assert "--force-all" in cmd_args
        assert "--file" in cmd_args

