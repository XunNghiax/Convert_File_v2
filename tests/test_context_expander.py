from character_scanner.context_expander import ContextExpander

def test_expand_full_sentence():
    expander = ContextExpander(min_length=15)
    line = "Sáng hôm sau, Trương Tử Kiến thức dậy. Hắn đi ra bờ sông ngắm cảnh."
    start = line.index("Trương Tử Kiến")
    end = start + len("Trương Tử Kiến")
    ctx = expander.expand_context(line, start, end)
    assert ctx == "Sáng hôm sau, Trương Tử Kiến thức dậy."

def test_expand_short_sentence():
    expander = ContextExpander(min_length=30)
    line = "Hắn tỉnh lại. Long Kiếm Phi thở dài một hơi. Trời lại đổ mưa."
    start = line.index("Long Kiếm Phi")
    end = start + len("Long Kiếm Phi")
    ctx = expander.expand_context(line, start, end)
    assert "Long Kiếm Phi thở dài một hơi." in ctx
