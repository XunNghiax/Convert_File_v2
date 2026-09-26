import json
from pathlib import Path
from character_scanner.scanner_engine import CharacterBlock

class OutputPackager:
    def __init__(self, prompt_path: Path):
        self.prompt_path = prompt_path

    def package(self, blocks: list[CharacterBlock], output_dir: Path, chunk_size: int = 40):
        output_dir.mkdir(parents=True, exist_ok=True)
        # 1. Master JSON
        master_path = output_dir / "scanner_master.json"
        master_data = [b.to_dict() for b in blocks]
        master_path.write_text(json.dumps(master_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 2. Markdown Chunks with Prompt
        prompt_content = ""
        if self.prompt_path.exists():
            prompt_content = self.prompt_path.read_text(encoding="utf-8").strip()

        folder_name = output_dir.name
        for chunk_idx, i in enumerate(range(0, len(blocks), chunk_size), start=1):
            chunk = blocks[i:i + chunk_size]
            md_path = output_dir / f"{folder_name}_{chunk_idx}.md"
            
            chunk_payload = [
                {
                    "id": b.id,
                    "source": b.source,
                    "target": b.target,
                    "context": b.context,
                    "dong_xuat_hien": b.dong_xuat_hien
                }
                for b in chunk
            ]
            json_str = json.dumps(chunk_payload, ensure_ascii=False, indent=2)
            content = f"{prompt_content}\n\n```json\n{json_str}\n```\n"
            md_path.write_text(content, encoding="utf-8")
