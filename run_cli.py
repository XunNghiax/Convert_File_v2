import sys
import os
import json
from pathlib import Path
import subprocess

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import (
        Progress, SpinnerColumn, BarColumn, TextColumn,
        TimeElapsedColumn, TimeRemainingColumn, MofNCompleteColumn,
        TaskProgressColumn
    )
    HAVE_RICH = True
    console = Console()
except ImportError:
    HAVE_RICH = False
    console = None

# Đảm bảo UTF-8 cho console Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def get_python_exe() -> str:
    """Trả về đường dẫn python thực thi, tự động ưu tiên venv của dự án nếu có."""
    if sys.platform.startswith("win"):
        venv_py = Path("venv/Scripts/python.exe")
    else:
        venv_py = Path("venv/bin/python")
    if venv_py.exists():
        return str(venv_py)
    return sys.executable

def get_data_stats():
    """Lấy số lượng mục hiện tại trong các file từ điển và kết quả."""
    char_path = Path("resources/dictionaries/character_dict.json")
    comm_path = Path("resources/dictionaries/common_dict.json")
    chinese_path = Path("resources/dictionaries/chinese_names_dict.json")
    hanviet_path = Path("resources/dictionaries/hanviet_dict.json")
    deconvert_path = Path("resources/dictionaries/deconvert_dict.json")
    import_path = Path("samples/import.json")
    import_hanviet_path = Path("samples/import_hanviet.json")
    suggested_path = Path("samples/suggested_terms.json")

    def _count_json(path):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return len(data) if isinstance(data, (dict, list)) else 0
            except Exception:
                return 0
        return None

    return {
        "character": _count_json(char_path) or 0,
        "common": _count_json(comm_path) or 0,
        "chinese_names": _count_json(chinese_path) or 0,
        "hanviet": _count_json(hanviet_path) or 0,
        "deconvert": _count_json(deconvert_path) or 0,
        "import_json": _count_json(import_path),
        "import_hanviet": _count_json(import_hanviet_path),
        "suggested_terms": _count_json(suggested_path)
    }

def print_banner():
    stats = get_data_stats()
    if HAVE_RICH and console:
        table = Table(box=None, padding=(0, 2), show_header=False)
        table.add_column("Key", style="bold cyan")
        table.add_column("Value", style="bold green")
        table.add_column("Desc", style="dim")

        table.add_row("• character_dict.json", f"{stats['character']:,} mục", "(Tên nhân vật)")
        table.add_row("• chinese_names_dict.json", f"{stats.get('chinese_names', 0):,} mục", "(Tên Hán Việt chuẩn)")
        table.add_row("• common_dict.json", f"{stats['common']:,} mục", "(Từ ngữ chung / Thành ngữ)")
        table.add_row("• hanviet_dict.json", f"{stats['hanviet']:,} mục", "(Từ điển Hán Việt)")
        if stats['deconvert'] > 0:
            table.add_row("• deconvert_dict.json", f"{stats['deconvert']:,} mục", "(Chống de-convert)")
        if stats['import_json'] is not None:
            table.add_row("• samples/import.json", f"{stats['import_json']:,} mục", "(Sẵn sàng nạp nhân vật)")
        if stats['import_hanviet'] is not None:
            table.add_row("• import_hanviet.json", f"{stats['import_hanviet']:,} mục", "(Sẵn sàng nạp Hán Việt)")
        if stats['suggested_terms'] is not None:
            table.add_row("• suggested_terms.json", f"{stats['suggested_terms']:,} mục", "(Từ mới thu hoạch)")

        banner_panel = Panel(
            table,
            title="[bold green]🌟 HỆ THỐNG DỊCH THUẬT & BIÊN TẬP TỪ ĐIỂN V2 (Convert_File_v2)[/bold green]",
            subtitle="[dim]Tiến trình thời gian thực • Hỗ trợ Rich UI[/dim]",
            border_style="green"
        )
        console.print(banner_panel)
    else:
        print("=" * 68)
        print("      HỆ THỐNG QUÉT NHÂN VẬT & BIÊN TẬP TỪ ĐIỂN DỊCH THUẬT V2")
        print("                      Dự án: Convert_File_v2")
        print("=" * 68)
        print("  📊 TRẠNG THÁI DỮ LIỆU HIỆN TẠI:")
        print(f"     • character_dict.json     : {stats['character']} mục (Tên nhân vật)")
        print(f"     • chinese_names_dict.json : {stats.get('chinese_names', 0)} mục (Tên Hán Việt chuẩn)")
        print(f"     • common_dict.json        : {stats['common']} mục (Từ ngữ chung / Thành ngữ)")
        print(f"     • hanviet_dict.json       : {stats['hanviet']} mục (Từ điển Hán Việt)")
        if stats['deconvert'] > 0:
            print(f"     • deconvert_dict.json     : {stats['deconvert']} mục (Chống de-convert)")
        if stats['import_json'] is not None:
            print(f"     • samples/import.json     : {stats['import_json']} mục (Sẵn sàng nạp nhân vật)")
        if stats['import_hanviet'] is not None:
            print(f"     • import_hanviet.json     : {stats['import_hanviet']} mục (Sẵn sàng nạp Hán Việt)")
        if stats['suggested_terms'] is not None:
            print(f"     • suggested_terms.json    : {stats['suggested_terms']} mục (Từ mới thu hoạch)")
        print("-" * 68)

def print_sub_banner(title: str):
    if HAVE_RICH and console:
        console.print(Panel(f"[bold yellow]{title}[/bold yellow]", border_style="cyan"))
    else:
        print("\n" + "=" * 68)
        print(f"  {title}")
        print("=" * 68)

def get_sample_txt_files():
    """Tìm danh sách file văn bản trong samples/."""
    samples_dir = Path("samples")
    if not samples_dir.exists():
        return []
    return [f for f in samples_dir.glob("*.txt") if f.is_file()]

def prompt_input_file(default="samples/exam.txt"):
    """Hỏi người dùng file đầu vào kèm gợi ý danh sách trong samples/."""
    txt_files = get_sample_txt_files()
    if txt_files:
        print("\n📂 Danh sách file văn bản tìm thấy trong samples/:")
        for idx, f in enumerate(txt_files, start=1):
            print(f"   [{idx}] {f.name}")
        val = input(f"\n👉 Chọn số thứ tự (1-{len(txt_files)}) hoặc nhập đường dẫn [Mặc định: {default}]: ").strip()
        if not val:
            return default
        if val.isdigit() and 1 <= int(val) <= len(txt_files):
            return str(txt_files[int(val) - 1])
        return val
    else:
        val = input(f"Nhập đường dẫn file văn bản [Mặc định: {default}]: ").strip()
        return val or default

