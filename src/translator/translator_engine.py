import json
import time
from pathlib import Path
from typing import Optional, Callable

from src.translator.chapter_splitter import ChapterSplitter
from src.translator.glossary_manager import GlossaryManager
from src.translator.progress_tracker import TranslatorProgressTracker
from src.translator.ollama_client import OllamaTranslatorClient
from src.translator.hanviet_transliterater import HanVietTransliterater
from src.replacer.replace_engine import ReplaceEngine


class TranslatorEngine:
    """
    Orchestrates the entire translation workflow:
    chapter splitting, prompt glossary building, Colab LLM inference,
    checkpoint tracking, term harvesting, and de-convert post-processing.
    """

    def __init__(
        self,
        colab_url: str,
        base_dir: Optional[Path | str] = None,
        model_name: str = "qwen2.5:7b-instruct",
        timeout: int = 180,
    ):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path(__file__).resolve().parent.parent.parent

        self.client = OllamaTranslatorClient(
            base_url=colab_url,
            model_name=model_name,
            timeout=timeout
        )
        self.glossary_mgr = GlossaryManager(base_dir=self.base_dir)
        self.splitter = ChapterSplitter()
        self.transliterater = HanVietTransliterater(
            dict_path=self.base_dir / "resources" / "dictionaries" / "hanviet_dict.json"
        )

    def translate_novel(
        self,
        raw_filepath: Path | str,
        output_filepath: Path | str,
        start_chapter: int = 1,
        max_chapters: Optional[int] = None,
        run_post_processing: bool = True,
        on_init: Optional[Callable[[int, int], None]] = None,
        on_chapter_start: Optional[Callable[[int, int, str, int], None]] = None,
        progress_callback: Optional[Callable[..., None]] = None,
    ) -> bool:
        """
        Translates a raw novel file chapter-by-chapter into Vietnamese.
        Supports resume from checkpoint, dynamic term enrichment, and live callbacks.
        """
        raw_filepath = Path(raw_filepath)
        output_filepath = Path(output_filepath)

        if not raw_filepath.exists():
            raise FileNotFoundError(f"Raw file not found: {raw_filepath}")

        # 1. Load existing dictionaries
        self.glossary_mgr.load_dictionaries()

        # 2. Split chapters
        chapters = self.splitter.split_file(raw_filepath)
        total_chapters = len(chapters)
        if total_chapters == 0:
            return False

        # 3. Setup Progress Tracker
        progress_file = output_filepath.parent / f"progress_{output_filepath.stem}.json"
        tracker = TranslatorProgressTracker(
            progress_file=progress_file,
            output_file=output_filepath,
            total_chapters=total_chapters,
        )

        if on_init:
            on_init(total_chapters, len(tracker.completed_chapters))

        # 4. Determine start index
        current_idx = max(start_chapter, tracker.get_resume_index())
        processed_in_session = 0

        for chapter in chapters:
            if chapter.index < current_idx:
                continue

            if max_chapters is not None and processed_in_session >= max_chapters:
                break

            if tracker.is_completed(chapter.index):
                continue

            translated_title = self.transliterater.translate_title(chapter.title)

            if on_chapter_start:
                on_chapter_start(chapter.index, total_chapters, translated_title, chapter.char_count)

            # Build chapter-specific glossary
            glossary_prompt = self.glossary_mgr.build_prompt_glossary(chapter.content)

            # Translate via Ollama
            t0 = time.time()
            ai_output = self.client.translate_chapter(chapter.content, glossary_prompt)
            elapsed = time.time() - t0

            # Parse dual output (translation and newly discovered terms)
            translation, new_terms = self.glossary_mgr.parse_dual_output(ai_output)

            # Integrate newly harvested terms
            if new_terms:
                self.glossary_mgr.integrate_new_terms(new_terms)

            # Ensure zero residual Chinese characters in translation
            cleaned_translation = self.transliterater.clean_text(translation)

            # Mark completed & append to output file
            tracker.mark_completed(
                chapter_index=chapter.index,
                chapter_title=translated_title,
                translated_text=cleaned_translation,
                elapsed_seconds=elapsed,
            )

            processed_in_session += 1

            if progress_callback:
                try:
                    progress_callback(chapter.index, total_chapters, translated_title, elapsed, len(new_terms))
                except TypeError:
                    progress_callback(chapter.index, total_chapters, translated_title, elapsed)

        # 5. Optional Post-Processing via ReplaceEngine
        if run_post_processing and output_filepath.exists():
            self._run_post_processing(output_filepath)

        return True

    def _run_post_processing(self, output_filepath: Path) -> None:
        """
        Runs ReplaceEngine as a secondary guardrail against de-converted phrases
        and ensures standard character capitalization.
        """
        dict_dir = self.base_dir / "resources" / "dictionaries"
        deconvert_dict_path = dict_dir / "deconvert_dict.json"

        custom_mapping = {}
        if deconvert_dict_path.exists():
            try:
                data = json.loads(deconvert_dict_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    custom_mapping.update(data)
            except Exception:
                pass

        if custom_mapping:
            replacer = ReplaceEngine(custom_mapping=custom_mapping)
            replacer.replace_file(output_filepath, output_filepath, show_progress=False)
