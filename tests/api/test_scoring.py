from apps.api.schemas.case import Case
from apps.api.schemas.result import CaseResult
from apps.api.services.scoring import compute_scores


def test_scoring_release_gate_fail_on_critical() -> None:
    cases = [
        Case(
            id="A4-01",
            attack_class="A4",
            priority="P1",
            severity="critical",
            weight=0.2,
            prompt="x",
            expected_verdict="BLOCK",
            tags=[],
            enabled=True,
        )
    ]
    results = [
        CaseResult(
            case_id="A4-01",
            attack_class="A4",
            expected_verdict="BLOCK",
            actual_verdict="ALLOW",
            passed=False,
            response_excerpt="unsafe",
        )
    ]

    summary = compute_scores(cases, results)
    assert summary["critical_failures"] == 1
    assert summary["release_gate"] == "FAIL"
