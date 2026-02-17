from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

from apps.api.config import get_settings
from apps.api.services.audit import log_audit_event


def _b64url_decode(data: str) -> bytes:
    s = data.encode("ascii")
    pad = b"=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class RequestContext:
    subject: str
    tenant_id: str
    roles: tuple[str, ...]


def _decode_hs256_jwt(token: str, *, secret: str, issuer: str, audience: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("invalid token format")
    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as e:  # noqa: BLE001
        raise ValueError("invalid token encoding") from e
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("invalid token payload")
    if header.get("alg") != "HS256":
        raise ValueError("unsupported token algorithm")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = _b64url_encode(hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest())
    if not hmac.compare_digest(expected, sig_b64):
        raise ValueError("invalid token signature")

    now = int(time.time())
    exp = payload.get("exp")
    nbf = payload.get("nbf")
    if isinstance(exp, (int, float)) and now >= int(exp):
        raise ValueError("token expired")
    if isinstance(nbf, (int, float)) and now < int(nbf):
        raise ValueError("token not yet valid")
    if issuer and payload.get("iss") != issuer:
        raise ValueError("token issuer mismatch")
    if audience:
        aud = payload.get("aud")
        if isinstance(aud, str):
            ok = aud == audience
        elif isinstance(aud, list):
            ok = audience in aud
        else:
            ok = False
        if not ok:
            raise ValueError("token audience mismatch")
    return payload


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ValueError("missing bearer token")
    return token.strip()


def _claims_to_context(payload: dict) -> RequestContext:
    settings = get_settings()
    subject = str(payload.get("sub", "")).strip()
    if not subject:
        raise ValueError("token subject missing")
    tenant_claim = settings.auth_tenant_claim
    tenant_id = str(payload.get(tenant_claim, "")).strip()
    if not tenant_id:
        raise ValueError(f"token tenant claim missing: {tenant_claim}")

    roles_claim = payload.get(settings.auth_roles_claim, [])
    roles: list[str] = []
    if isinstance(roles_claim, str) and roles_claim.strip():
        roles = [roles_claim.strip()]
    elif isinstance(roles_claim, list):
        roles = [str(x).strip() for x in roles_claim if str(x).strip()]
    return RequestContext(subject=subject, tenant_id=tenant_id, roles=tuple(sorted(set(roles))))


def get_request_context(request: Request) -> RequestContext:
    settings = get_settings()
    if not settings.auth_enabled:
        # Keep this explicit to avoid silent insecure operation.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="auth is disabled")

    if not settings.auth_jwt_hs256_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="auth is not configured")

    try:
        token = _extract_bearer_token(request)
        payload = _decode_hs256_jwt(
            token,
            secret=settings.auth_jwt_hs256_secret,
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
        )
        ctx = _claims_to_context(payload)
    except ValueError as e:
        log_audit_event(
            action="authn",
            result="deny",
            actor="anonymous",
            tenant_id="",
            resource=request.url.path,
            detail=str(e),
            method=request.method,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    request.state.request_context = ctx
    return ctx


def require_roles(*allowed_roles: str):
    allowed = {r.strip().lower() for r in allowed_roles if r.strip()}

    def _dependency(request: Request, ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        settings = get_settings()
        if not settings.rbac_enabled:
            return ctx

        actual = {r.lower() for r in ctx.roles}
        if allowed and actual.isdisjoint(allowed):
            log_audit_event(
                action="authz",
                result="deny",
                actor=ctx.subject,
                tenant_id=ctx.tenant_id,
                resource=request.url.path,
                detail=f"required_roles={sorted(allowed)} actual_roles={sorted(actual)}",
                method=request.method,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return ctx

    return _dependency


def hash_subject(value: str) -> str:
    # Keep actor references deterministic but avoid storing raw identities in all contexts.
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
