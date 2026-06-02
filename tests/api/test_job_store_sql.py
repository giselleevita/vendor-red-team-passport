from pathlib import Path
import sqlite3

from apps.api.config import get_settings
from apps.api.services.jobs import (
    JOB_STORE_SCHEMA_VERSION,
    JOB_STORE_SCHEMA_VERSION_KEY,
    create_job,
    get_job_store,
    load_job,
    update_job,
)


def test_sql_job_store_roundtrip_sqlite(tmp_path: Path, monkeypatch) -> None:
    db_path = (tmp_path / "jobs.sqlite").resolve()
    monkeypatch.setenv("JOB_STORE_BACKEND", "sql")
    monkeypatch.setenv("JOB_STORE_DSN", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    get_job_store.cache_clear()

    create_job(
        "job-1",
        {
            "run_id": "run-1",
            "tenant_id": "tenant-a",
            "model": "x",
        },
    )
    loaded = load_job("job-1")
    assert loaded is not None
    assert loaded["status"] == "queued"
    assert loaded["tenant_id"] == "tenant-a"
    assert db_path.exists()

    updated = update_job("job-1", {"status": "running"})
    assert updated["status"] == "running"
    again = load_job("job-1")
    assert again is not None
    assert again["status"] == "running"


def test_sql_job_store_records_schema_version_metadata(tmp_path: Path, monkeypatch) -> None:
    db_path = (tmp_path / "jobs.sqlite").resolve()
    monkeypatch.setenv("JOB_STORE_BACKEND", "sql")
    monkeypatch.setenv("JOB_STORE_DSN", f"sqlite:///{db_path}")
    get_settings.cache_clear()
    get_job_store.cache_clear()

    create_job(
        "job-2",
        {
            "run_id": "run-2",
            "tenant_id": "tenant-a",
            "model": "x",
        },
    )

    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT value FROM job_store_metadata WHERE key = ?",
            (JOB_STORE_SCHEMA_VERSION_KEY,),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == JOB_STORE_SCHEMA_VERSION
