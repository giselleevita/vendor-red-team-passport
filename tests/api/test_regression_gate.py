from __future__ import annotations

from apps.api.services.regression import regression_gate


def _passport(*, run_id: str, gate: str, crit: int, a4_status: str = "PASS") -> dict:
    return {
        "run_id": run_id,
        "summary": {
            "release_gate": gate,
            "critical_failures": crit,
            "overall_score": 50.0,
            "p1_pass_rate": 90.0,
            "p2_pass_rate": 90.0,
            "a9_schema_validity": 99.0,
        },
        "class_scores": [{"attack_class": "A4", "pass_rate": 100.0, "status": a4_status}],
    }


def test_regression_gate_critical_detects_increase() -> None:
    b = _passport(run_id="b", gate="FAIL", crit=0, a4_status="PASS")
    c = _passport(run_id="c", gate="FAIL", crit=1, a4_status="FAIL")
    d = regression_gate(baseline=b, candidate=c, fail_on="critical")
    assert d.ok is False
    assert any("critical_failures increased" in r for r in d.reasons)


def test_regression_gate_gate_mode_only_fails_pass_to_fail() -> None:
    b = _passport(run_id="b", gate="FAIL", crit=0)
    c = _passport(run_id="c", gate="FAIL", crit=0)
    d = regression_gate(baseline=b, candidate=c, fail_on="gate")
    assert d.ok is True

    b2 = _passport(run_id="b2", gate="PASS", crit=0)
    c2 = _passport(run_id="c2", gate="FAIL", crit=0)
    d2 = regression_gate(baseline=b2, candidate=c2, fail_on="gate")
    assert d2.ok is False

