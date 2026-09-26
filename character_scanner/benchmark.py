import json
from pathlib import Path

class Evaluator:
    def evaluate(self, predictions: list[dict], ground_truth: list[dict]) -> dict:
        gt_set = {(item["ten"].lower().strip(), item["dong_xuat_hien"]) for item in ground_truth}
        gt_names = {item["ten"].lower().strip() for item in ground_truth}

        pred_set = {(p.get("target", "").lower().strip(), p.get("dong_xuat_hien")) for p in predictions}
        pred_names = {p.get("target", "").lower().strip() for p in predictions}

        matched_exact = len(gt_set.intersection(pred_set))
        matched_names = len(gt_names.intersection(pred_names))

        recall_exact = matched_exact / len(gt_set) if gt_set else 0.0
        recall_names = matched_names / len(gt_names) if gt_names else 0.0

        precision_exact = matched_exact / len(pred_set) if pred_set else 0.0
        precision_names = matched_names / len(pred_names) if pred_names else 0.0

        return {
            "total_ground_truth": len(gt_set),
            "total_predictions": len(pred_set),
            "matched_exact": matched_exact,
            "matched_names": matched_names,
            "recall_exact": round(recall_exact, 4),
            "recall_names": round(recall_names, 4),
            "precision_exact": round(precision_exact, 4),
            "precision_names": round(precision_names, 4)
        }
