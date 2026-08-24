from __future__ import annotations

import pytest

from apps.api.services.jobs import SqlJobStore


def test_sqlite_job_store_full_lifecycle(tmp_path) -> None:
    store = SqlJobStore(f"sqlite:///{tmp_path / 'jobs.db'}")
    assert store.load_job("missing") is None
    created = store.create_job("job-1", {"tenant_id": "tenant", "run_id": "run-1"})
    assert created["status"] == "queued"
    assert store.load_job("job-1")["tenant_id"] == "tenant"
    updated = store.update_job("job-1", {"status": "succeeded", "finished_at_utc": "now"})
    assert updated["status"] == "succeeded"
    assert [job["job_id"] for job in store.list_jobs()] == ["job-1"]
    assert [job["job_id"] for job in store.list_jobs(status="succeeded", limit=0)] == ["job-1"]
    assert store.list_jobs(status="queued") == []
    with pytest.raises(FileNotFoundError):
        store.update_job("missing", {"status": "failed"})
    with pytest.raises(ValueError, match="unsupported"):
        SqlJobStore("mysql://localhost/jobs")

