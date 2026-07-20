from __future__ import annotations

import json

import pytest

from apps.api.config import get_settings
from apps.api.config_validation import validate_all
from apps.api.services import audit
from apps.api.services.observability import mask_secret
from scripts.verify_audit_log import verify_audit_log


def test_startup_validation_rejects_weak_auth_secret(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_JWT_HS256_SECRET", "short")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="at least 32 characters"):
        validate_all()


def test_startup_validation_allows_offline_mode_without_vendor_key(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_JWT_HS256_SECRET", "a" * 32)
    monkeypatch.setenv("FEATHERLESS_API_KEY", "")
    get_settings.cache_clear()

    validate_all()


def test_signed_audit_event_verifies(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "events.log"
    monkeypatch.setenv("VENDOR_RTP_MANIFEST_HMAC_KEY", "audit-secret")
    monkeypatch.setattr(audit, "_audit_log_path", lambda: log_path)
    get_settings.cache_clear()

    audit.log_audit_event(
        action="run.create",
        result="allow",
        actor="actor-hash",
        tenant_id="tenant-a",
        resource="/runs",
        method="POST",
    )

    event = json.loads(log_path.read_text(encoding="utf-8"))
    assert event["hmac_sha256"]
    assert verify_audit_log(log_path, "audit-secret") is True


def test_mask_secret_reveals_only_requested_prefix() -> None:
    assert mask_secret("abcdefgh", visible_chars=3) == "abc*****"
