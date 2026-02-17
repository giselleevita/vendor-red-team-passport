import sys
import base64
import hashlib
import hmac
import json
from pathlib import Path
import time

import pytest

from apps.api.config import get_settings

# Allow running `pytest` without editable install by ensuring repo root is on sys.path.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_hs256_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


@pytest.fixture(autouse=True)
def _security_defaults(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_JWT_HS256_SECRET", "test-secret")
    monkeypatch.setenv("RBAC_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEFAULT_TENANT_ID", "tenant-default")
    monkeypatch.setenv("AUTH_LEGACY_DEFAULT_TENANT_ID", "tenant-legacy")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def auth_header():
    def _make(*, sub: str = "user-1", tenant_id: str = "tenant-default", roles: list[str] | None = None) -> dict[str, str]:
        payload = {
            "sub": sub,
            "tenant_id": tenant_id,
            "roles": roles or ["viewer"],
            "exp": int(time.time()) + 3600,
        }
        token = make_hs256_jwt(payload, "test-secret")
        return {"Authorization": f"Bearer {token}"}

    return _make
