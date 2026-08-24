from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

from apps.api.services.audit import AUDIT_FORMAT_VERSION, GENESIS_HASH


def _canonical_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _hmac(value: dict, secret: str) -> str:
    return hmac.new(secret.encode(), _canonical_json(value).encode(), hashlib.sha256).hexdigest()


def _event_hash(event: dict) -> str:
    return hashlib.sha256(_canonical_json(event).encode()).hexdigest()


def verify_audit_log(audit_log_path: Path, secret: str, *, require_checkpoint: bool = True) -> bool:
    if not audit_log_path.exists() or not secret.strip():
        return False
    expected_sequence = 1
    expected_previous_hash = GENESIS_HASH
    last_event_hash = GENESIS_HASH
    try:
        lines = [line for line in audit_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in lines:
            event = json.loads(line)
            signature = event.pop("event_hmac_sha256")
            if event.get("format_version") != AUDIT_FORMAT_VERSION:
                return False
            if event.get("sequence") != expected_sequence:
                return False
            if event.get("previous_event_hash") != expected_previous_hash:
                return False
            if not hmac.compare_digest(_hmac(event, secret), signature):
                return False
            event["event_hmac_sha256"] = signature
            last_event_hash = _event_hash(event)
            expected_previous_hash = last_event_hash
            expected_sequence += 1
        checkpoint_path = audit_log_path.with_suffix(".checkpoint.json")
        if not checkpoint_path.exists():
            return not require_checkpoint
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        checkpoint_signature = checkpoint.pop("checkpoint_hmac_sha256")
        if not hmac.compare_digest(_hmac(checkpoint, secret), checkpoint_signature):
            return False
        return (
            checkpoint.get("format_version") == AUDIT_FORMAT_VERSION
            and checkpoint.get("last_sequence") == expected_sequence - 1
            and checkpoint.get("last_event_hash") == last_event_hash
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
