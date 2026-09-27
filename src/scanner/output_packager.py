import json
import gc
from pathlib import Path
from typing import Iterable, Union
from .scanner_engine import CharacterBlock

class OutputPackager:
    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path

    def package(
        self,
        blocks: Union[list[CharacterBlock], Iterable[CharacterBlock]],
        output_dir: Path,
        chunk_size: int = 40
    ) -> int:
        """
        Đóng gói blocks:
        - Mỗi khi gom đủ 1 file nhỏ (chunk_size), lập tức xuất ra file .md và giải phóng RAM.
        - Stream ghi scanner_master.json trực tiếp vào ổ đĩa, không giữ toàn bộ mảng JSON trong bộ nhớ.
        """
        if output_dir.suffix:
            target_file = output_dir
            output_dir = target_file.parent
            master_name = target_file.name
        else:
            master_name = "scanner_master.json"

        output_dir.mkdir(parents=True, exist_ok=True)
        folder_name = output_dir.name

        # Dọn dẹp các file markdown cũ trong thư mục
        for existing in output_dir.glob(f"{folder_name}_*.md"):
            try:
                existing.unlink()
            except Exception:
                pass

        # Nạp prompt mẫu
        prompt_content = ""
        if self.prompt_path.exists():
            prompt_content = self.prompt_path.read_text(encoding="utf-8").strip()

        master_path = output_dir / master_name
        total_blocks = 0
        chunk_idx = 0
        current_chunk: list[CharacterBlock] = []

        with open(master_path, "w", encoding="utf-8") as f_master:
            f_master.write("[\n")
            first_entry = True

            for block in blocks:
                total_blocks += 1
                current_chunk.append(block)

                # Ghi block vào scanner_master.json dạng stream
                if not first_entry:
                    f_master.write(",\n")
                else:
                    first_entry = False

                block_dict = block.to_output_dict()
                block_json = json.dumps(block_dict, ensure_ascii=False, indent=2)
                indented = "  " + block_json.replace("\n", "\n  ")
                f_master.write(indented)

                # Khi tích lũy đủ 1 file nhỏ -> Xuất ngay ra file .md và giải phóng RAM
                if len(current_chunk) >= chunk_size:
                    chunk_idx += 1
                    self._write_chunk_file(
                        output_dir, folder_name, chunk_idx, current_chunk, prompt_content
                    )
                    current_chunk.clear()
                    gc.collect()

            # Nếu còn các block cuối cùng (< chunk_size) -> Xuất file nhỏ cuối
            if current_chunk:
                chunk_idx += 1
                self._write_chunk_file(
                    output_dir, folder_name, chunk_idx, current_chunk, prompt_content
                )
                current_chunk.clear()
                gc.collect()

            f_master.write("\n]\n")

        print(f"[+] Hoàn thành đóng gói: Đã xuất {chunk_idx} file nhỏ ({folder_name}_*.md) và '{master_path.name}'.")
        return total_blocks

    def _write_chunk_file(
        self,
        output_dir: Path,
        folder_name: str,
        chunk_idx: int,
        chunk: list[CharacterBlock],
        prompt_content: str
    ):
        """Ghi 1 file nhỏ .md xuống đĩa và thu hồi bộ nhớ ngay."""
        md_path = output_dir / f"{folder_name}_{chunk_idx}.md"
        chunk_payload = [b.to_output_dict() for b in chunk]
        json_str = json.dumps(chunk_payload, ensure_ascii=False, indent=2)
        content = f"{prompt_content}\n\n```json\n{json_str}\n```\n"
        md_path.write_text(content, encoding="utf-8")
        print(f"\n[+] [File nhỏ {chunk_idx}] Đã ghi '{md_path.name}' ({len(chunk)} nhân vật) & giải phóng bộ nhớ.", flush=True)
