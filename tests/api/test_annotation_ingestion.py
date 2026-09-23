from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.ingest_annotations import agreement, load_labels


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "label", "notes"])
        writer.writeheader()
        writer.writerows(rows)


def test_annotation_ingestion_requires_complete_valid_unique_labels(tmp_path: Path) -> None:
    path = tmp_path / "review.csv"
    _write(path, [{"id": "one", "label": "BLOCK", "notes": ""}])
    with pytest.raises(ValueError, match="incomplete"):
        load_labels(path, {"one", "two"})

    _write(
        path,
        [
            {"id": "one", "label": "BLOCK", "notes": ""},
            {"id": "one", "label": "ALLOW", "notes": ""},
        ],
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_labels(path, {"one"})


def test_inter_rater_agreement_is_reproducible() -> None:
    result = agreement({"one": "BLOCK", "two": "ALLOW"}, {"one": "BLOCK", "two": "ALLOW"})
    assert result == {"raw_agreement": 1.0, "cohen_kappa": 1.0}
