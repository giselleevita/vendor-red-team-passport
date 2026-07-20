from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import uuid
from pathlib import Path

from apps.api.config import get_settings
from apps.api.services.run_store import reports_dir


def _audit_log_path() -> Path:
    d = reports_dir() / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d / "events.log"


def _compute_event_hmac(event_json: str, secret: str) -> str:
    """
    Compute HMAC-SHA256 for an audit event (for tamper detection).

    Args:
        event_json: JSON string of the event (must be canonical/sorted)
        secret: HMAC secret key

    Returns:
        Hex-encoded HMAC-SHA256 digest
    """
    return hmac.new(
        secret.encode("utf-8"),
        event_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def log_audit_event(
    *,
    action: str,
    result: str,
    actor: str,
    tenant_id: str,
    resource: str,
    detail: str = "",
    method: str = "",
) -> None:
    """
    Log an audit event (authentication, authorization, API activity).

    If VENDOR_RTP_MANIFEST_HMAC_KEY is set, each event is signed with HMAC-SHA256
    for tamper detection. The HMAC is computed before the event is written, allowing
    offline verification of log integrity.

    Args:
        action: Event action (e.g., "authn", "authz", "run.create")
        result: Event result ("allow" or "deny")
        actor: Actor identity (preferably hashed for privacy)
        tenant_id: Tenant ID for multi-tenancy
        resource: Resource being accessed (URL path, run_id, etc.)
        detail: Additional detail (limited to 300 chars)
        method: HTTP method (GET, POST, etc.)
    """
    event = {
        "event_id": str(uuid.uuid4()),
        "ts": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "action": action,
        "result": result,
        "actor": actor,
        "tenant_id": tenant_id,
        "method": method,
        "resource": resource,
        "detail": detail[:300],
    }

    # Add HMAC signature if secret is configured
    settings = get_settings()
    hmac_secret = (settings.vendor_rtp_manifest_hmac_key or "").strip()
    if hmac_secret:
        # Compute HMAC on a canonical (sorted) JSON representation
        event_json = json.dumps(event, ensure_ascii=True, sort_keys=True)
        event["hmac_sha256"] = _compute_event_hmac(event_json, hmac_secret)

    # Append to the local log. The optional signature makes later tampering detectable.
    p = _audit_log_path()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")
