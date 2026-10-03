from tools.migrate_dictionaries_to_kv import convert_dict_list_to_kv

def test_convert_character_dict_to_kv():
    raw_list = [
        {"id": "ch-1", "source": "Ung nhân", "target": "Yasuhito", "Tag": "Thiên hoàng"},
        {"id": "ch-2", "source": "thực hạnh tiểu bách hợp", "target": "jikko sayuri", "Tag": ""}
    ]
    result = convert_dict_list_to_kv(raw_list, is_character=True)
    assert result == {
        "ung nhân": "Yasuhito",
        "thực hạnh tiểu bách hợp": "Jikko Sayuri"
    }

def test_convert_common_dict_to_kv():
    raw_list = [
        {"id": "co-1", "source": "Đông Phương", "target": "phương đông", "category": "Khớp"}
    ]
    result = convert_dict_list_to_kv(raw_list, is_character=False)
    assert result == {
        "đông phương": "phương đông"
    }