def get_raw_txt_files():
    """Tìm danh sách file raw trong craw/ và samples/."""
    candidates = []
    for d in [Path("craw"), Path("samples")]:
        if d.exists():
            for f in sorted(d.glob("*.txt")):
                if f.is_file():
                    candidates.append(f)
    return candidates

def prompt_raw_file(default="craw/shao_long_feng_liu_raw.txt"):
    """Hỏi người dùng chọn file raw với danh sách gợi ý."""
    raw_files = get_raw_txt_files()
    if raw_files:
        print("\n📂 Danh sách file raw tìm thấy trong craw/ và samples/:")
        for idx, f in enumerate(raw_files, start=1):
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   [{idx}] {f.as_posix()} ({size_mb:.2f} MB)")
        val = input(f"\n👉 Chọn số thứ tự (1-{len(raw_files)}) hoặc nhập đường dẫn [Mặc định: {default}]: ").strip()
        if not val:
            return default
        if val.isdigit() and 1 <= int(val) <= len(raw_files):
            return str(raw_files[int(val) - 1])
        return val
    else:
        val = input(f"Nhập đường dẫn file raw [Mặc định: {default}]: ").strip()
        return val or default


# =====================================================================
# MENU CON: [1] DỊCH THUẬT AI (OLLAMA / COLAB)
# =====================================================================
def menu_ai_translation():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🌐 NHÓM 1: DỊCH THUẬT AI (OLLAMA QWEN2.5 / GOOGLE COLAB)")
            print("  [1] 🚀 Dịch tiểu thuyết raw toàn trình (Colab Server API)")
            print("  [2] 📡 Kiểm tra kết nối nhanh tới máy chủ Colab / Ollama")
            print("  [3] 🧹 Chuẩn hóa & Sửa tên Hán Việt cho các chương đã dịch")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-3) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print_sub_banner("Dịch tiểu thuyết raw bằng Ollama Qwen2.5")
                colab_url = input("👉 Nhập URL Public Colab (ví dụ: https://xxx.trycloudflare.com): ").strip()
                if not colab_url:
                    if HAVE_RICH and console:
                        console.print(Panel("[bold red]❌ URL không được để trống![/bold red]", border_style="red"))
                    else:
                        print("❌ URL không được để trống!")
                    input("👉 Nhấn Enter để tiếp tục...")
                    continue

                from src.translator.translator_engine import TranslatorEngine
                if HAVE_RICH and console:
                    with console.status(f"[bold cyan]Đang kiểm tra kết nối tới Colab Ollama ({colab_url})...", spinner="dots"):
                        engine = TranslatorEngine(colab_url=colab_url)
                        healthy = engine.client.check_health()
                    if not healthy:
                        console.print(Panel(
                            f"[bold red]❌ Không thể kết nối tới Ollama tại {colab_url}.[/bold red]\n"
                            "Vui lòng kiểm tra notebook Colab và đường link Cloudflare Tunnel.",
                            border_style="red"
                        ))
                        input("👉 Nhấn Enter để tiếp tục...")
                        continue
                    console.print("[bold green]✅ Kết nối Ollama thành công![/bold green]")
                else:
                    print("\n[*] Đang kiểm tra kết nối tới Colab Ollama...")
                    engine = TranslatorEngine(colab_url=colab_url)
                    if not engine.client.check_health():
                        print(f"❌ Không thể kết nối tới Ollama tại {colab_url}.")
                        print("    Vui lòng kiểm tra notebook Colab và đường link Cloudflare Tunnel.")
                        input("👉 Nhấn Enter để tiếp tục...")
                        continue
                    print("✅ Kết nối Ollama thành công!")

                raw_file = prompt_raw_file("craw/shao_long_feng_liu_raw.txt")
                raw_path = Path(raw_file)
                if not raw_path.exists():
                    if HAVE_RICH and console:
                        console.print(Panel(f"[bold red]❌ Không tìm thấy file: {raw_file}[/bold red]", border_style="red"))
                    else:
                        print(f"❌ Không tìm thấy file: {raw_file}")
                    input("👉 Nhấn Enter để tiếp tục...")
                    continue

                default_out = f"convert/translated/{raw_path.stem}_vietnamese.txt"
                out_file = input(f"👉 File kết quả bản dịch [Mặc định: {default_out}]: ").strip() or default_out

                start_chap_str = input("👉 Bắt đầu từ chương số (hoặc tự động resume) [Mặc định: tự động]: ").strip()
                start_chap = int(start_chap_str) if start_chap_str.isdigit() else 1

                max_chap_str = input("👉 Giới hạn số chương cần dịch (để trống = dịch toàn bộ) [Mặc định: Toàn bộ]: ").strip()
                max_chap = int(max_chap_str) if max_chap_str.isdigit() else None

                post_proc = input("👉 Tự động chạy ReplaceEngine hậu kỳ sau khi dịch? (Y/n) [Mặc định: Y]: ").strip().lower() != "n"

                try:
                    if HAVE_RICH and console:
                        raw_size_mb = raw_path.stat().st_size / (1024 * 1024)
                        info_panel = Panel(
                            f"[bold white]• File raw:[/bold white]    [cyan]{raw_path.as_posix()}[/cyan] ({raw_size_mb:.2f} MB)\n"
                            f"[bold white]• File dịch:[/bold white]   [green]{out_file}[/green]\n"
                            f"[bold white]• Checkpoint:[/bold white]  [yellow]progress_{Path(out_file).stem}.json[/yellow]\n"
                            f"[bold white]• Máy chủ:[/bold white]     [magenta]{colab_url}[/magenta]",
                            title="[bold green]🚀 TIẾN TRÌNH DỊCH THUẬT AI (OLLAMA QWEN2.5)[/bold green]",
                            border_style="green"
                        )
                        console.print(info_panel)

                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[bold cyan]{task.description}"),
                            BarColumn(bar_width=25),
                            TaskProgressColumn(),
                            MofNCompleteColumn(),
                            "•",
                            TimeElapsedColumn(),
                            "•",
                            TimeRemainingColumn(),
                            console=console,
                            transient=False
                        ) as progress:
                            total_task = progress.add_task("[bold green]Tiến độ file", total=100, completed=0)
                            chapter_task = progress.add_task("[bold yellow]Chương hiện tại", total=100, completed=0)

                            def _on_init(total_cnt, completed_cnt):
                                progress.update(total_task, total=total_cnt, completed=completed_cnt)

                            def _on_chap_start(cur_idx, total_cnt, chap_title, char_count):
                                progress.update(
                                    chapter_task,
                                    description=f"[bold yellow]Đang dịch [{cur_idx}/{total_cnt}]: {chap_title[:25]}... ({char_count} ký tự)",
                                    total=100,
                                    completed=20
                                )

                            def _on_chap_end(cur_idx, total_cnt, chap_title, elapsed, new_terms_count=0):
                                progress.update(total_task, advance=1)
                                progress.update(
                                    chapter_task,
                                    description=f"[bold green]Xong [{cur_idx}/{total_cnt}]: {chap_title[:20]} ({elapsed:.1f}s)",
                                    completed=100
                                )
                                console.print(
                                    f"   [bold green]✓[/bold green] [{cur_idx}/{total_cnt}] [bold white]{chap_title}[/bold white] "
                                    f"([cyan]{elapsed:.1f}s[/cyan]) | [yellow]+{new_terms_count} từ mới[/yellow] | Checkpoint đã lưu"
                                )

                            engine.translate_novel(
                                raw_filepath=raw_path,
                                output_filepath=out_file,
                                start_chapter=start_chap,
                                max_chapters=max_chap,
                                run_post_processing=post_proc,
                                on_init=_on_init,
                                on_chapter_start=_on_chap_start,
                                progress_callback=_on_chap_end
                            )

                        console.print(Panel(f"[bold green]🎉 DỊCH THUẬT HOÀN TẤT THÀNH CÔNG![/bold green]\n📄 Kết quả đã lưu tại: [cyan]{out_file}[/cyan]", border_style="green"))

                    else:
                        print(f"\n🚀 Bắt đầu tiến trình dịch thuật...")
                        print(f"   • File raw: {raw_file}")
                        print(f"   • File dịch: {out_file}")
                        print(f"   • Checkpoint: progress_{Path(out_file).stem}.json")
                        print("-" * 68)

                        def _progress_cb(cur_idx, total_cnt, chap_title, elapsed, new_terms_count=0):
                            print(f"   [+] Hoàn thành [{cur_idx}/{total_cnt}] ({elapsed:.1f}s, +{new_terms_count} từ): {chap_title}")

                        engine.translate_novel(
                            raw_filepath=raw_path,
                            output_filepath=out_file,
                            start_chapter=start_chap,
                            max_chapters=max_chap,
                            run_post_processing=post_proc,
                            progress_callback=_progress_cb
                        )
                        print("\n🎉 DỊCH THUẬT HOÀN TẤT THÀNH CÔNG!")
                        print(f"📄 File kết quả đã lưu tại: {out_file}")

                except Exception as e:
                    if HAVE_RICH and console:
                        console.print(Panel(f"[bold red]❌ Lỗi trong quá trình dịch: {e}[/bold red]", border_style="red"))
                    else:
                        print(f"\n❌ Lỗi trong quá trình dịch: {e}")

                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print_sub_banner("Kiểm tra kết nối máy chủ Colab / Ollama")
                colab_url = input("👉 Nhập URL Public Colab: ").strip()
                if not colab_url:
                    if HAVE_RICH and console:
                        console.print(Panel("[bold red]❌ URL không được để trống![/bold red]", border_style="red"))
                    else:
                        print("❌ URL không được để trống!")
                else:
                    from src.translator.ollama_client import OllamaTranslatorClient
                    client = OllamaTranslatorClient(base_url=colab_url)
                    if HAVE_RICH and console:
                        with console.status(f"[bold cyan]Đang gửi tín hiệu kiểm tra tới {colab_url}...", spinner="dots"):
                            healthy = client.check_health()
                        if healthy:
                            console.print(Panel(
                                f"[bold green]✅ KẾT NỐI THÀNH CÔNG![/bold green]\n"
                                f"Máy chủ Ollama tại [cyan]{colab_url}[/cyan] đang hoạt động bình thường.",
                                border_style="green"
                            ))
                        else:
                            console.print(Panel(
                                f"[bold red]❌ KẾT NỐI THẤT BẠI![/bold red]\n"
                                f"Không thể kết nối tới [yellow]{colab_url}[/yellow].\n"
                                f"Vui lòng kiểm tra lại Cloudflare Tunnel hoặc GPU Colab.",
                                border_style="red"
                            ))
                    else:
                        print(f"[*] Đang gửi tín hiệu kiểm tra tới {colab_url}...")
                        if client.check_health():
                            print("✅ KẾT NỐI THÀNH CÔNG! Máy chủ Ollama đang hoạt động bình thường.")
                        else:
                            print("❌ KẾT NỐI THẤT BẠI! Vui lòng kiểm tra lại Cloudflare Tunnel hoặc GPU Colab.")
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "3":
                print_sub_banner("Chuẩn hóa & Sửa tên Hán Việt cho các chương đã dịch")
                from tools.fix_translated_names import fix_translated_file
                default_target = "convert/translated/shao_long_feng_liu_raw_vietnamese.txt"
                target_input = input(f"👉 Nhập đường dẫn file dịch cần sửa [Mặc định: {default_target}]: ").strip() or default_target
                fix_translated_file(target_input)
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                if HAVE_RICH and console:
                    console.print(Panel("[bold red]❌ Lựa chọn không hợp lệ![/bold red]", border_style="red"))
                else:
                    print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [2] QUÉT & XỬ LÝ TÊN NHÂN VẬT
