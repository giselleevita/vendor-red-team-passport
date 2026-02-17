from __future__ import annotations

from datetime import datetime, timezone

from apps.api.services.jobs import load_job, update_job
from apps.api.services.orchestrator import run_orchestrated
from apps.api.services.profiles import load_profile


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def execute_job(job_id: str) -> dict:
    job = load_job(job_id)
    if job is None:
        raise FileNotFoundError(f"job not found: {job_id}")

    status = str(job.get("status", "")).strip()
    if status in {"succeeded", "failed"}:
        return job

    if status != "running":
        job = update_job(job_id, {"status": "running", "started_at_utc": _utc_now_iso()})

    try:
        profile_ref = str(job.get("profile_ref", "")).strip()
        profile = load_profile(profile_ref, allow_external_paths=False) if profile_ref else None
        only_classes_raw = job.get("only_classes")
        only_classes = only_classes_raw if isinstance(only_classes_raw, list) and only_classes_raw else None
        params = job.get("params") if isinstance(job.get("params"), dict) else None
        run_orchestrated(
            model=str(job.get("model", "")),
            only_classes=only_classes,
            a9_mode=str(job.get("a9_mode", "auto")),
            params=params,
            tenant_id=str(job.get("tenant_id", "")),
            run_id=str(job.get("run_id", "")),
            suite_path=str(job.get("suite_path", "data/cases/cases.v1.json")),
            profile=profile,
        )
        return update_job(
            job_id,
            {
                "status": "succeeded",
                "finished_at_utc": _utc_now_iso(),
            },
        )
    except Exception as e:  # noqa: BLE001
        return update_job(
            job_id,
            {
                "status": "failed",
                "finished_at_utc": _utc_now_iso(),
                "error": str(e)[:240],
            },
        )

