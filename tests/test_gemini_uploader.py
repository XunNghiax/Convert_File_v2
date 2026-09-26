from pathlib import Path
from character_scanner.gemini_uploader import GeminiUploader

def test_gemini_uploader_init():
    uploader = GeminiUploader(Path("user_data/chrome_profiles/chrome_data_1"))
    assert uploader.profile_dir == Path("user_data/chrome_profiles/chrome_data_1")
    assert uploader.json_extractor is not None