# =====================================================================
def menu_character_scanner():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("👥 NHÓM 2: QUÉT & XỬ LÝ TÊN NHÂN VẬT (CHARACTER SCANNER)")
            print("  [1] 🚀 Toàn trình: Quét nhân vật + Tự động gửi Gemini -> samples/import.json")
            print("  [2] 🔍 Chỉ quét nhân vật (Xuất thư mục scanner/ gồm .md & master JSON)")
            print("  [3] 🌐 Chỉ gửi các file trong scanner/ lên Gemini -> samples/import.json")
            print("  [4] 🎯 Lọc nhanh scanner/ theo số lần xuất hiện (min-count)")
            print("  [5] ♻️  Đặt lại tiến trình (Reset progress) gửi Gemini")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-5) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print_sub_banner("Toàn trình: Quét văn bản và tự động gửi Gemini")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                include_known = input("Liệt kê cả nhân vật đã có trong từ điển? (y/N) [Mặc định: N]: ").strip().lower() == "y"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import.json]: ").strip() or "samples/import.json"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.main",
                    "--input", inp,
                    "--output", "scanner",
                    "--chunk-size", chunk,
                    "--min-count", min_cnt,
                    "--upload-gemini",
                    "--profile-dir", prof,
                    "--output-import-json", out_json
                ]
                if include_known:
                    cmd.append("--include-known")

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File nguồn:[/bold white]     [cyan]{inp}[/cyan]\n"
                        f"[bold white]• Số lần xuất hiện:[/bold white] [yellow]>={min_cnt}[/yellow]\n"
                        f"[bold white]• Kích thước chunk:[/bold white] [yellow]{chunk} block/file[/yellow]\n"
                        f"[bold white]• Lấy từ đã biết:[/bold white]  [yellow]{'Có' if include_known else 'Không'}[/yellow]\n"
                        f"[bold white]• Chrome Profile:[/bold white] [magenta]{prof}[/magenta]\n"
                        f"[bold white]• File kết quả:[/bold white]   [green]{out_json}[/green]",
                        title="[bold green]👥 TIẾN TRÌNH QUÉT NHÂN VẬT & GỬI GEMINI[/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold green]🎉 HOÀN THÀNH QUY TRÌNH QUÉT NHÂN VẬT![/bold green]\n"
                        f"📄 File kết quả đã sẵn sàng tại: [cyan]{out_json}[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print_sub_banner("Chỉ quét văn bản nhân vật")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                include_known = input("Liệt kê cả nhân vật đã có trong từ điển? (y/N) [Mặc định: N]: ").strip().lower() == "y"

                workers = input("Số luồng quét song song [Mặc định: 1]: ").strip() or "1"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.main",
                    "--input", inp,
                    "--output", "scanner",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk,
                    "--workers", workers
                ]
                if include_known:
                    cmd.append("--include-known")

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File nguồn:[/bold white]     [cyan]{inp}[/cyan]\n"
                        f"[bold white]• Số lần xuất hiện:[/bold white] [yellow]>={min_cnt}[/yellow]\n"
                        f"[bold white]• Kích thước chunk:[/bold white] [yellow]{chunk} block/file[/yellow]\n"
                        f"[bold white]• Luồng xử lý:[/bold white]      [magenta]{workers} worker(s)[/magenta]\n"
                        f"[bold white]• Thư mục đích:[/bold white]   [green]scanner/[/green]",
                        title="[bold green]🔍 TIẾN TRÌNH QUÉT NHÂN VẬT (CHỈ QUÉT)[/bold green]",
                        border_style="cyan"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        "[bold green]🎉 QUÉT NHÂN VẬT HOÀN TẤT![/bold green]\n"
                        "📂 Các file markdown và master JSON đã được lưu trong [cyan]scanner/[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "3":
                print_sub_banner("Chỉ gửi các file scanner có sẵn lên Gemini")
                scanner_dir = input("Thư mục chứa các file .md [Mặc định: scanner]: ").strip() or "scanner"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import.json]: ").strip() or "samples/import.json"
                delay = input("Thời gian nghỉ giữa các file (giây) [Mặc định: 5]: ").strip() or "5"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.main",
                    "--upload-only",
                    "--output", scanner_dir,
                    "--profile-dir", prof,
                    "--output-import-json", out_json,
                    "--gemini-delay", delay
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• Thư mục scanner:[/bold white] [cyan]{scanner_dir}[/cyan]\n"
                        f"[bold white]• Chrome Profile:[/bold white]  [magenta]{prof}[/magenta]\n"
                        f"[bold white]• File kết quả:[/bold white]    [green]{out_json}[/green]\n"
                        f"[bold white]• Giãn cách gửi:[/bold white]   [yellow]{delay}s[/yellow]",
                        title="[bold green]🌐 TIẾN TRÌNH GỬI GEMINI TỰ ĐỘNG[/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold green]🎉 GỬI GEMINI HOÀN TẤT![/bold green]\n"
                        f"📄 File kết quả đã lưu tại: [cyan]{out_json}[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "4":
                print_sub_banner("Lọc nhanh file scanner theo số lần xuất hiện (min-count)")
                min_cnt = input("Số lần xuất hiện tối thiểu cần giữ lại [Mặc định: 2]: ").strip() or "2"
                chunk = input("Số block mỗi file .md [Mặc định: 40]: ").strip() or "40"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.main",
                    "--filter-only",
                    "--output", "scanner",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• Thư mục scanner:[/bold white] [cyan]scanner/[/cyan]\n"
                        f"[bold white]• Lọc tần suất:[/bold white]    [yellow]>={min_cnt}[/yellow]\n"
                        f"[bold white]• Kích thước chunk:[/bold white] [yellow]{chunk} block/file[/yellow]",
                        title="[bold green]🎯 TIẾN TRÌNH LỌC SCANNER (MIN-COUNT)[/bold green]",
                        border_style="cyan"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        "[bold green]🎉 LỌC SCANNER HOÀN TẤT![/bold green]\n"
                        "📂 Các file markdown sau lọc đã được cập nhật trong [cyan]scanner/[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "5":
                print_sub_banner("Đặt lại tiến trình & gửi lại lên Gemini")
                confirm = input("⚠️ Bạn có chắc muốn xóa lịch sử tiến trình cũ và gửi lại từ đầu? (y/N): ").strip().lower()
                if confirm in ("y", "yes"):
                    prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                    cmd = [
                        get_python_exe(), "-m", "src.scanner.main",
                        "--upload-only",
                        "--output", "scanner",
                        "--profile-dir", prof,
                        "--reset-gemini-progress"
                    ]
                    if HAVE_RICH and console:
                        console.print(Panel(
                            "[bold yellow]♻️ Đang đặt lại tiến trình gửi Gemini và bắt đầu gửi lại từ chunk đầu tiên...[/bold yellow]",
                            border_style="yellow"
                        ))
                    else:
                        print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")
                    subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                if HAVE_RICH and console:
                    console.print(Panel("[bold red]❌ Lựa chọn không hợp lệ![/bold red]", border_style="red"))
                else:
                    print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [3] QUÉT & XỬ LÝ TỪ HÁN VIỆT / CỤM TỪ LẠ
