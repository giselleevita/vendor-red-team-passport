from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.services.audit import log_audit_event
from apps.api.services.auth import RequestContext, hash_subject, require_roles
from apps.api.services.profiles import list_profiles, load_profile

router = APIRouter()


@router.get("/profiles")
def get_profiles(ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin"))) -> list[dict]:
    _ = ctx
    return list_profiles()


@router.get("/profiles/{name}")
def get_profile(
    name: str,
    request: Request,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    try:
        profile = load_profile(name, allow_external_paths=False)
        log_audit_event(
            action="profile.read",
            result="allow",
            actor=hash_subject(ctx.subject),
            tenant_id=ctx.tenant_id,
            resource=request.url.path,
            detail=f"profile={name}",
            method=request.method,
        )
        return profile
    except FileNotFoundError as e:
        log_audit_event(
            action="profile.read",
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
            action="profile.read",
            result="deny",
            actor=hash_subject(ctx.subject),
            tenant_id=ctx.tenant_id,
            resource=request.url.path,
            detail=str(e),
            method=request.method,
        )
        raise HTTPException(status_code=400, detail=str(e)) from e
