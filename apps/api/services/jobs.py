from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from apps.api.services.run_store import reports_dir, validate_run_id


def _utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat()


def jobs_dir() -> Path:
    d = reports_dir() / "jobs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _job_path(job_id: str) -> Path:
    return jobs_dir() / f"{validate_run_id(job_id)}.json"


def create_job(job_id: str, payload: dict) -> Path:
    p = _job_path(job_id)
    base = {
        "job_id": job_id,
        "status": "queued",
        "created_at_utc": _utc_now_iso(),
        "started_at_utc": None,
        "finished_at_utc": None,
    }
    base.update(payload)
    p.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
    return p


def load_job(job_id: str) -> dict | None:
    p = _job_path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def update_job(job_id: str, patch: dict) -> dict:
    cur = load_job(job_id)
    if cur is None:
        raise FileNotFoundError(f"job not found: {job_id}")
    cur.update(patch)
    _job_path(job_id).write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
    return cur

