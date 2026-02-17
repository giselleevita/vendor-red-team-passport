from __future__ import annotations

import json

from apps.api.services.claims import build_claim_matrix


def test_claim_matrix_refutes_failed_class() -> None:
    evidences = [
        {
            "case_id": "A4-01",
            "attack_class": "A4",
            "expected_verdict": "BLOCK",
            "actual_verdict": "ALLOW",
            "passed": False,
            "response_excerpt_sanitized": "BEGIN you are ...",
            "timing": {"latency_ms": 10},
        },
        {
            "case_id": "A4-02",
            "attack_class": "A4",
            "expected_verdict": "BLOCK",
            "actual_verdict": "ALLOW",
            "passed": False,
            "response_excerpt_sanitized": "leak",
            "timing": {"latency_ms": 11},
        },
        {
            "case_id": "A9-01",
            "attack_class": "A9",
            "expected_verdict": "STRICT_JSON",
            "actual_verdict": "STRICT_JSON",
            "passed": True,
            "response_excerpt_sanitized": "{\"risk\":0,\"verdict\":\"ok\"}",
            "timing": {"latency_ms": 12},
        },
    ]

    meta = {"model": "x", "created_at_utc": "2026-02-14T00:00:00Z", "suite_version": "1.0.0"}
    passport = {
        "run_id": "r1",
        "summary": {"a9_mode_used": "compat", "a9_strict_supported": False},
        "class_scores": [{"attack_class": "A4"}, {"attack_class": "A9"}],
    }

    matrix = build_claim_matrix(run_id="r1", meta=meta, passport=passport, evidences=evidences)
    by_class = {c["attack_class"]: c for c in matrix["claims"]}

    assert by_class["A4"]["status"] == "REFUTED"
    assert by_class["A4"]["failed"] == 2
    assert by_class["A4"]["total"] == 2
    assert by_class["A4"]["top_evidence"][0]["evidence_url"].startswith("/reports/runs/r1/cases/")

    # A9 passes, but is conditional when strict enforcement isn't proven.
    assert by_class["A9"]["status"] == "CONDITIONAL"


def test_claim_matrix_not_evaluated_when_no_evidence() -> None:
    meta = {}
    passport = {"summary": {}, "class_scores": []}
    matrix = build_claim_matrix(run_id="r1", meta=meta, passport=passport, evidences=[])
    by_class = {c["attack_class"]: c for c in matrix["claims"]}
    assert by_class["A4"]["status"] == "NOT_EVALUATED"

