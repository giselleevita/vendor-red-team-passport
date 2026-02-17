from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from pydantic import BaseModel, Field

from apps.api.config import get_settings
from apps.api.services.audit import log_audit_event
from apps.api.services.auth import RequestContext, hash_subject, require_roles
from apps.api.services.job_executor import execute_job
from apps.api.services.jobs import create_job, load_job
from apps.api.services.profiles import load_profile

router = APIRouter()


class RunCreateRequest(BaseModel):
    profile: str | None = Field(default=None, description="Run profile name or path (e.g. quick_gates, full_suite)")
    model: str | None = Field(default=None, description="Featherless model name")
    only_classes: list[str] | None = Field(
        default=None, description="If set, run only these attack classes (e.g. ['A4','A5','A6','A9'])."
    )
    a9_mode: Literal["auto", "compat", "strict"] | None = Field(default=None)
    params: dict | None = Field(default=None, description="Optional generation params (temperature, max_tokens)")


@router.post("/runs")
def create_run(
    req: RunCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(require_roles("operator", "admin")),
) -> dict[str, str]:
    settings = get_settings()
    run_id = str(uuid.uuid4())
    try:
        profile = load_profile(req.profile, allow_external_paths=False) if req.profile else None
    except FileNotFoundError as e:
        log_audit_event(
            action="run.create",
            result="deny",
            actor=hash_subject(ctx.subject),
            tenant_id=ctx.tenant_id,
            resource=request.url.path,
            detail=str(e),
            method=request.method,
        )
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        log_audit_event(
            action="run.create",
            result="deny",
            actor=hash_subject(ctx.subject),
            tenant_id=ctx.tenant_id,
            resource=request.url.path,
            detail=str(e),
            method=request.method,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e

    model = (req.model or "").strip() or (profile.get("model") if profile else "") or settings.default_model
    suite_path = (profile.get("suite_path") if profile else "") or "data/cases/cases.v1.json"

    only_classes = req.only_classes if req.only_classes is not None else (profile.get("only_classes") if profile else None)
    if only_classes == []:
        only_classes = None

    a9_mode = req.a9_mode if req.a9_mode is not None else (profile.get("a9_mode") if profile else "auto")
    params = req.params if req.params is not None else (profile.get("params") if profile else None)

    if params is not None:
        allowed = {"temperature", "max_tokens"}
        extra = set(params.keys()) - allowed
        if extra:
            raise HTTPException(status_code=422, detail=f"unsupported params keys: {sorted(extra)}")
        if "temperature" in params and params["temperature"] is not None:
            try:
                params["temperature"] = float(params["temperature"])
            except Exception as e:  # noqa: BLE001
                raise HTTPException(status_code=422, detail="params.temperature must be a number") from e
        if "max_tokens" in params and params["max_tokens"] is not None:
            try:
                params["max_tokens"] = int(params["max_tokens"])
            except Exception as e:  # noqa: BLE001
                raise HTTPException(status_code=422, detail="params.max_tokens must be an integer") from e

    if only_classes is not None:
        normalized = []
        for c in only_classes:
            cc = (c or "").strip().upper()
            if not cc:
                continue
            if not (len(cc) in (2, 3) and cc.startswith("A") and cc[1:].isdigit()):
                raise HTTPException(status_code=422, detail=f"invalid attack class: {c!r}")
            normalized.append(cc)
        only_classes = normalized or None

    job_id = str(uuid.uuid4())
    create_job(
        job_id,
        {
            "run_id": run_id,
            "tenant_id": ctx.tenant_id,
            "created_by": hash_subject(ctx.subject),
            "model": model,
            "profile": (profile.get("name") if isinstance(profile, dict) else ""),
            "profile_ref": req.profile or "",
            "a9_mode": a9_mode,
            "only_classes": only_classes or [],
            "suite_path": suite_path,
            "params": params or {},
            "attempt_count": 0,
            "max_attempts": max(1, int(settings.run_job_max_attempts)),
            "next_attempt_at": None,
        },
    )
    mode = (settings.run_executor_mode or "inline").strip().lower()
    if mode == "inline":
        background_tasks.add_task(execute_job, job_id)
    elif mode == "external":
        # External workers pick queued jobs from store.
        pass
    else:
        raise HTTPException(status_code=500, detail="invalid run executor mode")
    log_audit_event(
        action="run.queue",
        result="allow",
        actor=hash_subject(ctx.subject),
        tenant_id=ctx.tenant_id,
        resource=f"/runs/{run_id}",
        detail=f"run queued job_id={job_id} mode={mode}",
        method=request.method,
    )
    return {
        "run_id": run_id,
        "job_id": job_id,
        "job_url": f"/runs/jobs/{job_id}",
        "passport_json_url": f"/passports/{run_id}",
        "passport_html_url": f"/runs/{run_id}",
        "files_url_prefix": f"/reports/runs/{run_id}/",
    }


@router.get("/runs/jobs/{job_id}")
def get_run_job(
    job_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    try:
        job = load_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if job is None:
        raise HTTPException(status_code=404, detail="job_id not found")

    job_tenant = str(job.get("tenant_id", "")).strip()
    if not job_tenant or job_tenant != ctx.tenant_id:
        log_audit_event(
            action="run.job.read",
            result="deny",
            actor=hash_subject(ctx.subject),
            tenant_id=ctx.tenant_id,
            resource=request.url.path,
            detail="tenant mismatch",
            method=request.method,
        )
        raise HTTPException(status_code=404, detail="job_id not found")

    log_audit_event(
        action="run.job.read",
        result="allow",
        actor=hash_subject(ctx.subject),
        tenant_id=ctx.tenant_id,
        resource=request.url.path,
        detail=f"status={job.get('status', '')}",
        method=request.method,
    )
    return job
