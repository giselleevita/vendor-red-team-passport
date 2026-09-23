from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    source = json.loads(Path("data/calibration/evaluator_golden.v2.json").read_text(encoding="utf-8"))
    samples = source["samples"]
    output = Path("data/calibration/independent_review")
    output.mkdir(parents=True, exist_ok=True)
    blinded = [
        {
            "id": item["id"],
            "attack_class": item["attack_class"],
            "case_expected": item["case_expected"],
            "category": item["category"],
            "language": item["language"],
            "response": item["response"],
        }
        for item in samples
    ]
    (output / "blinded_samples.json").write_text(
        json.dumps(
            {
                "schema_version": "independent-review.v1",
                "review_status": "pending",
                "sample_count": len(blinded),
                "samples": blinded,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with (output / "reviewer_template.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "label", "notes"])
        writer.writeheader()
        writer.writerows({"id": item["id"], "label": "", "notes": ""} for item in blinded)


if __name__ == "__main__":
    main()
