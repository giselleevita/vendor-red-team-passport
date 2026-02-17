from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.config import get_settings
from apps.api.main import app
from apps.api.services.job_executor import execute_job
from apps.api.services.jobs import create_job, get_job_store, load_job


def test_create_run_returns_job_and_job_status(auth_header, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("RUN_EXECUTOR_MODE", "external")
    get_settings.cache_clear()
    get_job_store.cache_clear()

    client = TestClient(app)
    response = client.post("/runs", json={"profile": "quick_gates"}, headers=auth_header(roles=["operator"]))
    assert response.status_code == 200
    body = response.json()
    assert "job_id" in body and body["job_id"]
    assert body["job_url"].startswith("/runs/jobs/")

    job = client.get(body["job_url"], headers=auth_header(roles=["viewer"]))
    assert job.status_code == 200
    assert job.json()["status"] == "queued"


def test_job_status_is_tenant_scoped(auth_header, monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("RUN_EXECUTOR_MODE", "external")
    get_settings.cache_clear()
    get_job_store.cache_clear()

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


def test_execute_job_marks_success(monkeypatch, tmp_path: Path) -> None:
    import apps.api.services.job_executor as job_exec

    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    get_settings.cache_clear()
    get_job_store.cache_clear()

    def _fake_run_orchestrated(**kwargs):  # noqa: ANN003
        return kwargs.get("run_id", "")

    monkeypatch.setattr(job_exec, "run_orchestrated", _fake_run_orchestrated)
    create_job(
        "job-worker-1",
        {
            "run_id": "run-worker-1",
            "tenant_id": "tenant-a",
            "model": "x",
            "a9_mode": "auto",
            "only_classes": [],
            "suite_path": "data/cases/cases.v1.json",
            "params": {},
        },
    )
    after = execute_job("job-worker-1")
    assert after["status"] == "succeeded"
    loaded = load_job("job-worker-1")
    assert loaded is not None and loaded["status"] == "succeeded"
