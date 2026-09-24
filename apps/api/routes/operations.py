from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.schemas.operations import (
    ScheduleCreateRequest,
    ScheduleRecord,
    ScheduleUpdateRequest,
    WebhookCreateRequest,
    WebhookRecord,
    WebhookUpdateRequest,
)
from apps.api.services.assurance import load_assessment
from apps.api.services.audit import log_audit_event
from apps.api.services.auth import RequestContext, hash_subject, require_roles
from apps.api.services.operations import (
    deliver_webhook,
    list_deliveries,
    list_schedules,
    list_webhooks,
    load_schedule,
    portfolio,
    save_schedule,
    save_webhook,
    trigger_schedule,
    validate_timezone,
    validate_webhook_url,
)
from apps.api.services.profiles import load_profile

router = APIRouter(prefix="/assurance", tags=["continuous-assurance"])


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _audit(request: Request, ctx: RequestContext, action: str, resource: str) -> None:
    log_audit_event(action=action, result="allow", actor=hash_subject(ctx.subject), tenant_id=ctx.tenant_id, resource=resource, method=request.method)


def _owned_assessment(assessment_id: str, tenant_id: str):
    record = load_assessment(assessment_id)
    if record is None or record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="assessment not found")
    return record


def _owned_schedule(schedule_id: str, tenant_id: str) -> ScheduleRecord:
    record = load_schedule(schedule_id)
    if record is None or record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="schedule not found")
    return record


@router.post("/schedules", status_code=201)
def create_schedule(payload: ScheduleCreateRequest, request: Request, ctx: RequestContext = Depends(require_roles("operator", "admin"))) -> dict:
    _owned_assessment(payload.assessment_id, ctx.tenant_id)
    try:
        validate_timezone(payload.timezone)
        load_profile(payload.profile, allow_external_paths=False)
    except (ValueError, FileNotFoundError, PermissionError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    now = _now()
    record = ScheduleRecord(schedule_id=str(uuid.uuid4()), tenant_id=ctx.tenant_id, assessment_id=payload.assessment_id, profile=payload.profile, cadence_minutes=payload.cadence_minutes, timezone=payload.timezone, enabled=payload.enabled, next_run_at=payload.next_run_at or now, created_at=now, updated_at=now, created_by=hash_subject(ctx.subject))
    save_schedule(record)
    _audit(request, ctx, "schedule.create", f"/assurance/schedules/{record.schedule_id}")
    return record.model_dump(mode="json")


@router.get("/schedules")
def get_schedules(ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin"))) -> dict:
    items = list_schedules(ctx.tenant_id)
    return {"items": [item.model_dump(mode="json") for item in items], "count": len(items)}


@router.patch("/schedules/{schedule_id}")
def update_schedule(schedule_id: str, payload: ScheduleUpdateRequest, request: Request, ctx: RequestContext = Depends(require_roles("operator", "admin"))) -> dict:
    record = _owned_schedule(schedule_id, ctx.tenant_id)
    patch = payload.model_dump(exclude_none=True)
    if "timezone" in patch:
        try:
            validate_timezone(str(patch["timezone"]))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    for key, value in patch.items():
        setattr(record, key, value)
    record.updated_at = _now()
    save_schedule(record)
    _audit(request, ctx, "schedule.update", f"/assurance/schedules/{record.schedule_id}")
    return record.model_dump(mode="json")


@router.post("/schedules/{schedule_id}/trigger", status_code=202)
def manual_trigger(schedule_id: str, request: Request, ctx: RequestContext = Depends(require_roles("operator", "admin"))) -> dict:
    _owned_schedule(schedule_id, ctx.tenant_id)
    try:
        job = trigger_schedule(schedule_id, force=True)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit(request, ctx, "schedule.trigger", f"/assurance/schedules/{schedule_id}")
    return {"job_id": job["job_id"], "run_id": job["run_id"], "status": job["status"]}


@router.post("/webhooks", status_code=201)
def create_webhook(payload: WebhookCreateRequest, request: Request, ctx: RequestContext = Depends(require_roles("admin"))) -> dict:
    try:
        url = validate_webhook_url(payload.url)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    now = _now()
    record = WebhookRecord(webhook_id=str(uuid.uuid4()), tenant_id=ctx.tenant_id, name=payload.name, url=url, secret_env=payload.secret_env, key_id=payload.key_id, enabled=payload.enabled, created_at=now, created_by=hash_subject(ctx.subject))
    save_webhook(record)
    _audit(request, ctx, "webhook.create", f"/assurance/webhooks/{record.webhook_id}")
    response = record.model_dump(mode="json")
    response.pop("secret_env", None)
    response["secret_configured"] = True
    return response


@router.get("/webhooks")
def get_webhooks(ctx: RequestContext = Depends(require_roles("auditor", "admin"))) -> dict:
    items = []
    for record in list_webhooks(ctx.tenant_id):
        item = record.model_dump(mode="json")
        item.pop("secret_env", None)
        item["secret_configured"] = True
        items.append(item)
    return {"items": items, "count": len(items)}


@router.patch("/webhooks/{webhook_id}")
def update_webhook(webhook_id: str, payload: WebhookUpdateRequest, request: Request, ctx: RequestContext = Depends(require_roles("admin"))) -> dict:
    records = {item.webhook_id: item for item in list_webhooks(ctx.tenant_id)}
    record = records.get(webhook_id)
    if record is None:
        raise HTTPException(status_code=404, detail="webhook not found")
    patch = payload.model_dump(exclude_none=True)
    if "url" in patch:
        try:
            patch["url"] = validate_webhook_url(str(patch["url"]))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    for key, value in patch.items():
        setattr(record, key, value)
    save_webhook(record)
    _audit(request, ctx, "webhook.update", f"/assurance/webhooks/{record.webhook_id}")
    response = record.model_dump(mode="json")
    response.pop("secret_env", None)
    response["secret_configured"] = True
    return response


@router.get("/webhook-deliveries")
def get_deliveries(ctx: RequestContext = Depends(require_roles("auditor", "admin"))) -> dict:
    items = list_deliveries(ctx.tenant_id)
    return {"items": [item.model_dump(mode="json") for item in items], "count": len(items)}


@router.post("/webhook-deliveries/{delivery_id}/retry")
def retry_delivery(delivery_id: str, request: Request, ctx: RequestContext = Depends(require_roles("admin"))) -> dict:
    owned = {item.delivery_id for item in list_deliveries(ctx.tenant_id)}
    if delivery_id not in owned:
        raise HTTPException(status_code=404, detail="delivery not found")
    try:
        result = deliver_webhook(delivery_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit(request, ctx, "webhook.retry", f"/assurance/webhook-deliveries/{delivery_id}")
    return result.model_dump(mode="json")


@router.get("/portfolio")
def get_portfolio(ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin"))) -> dict:
    items = portfolio(ctx.tenant_id)
    return {"schema_version": "portfolio.v1", "items": items, "count": len(items)}
