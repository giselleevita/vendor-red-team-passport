from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ALLOWED_LABELS = {"BLOCK", "ALLOW", "STRICT_JSON", "NON_JSON", "UNCERTAIN"}


def load_labels(path: Path, expected_ids: set[str]) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or set(rows[0]) != {"id", "label", "notes"}:
        raise ValueError("review file must contain exactly id,label,notes columns")
    labels: dict[str, str] = {}
    for row in rows:
        sample_id = row["id"].strip()
        label = row["label"].strip().upper()
        if sample_id in labels:
            raise ValueError(f"duplicate sample id: {sample_id}")
        if sample_id not in expected_ids:
            raise ValueError(f"unknown sample id: {sample_id}")
        if label not in ALLOWED_LABELS:
            raise ValueError(f"invalid or missing label for {sample_id}")
        labels[sample_id] = label
    missing = expected_ids - set(labels)
    if missing:
        raise ValueError(f"review file is incomplete: {len(missing)} labels missing")
    return labels


def agreement(first: dict[str, str], second: dict[str, str]) -> dict[str, float]:
    ids = sorted(first)
    observed = sum(first[item] == second[item] for item in ids) / len(ids)
    first_counts = Counter(first.values())
    second_counts = Counter(second.values())
    expected = sum((first_counts[label] / len(ids)) * (second_counts[label] / len(ids)) for label in ALLOWED_LABELS)
    kappa = (observed - expected) / (1 - expected) if expected < 1 else 1.0
    return {"raw_agreement": round(observed, 4), "cohen_kappa": round(kappa, 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate two independent blinded annotation files.")
    parser.add_argument("reviewer_one", type=Path)
    parser.add_argument("reviewer_two", type=Path)
    parser.add_argument("--kit", type=Path, default=Path("data/calibration/independent_review/blinded_samples.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/independent-review.json"))
    args = parser.parse_args()
    kit = json.loads(args.kit.read_text(encoding="utf-8"))
    ids = {item["id"] for item in kit["samples"]}
    first = load_labels(args.reviewer_one, ids)
    second = load_labels(args.reviewer_two, ids)
    result = {
        "schema_version": "independent-review-results.v1",
        "review_status": "human_reviewed",
        "sample_count": len(ids),
        "inter_rater": agreement(first, second),
        "adjudication_required_count": sum(first[item] != second[item] for item in ids),
        "note": "Evaluator accuracy is calculated only after disagreements receive a separate adjudicated label.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
