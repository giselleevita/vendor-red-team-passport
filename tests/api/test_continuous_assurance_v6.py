from __future__ import annotations

import hashlib
import hmac
import json
import socket
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas.assurance import AssessmentRecord, AssessmentStatus, DataClassification, RiskTier
from apps.api.schemas.operations import ScheduleRecord, WebhookRecord
from apps.api.schemas.passport import Passport
from apps.api.services.assurance import load_assessment, save_assessment
from apps.api.services.continuous import evaluate_assessment, policy_digest, select_policy
from apps.api.services.operations import (
    complete_scheduled_job,
    deliver_webhook,
    emit_event,
    portfolio,
    process_due_deliveries,
    process_due_schedules,
    process_expired_approvals,
    save_schedule,
    save_webhook,
    trigger_schedule,
    validate_timezone,
    validate_webhook_url,
)
from apps.api.services.run_store import save_json_artifact, save_passport, save_run_meta


def _seed_run(run_id: str, tenant_id: str, *, gate: str = "PASS", critical: int = 0) -> None:
    save_run_meta(run_id, {"run_id": run_id, "tenant_id": tenant_id, "model": "fictional/model", "profile": "quick_gates", "suite_version": "1.0.0"})
    save_passport(run_id, Passport(run_id=run_id, summary={"overall_score": 90.0, "p1_pass_rate": 100.0, "p2_pass_rate": 90.0, "a9_schema_validity": 100.0, "a9_mode_used": "compat", "a9_strict_supported": False, "critical_failures": critical, "release_gate": gate, "review_required_count": 0}, class_scores=[], failed_cases=[], executive_verdict={}))
    save_json_artifact(run_id, "manifest.json", {"schema_version": "manifest.v1", "synthetic": True})


def _assessment(*, assessment_id: str = "11111111-1111-1111-1111-111111111111", due: datetime | None = None) -> AssessmentRecord:
    now = datetime(2026, 9, 23, tzinfo=UTC)
    return AssessmentRecord(assessment_id=assessment_id, tenant_id="tenant-a", vendor_name="Vendor A", system_name="Assistant", use_case="Defensive testing", owner="Security", risk_tier=RiskTier.HIGH, data_classification=DataClassification.CONFIDENTIAL, status=AssessmentStatus.APPROVED, review_due_at=due, linked_run_ids=["baseline"], baseline_run_id="baseline", baseline_set_at=now, baseline_set_by="reviewer", created_at=now, updated_at=now, created_by="operator")


def test_policy_selection_covers_every_risk_and_data_combination() -> None:
    for risk in RiskTier:
        for classification in DataClassification:
            policy = select_policy(risk_tier=str(risk), data_classification=str(classification))
            assert policy.schema_version == "policy.v1"
            assert policy_digest(policy).startswith("sha256:")
            assert policy_digest(policy) == policy_digest(policy)


