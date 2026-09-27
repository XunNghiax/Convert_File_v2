from pathlib import Path
from src.scanner.gemini_uploader import GeminiUploader

def test_gemini_uploader_init():
    uploader = GeminiUploader("chrome_profiles")
    assert uploader.profile_dir.exists()
    assert (uploader.profile_dir / "Default").exists()
    assert uploader.json_extractor is not None
