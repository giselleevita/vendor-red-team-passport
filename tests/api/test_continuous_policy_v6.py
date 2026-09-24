from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas.assurance import AssessmentRecord, AssessmentStatus, DataClassification, RiskTier
from apps.api.schemas.passport import Passport
from apps.api.services.continuous import evaluate_assessment, policy_digest, refresh_expiry, select_policy
from apps.api.services.run_store import save_json_artifact, save_passport, save_run_meta


def _seed_run(run_id: str, tenant_id: str, *, gate: str = "PASS", critical: int = 0) -> None:
    save_run_meta(run_id, {"run_id": run_id, "tenant_id": tenant_id, "model": "fictional/model", "profile": "quick_gates", "suite_version": "1.0.0"})
    save_passport(run_id, Passport(run_id=run_id, summary={"overall_score": 90.0, "p1_pass_rate": 100.0, "p2_pass_rate": 90.0, "a9_schema_validity": 100.0, "a9_mode_used": "compat", "a9_strict_supported": False, "critical_failures": critical, "release_gate": gate, "review_required_count": 0}, class_scores=[], failed_cases=[], executive_verdict={}))
    save_json_artifact(run_id, "manifest.json", {"schema_version": "manifest.v1", "synthetic": True})


def _assessment(*, due: datetime | None = None) -> AssessmentRecord:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return AssessmentRecord(assessment_id="11111111-1111-1111-1111-111111111111", tenant_id="tenant-a", vendor_name="Vendor A", system_name="Assistant", use_case="Defensive testing", owner="Security", risk_tier=RiskTier.HIGH, data_classification=DataClassification.CONFIDENTIAL, status=AssessmentStatus.APPROVED, review_due_at=due, linked_run_ids=["baseline"], baseline_run_id="baseline", baseline_set_at=now, baseline_set_by="reviewer", created_at=now, updated_at=now, created_by="operator")


def test_policy_matrix_and_digest_are_stable() -> None:
    for risk in RiskTier:
        for classification in DataClassification:
            policy = select_policy(risk_tier=risk, data_classification=classification)
            assert policy.schema_version == "policy.v1"
            assert policy_digest(policy) == policy_digest(policy)
    try:
        select_policy(risk_tier="low", data_classification="public", policy_id="strict")
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched policy accepted")


def test_policy_pass_fail_unknown_and_version_compatibility(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("baseline", "tenant-a")
    _seed_run("passing", "tenant-a")
    _seed_run("failing", "tenant-a", gate="FAIL", critical=1)
    record = _assessment()
    assert evaluate_assessment(record, "passing")["outcome"] == "PASS"
    failed = evaluate_assessment(record, "failing")
    assert failed["outcome"] == "FAIL"
    assert {"DRIFT_REGRESSION", "RELEASE_GATE_FAILED"} <= set(failed["reason_codes"])
    meta_path = tmp_path / "reports" / "runs" / "passing" / "run.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["suite_version"] = "2.0.0"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    incompatible = evaluate_assessment(record, "passing")
    assert incompatible["outcome"] == "UNKNOWN"
    assert "INCOMPATIBLE_EVALUATION_VERSION" in incompatible["reason_codes"]


def test_missing_malformed_and_expired_evidence_fail_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("baseline", "tenant-a")
    _seed_run("candidate", "tenant-a")
    manifest = tmp_path / "reports" / "runs" / "candidate" / "manifest.json"
    manifest.unlink()
    incomplete = evaluate_assessment(_assessment(), "candidate")
    assert incomplete["outcome"] == "UNKNOWN"
    assert "MANDATORY_EVIDENCE_MISSING_MANIFEST" in incomplete["reason_codes"]
    (tmp_path / "reports" / "runs" / "candidate" / "passport.json").write_text("{broken", encoding="utf-8")
    malformed = evaluate_assessment(_assessment(), "candidate")
    assert malformed["outcome"] == "UNKNOWN"
    expired_record = _assessment(due=datetime(2026, 9, 22, tzinfo=UTC))
    expired = evaluate_assessment(expired_record, "missing", now=datetime(2026, 9, 23, tzinfo=UTC))
    assert expired["outcome"] == "FAIL"
    assert refresh_expiry(expired_record, now=datetime(2026, 9, 23, tzinfo=UTC)) is True
    assert expired_record.status == AssessmentStatus.EXPIRED


def test_baseline_api_requires_approval_and_preserves_history(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("baseline", "tenant-a")
    _seed_run("replacement", "tenant-a")
    client = TestClient(app)
    operator = auth_header(tenant_id="tenant-a", roles=["operator"])
    auditor = auth_header(tenant_id="tenant-a", roles=["auditor"])
    payload = {"vendor_name": "Vendor A", "system_name": "Assistant", "use_case": "Defensive review workflow", "owner": "Security", "risk_tier": "high", "data_classification": "confidential", "linked_run_ids": ["baseline"]}
    assessment_id = client.post("/assessments", json=payload, headers=operator).json()["assessment_id"]
    body = {"run_id": "baseline", "rationale": "Initial approved evidence baseline."}
    assert client.put(f"/assessments/{assessment_id}/baseline", json=body, headers=auditor).status_code == 409
    assert client.post(f"/assessments/{assessment_id}/submit", headers=operator).status_code == 200
    assert client.post(f"/assessments/{assessment_id}/decision", json={"verdict": "approved", "rationale": "Evidence satisfies the documented assurance policy."}, headers=auditor).status_code == 200
    assert client.put(f"/assessments/{assessment_id}/baseline", json=body, headers=auditor).status_code == 200
    replaced = client.put(f"/assessments/{assessment_id}/baseline", json={"run_id": "replacement", "rationale": "Reviewer approved an explicit replacement baseline."}, headers=auditor)
    assert replaced.json()["baseline_history"][0]["run_id"] == "baseline"
