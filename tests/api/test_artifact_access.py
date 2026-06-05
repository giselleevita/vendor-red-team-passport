from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas.passport import Passport
from apps.api.services.run_store import save_case_evidence, save_json_artifact, save_passport, save_run_meta


def _seed_run(run_id: str, *, tenant_id: str) -> None:
    save_run_meta(
        run_id,
        {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "created_at_utc": "2026-02-17T00:00:00+00:00",
            "model": "x",
            "suite_version": "1.0.0",
        },
    )
    save_passport(
        run_id,
        Passport(
            run_id=run_id,
            summary={
                "overall_score": 80.0,
                "p1_pass_rate": 100.0,
                "p2_pass_rate": 80.0,
                "a9_schema_validity": 100.0,
                "a9_mode_used": "compat",
                "a9_strict_supported": False,
                "critical_failures": 0,
                "release_gate": "FAIL",
            },
            class_scores=[{"attack_class": "A9", "pass_rate": 80.0, "status": "FAIL"}],
            failed_cases=[
                {
                    "case_id": "A9-01",
                    "attack_class": "A9",
                    "expected": "STRICT_JSON",
                    "actual": "NON_JSON",
                    "latency_ms": 12,
                }
            ],
            executive_verdict={
                "decision": "REJECT",
                "required_remediations": ["Fix structured-output handling."],
                "compliance_mapping": {},
            },
        ),
    )
    save_json_artifact(run_id, "policy.json", {"version": "policy.test"})
    save_case_evidence(
        run_id,
        "A9-01",
        {
            "case_id": "A9-01",
            "attack_class": "A9",
            "expected_verdict": "STRICT_JSON",
            "actual_verdict": "NON_JSON",
            "passed": False,
            "response_excerpt_sanitized": "plain text",
            "timing": {"latency_ms": 12},
        },
    )


def test_reports_static_mount_is_not_public(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("tenant-a-run", tenant_id="tenant-a")

    client = TestClient(app)
    response = client.get("/reports/runs/tenant-a-run/policy.json")
    assert response.status_code == 404


def test_interactive_api_docs_are_not_public() -> None:
    client = TestClient(app)

    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_artifact_route_requires_auth_and_tenant_match(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("tenant-a-run", tenant_id="tenant-a")

    client = TestClient(app)
    unauthenticated = client.get("/runs/tenant-a-run/artifacts/policy.json")
    assert unauthenticated.status_code == 401

    allowed = client.get(
        "/runs/tenant-a-run/artifacts/policy.json",
        headers=auth_header(tenant_id="tenant-a", roles=["viewer"]),
    )
    assert allowed.status_code == 200
    assert allowed.json()["version"] == "policy.test"

    denied = client.get(
        "/runs/tenant-a-run/artifacts/policy.json",
        headers=auth_header(tenant_id="tenant-b", roles=["viewer"]),
    )
    assert denied.status_code == 404


def test_case_evidence_route_requires_tenant_match(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("tenant-a-run", tenant_id="tenant-a")

    client = TestClient(app)
    allowed = client.get(
        "/runs/tenant-a-run/cases/A9-01.json",
        headers=auth_header(tenant_id="tenant-a", roles=["auditor"]),
    )
    assert allowed.status_code == 200
    assert allowed.json()["response_excerpt_sanitized"] == "plain text"

    denied = client.get(
        "/runs/tenant-a-run/cases/A9-01.json",
        headers=auth_header(tenant_id="tenant-b", roles=["auditor"]),
    )
    assert denied.status_code == 404


def test_generated_passport_uses_authenticated_artifact_links(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("tenant-a-run", tenant_id="tenant-a")

    client = TestClient(app)
    response = client.get("/runs/tenant-a-run", headers=auth_header(tenant_id="tenant-a", roles=["viewer"]))
    assert response.status_code == 200
    assert "/runs/tenant-a-run/artifacts/policy.json" in response.text
    assert "/runs/tenant-a-run/cases/A9-01.json" in response.text
    assert "/reports/" not in response.text


def test_invalid_case_id_returns_400(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("tenant-a-run", tenant_id="tenant-a")

    client = TestClient(app)
    response = client.get(
        "/runs/tenant-a-run/cases/bad%5Ccase.json",
        headers=auth_header(tenant_id="tenant-a", roles=["viewer"]),
    )
    assert response.status_code == 400
