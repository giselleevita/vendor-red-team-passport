from __future__ import annotations

from scripts.analyze_external_ai_review import build_metrics


def test_external_ai_review_is_complete_and_truthfully_labelled() -> None:
    metrics = build_metrics()
    assert metrics["reviewer_type"] == "external_ai_chatgpt"
    assert metrics["reference_type"] == "project-authored synthetic labels"
    assert metrics["sample_count"] == 260
    assert 0 <= metrics["exact_agreement"] <= 1
    assert 0 <= metrics["macro_f1"] <= 1
    assert metrics["limitations"]
