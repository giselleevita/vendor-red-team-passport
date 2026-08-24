import sys
import time
from pathlib import Path

import jwt
import pytest

from apps.api.config import get_settings
from apps.api.services.jobs import get_job_store
from apps.api.services.observability import reset_metrics

# Allow running `pytest` without editable install by ensuring repo root is on sys.path.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def make_hs256_jwt(payload: dict, secret: str) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def _security_defaults(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_JWT_HS256_SECRET", "test-secret-at-least-32-characters")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "vendor-rtp-tests")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "vendor-rtp-api")
    monkeypatch.setenv("RBAC_ENABLED", "true")
    monkeypatch.setenv("AUTH_DEFAULT_TENANT_ID", "tenant-default")
    monkeypatch.setenv("AUTH_LEGACY_DEFAULT_TENANT_ID", "tenant-legacy")
    get_settings.cache_clear()
    get_job_store.cache_clear()
    yield
    get_settings.cache_clear()
    get_job_store.cache_clear()


@pytest.fixture(autouse=True)
def _reset_observability_state():
    reset_metrics()
    yield
    reset_metrics()


@pytest.fixture
def auth_header():
    def _make(*, sub: str = "user-1", tenant_id: str = "tenant-default", roles: list[str] | None = None) -> dict[str, str]:
        payload = {
            "sub": sub,
            "tenant_id": tenant_id,
            "roles": roles or ["viewer"],
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "iss": "vendor-rtp-tests",
            "aud": "vendor-rtp-api",
        }
        token = make_hs256_jwt(payload, "test-secret-at-least-32-characters")
        return {"Authorization": f"Bearer {token}"}

    return _make
