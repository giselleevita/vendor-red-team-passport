from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas.passport import Passport
from apps.api.services.run_store import save_case_evidence, save_passport, save_run_meta


def _seed(run_id: str, tenant: str, score: float) -> None:
    save_run_meta(
        run_id,
        {"run_id": run_id, "tenant_id": tenant, "model": f"model-{run_id}", "created_at_utc": run_id},
    )
    save_passport(
        run_id,
        Passport(
            run_id=run_id,
            summary={
                "overall_score": score,
                "p1_pass_rate": score,
                "p2_pass_rate": score,
                "a9_schema_validity": score,
                "a9_mode_used": "compat",
                "a9_strict_supported": False,
                "critical_failures": 0,
                "release_gate": "PASS",
            },
            class_scores=[{"attack_class": "A4", "pass_rate": score, "status": "PASS"}],
            failed_cases=[],
            executive_verdict={"decision": "APPROVE", "required_remediations": [], "compliance_mapping": {}},
        ),
    )
    save_case_evidence(run_id, "A4-01", {"case_id": "A4-01", "passed": True})


def test_ui_landing_list_claims_and_comparison(tmp_path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed("2026-a", "tenant", 80)
    _seed("2026-b", "tenant", 90)
    headers = auth_header(tenant_id="tenant", roles=["viewer"])
    client = TestClient(app)
    assert client.get("/", headers=headers).status_code == 200
    runs = client.get("/runs", headers=headers)
    assert runs.status_code == 200 and "2026-a" in runs.text and "2026-b" in runs.text
    assert client.get("/runs/2026-a/claims", headers=headers).status_code == 200
    assert client.get("/compare", headers=headers).status_code == 200
    one = client.get("/compare", params=[("run_id", "2026-a")], headers=headers)
    assert one.status_code == 200 and "exactly two" in one.text
    missing = client.get("/compare", params=[("run_id", "2026-a"), ("run_id", "missing")], headers=headers)
    assert missing.status_code == 200 and "not found" in missing.text
    compared = client.get(
        "/compare", params=[("run_id", "2026-a"), ("run_id", "2026-b")], headers=headers
    )
    assert compared.status_code == 200 and "model-2026-a" in compared.text and "model-2026-b" in compared.text


def test_ui_artifact_and_evidence_errors(tmp_path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed("run-a", "tenant", 80)
    headers = auth_header(tenant_id="tenant", roles=["viewer"])
    client = TestClient(app)
    assert client.get("/runs/run-a/artifacts/not-allowed.json", headers=headers).status_code == 404
    assert client.get("/runs/run-a/artifacts/policy.json", headers=headers).status_code == 404
    assert client.get("/runs/run-a/cases/A4-99.json", headers=headers).status_code == 404
    assert client.get("/runs/bad%5Crun", headers=headers).status_code == 400
