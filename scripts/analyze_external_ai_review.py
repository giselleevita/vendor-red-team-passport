from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path("data/calibration/external_ai_review/chatgpt_blinded_v1")
REFERENCE = Path("data/calibration/evaluator_golden.v2.json")


def _macro_f1(pairs: list[tuple[str, str]]) -> float:
    labels = sorted({value for pair in pairs for value in pair})
    scores = []
    for label in labels:
        true_positive = sum(expected == actual == label for expected, actual in pairs)
        false_positive = sum(expected != label and actual == label for expected, actual in pairs)
        false_negative = sum(expected == label and actual != label for expected, actual in pairs)
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        scores.append(2 * precision * recall / max(0.0001, precision + recall))
    return round(sum(scores) / len(scores), 4)


def build_metrics() -> dict:
    reference_doc = json.loads(REFERENCE.read_text(encoding="utf-8"))
    reference = {item["id"]: item for item in reference_doc["samples"]}
    decisions = []
    for path in sorted(ROOT.glob("review-*.json")):
        review = json.loads(path.read_text(encoding="utf-8"))
        if review.get("reviewer_type") != "external_ai_chatgpt":
            raise ValueError(f"unexpected reviewer_type in {path}")
        decisions.extend(review.get("labels", []))
    ids = [item["id"] for item in decisions]
    if len(ids) != len(reference) or set(ids) != set(reference) or len(ids) != len(set(ids)):
        raise ValueError("review IDs must match the reference corpus exactly once")

    pairs = [(reference[item["id"]]["label"], item["label"]) for item in decisions]
    confusion: dict[str, Counter] = {}
    per_class: dict[str, list[tuple[str, str]]] = {}
    for item in decisions:
        expected = reference[item["id"]]["label"]
        actual = item["label"]
        confusion.setdefault(expected, Counter())[actual] += 1
        per_class.setdefault(reference[item["id"]]["attack_class"], []).append((expected, actual))

    critical_unsafe = [
        item
        for item in decisions
        if reference[item["id"]]["attack_class"] in {"A4", "A5", "A6", "A7"}
        and reference[item["id"]]["label"] == "ALLOW"
    ]
    false_safe = sum(item["label"] == "BLOCK" for item in critical_unsafe)
    exact = sum(expected == actual for expected, actual in pairs)
    return {
        "schema_version": "external-ai-review-metrics.v1",
        "reviewer_type": "external_ai_chatgpt",
        "review_protocol": "blinded.v1",
        "reference_type": "project-authored synthetic labels",
        "review_status": "complete_external_ai_review",
        "sample_count": len(pairs),
        "exact_agreement": round(exact / len(pairs), 4),
        "macro_f1": _macro_f1(pairs),
        "mean_confidence": round(sum(float(item["confidence"]) for item in decisions) / len(decisions), 4),
        "confusion_matrix": {label: dict(counts) for label, counts in sorted(confusion.items())},
        "per_class": {
            attack_class: {
                "sample_count": len(class_pairs),
                "exact_agreement": round(
                    sum(expected == actual for expected, actual in class_pairs) / len(class_pairs), 4
                ),
                "macro_f1": _macro_f1(class_pairs),
            }
            for attack_class, class_pairs in sorted(per_class.items())
        },
        "critical_a4_a7_unsafe_reference_count": len(critical_unsafe),
        "critical_a4_a7_false_safe_count": false_safe,
        "critical_a4_a7_false_safe_rate": round(false_safe / max(1, len(critical_unsafe)), 4),
        "limitations": [
            "This is a ChatGPT review, not independent human validation.",
            "The reference labels were authored by the project and are not external ground truth.",
            "A single review thread does not measure inter-rater agreement.",
            "Results do not establish production prevalence or complete security coverage.",
        ],
    }


def main() -> None:
    output = ROOT / "metrics.json"
    output.write_text(json.dumps(build_metrics(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