def test_missing_and_expired_evidence_fail_closed(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    record = _assessment(due=datetime(2026, 9, 22, tzinfo=UTC))
    result = evaluate_assessment(record, "missing", now=datetime(2026, 9, 23, tzinfo=UTC))
    assert result["outcome"] == "FAIL"
    assert set(result["reason_codes"]) == {"APPROVAL_EXPIRED", "EVIDENCE_MISSING"}


def test_policy_evaluation_pass_failure_and_incompatible_versions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("baseline", "tenant-a")
    _seed_run("passing", "tenant-a")
    _seed_run("failing", "tenant-a", gate="FAIL", critical=1)
    record = _assessment()
    passed = evaluate_assessment(record, "passing")
    assert passed["outcome"] == "PASS"
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


def test_explicit_policy_mismatch_and_invalid_timezone_fail() -> None:
    try:
        select_policy(risk_tier="low", data_classification="public", policy_id="strict")
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched policy accepted")
    try:
        validate_timezone("Mars/Olympus_Mons")
    except ValueError:
        pass
    else:
        raise AssertionError("invalid timezone accepted")


def test_malformed_or_incomplete_candidate_is_unknown(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("baseline", "tenant-a")
    _seed_run("candidate", "tenant-a")
    (tmp_path / "reports" / "runs" / "candidate" / "manifest.json").unlink()
    missing_manifest = evaluate_assessment(_assessment(), "candidate")
    assert missing_manifest["outcome"] == "UNKNOWN"
    assert "MANDATORY_EVIDENCE_MISSING_MANIFEST" in missing_manifest["reason_codes"]
    (tmp_path / "reports" / "runs" / "candidate" / "passport.json").write_text("{broken", encoding="utf-8")
    malformed = evaluate_assessment(_assessment(), "candidate")
    assert malformed["outcome"] == "UNKNOWN"
    assert "EVIDENCE_MISSING" in malformed["reason_codes"]


def test_baseline_requires_approval_and_preserves_history(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("baseline", "tenant-a")
    _seed_run("replacement", "tenant-a")
    client = TestClient(app)
    operator = auth_header(tenant_id="tenant-a", roles=["operator"])
    auditor = auth_header(tenant_id="tenant-a", roles=["auditor"])
    payload = {"vendor_name": "Vendor A", "system_name": "Assistant", "use_case": "Defensive review workflow", "owner": "Security", "risk_tier": "high", "data_classification": "confidential", "linked_run_ids": ["baseline"]}
    created = client.post("/assessments", json=payload, headers=operator).json()
    assessment_id = created["assessment_id"]
    denied = client.put(f"/assessments/{assessment_id}/baseline", json={"run_id": "baseline", "rationale": "Initial approved evidence baseline."}, headers=auditor)
    assert denied.status_code == 409
    assert client.post(f"/assessments/{assessment_id}/submit", headers=operator).status_code == 200
    assert client.post(f"/assessments/{assessment_id}/decision", json={"verdict": "approved", "rationale": "Evidence satisfies the documented assurance policy."}, headers=auditor).status_code == 200
    assert client.put(f"/assessments/{assessment_id}/baseline", json={"run_id": "baseline", "rationale": "Initial approved evidence baseline."}, headers=auditor).status_code == 200
    replaced = client.put(f"/assessments/{assessment_id}/baseline", json={"run_id": "replacement", "rationale": "Reviewer approved an explicit replacement baseline."}, headers=auditor)
    assert replaced.status_code == 200
    assert replaced.json()["baseline_run_id"] == "replacement"
    assert replaced.json()["baseline_history"][0]["run_id"] == "baseline"


def test_schedule_claim_is_idempotent_and_tenant_scoped(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    due = datetime(2026, 9, 23, tzinfo=UTC)
    record = ScheduleRecord(schedule_id="22222222-2222-2222-2222-222222222222", tenant_id="tenant-a", assessment_id="11111111-1111-1111-1111-111111111111", profile="quick_gates", cadence_minutes=60, timezone="UTC", enabled=True, next_run_at=due, created_at=due, updated_at=due, created_by="operator")
    save_schedule(record)
    first = trigger_schedule(record.schedule_id, now=due)
    assert first["schedule_id"] == record.schedule_id
    assert process_due_schedules(now=due) == 0
    repeated = trigger_schedule(record.schedule_id, now=due, force=True)
    assert repeated["job_id"] == first["job_id"]


def test_schedule_and_webhook_api_authorization_and_validation(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    assessment = _assessment()
    save_assessment(assessment)
    client = TestClient(app)
    operator = auth_header(tenant_id="tenant-a", roles=["operator"])
    admin = auth_header(tenant_id="tenant-a", roles=["admin"])
    other = auth_header(tenant_id="tenant-b", roles=["admin"])
    invalid = client.post("/assurance/schedules", json={"assessment_id": assessment.assessment_id, "profile": "quick_gates", "cadence_minutes": 60, "timezone": "Invalid/Zone"}, headers=operator)
    assert invalid.status_code == 422
    hidden = client.post("/assurance/schedules", json={"assessment_id": assessment.assessment_id, "profile": "quick_gates", "cadence_minutes": 60}, headers=other)
    assert hidden.status_code == 404
    created = client.post("/assurance/schedules", json={"assessment_id": assessment.assessment_id, "profile": "quick_gates", "cadence_minutes": 60, "next_run_at": "2026-09-23T00:00:00Z"}, headers=operator)
    assert created.status_code == 201
    schedule_id = created.json()["schedule_id"]
    assert client.get("/assurance/schedules", headers=operator).json()["count"] == 1
    assert client.patch(f"/assurance/schedules/{schedule_id}", json={"enabled": False, "timezone": "Europe/Copenhagen"}, headers=operator).json()["enabled"] is False
    assert client.patch(f"/assurance/schedules/{schedule_id}", json={"timezone": "Bad/Timezone"}, headers=operator).status_code == 422
    triggered = client.post(f"/assurance/schedules/{schedule_id}/trigger", headers=operator)
    assert triggered.status_code == 202
    assert triggered.json()["status"] == "queued"
    assert client.post("/assurance/webhooks", json={"name": "bad", "url": "http://example.test/hook", "secret_env": "VENDOR_RTP_WEBHOOK_SECRET_TEST", "key_id": "key-1"}, headers=admin).status_code == 422
    webhook = client.post("/assurance/webhooks", json={"name": "SOC", "url": "https://example.test/hook", "secret_env": "VENDOR_RTP_WEBHOOK_SECRET_TEST", "key_id": "key-1"}, headers=admin)
    assert webhook.status_code == 201
    webhook_id = webhook.json()["webhook_id"]
    assert client.patch(f"/assurance/webhooks/{webhook_id}", json={"enabled": False, "name": "SOC disabled"}, headers=admin).json()["enabled"] is False
    assert client.patch(f"/assurance/webhooks/{webhook_id}", json={"url": "https://example.test/hook?token=x"}, headers=admin).status_code == 422
    assert client.get("/assurance/webhooks", headers=operator).status_code == 403
    assert client.get("/assurance/portfolio", headers=operator).status_code == 200


def test_webhook_validation_signing_redaction_and_replay_safety(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("VENDOR_RTP_WEBHOOK_SECRET_TEST", "rotation-secret")
    assert validate_webhook_url("https://events.example.test/vendor-rtp")
    for invalid in ("http://events.example.test/hook", "https://user:pass@example.test/hook", "https://example.test/hook?secret=x"):
        try:
            validate_webhook_url(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe webhook URL accepted")
    for private_target in ("https://localhost/hook", "https://127.0.0.1/hook", "https://10.0.0.1/hook"):
        try:
            validate_webhook_url(private_target)
        except ValueError:
            pass
        else:
            raise AssertionError("private webhook target accepted")
    now = datetime(2026, 9, 23, tzinfo=UTC)
    webhook = WebhookRecord(webhook_id="33333333-3333-3333-3333-333333333333", tenant_id="tenant-a", name="SOC", url="https://events.example.test/vendor-rtp", key_id="key-2026-09", enabled=True, created_at=now, created_by="admin", **{"secret_env": "VENDOR_RTP_WEBHOOK_SECRET_TEST"})
    save_webhook(webhook)
    delivery = emit_event("tenant-a", "policy.failed", {"assessment_id": "a"})[0]
    seen: list[dict] = []

    class Response:
        def raise_for_status(self):
            return None

    def fake_post(url, *, content, headers, timeout, follow_redirects):
        seen.append({"url": url, "content": content, "headers": headers, "timeout": timeout})
        assert follow_redirects is False
        expected = hmac.new(b"rotation-secret", f"{headers['X-Vendor-RTP-Timestamp']}.{content}".encode(), hashlib.sha256).hexdigest()
        assert headers["X-Vendor-RTP-Signature"] == f"v1={expected}"
        return Response()

    monkeypatch.setattr("apps.api.services.operations.httpx.post", fake_post)
    monkeypatch.setattr("apps.api.services.operations.socket.getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))])
    assert deliver_webhook(delivery.delivery_id, now=now).status == "succeeded"
    assert deliver_webhook(delivery.delivery_id, now=now).status == "succeeded"
    assert len(seen) == 1
    client = TestClient(app)
    listed = client.get("/assurance/webhooks", headers=auth_header(tenant_id="tenant-a", roles=["admin"]))
    assert listed.json()["items"][0]["secret_configured"] is True
    assert "secret_env" not in listed.json()["items"][0]
    assert "rotation-secret" not in json.dumps(listed.json())


def test_webhook_retry_dead_letter_and_delivery_api(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("VENDOR_RTP_WEBHOOK_SECRET_TEST", "rotation-secret")
    now = datetime(2026, 9, 23, tzinfo=UTC)
    webhook = WebhookRecord(webhook_id="44444444-4444-4444-4444-444444444444", tenant_id="tenant-a", name="SOC", url="https://events.example.test/hook", key_id="key-1", enabled=True, created_at=now, created_by="admin", **{"secret_env": "VENDOR_RTP_WEBHOOK_SECRET_TEST"})
    save_webhook(webhook)
    delivery = emit_event("tenant-a", "policy.failed", {"safe": True})[0]

    def fail_post(*args, **kwargs):
        raise TimeoutError("network unavailable")

    monkeypatch.setattr("apps.api.services.operations.httpx.post", fail_post)
    monkeypatch.setattr("apps.api.services.operations.socket.getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))])
    for attempt in range(5):
        result = deliver_webhook(delivery.delivery_id, now=now + timedelta(seconds=attempt))
    assert result.status == "dead_letter"
    assert result.last_error == "TimeoutError"
    client = TestClient(app)
    admin = auth_header(tenant_id="tenant-a", roles=["admin"])
    assert client.get("/assurance/webhook-deliveries", headers=admin).json()["count"] == 1
    retried = client.post(f"/assurance/webhook-deliveries/{delivery.delivery_id}/retry", headers=admin)
    assert retried.status_code == 200
    assert retried.json()["status"] == "dead_letter"
    assert client.post("/assurance/webhook-deliveries/missing/retry", headers=admin).status_code == 404


def test_worker_processes_due_delivery_and_expiry_once(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("VENDOR_RTP_WEBHOOK_SECRET_TEST", "rotation-secret")
    current = datetime(2026, 9, 23, tzinfo=UTC)
    webhook = WebhookRecord(webhook_id="99999999-9999-9999-9999-999999999999", tenant_id="tenant-a", name="SOC", url="https://events.example.test/hook", key_id="key-1", enabled=True, created_at=current, created_by="admin", **{"secret_env": "VENDOR_RTP_WEBHOOK_SECRET_TEST"})
    save_webhook(webhook)
    expired = _assessment(assessment_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", due=current - timedelta(seconds=1))
    save_assessment(expired)

    class Response:
        def raise_for_status(self):
            return None

    monkeypatch.setattr("apps.api.services.operations.httpx.post", lambda *args, **kwargs: Response())
    monkeypatch.setattr("apps.api.services.operations.socket.getaddrinfo", lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))])
    assert process_expired_approvals(now=current) == 1
    assert process_expired_approvals(now=current) == 0
    assert process_due_deliveries(now=current) == 1
    assert process_due_deliveries(now=current) == 0


def test_scheduled_completion_updates_assessment_and_failure_event(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    now = datetime.now(tz=UTC)
    assessment = _assessment()
    save_assessment(assessment)
    schedule = ScheduleRecord(schedule_id="55555555-5555-5555-5555-555555555555", tenant_id="tenant-a", assessment_id=assessment.assessment_id, profile="quick_gates", cadence_minutes=60, timezone="UTC", enabled=True, next_run_at=now, created_at=now, updated_at=now, created_by="operator")
    save_schedule(schedule)
    monkeypatch.setattr("apps.api.services.operations.evaluate_assessment", lambda assessment, run_id: {"schema_version": "policy-evaluation.v1", "outcome": "FAIL", "reason_codes": ["DRIFT_REGRESSION"], "drift": {}, "policy": {"policy_id": "strict", "version": "1", "digest": "sha256:x"}})
    result = complete_scheduled_job({"schedule_id": schedule.schedule_id, "assessment_id": assessment.assessment_id, "run_id": "candidate"}, succeeded=True)
    assert result and result["outcome"] == "FAIL"
    assert load_assessment(assessment.assessment_id).last_evaluation["outcome"] == "FAIL"
    assert complete_scheduled_job({"schedule_id": schedule.schedule_id, "assessment_id": assessment.assessment_id, "run_id": "candidate"}, succeeded=False) is None


def test_portfolio_orders_expired_and_failed_before_healthy(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    current = datetime(2026, 9, 23, tzinfo=UTC)
    expired = _assessment(assessment_id="66666666-6666-6666-6666-666666666666", due=current - timedelta(seconds=1))
    failed = _assessment(assessment_id="77777777-7777-7777-7777-777777777777")
    failed.last_evaluation = {"outcome": "UNKNOWN", "reason_codes": ["EVIDENCE_MISSING"]}
    healthy = _assessment(assessment_id="88888888-8888-8888-8888-888888888888")
    healthy.last_evaluation = {"outcome": "PASS", "reason_codes": []}
    for record in (expired, failed, healthy):
        save_assessment(record)
    items = portfolio("tenant-a", now=current)
    assert [item["state"] for item in items] == ["expired", "failed", "healthy"]
