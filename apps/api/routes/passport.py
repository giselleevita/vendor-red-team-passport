from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.services.audit import log_audit_event
from apps.api.services.auth import RequestContext, hash_subject, require_roles
from apps.api.services.run_store import load_passport, load_run_meta, run_accessible_by_tenant

router = APIRouter()


@router.get("/passports/{run_id}")
def get_passport(
    run_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    try:
        meta = load_run_meta(run_id)
    except ValueError as e:
        log_audit_event(
            action="passport.read",
            result="deny",
            actor=hash_subject(ctx.subject),
            tenant_id=ctx.tenant_id,
            resource=request.url.path,
            detail=str(e),
            method=request.method,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
    if meta is None:
        raise HTTPException(status_code=404, detail="run_id not found")
    if not run_accessible_by_tenant(run_id, ctx.tenant_id):
        log_audit_event(
            action="passport.read",
            result="deny",
            actor=hash_subject(ctx.subject),
            tenant_id=ctx.tenant_id,
            resource=request.url.path,
            detail="tenant mismatch",
            method=request.method,
        )
        raise HTTPException(status_code=404, detail="run_id not found")
    passport = load_passport(run_id)
    if passport is None:
        raise HTTPException(status_code=404, detail="run_id not found")
    log_audit_event(
        action="passport.read",
        result="allow",
        actor=hash_subject(ctx.subject),
        tenant_id=ctx.tenant_id,
        resource=request.url.path,
        detail="passport returned",
        method=request.method,
    )
    return passport.model_dump()