# =====================================================================
def menu_hanviet_scanner():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🏮 NHÓM 3: QUÉT & XỬ LÝ TỪ HÁN VIỆT / CỤM TỪ LẠ (HANVIET SCANNER)")
            print("  [1] 🏮 Toàn trình: Quét Hán Việt + Tự động gửi Gemini -> samples/import_hanviet.json")
            print("  [2] 🔍 Chỉ quét từ Hán Việt & Cụm từ bất thường (Xuất scanner/hanviet/)")
            print("  [3] 🌐 Chỉ gửi các file trong scanner/hanviet/ lên Gemini")
            print("  [4] 🎯 Lọc nhanh scanner/hanviet/ theo số lần xuất hiện (min-count)")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-4) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print_sub_banner("Toàn trình: Quét Hán Việt & Tự động gửi Gemini")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import_hanviet.json]: ").strip() or "samples/import_hanviet.json"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.hanviet_scanner",
                    "--input", inp,
                    "--output", "scanner/hanviet",
                    "--chunk-size", chunk,
                    "--min-count", min_cnt,
                    "--upload-gemini",
                    "--profile-dir", prof,
                    "--output-import-json", out_json
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File nguồn:[/bold white]     [cyan]{inp}[/cyan]\n"
                        f"[bold white]• Số lần xuất hiện:[/bold white] [yellow]>={min_cnt}[/yellow]\n"
                        f"[bold white]• Kích thước chunk:[/bold white] [yellow]{chunk} block/file[/yellow]\n"
                        f"[bold white]• Chrome Profile:[/bold white] [magenta]{prof}[/magenta]\n"
                        f"[bold white]• File kết quả:[/bold white]   [green]{out_json}[/green]",
                        title="[bold green]🏮 TIẾN TRÌNH QUÉT HÁN VIỆT TOÀN TRÌNH[/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold green]🎉 HOÀN THÀNH QUY TRÌNH QUÉT HÁN VIỆT TOÀN TRÌNH![/bold green]\n"
                        f"📄 File kết quả đã sẵn sàng tại: [cyan]{out_json}[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print_sub_banner("Chỉ quét từ Hán Việt & Cụm từ bất thường")
                inp = prompt_input_file("samples/exam.txt")
                min_cnt = input("Số lần xuất hiện tối thiểu [Mặc định: 1]: ").strip() or "1"
                chunk = input("Số lượng block mỗi file nhỏ .md [Mặc định: 40]: ").strip() or "40"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.hanviet_scanner",
                    "--input", inp,
                    "--output", "scanner/hanviet",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File nguồn:[/bold white]     [cyan]{inp}[/cyan]\n"
                        f"[bold white]• Số lần xuất hiện:[/bold white] [yellow]>={min_cnt}[/yellow]\n"
                        f"[bold white]• Kích thước chunk:[/bold white] [yellow]{chunk} block/file[/yellow]\n"
                        f"[bold white]• Thư mục đích:[/bold white]   [green]scanner/hanviet/[/green]",
                        title="[bold green]🔍 TIẾN TRÌNH QUÉT HÁN VIỆT (CHỈ QUÉT)[/bold green]",
                        border_style="cyan"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        "[bold green]🎉 QUÉT HÁN VIỆT HOÀN TẤT![/bold green]\n"
                        "📂 Các file markdown đã được lưu trong [cyan]scanner/hanviet/[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "3":
                print_sub_banner("Chỉ gửi các file Hán Việt lên Gemini")
                scanner_dir = input("Thư mục chứa các file .md [Mặc định: scanner/hanviet]: ").strip() or "scanner/hanviet"
                prof = input("Thư mục Profile Chrome [Mặc định: runtime/chrome_profiles]: ").strip() or "runtime/chrome_profiles"
                out_json = input("File JSON kết quả [Mặc định: samples/import_hanviet.json]: ").strip() or "samples/import_hanviet.json"
                delay = input("Thời gian nghỉ giữa các file (giây) [Mặc định: 5]: ").strip() or "5"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.hanviet_scanner",
                    "--upload-only",
                    "--output", scanner_dir,
                    "--profile-dir", prof,
                    "--output-import-json", out_json,
                    "--gemini-delay", delay
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• Thư mục scanner:[/bold white] [cyan]{scanner_dir}[/cyan]\n"
                        f"[bold white]• Chrome Profile:[/bold white]  [magenta]{prof}[/magenta]\n"
                        f"[bold white]• File kết quả:[/bold white]    [green]{out_json}[/green]\n"
                        f"[bold white]• Giãn cách gửi:[/bold white]   [yellow]{delay}s[/yellow]",
                        title="[bold green]🌐 TIẾN TRÌNH GỬI HÁN VIỆT LÊN GEMINI[/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold green]🎉 GỬI HÁN VIỆT LÊN GEMINI HOÀN TẤT![/bold green]\n"
                        f"📄 File kết quả đã lưu tại: [cyan]{out_json}[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "4":
                print_sub_banner("Lọc nhanh file Hán Việt theo min-count")
                min_cnt = input("Số lần xuất hiện tối thiểu cần giữ lại [Mặc định: 2]: ").strip() or "2"
                chunk = input("Số block mỗi file .md [Mặc định: 40]: ").strip() or "40"

                cmd = [
                    get_python_exe(), "-m", "src.scanner.hanviet_scanner",
                    "--filter-only",
                    "--output", "scanner/hanviet",
                    "--min-count", min_cnt,
                    "--chunk-size", chunk
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• Thư mục scanner:[/bold white] [cyan]scanner/hanviet/[/cyan]\n"
                        f"[bold white]• Lọc tần suất:[/bold white]    [yellow]>={min_cnt}[/yellow]\n"
                        f"[bold white]• Kích thước chunk:[/bold white] [yellow]{chunk} block/file[/yellow]",
                        title="[bold green]🎯 TIẾN TRÌNH LỌC HÁN VIỆT (MIN-COUNT)[/bold green]",
                        border_style="cyan"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        "[bold green]🎉 LỌC HÁN VIỆT HOÀN TẤT![/bold green]\n"
                        "📂 Các file sau lọc đã được cập nhật trong [cyan]scanner/hanviet/[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                if HAVE_RICH and console:
                    console.print(Panel("[bold red]❌ Lựa chọn không hợp lệ![/bold red]", border_style="red"))
                else:
                    print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [4] QUẢN LÝ TỪ ĐIỂN & NẠP DỮ LIỆU
# =====================================================================
def menu_dictionary_manager():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("📖 NHÓM 4: QUẢN LÝ TỪ ĐIỂN & NẠP DỮ LIỆU (DICTIONARY MANAGER)")
            print("  [1] 📥 Nạp samples/import.json vào từ điển (Tự động phân loại theo is_character)")
            print("  [2] 📥 Nạp samples/import_hanviet.json vào hanviet_dict.json")
            print("  [3] 📥 Nạp từ mới thu hoạch (samples/suggested_terms.json) vào từ điển")
            print("  [4] ✍️  Nhập thủ công từng từ vào từ điển (Interactive mode)")
            print("  [5] ⚡ Nạp trực tiếp samples/import.json (Không cần điều kiện gì / Bỏ qua lọc)")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-5) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print_sub_banner("Nạp dữ liệu vào từ điển (Import)")
                if HAVE_RICH and console:
                    console.print("[dim]💡 Cơ chế tự động phân bổ:\n   • is_character == true  -> nạp vào character_dict.json\n   • is_character == false -> nạp vào common_dict.json[/dim]\n")
                else:
                    print("💡 Cơ chế tự động phân bổ:")
                    print("   • is_character == true  -> nạp vào character_dict.json")
                    print("   • is_character == false -> nạp vào common_dict.json")
                    print()

                file_imp = input("Nhập đường dẫn file cần import [Mặc định: samples/import.json]: ").strip() or "samples/import.json"
                dict_dst = input("Đường dẫn từ điển đích [Để trống: Tự động phân bổ theo is_character]: ").strip()

                cmd = [get_python_exe(), "-m", "src.importer.main", "--file", file_imp]
                if dict_dst:
                    cmd.extend(["--dict", dict_dst])

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File nguồn:[/bold white]     [cyan]{file_imp}[/cyan]\n"
                        f"[bold white]• Phân loại:[/bold white]      [yellow]Tự động (is_character -> character / common)[/yellow]\n"
                        f"[bold white]• Từ điển đích:[/bold white]  [green]{dict_dst or 'Tự động phân bổ'}[/green]",
                        title="[bold green]📥 TIẾN TRÌNH NẠP DỮ LIỆU TỪ ĐIỂN[/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel("[bold green]🎉 Hoàn tất quá trình nạp từ điển![/bold green]", border_style="green"))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print_sub_banner("Nạp kết quả vào từ điển Hán Việt (hanviet_dict.json)")
                file_imp = input("File JSON cần import [Mặc định: samples/import_hanviet.json]: ").strip() or "samples/import_hanviet.json"
                dict_dst = "resources/dictionaries/hanviet_dict.json"

                cmd = [
                    get_python_exe(), "-m", "src.importer.main",
                    "--file", file_imp,
                    "--dict", dict_dst
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File nguồn:[/bold white]     [cyan]{file_imp}[/cyan]\n"
                        f"[bold white]• Từ điển đích:[/bold white]  [green]{dict_dst}[/green]",
                        title="[bold green]🏮 NẠP TỪ ĐIỂN HÁN VIỆT[/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel("[bold green]🎉 Hoàn tất nạp từ điển Hán Việt![/bold green]", border_style="green"))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "3":
                print_sub_banner("Nạp từ mới thu hoạch từ dịch thuật")
                suggested_file = Path("samples/suggested_terms.json")
                if not suggested_file.exists():
                    if HAVE_RICH and console:
                        console.print(Panel("[bold yellow]⚠️ Chưa có file samples/suggested_terms.json (được tự động sinh ra khi dịch tiểu thuyết ở Nhóm 1).[/bold yellow]", border_style="yellow"))
                    else:
                        print("⚠️ Chưa có file samples/suggested_terms.json (được tự động sinh ra khi dịch tiểu thuyết ở Nhóm 1).")
                else:
                    target_dict = input("Nạp vào từ điển nào? (1: common_dict.json, 2: character_dict.json) [Mặc định: 1]: ").strip() or "1"
                    dest_file = "resources/dictionaries/character_dict.json" if target_dict == "2" else "resources/dictionaries/common_dict.json"
                    cmd = [
                        get_python_exe(), "-m", "src.importer.main",
                        "--file", str(suggested_file),
                        "--dict", dest_file
                    ]

                    if HAVE_RICH and console:
                        console.print(Panel(
                            f"[bold white]• File nguồn:[/bold white]     [cyan]{suggested_file}[/cyan]\n"
                            f"[bold white]• Từ điển đích:[/bold white]  [green]{dest_file}[/green]",
                            title="[bold green]📥 NẠP TỪ MỚI THU HOẠCH[/bold green]",
                            border_style="green"
                        ))
                    else:
                        print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                    subprocess.run(cmd)

                    if HAVE_RICH and console:
                        console.print(Panel("[bold green]🎉 Hoàn tất nạp từ mới thu hoạch![/bold green]", border_style="green"))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "4":
                print_sub_banner("Nhập thủ công từng từ vào từ điển")
                cmd = [get_python_exe(), "-m", "src.importer.main", "--interactive"]
                subprocess.run(cmd)
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "5":
                print_sub_banner("Nạp trực tiếp samples/import.json vào từ điển (Không cần điều kiện gì)")
                if HAVE_RICH and console:
                    console.print("[bold yellow]⚡ Chế độ nạp trực tiếp:[/bold yellow] [dim]Bỏ qua mọi kiểm tra số từ, không lọc cảnh báo, không giới hạn trùng lặp. Nạp toàn bộ dữ liệu thô vào từ điển.[/dim]\n")
                else:
                    print("⚡ Chế độ nạp trực tiếp: Bỏ qua kiểm tra số từ, không lọc cảnh báo, nạp toàn bộ dữ liệu thô vào từ điển.\n")

                file_imp = input("Nhập đường dẫn file cần import [Mặc định: samples/import.json]: ").strip() or "samples/import.json"
                dict_dst = input("Đường dẫn từ điển đích [Để trống: Tự động phân bổ theo is_character]: ").strip()

                cmd = [get_python_exe(), "-m", "src.importer.main", "--file", file_imp, "--force-all"]
                if dict_dst:
                    cmd.extend(["--dict", dict_dst])

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File nguồn:[/bold white]     [cyan]{file_imp}[/cyan]\n"
                        f"[bold white]• Chế độ:[/bold white]         [bold green]Nạp trực tiếp (Không điều kiện / Force all)[/bold green]\n"
                        f"[bold white]• Từ điển đích:[/bold white]  [green]{dict_dst or 'Tự động phân bổ theo is_character'}[/green]",
                        title="[bold green]⚡ TIẾN TRÌNH NẠP TRỰC TIẾP (KHÔNG ĐIỀU KIỆN)[/bold green]",
                        border_style="yellow"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel("[bold green]🎉 Hoàn tất quá trình nạp trực tiếp toàn bộ dữ liệu![/bold green]", border_style="green"))
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                if HAVE_RICH and console:
                    console.print(Panel("[bold red]❌ Lựa chọn không hợp lệ![/bold red]", border_style="red"))
                else:
                    print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [5] THAY THẾ VĂN BẢN (REPLACE ENGINE)
