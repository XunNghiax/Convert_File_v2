from src.scanner.json_extractor import JSONExtractor

def test_extract_code_block_json():
    raw = """Dưới đây là kết quả đã biên tập:
```json
[
  {
    "id": "ch_0001",
    "is_character": true,
    "source": "Trương Tử Kiến",
    "target": "Trương Tử Kiến"
  }
]
```
Hy vọng bạn hài lòng!"""
    extractor = JSONExtractor()
    data = extractor.extract_json(raw)
    assert len(data) == 1
    assert data[0]["source"] == "Trương Tử Kiến"

def test_extract_fallback_brackets():
    raw = """Đây là kết quả:
[
  {"id": "ch_0001", "is_character": true, "source": "Lâm Ngọc Chi", "target": "Lâm Ngọc Chi"}
]"""
    extractor = JSONExtractor()
    data = extractor.extract_json(raw)
    assert len(data) == 1
    assert data[0]["target"] == "Lâm Ngọc Chi"
