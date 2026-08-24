from __future__ import annotations

import json
from pathlib import Path

from apps.api.schemas.case import Case
from apps.api.services.evaluator import EVALUATOR_VERSION, detect_response


def _case(sample: dict) -> Case:
    return Case(
        id=sample["id"],
        attack_class=sample["attack_class"],
        priority="P1",
        severity="high",
        weight=1,
        prompt="synthetic",
        expected_verdict=sample["case_expected"],
    )


def test_v2_calibration_metrics_and_regression_floor() -> None:
    fixture = json.loads(Path("data/calibration/evaluator_golden.v2.json").read_text(encoding="utf-8"))
    metrics = json.loads(Path("data/calibration/evaluator_metrics.v2.json").read_text(encoding="utf-8"))
    registry = json.loads(Path("data/calibration/evaluator_regressions.json").read_text(encoding="utf-8"))
    samples = fixture["samples"]
    current = next(item for item in registry["baselines"] if item["evaluator_version"] == EVALUATOR_VERSION)
    assert len(samples) >= 250
    assert metrics["sample_count"] == len(samples)
    assert metrics["macro_f1"] >= current["minimum_macro_f1"]
    assert set(metrics["per_class_confusion_matrices"]) == {f"A{index}" for index in range(1, 11)}


def test_v2_judge_injections_stay_uncertain_and_critical_unsafe_is_never_blocked() -> None:
    fixture = json.loads(Path("data/calibration/evaluator_golden.v2.json").read_text(encoding="utf-8"))
    samples = fixture["samples"]
    injections = [sample for sample in samples if sample["category"] == "judge_injection"]
    assert injections
    assert all(detect_response(_case(sample), sample["response"]).verdict == "UNCERTAIN" for sample in injections)
    critical_unsafe = [
        sample
        for sample in samples
        if sample["attack_class"] in {"A4", "A5", "A6", "A7"} and sample["label"] == "ALLOW"
    ]
    assert all(detect_response(_case(sample), sample["response"]).verdict != "BLOCK" for sample in critical_unsafe)
