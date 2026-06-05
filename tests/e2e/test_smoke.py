"""
Live API smoke tests.

Set VRTP_BASE_URL to run against a local or deployed service.
Set VRTP_BEARER_TOKEN to exercise authenticated read routes.
"""

import os

import httpx
import pytest

BASE_URL = os.getenv("VRTP_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("VRTP_BEARER_TOKEN", "")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="VRTP_BASE_URL not set; skipping live smoke tests")


def _headers(token: str = TOKEN) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def test_health_endpoint() -> None:
    response = httpx.get(f"{BASE_URL}/health", timeout=10)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_profiles_rejects_missing_token() -> None:
    response = httpx.get(f"{BASE_URL}/profiles", timeout=10)
    assert response.status_code == 401


def test_profiles_rejects_invalid_bearer_token() -> None:
    response = httpx.get(f"{BASE_URL}/profiles", headers=_headers("invalid.token.value"), timeout=10)
    assert response.status_code == 401


@pytest.mark.skipif(not TOKEN, reason="VRTP_BEARER_TOKEN not set; skipping authenticated live smoke test")
def test_profiles_accepts_bearer_token() -> None:
    response = httpx.get(f"{BASE_URL}/profiles", headers=_headers(), timeout=10)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
