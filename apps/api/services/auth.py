from __future__ import annotations

import hashlib
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt import InvalidTokenError

from apps.api.config import get_settings
from apps.api.services.audit import log_audit_event

JWT_ALGORITHMS = ["HS256"]
JWT_LEEWAY_SECONDS = 30


@dataclass(frozen=True)
class RequestContext:
    subject: str
    tenant_id: str
    roles: tuple[str, ...]


def _decode_hs256_jwt(token: str, *, secret: str, issuer: str, audience: str) -> dict:
    settings = get_settings()
    required = [
        "exp",
        "iat",
        "sub",
        settings.auth_tenant_claim,
        settings.auth_roles_claim,
        "iss",
        "aud",
    ]
    return jwt.decode(
        token,
        secret,
        algorithms=JWT_ALGORITHMS,
        issuer=issuer,
        audience=audience,
        leeway=JWT_LEEWAY_SECONDS,
        options={"require": required},
    )


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token.strip():
        raise InvalidTokenError("missing_bearer_token")
    return token.strip()


def _claims_to_context(payload: dict) -> RequestContext:
    settings = get_settings()
    subject = payload.get("sub")
    tenant_id = payload.get(settings.auth_tenant_claim)
    roles_claim = payload.get(settings.auth_roles_claim)
    if not isinstance(subject, str) or not subject.strip():
        raise InvalidTokenError("invalid_subject_claim")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise InvalidTokenError("invalid_tenant_claim")
    if not isinstance(roles_claim, list) or not roles_claim:
        raise InvalidTokenError("invalid_roles_claim")
    if not all(isinstance(role, str) and role.strip() for role in roles_claim):
        raise InvalidTokenError("invalid_roles_claim")
    roles = tuple(sorted({role.strip() for role in roles_claim}))
    return RequestContext(subject=subject.strip(), tenant_id=tenant_id.strip(), roles=roles)


def _reason_code(exc: InvalidTokenError) -> str:
    name = type(exc).__name__.removesuffix("Error")
    return f"jwt_{name.lower()}"[:80]


def get_request_context(request: Request) -> RequestContext:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="authentication unavailable")
    if not settings.auth_jwt_hs256_secret or not settings.auth_jwt_issuer or not settings.auth_jwt_audience:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="authentication unavailable")
    try:
        payload = _decode_hs256_jwt(
            _extract_bearer_token(request),
            secret=settings.auth_jwt_hs256_secret,
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
        )
        context = _claims_to_context(payload)
    except InvalidTokenError as exc:
        log_audit_event(
            action="authn",
            result="deny",
            actor="anonymous",
            tenant_id="",
            resource=request.url.path,
            detail=_reason_code(exc),
            method=request.method,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token") from exc
    request.state.request_context = context
    return context


def require_roles(*allowed_roles: str):
    allowed = {role.strip().lower() for role in allowed_roles if role.strip()}

    def _dependency(
        request: Request,
        context: RequestContext = Depends(get_request_context),
    ) -> RequestContext:
        settings = get_settings()
        if not settings.rbac_enabled:
            return context
        actual = {role.lower() for role in context.roles}
        if allowed and actual.isdisjoint(allowed):
            log_audit_event(
                action="authz",
                result="deny",
                actor=hash_subject(context.subject),
                tenant_id=context.tenant_id,
                resource=request.url.path,
                detail="role_requirement_not_met",
                method=request.method,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return context

    return _dependency


def hash_subject(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
