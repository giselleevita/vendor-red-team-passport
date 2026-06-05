"""
Live UI access checks for authenticated pages.

Regression scoring itself is covered by offline unit tests. These checks only
verify that deployed server-rendered pages enforce bearer auth and load with a
valid token.
"""

import os

import httpx
import pytest

BASE_URL = os.getenv("VRTP_BASE_URL", "").rstrip("/")
TOKEN = os.getenv("VRTP_BEARER_TOKEN", "")

pytestmark = pytest.mark.skipif(not BASE_URL, reason="VRTP_BASE_URL not set; skipping live UI checks")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_compare_page_rejects_missing_token() -> None:
    response = httpx.get(f"{BASE_URL}/compare", timeout=10)
    assert response.status_code == 401


@pytest.mark.skipif(not TOKEN, reason="VRTP_BEARER_TOKEN not set; skipping authenticated live UI checks")
def test_compare_page_loads_with_bearer_token() -> None:
    response = httpx.get(f"{BASE_URL}/compare", headers=_headers(), timeout=10)
    assert response.status_code == 200
    assert "Compare" in response.text


@pytest.mark.skipif(not TOKEN, reason="VRTP_BEARER_TOKEN not set; skipping authenticated live UI checks")
def test_runs_page_loads_with_bearer_token() -> None:
    response = httpx.get(f"{BASE_URL}/runs", headers=_headers(), timeout=10)
    assert response.status_code == 200
    assert "Runs" in response.text
