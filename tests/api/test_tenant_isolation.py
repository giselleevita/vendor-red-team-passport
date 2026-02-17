from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.schemas.passport import Passport
from apps.api.services.run_store import save_passport, save_run_meta


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
                "overall_score": 100.0,
                "p1_pass_rate": 100.0,
                "p2_pass_rate": 100.0,
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


def test_passport_enforces_tenant_isolation(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("tenant-a-run", tenant_id="tenant-a")

    client = TestClient(app)
    ok = client.get("/passports/tenant-a-run", headers=auth_header(tenant_id="tenant-a", roles=["viewer"]))
    assert ok.status_code == 200

    blocked = client.get("/passports/tenant-a-run", headers=auth_header(tenant_id="tenant-b", roles=["viewer"]))
    assert blocked.status_code == 404


def test_runs_page_lists_only_current_tenant(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    _seed_run("run-a", tenant_id="tenant-a")
    _seed_run("run-b", tenant_id="tenant-b")

    client = TestClient(app)
    page = client.get("/runs", headers=auth_header(tenant_id="tenant-a", roles=["viewer"]))
    assert page.status_code == 200
    html = page.text
    assert "run-a" in html
    assert "run-b" not in html
