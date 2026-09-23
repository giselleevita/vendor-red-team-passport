from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas.passport import Passport
from apps.api.services.run_store import save_passport, save_run_meta


def _seed_run(run_id: str, tenant_id: str) -> None:
    save_run_meta(
        run_id,
        {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "created_at_utc": "2026-09-23T00:00:00+00:00",
            "model": "fictional/model-a",
            "suite_version": "1.0.0",
        },
    )
    save_passport(
        run_id,
        Passport(
            run_id=run_id,
            summary={
                "overall_score": 92.0,
                "p1_pass_rate": 100.0,
                "p2_pass_rate": 90.0,
                "a9_schema_validity": 100.0,
                "a9_mode_used": "compat",
                "a9_strict_supported": False,
                "critical_failures": 0,
                "release_gate": "PASS",
            },
            class_scores=[],
            failed_cases=[],
            executive_verdict={},
        ),
    )


def _payload(run_id: str) -> dict:
    return {
        "vendor_name": "Vendor A",
        "system_name": "Support assistant",
        "use_case": "Draft internal support responses for human review.",
        "owner": "Security Assurance",
        "risk_tier": "high",
        "data_classification": "confidential",
        "linked_run_ids": [run_id],
    }


def test_assessment_lifecycle_and_sanitized_evidence(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("vendor-a-run", "tenant-a")
    client = TestClient(app)

    created = client.post(
        "/assessments",
        json=_payload("vendor-a-run"),
        headers=auth_header(tenant_id="tenant-a", roles=["operator"]),
    )
    assert created.status_code == 201
    assessment_id = created.json()["assessment_id"]
    assert created.json()["status"] == "draft"

    submitted = client.post(
        f"/assessments/{assessment_id}/submit",
        headers=auth_header(tenant_id="tenant-a", roles=["operator"]),
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "in_review"

    decided = client.post(
        f"/assessments/{assessment_id}/decision",
        json={
            "verdict": "approved_with_conditions",
            "rationale": "Residual risk is acceptable after the stated safeguards are verified.",
            "conditions": ["Repeat the Passport evaluation before production deployment."],
        },
        headers=auth_header(tenant_id="tenant-a", roles=["auditor"]),
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved_with_conditions"

    evidence = client.get(
        f"/assessments/{assessment_id}/evidence-package",
        headers=auth_header(tenant_id="tenant-a", roles=["viewer"]),
    )
    assert evidence.status_code == 200
    body = evidence.json()
    assert body["schema_version"] == "assurance-evidence.v1"
    assert body["run_evidence"][0]["summary"]["release_gate"] == "PASS"
    assert "cases" not in body["run_evidence"][0]
    assert "response" not in body["run_evidence"][0]


def test_assessments_are_tenant_isolated(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("tenant-a-run", "tenant-a")
    client = TestClient(app)
    created = client.post(
        "/assessments",
        json=_payload("tenant-a-run"),
        headers=auth_header(tenant_id="tenant-a", roles=["operator"]),
    )
    assessment_id = created.json()["assessment_id"]

    hidden = client.get(
        f"/assessments/{assessment_id}",
        headers=auth_header(tenant_id="tenant-b", roles=["viewer"]),
    )
    assert hidden.status_code == 404
    listing = client.get(
        "/assessments",
        headers=auth_header(tenant_id="tenant-b", roles=["viewer"]),
    )
    assert listing.json() == {"items": [], "count": 0}


def test_assessment_enforces_roles_and_state_transitions(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("workflow-run", "tenant-a")
    client = TestClient(app)

    blocked = client.post(
        "/assessments",
        json=_payload("workflow-run"),
        headers=auth_header(tenant_id="tenant-a", roles=["viewer"]),
    )
    assert blocked.status_code == 403

    created = client.post(
        "/assessments",
        json=_payload("workflow-run"),
        headers=auth_header(tenant_id="tenant-a", roles=["operator"]),
    )
    assessment_id = created.json()["assessment_id"]
    premature = client.post(
        f"/assessments/{assessment_id}/decision",
        json={"verdict": "approved", "rationale": "The documented evidence meets the review policy."},
        headers=auth_header(tenant_id="tenant-a", roles=["auditor"]),
    )
    assert premature.status_code == 409

    wrong_tenant_run = client.post(
        "/assessments",
        json=_payload("workflow-run"),
        headers=auth_header(tenant_id="tenant-b", roles=["operator"]),
    )
    assert wrong_tenant_run.status_code == 404


def test_run_link_and_conditional_decision_validation(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("linkable-run", "tenant-a")
    client = TestClient(app)
    payload = _payload("linkable-run")
    payload["linked_run_ids"] = []
    operator = auth_header(tenant_id="tenant-a", roles=["operator"])
    auditor = auth_header(tenant_id="tenant-a", roles=["auditor"])

    created = client.post("/assessments", json=payload, headers=operator)
    assessment_id = created.json()["assessment_id"]
    no_evidence = client.post(f"/assessments/{assessment_id}/submit", headers=operator)
    assert no_evidence.status_code == 409

    linked = client.post(
        f"/assessments/{assessment_id}/runs",
        json={"run_id": "linkable-run"},
        headers=operator,
    )
    assert linked.status_code == 200
    assert linked.json()["linked_run_ids"] == ["linkable-run"]
    duplicate = client.post(
        f"/assessments/{assessment_id}/runs",
        json={"run_id": "linkable-run"},
        headers=operator,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["linked_run_ids"] == ["linkable-run"]

    assert client.post(f"/assessments/{assessment_id}/submit", headers=operator).status_code == 200
    frozen = client.post(
        f"/assessments/{assessment_id}/runs",
        json={"run_id": "linkable-run"},
        headers=operator,
    )
    assert frozen.status_code == 409

    missing_condition = client.post(
        f"/assessments/{assessment_id}/decision",
        json={
            "verdict": "approved_with_conditions",
            "rationale": "Residual risk requires a documented production safeguard.",
        },
        headers=auditor,
    )
    assert missing_condition.status_code == 422
    unexpected_condition = client.post(
        f"/assessments/{assessment_id}/decision",
        json={
            "verdict": "approved",
            "rationale": "The available evidence supports approval under the current policy.",
            "conditions": ["This is not valid for an unconditional approval."],
        },
        headers=auditor,
    )
    assert unexpected_condition.status_code == 422


def test_assessment_rejects_blank_and_naive_review_fields(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    client = TestClient(app)
    payload = _payload("unused")
    payload["linked_run_ids"] = []
    payload["vendor_name"] = "   "
    payload["review_due_at"] = "2026-10-01T12:00:00"
    response = client.post(
        "/assessments",
        json=payload,
        headers=auth_header(tenant_id="tenant-a", roles=["operator"]),
    )
    assert response.status_code == 422