# =====================================================================
def menu_replace_engine():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🔄 NHÓM 5: THAY THẾ VĂN BẢN & HẬU KỲ (REPLACE ENGINE)")
            print("  [1] 🔄 Thay thế văn bản bằng từ điển (Single-Pass Longest Match)")
            print("  [2] 🛡️ Quét & Thay thế các lỗi de-convert tên riêng (deconvert_dict.json)")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-2) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print_sub_banner("Thay thế văn bản bằng từ điển (Replace Engine)")
                inp = prompt_input_file("samples/exam.txt")
                p_inp = Path(inp)
                default_out = f"convert/{p_inp.stem}_converted{p_inp.suffix}"
                out = input(f"Đường dẫn file kết quả [Mặc định: {default_out}]: ").strip() or default_out
                workers = input("Số luồng xử lý song song [Mặc định: 1 (Tối ưu Trie >40.000 dòng/s)]: ").strip() or "1"

                cmd = [
                    get_python_exe(), "-m", "src.replacer.main",
                    "--input", inp,
                    "--output", out,
                    "--workers", workers
                ]

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold white]• File đầu vào:[/bold white] [cyan]{inp}[/cyan]\n"
                        f"[bold white]• File đầu ra:[/bold white]  [green]{out}[/green]\n"
                        f"[bold white]• Luồng xử lý:[/bold white] [magenta]{workers} worker(s)[/magenta]\n"
                        f"[bold white]• Thuật toán:[/bold white]   [yellow]Fast Trie Single-Pass + Prefix/Negative Guards[/yellow]",
                        title="[bold green]🔄 TIẾN TRÌNH THAY THẾ TỪ ĐIỂN SIÊU TỐC[/bold green]",
                        border_style="green"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                subprocess.run(cmd)

                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold green]🎉 THAY THẾ VĂN BẢN HOÀN TẤT![/bold green]\n"
                        f"📄 Kết quả đã lưu tại: [cyan]{out}[/cyan]",
                        border_style="green"
                    ))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print_sub_banner("Làm sạch lỗi de-convert tên riêng")
                inp = prompt_input_file("samples/exam.txt")
                p_inp = Path(inp)
                default_out = f"convert/{p_inp.stem}_deconverted{p_inp.suffix}"
                out = input(f"Đường dẫn file kết quả [Mặc định: {default_out}]: ").strip() or default_out

                from src.replacer.replace_engine import ReplaceEngine
                deconvert_file = Path("resources/dictionaries/deconvert_dict.json")
                if not deconvert_file.exists():
                    if HAVE_RICH and console:
                        console.print(Panel("[bold red]❌ Không tìm thấy resources/dictionaries/deconvert_dict.json![/bold red]", border_style="red"))
                    else:
                        print("❌ Không tìm thấy resources/dictionaries/deconvert_dict.json!")
                else:
                    try:
                        if HAVE_RICH and console:
                            console.print(Panel(
                                f"[bold white]• File đầu vào:[/bold white]    [cyan]{inp}[/cyan]\n"
                                f"[bold white]• File đầu ra:[/bold white]     [green]{out}[/green]\n"
                                f"[bold white]• Từ điển sửa lỗi:[/bold white] [yellow]resources/dictionaries/deconvert_dict.json[/yellow]",
                                title="[bold green]🛡️ LÀM SẠCH LỖI DE-CONVERT TÊN RIÊNG[/bold green]",
                                border_style="green"
                            ))
                        mapping = json.loads(deconvert_file.read_text(encoding="utf-8"))
                        engine = ReplaceEngine(custom_mapping=mapping)
                        stats = engine.replace_file(inp, out, show_progress=True)
                        if HAVE_RICH and console:
                            console.print(Panel(
                                f"[bold green]🎉 LÀM SẠCH DE-CONVERT HOÀN TẤT THÀNH CÔNG![/bold green]\n"
                                f"[bold white]• Số lỗi đã sửa:[/bold white] [green]{stats.total_replacements}[/green] vị trí\n"
                                f"[bold white]• File lưu tại:[/bold white]   [cyan]{out}[/cyan]",
                                border_style="green"
                            ))
                        else:
                            print(f"\n✅ Đã hoàn thành! Đã sửa {stats.total_replacements} vị trí lỗi.")
                            print(f"📄 Kết quả lưu tại: {out}")
                    except Exception as e:
                        if HAVE_RICH and console:
                            console.print(Panel(f"[bold red]❌ Lỗi: {e}[/bold red]", border_style="red"))
                        else:
                            print(f"❌ Lỗi: {e}")
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                if HAVE_RICH and console:
                    console.print(Panel("[bold red]❌ Lựa chọn không hợp lệ![/bold red]", border_style="red"))
                else:
                    print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CON: [6] CÔNG CỤ HỆ THỐNG & KIỂM THỬ
