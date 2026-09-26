from character_scanner.benchmark import Evaluator

def test_evaluator():
    ground_truth = [
        {"ten": "Trương Tử Kiến", "dong_xuat_hien": 9},
        {"ten": "Lâm Ngọc Chi", "dong_xuat_hien": 17}
    ]
    predictions = [
        {"target": "Trương Tử Kiến", "dong_xuat_hien": 9},
        {"target": "Người Khác", "dong_xuat_hien": 20}
    ]
    ev = Evaluator()
    metrics = ev.evaluate(predictions, ground_truth)
    assert metrics["matched_exact"] == 1
    assert metrics["recall_exact"] == 0.5
    assert metrics["precision_exact"] == 0.5
