from apps.api.services.coverage import build_coverage_report
from apps.api.services.taxonomy import TAXONOMY_VERSION, class_taxonomy


def test_taxonomy_matches_actual_case_meanings() -> None:
    taxonomy = class_taxonomy()
    assert taxonomy["A4"]["label"] == "System prompt leakage"
    assert taxonomy["A4"]["owasp"] == ["LLM07:2025"]
    assert taxonomy["A5"]["owasp"] == ["LLM02:2025"]
    assert taxonomy["A7"]["owasp"] == []
    assert taxonomy["A8"]["relationship"] == "policy-safety"
    assert taxonomy["A10"]["owasp"] == ["LLM10:2025"]


def test_coverage_v2_is_versioned_and_does_not_overclaim() -> None:
    report = build_coverage_report(evaluated_classes=[f"A{index}" for index in range(1, 11)])
    assert report["version"] == "coverage.v2"
    assert report["taxonomy_version"] == TAXONOMY_VERSION
    rows = {row["attack_class"]: row for row in report["by_attack_class"]}
    assert rows["A7"]["owasp"] == []
    assert rows["A9"]["relationship"] == "related"
    assert report["summary"]["suite_process_functions"] == ["GOVERN", "MAP"]


def test_coverage_v2_quantifies_cases_and_carries_disclaimer() -> None:
    counts = {f"A{i}": 10 for i in range(1, 11)}
    report = build_coverage_report(evaluated_classes=list(counts), case_counts=counts)
    assert "not certification" in report["disclaimer"].lower()
    assert report["total_cases"] == 100
    rows = {row["attack_class"]: row for row in report["by_attack_class"]}
    assert all(rows[f"A{i}"]["cases"] == 10 for i in range(1, 11))
    assert rows["A1"]["owasp"][0]["id"] == "LLM01:2025"


def test_coverage_v2_case_counts_default_to_zero_when_absent() -> None:
    report = build_coverage_report(evaluated_classes=["A1", "A2"])
    rows = {row["attack_class"]: row for row in report["by_attack_class"]}
    assert rows["A1"]["cases"] == 0
    assert report["total_cases"] == 0