# =====================================================================
def menu_system_tools():
    while True:
        try:
            clear_screen()
            print_banner()
            print_sub_banner("🛠️ NHÓM 6: CÔNG CỤ HỆ THỐNG & KIỂM THỬ (SYSTEM & TESTS)")
            print("  [1] 🧪 Chạy toàn bộ Unit Tests hệ thống (Pytest)")
            print("  [2] 📊 Xem chi tiết đường dẫn và số lượng file tài nguyên")
            print("  [0] ↩️  Quay lại menu chính")
            print("-" * 68)

            choice = input("👉 Nhập lựa chọn (0-2) [Mặc định: 1]: ").strip() or "1"
            if choice == "0":
                return

            elif choice == "1":
                print_sub_banner("Chạy kiểm thử hệ thống (Unit Tests)")
                cmd = [get_python_exe(), "-m", "pytest", "tests/", "-v"]
                if HAVE_RICH and console:
                    console.print(Panel(
                        f"[bold cyan]🧪 Đang thực thi toàn bộ bài kiểm thử đơn vị với pytest...[/bold cyan]\n"
                        f"Lệnh: [dim]{' '.join(cmd)}[/dim]",
                        border_style="cyan"
                    ))
                else:
                    print(f"\n[*] Đang thực thi: {' '.join(cmd)}\n")

                ret = subprocess.run(cmd)

                if HAVE_RICH and console:
                    if ret.returncode == 0:
                        console.print(Panel("[bold green]✅ TẤT CẢ CÁC BÀI KIỂM THỬ ĐỀU ĐẠT CHUẨN![/bold green]", border_style="green"))
                    else:
                        console.print(Panel("[bold red]❌ CÓ BÀI KIỂM THỬ THẤT BẠI. Vui lòng xem log chi tiết ở trên.[/bold red]", border_style="red"))
                input("\n👉 Nhấn Enter để tiếp tục...")

            elif choice == "2":
                print_sub_banner("Chi tiết tài nguyên hệ thống")
                stats = get_data_stats()
                if HAVE_RICH and console:
                    dict_table = Table(title="[bold green]📁 THƯ MỤC & TỪ ĐIỂN HỆ THỐNG[/bold green]", border_style="cyan")
                    dict_table.add_column("Loại tài nguyên", style="bold white")
                    dict_table.add_column("Số lượng mục", style="bold green", justify="right")
                    dict_table.add_column("Đường dẫn / Chức năng", style="dim")

                    meta = {
                        "character": ("resources/dictionaries/character_dict.json", "Tên nhân vật"),
                        "chinese_names": ("resources/dictionaries/chinese_names_dict.json", "Tên Hán Việt chuẩn"),
                        "common": ("resources/dictionaries/common_dict.json", "Từ ngữ chung / Thành ngữ"),
                        "hanviet": ("resources/dictionaries/hanviet_dict.json", "Từ điển Hán Việt"),
                        "deconvert": ("resources/dictionaries/deconvert_dict.json", "Chống lỗi de-convert"),
                        "import_json": ("samples/import.json", "Kết quả quét nhân vật"),
                        "import_hanviet": ("samples/import_hanviet.json", "Kết quả quét Hán Việt"),
                        "suggested_terms": ("samples/suggested_terms.json", "Từ mới thu hoạch khi dịch")
                    }
                    for k, v in stats.items():
                        path_desc, note = meta.get(k, ("", ""))
                        val_str = f"{v:,} mục" if v is not None else "[dim]Chưa có[/dim]"
                        dict_table.add_row(k, val_str, f"{path_desc} ({note})")
                    console.print(dict_table)

                    raw_files = get_raw_txt_files()
                    raw_table = Table(title="[bold green]📁 DANH SÁCH FILE VĂN BẢN (CRAW/ & SAMPLES/)[/bold green]", border_style="cyan")
                    raw_table.add_column("Tên file", style="bold white")
                    raw_table.add_column("Dung lượng (MB)", style="bold yellow", justify="right")
                    raw_table.add_column("Đường dẫn tương đối", style="magenta")

                    for f in raw_files:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        raw_table.add_row(f.name, f"{size_mb:.2f} MB", f.as_posix())
                    console.print(raw_table)
                else:
                    print("📁 THƯ MỤC VÀ TỪ ĐIỂN:")
                    for k, v in stats.items():
                        print(f"   • {k:20s}: {v if v is not None else 'Chưa có'}")
                    print("\n📁 DANH SÁCH FILE RAW TRONG CRAW/ & SAMPLES/:")
                    for f in get_raw_txt_files():
                        size_mb = f.stat().st_size / (1024 * 1024)
                        print(f"   • {f.as_posix()} ({size_mb:.2f} MB)")
                input("\n👉 Nhấn Enter để tiếp tục...")

            else:
                if HAVE_RICH and console:
                    console.print(Panel("[bold red]❌ Lựa chọn không hợp lệ![/bold red]", border_style="red"))
                else:
                    print("❌ Lựa chọn không hợp lệ!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n[!] Đã hủy thao tác. Quay lại menu trước...")
            return


