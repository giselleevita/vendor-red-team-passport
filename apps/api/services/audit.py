from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import hmac
import json
import os
import uuid
from pathlib import Path

from apps.api.config import get_settings
from apps.api.services.run_store import reports_dir

AUDIT_FORMAT_VERSION = "audit.v2"
GENESIS_HASH = "0" * 64


def _audit_log_path() -> Path:
    directory = reports_dir() / "audit"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "events.log"


def _checkpoint_path(log_path: Path) -> Path:
    return log_path.with_suffix(".checkpoint.json")


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _compute_event_hmac(event_json: str, secret: str) -> str:
    return hmac.new(secret.encode(), event_json.encode(), hashlib.sha256).hexdigest()


def _event_hash(event: dict) -> str:
    return hashlib.sha256(_canonical_json(event).encode()).hexdigest()


def _last_event(log_path: Path) -> tuple[int, str]:
    if not log_path.exists():
        return 0, GENESIS_HASH
    last_line = ""
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                last_line = line
    if not last_line:
        return 0, GENESIS_HASH
    event = json.loads(last_line)
    if event.get("format_version") != AUDIT_FORMAT_VERSION or "sequence" not in event:
        legacy_path = log_path.with_name(f"events.legacy-{uuid.uuid4().hex[:12]}.log")
        os.replace(log_path, legacy_path)
        return 0, GENESIS_HASH
    return int(event["sequence"]), _event_hash(event)


def _write_checkpoint(log_path: Path, event: dict, secret: str) -> None:
    checkpoint = {
        "format_version": AUDIT_FORMAT_VERSION,
        "last_sequence": event["sequence"],
        "last_event_hash": _event_hash(event),
    }
    if secret:
        checkpoint["checkpoint_hmac_sha256"] = _compute_event_hmac(_canonical_json(checkpoint), secret)
    target = _checkpoint_path(log_path)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(_canonical_json(checkpoint) + "\n", encoding="utf-8")
    os.replace(temporary, target)


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
    """Append one concurrency-safe, hash-chained audit event."""
    log_path = _audit_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = log_path.with_suffix(".lock")
    secret = (get_settings().vendor_rtp_manifest_hmac_key or "").strip()

    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            last_sequence, previous_hash = _last_event(log_path)
            event = {
                "format_version": AUDIT_FORMAT_VERSION,
                "sequence": last_sequence + 1,
                "previous_event_hash": previous_hash,
                "event_id": str(uuid.uuid4()),
                "ts": dt.datetime.now(tz=dt.UTC).isoformat(),
                "action": action,
                "result": result,
                "actor": actor,
                "tenant_id": tenant_id,
                "method": method,
                "resource": resource,
                "detail": detail[:300],
            }
            if secret:
                event["event_hmac_sha256"] = _compute_event_hmac(_canonical_json(event), secret)
            with log_path.open("a", encoding="utf-8") as output:
                output.write(_canonical_json(event) + "\n")
                output.flush()
                os.fsync(output.fileno())
            _write_checkpoint(log_path, event, secret)
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
