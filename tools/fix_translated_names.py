import shutil
from pathlib import Path

# Mapping of incorrect Pinyin/phonetic translations to standard Sino-Vietnamese names
NAME_REPLACEMENTS = [
    # Complex phrase replacements first
    ("Xinh đẹp Yuzhen", "Ngọc Trinh xinh đẹp"),
    ("xinh đẹp Yuzhen", "Ngọc Trinh xinh đẹp"),
    
    # Character names (Pinyin variants)
    ("Mei Yuxuan", "Mai Ngọc Huyên"),
    ("Mai Yuxuan", "Mai Ngọc Huyên"),
    ("Mai Yu Xuan", "Mai Ngọc Huyên"),
    ("Qúy Yuxuan", "Quý Ngọc Huyên"),
    
    ("Qiu Yuzhen", "Khâu Ngọc Trinh"),
    ("Qiu Yu Zhen", "Khâu Ngọc Trinh"),
    ("Qiu chị", "chị Khâu"),
    ("chị Qiu", "chị Khâu"),
    ("chị Zhen", "chị Trinh"),
    ("Yuzhen", "Ngọc Trinh"),
    
    ("A Fei", "A Phi"),
    ("anh Fei", "anh Phi"),
    ("anh ta Fei", "anh ta Phi"),
    ("Fei,", "Phi,"),
    
    ("Zhu Weidong", "Chu Vệ Đông"),
    ("Chu Weidong", "Chu Vệ Đông"),
    
    ("Dương Ý Dung", "Dương Ngọc Nhã"),
    ("Dương Ý Quân", "Dương Ngọc Khanh"),
    ("Dương Ý Nhiên", "Dương Ngọc Nhàn"),
    ("Mạc Đệ", "Mạnh Đức"),
    
    ("Lưu Úy Nhu", "Liễu Ngọc Như"),
    ("Lữ Ý Như", "Liễu Ngọc Như"),
    ("Tiêu Mỹ Mê", "Điền Tú Mai"),
    ("Trần Thủy Văn", "Tiền Tuyết Văn"),
    ("Chu Y Mị", "Chu Ngọc Mị"),
    ("Sư Lợi Na", "Tôn Lệ Na"),
    ("Sư cô Sư cô", "Tiết Lệ Di"),
    
    ("Xue Yu Yi", "Tiết Lệ Di"),
    ("Xue chị", "chị Tiết"),
    
    ("Yuzhi", "Ngọc Chi"),
    ("Zijian", "Tử Kiến"),
    ("Xuwen", "Tuyết Văn"),
    ("Xiaojing", "Tiểu Tinh"),
    ("Xuan Wu", "Huyền Vũ"),
    ("Zhang Ziqiang", "Trương Tử Cường"),
    ("Xia Yu He", "Hạ Vũ Hà"),
    ("Xia Yuhuo", "Hạ Vũ Hà"),
    ("Nguyễn Yuchai", "Nguyễn Ngọc Thoa"),
    ("Kim Zi Fei", "Kim Tử Phi"),
    ("Zhang Wei Ping", "Trương Vệ Bình"),
    ("Zhang Yimou", "Trương Nghệ Mưu"),
    ("Zhang Minggao", "Trương Minh Cao"),
]

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    HAVE_RICH = True
except ImportError:
    HAVE_RICH = False

def fix_translated_file(target_path: Path | str) -> dict[str, int]:
    target_path = Path(target_path)
    if not target_path.exists():
        if HAVE_RICH:
            Console().print(f"[bold red]❌ Không tìm thấy file: {target_path}[/bold red]")
        else:
            print(f"❌ Không tìm thấy file: {target_path}")
        return {}

    console = Console() if HAVE_RICH else None

    # 1. Backup original file
    backup_path = target_path.with_suffix(target_path.suffix + ".bak")
    if not backup_path.exists():
        shutil.copy2(target_path, backup_path)
        if console:
            console.print(f"📦 [bold cyan]Đã tạo bản sao lưu tại:[/bold cyan] {backup_path}")
        else:
            print(f"📦 Đã tạo bản sao lưu tại: {backup_path}")

    # 2. Read content
    content = target_path.read_text(encoding="utf-8")

    stats = {}
    total_replaced = 0

    # 3. Perform replacements with Rich Progress bar
    if console:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(bar_width=25),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Đang quét & thay thế tên Hán Việt...", total=len(NAME_REPLACEMENTS))
            for old_name, new_name in NAME_REPLACEMENTS:
                count = content.count(old_name)
                if count > 0:
                    content = content.replace(old_name, new_name)
                    stats[old_name] = count
                    total_replaced += count
                progress.advance(task, 1)
    else:
        for old_name, new_name in NAME_REPLACEMENTS:
            count = content.count(old_name)
            if count > 0:
                content = content.replace(old_name, new_name)
                stats[old_name] = count
                total_replaced += count

    # 4. Save cleaned file
    target_path.write_text(content, encoding="utf-8")

    # 5. Render results with Rich Table
    if console:
        table = Table(
            title="[bold green]🎉 KẾT QUẢ CHUẨN HÓA TÊN HÁN VIỆT TRÊN FILE DỊCH[/bold green]",
            border_style="green",
            show_lines=True
        )
        table.add_column("STT", style="cyan", justify="center", width=6)
        table.add_column("Tên cũ (Pinyin / Sai)", style="yellow", width=25)
        table.add_column("Tên mới (Hán Việt chuẩn)", style="bold green", width=25)
        table.add_column("Số lần sửa", style="magenta", justify="right", width=12)

        mapping_dict = dict(NAME_REPLACEMENTS)
        if stats:
            for idx, (old, cnt) in enumerate(stats.items(), start=1):
                table.add_row(str(idx), old, mapping_dict[old], f"{cnt:,}")
        else:
            table.add_row("-", "Không phát hiện tên sai", "Đã chuẩn hóa 100%", "0")

        console.print(table)
        summary_panel = Panel(
            f"[bold white]• Tổng số lượt sửa tên:[/bold white]   [bold green]{total_replaced:,} lần[/bold green]\n"
            f"[bold white]• File kết quả cập nhật:[/bold white]  [cyan]{target_path.as_posix()}[/cyan]\n"
            f"[bold white]• File sao lưu an toàn:[/bold white]   [yellow]{backup_path.as_posix()}[/yellow]",
            title="[bold green]✓ HOÀN TẤT CHUẨN HÓA HẬU KỲ[/bold green]",
            border_style="green"
        )
        console.print(summary_panel)
    else:
        print("\n" + "=" * 60)
        print("🎉 KẾT QUẢ SỬA TÊN TOÀN BỘ CÁC CHƯƠNG ĐÃ DỊCH:")
        print("=" * 60)
        for old, cnt in stats.items():
            new = dict(NAME_REPLACEMENTS)[old]
            print(f"  • {old:18} ➔ {new:18} ({cnt} lần)")
        print("-" * 60)
        print(f"Tổng số lượt tên đã được chuẩn hóa Hán Việt: {total_replaced} lần")
        print(f"File kết quả đã được cập nhật tại: {target_path}")
        print("=" * 60)

    return stats


if __name__ == "__main__":
    default_file = Path(__file__).resolve().parent.parent / "convert" / "translated" / "shao_long_feng_liu_raw_vietnamese.txt"
    fix_translated_file(default_file)