# =====================================================================
# MENU CHÍNH (MAIN MENU)
# =====================================================================
def main_menu():
    while True:
        try:
            clear_screen()
            print_banner()
            print("  [ CÁC NHÓM CHỨC NĂNG HỆ THỐNG ]")
            print("  [1] 🌐 Dịch thuật AI (Ollama Qwen2.5 / Google Colab)")
            print("  [2] 👥 Quét & Xử lý Tên Nhân vật (Character Scanner)")
            print("  [3] 🏮 Quét & Xử lý Từ Hán Việt / Cụm từ lạ (Hanviet Scanner)")
            print("  [4] 📖 Quản lý Từ điển & Nạp Dữ liệu (Dictionary Manager)")
            print("  [5] 🔄 Thay thế Văn bản & Hậu kỳ (Replace Engine)")
            print("  [6] 🛠️ Công cụ Hệ thống & Kiểm thử (System & Tests)")
            print("  [0] ❌ Thoát chương trình")
            print("=" * 68)

            choice = input("👉 Nhập nhóm chức năng bạn muốn chọn (0-6) [Mặc định: 1]: ").strip()
            if not choice:
                choice = "1"

            if choice == "0":
                print("\n👋 Cảm ơn bạn đã sử dụng chương trình. Tạm biệt!")
                break
            elif choice == "1":
                menu_ai_translation()
            elif choice == "2":
                menu_character_scanner()
            elif choice == "3":
                menu_hanviet_scanner()
            elif choice == "4":
                menu_dictionary_manager()
            elif choice == "5":
                menu_replace_engine()
            elif choice == "6":
                menu_system_tools()
            else:
                print("❌ Lựa chọn không hợp lệ. Vui lòng chọn số từ 0 đến 6!")
                input("👉 Nhấn Enter để tiếp tục...")

        except KeyboardInterrupt:
            print("\n\n[!] Đã hủy thao tác qua phím tắt (Ctrl+C). Đang thoát...")
            break


if __name__ == "__main__":
    main_menu()
