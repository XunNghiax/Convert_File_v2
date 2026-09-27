from src.replacer.replace_engine import ReplaceEngine

def test_prefix_guard_prevents_duplicate_expansion():
    """
    Kiểm tra Prefix Guard:
    Khi có quy tắc Kiếm Phi -> Long Kiếm Phi:
    - Nếu trước 'Kiếm Phi' đã có 'Long ' thì KHÔNG ĐƯỢC thay tiếp thành 'Long Long Kiếm Phi'.
    - Nếu đứng độc lập 'Kiếm Phi' thì được thay thành 'Long Kiếm Phi'.
    """
    custom_map = {
        "Kiếm Phi": "Long Kiếm Phi"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    # 1. Đứng độc lập: Được thay thế thành Long Kiếm Phi
    text1 = "Kiếm Phi mỉm cười gật đầu."
    assert engine.replace_line(text1) == "Long Kiếm Phi mỉm cười gật đầu."

    # 2. Đã có họ Long đi trước: Giữ nguyên, không biến thành Long Long Kiếm Phi!
    text2 = "Long Kiếm Phi bước vào phòng cùng Kiếm Phi."
    result2 = engine.replace_line(text2)
    assert result2 == "Long Kiếm Phi bước vào phòng cùng Long Kiếm Phi."
    assert "Long Long Kiếm Phi" not in result2

def test_negative_context_guard_preserves_descriptive_phrases():
    """
    Kiểm tra Negative Context Guard:
    - Cụm từ miêu tả 'bóng hình xinh đẹp' khi đứng sau lượng từ / quán từ ('một', 'những', 'vóc dáng'...)
      phải được BẢO VỆ NGUYÊN VẸN, không bị thay thế thành 'Thiến Ảnh'.
    - Khi là tên nhân vật (đứng sau đại từ hoặc họ) thì được thay thế đúng.
    """
    custom_map = {
        "bóng hình xinh đẹp": "Thiến Ảnh",
        "Thẩm bóng hình xinh đẹp": "Thẩm Thiến Ảnh"
    }
    engine = ReplaceEngine(custom_mapping=custom_map)

    # 1. Câu miêu tả thuần túy: Có 'một' -> Không được thay thế!
    text_desc1 = "Đó thật là một bóng hình xinh đẹp khiến người mê đắm."
    assert engine.replace_line(text_desc1) == "Đó thật là một bóng hình xinh đẹp khiến người mê đắm."

    # 2. Câu miêu tả: Có 'vóc dáng' -> Không được thay thế!
    text_desc2 = "Nhìn vóc dáng bóng hình xinh đẹp từ đằng xa."
    assert engine.replace_line(text_desc2) == "Nhìn vóc dáng bóng hình xinh đẹp từ đằng xa."

    # 3. Có họ đầy đủ: Ưu tiên Longest-Match
    text_name1 = "Thẩm bóng hình xinh đẹp bước ra chào mọi người."
    assert engine.replace_line(text_name1) == "Thẩm Thiến Ảnh bước ra chào mọi người."

    # 4. Tên riêng không có từ miêu tả phía trước
    text_name2 = "Nàng bóng hình xinh đẹp khẽ mỉm cười e lệ."
    assert engine.replace_line(text_name2) == "Nàng Thiến Ảnh khẽ mỉm cười e lệ."
