from __future__ import annotations

import datetime as dt
import json
import uuid
from pathlib import Path

from apps.api.services.run_store import reports_dir


def _audit_log_path() -> Path:
    d = reports_dir() / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d / "events.log"


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
    p = _audit_log_path()
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")

