"""
E2E smoke tests — run against a live local server (or CI docker-compose).
Requires: VRTP_BASE_URL and VRTP_API_KEY env vars.
Skipped automatically when VRTP_BASE_URL is not set.
"""
import os
import time
import pytest
import requests

BASE_URL = os.getenv("VRTP_BASE_URL", "")
API_KEY  = os.getenv("VRTP_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="VRTP_BASE_URL not set — skipping e2e tests"
)

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def _poll(run_id: str, timeout: int = 60) -> dict:
    """Poll GET /runs/{run_id} until status != pending/running or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/api/v1/runs/{run_id}", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        if data["status"] not in ("pending", "running"):
            return data
        time.sleep(2)
    pytest.fail(f"Run {run_id} did not complete within {timeout}s")


class TestSmokeRunPipeline:
    """Happy-path: POST /runs → poll → verify completed."""

    def test_create_and_complete_quick_profile(self):
        payload = {
            "profile": "quick_gates",
            "label": "e2e-smoke"
        }
        r = requests.post(f"{BASE_URL}/api/v1/runs", json=payload, headers=HEADERS)
        assert r.status_code == 202, r.text
        run_id = r.json()["run_id"]
        assert run_id

        result = _poll(run_id)
        assert result["status"] == "completed", f"Unexpected status: {result}"
        assert result["summary"]["total"] > 0
        assert "pass_rate" in result["summary"]

    def test_run_has_passport(self):
        payload = {"profile": "quick_gates", "label": "e2e-passport"}
        r = requests.post(f"{BASE_URL}/api/v1/runs", json=payload, headers=HEADERS)
        r.raise_for_status()
        run_id = r.json()["run_id"]
        _poll(run_id)

        # Fetch passport
        pr = requests.get(f"{BASE_URL}/api/v1/runs/{run_id}/passport", headers=HEADERS)
        assert pr.status_code == 200, pr.text
        passport = pr.json()
        assert passport["run_id"] == run_id
        assert "claims" in passport
        assert "signature" in passport

    def test_health_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestSmokeCompare:
    """Run two jobs with the same profile and compare them."""

    @pytest.fixture(scope="class")
    def two_run_ids(self):
        ids = []
        for _ in range(2):
            r = requests.post(
                f"{BASE_URL}/api/v1/runs",
                json={"profile": "quick_gates", "label": "e2e-compare"},
                headers=HEADERS
            )
            r.raise_for_status()
            run_id = r.json()["run_id"]
            _poll(run_id)
            ids.append(run_id)
        return ids

    def test_compare_two_runs(self, two_run_ids):
        a, b = two_run_ids
        r = requests.get(
            f"{BASE_URL}/api/v1/runs/compare",
            params={"a": a, "b": b},
            headers=HEADERS
        )
        assert r.status_code == 200, r.text
        cmp = r.json()
        assert "delta_pass_rate" in cmp
        assert "regression" in cmp


class TestSmokeAuth:
    """Unauthenticated requests should be rejected."""

    def test_no_key_returns_401(self):
        r = requests.post(
            f"{BASE_URL}/api/v1/runs",
            json={"profile": "quick_gates"},
        )
        assert r.status_code in (401, 403)

    def test_invalid_key_returns_401(self):
        r = requests.post(
            f"{BASE_URL}/api/v1/runs",
            json={"profile": "quick_gates"},
            headers={"X-API-Key": "invalid-key-xxxx"}
        )
        assert r.status_code in (401, 403)
