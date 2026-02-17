from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app


def test_create_run_returns_job_and_job_status(auth_header, monkeypatch, tmp_path: Path) -> None:
    import apps.api.routes.run as run_route

    def _fake_run_orchestrated(**kwargs):  # noqa: ANN003
        return kwargs.get("run_id", "")

    monkeypatch.setattr(run_route, "run_orchestrated", _fake_run_orchestrated)
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))

    client = TestClient(app)
    response = client.post("/runs", json={"profile": "quick_gates"}, headers=auth_header(roles=["operator"]))
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body and body["job_id"]
    assert body["job_url"].startswith("/runs/jobs/")

    job = client.get(body["job_url"], headers=auth_header(roles=["viewer"]))
    assert job.status_code == 200
    assert job.json()["status"] in {"queued", "running", "succeeded"}


def test_job_status_is_tenant_scoped(auth_header, monkeypatch, tmp_path: Path) -> None:
    import apps.api.routes.run as run_route

    def _fake_run_orchestrated(**kwargs):  # noqa: ANN003
        return kwargs.get("run_id", "")

    monkeypatch.setattr(run_route, "run_orchestrated", _fake_run_orchestrated)
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))

    client = TestClient(app)
    created = client.post(
        "/runs",
        json={"profile": "quick_gates"},
        headers=auth_header(tenant_id="tenant-a", roles=["operator"]),
    )
    assert created.status_code == 200
    job_url = created.json()["job_url"]

    denied = client.get(job_url, headers=auth_header(tenant_id="tenant-b", roles=["viewer"]))
    assert denied.status_code == 404
