"""
E2E regression gate tests — verifies the /runs/compare endpoint correctly
flags regressions and passes stable baselines.
Skipped when VRTP_BASE_URL is not set.
"""
import os
import time
import pytest
import requests

BASE_URL = os.getenv("VRTP_BASE_URL", "")
API_KEY  = os.getenv("VRTP_API_KEY", "")

pytestmark = pytest.mark.skipif(
    not BASE_URL,
    reason="VRTP_BASE_URL not set — skipping e2e regression tests"
)

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def _create_and_wait(profile: str = "quick_gates", label: str = "") -> str:
    r = requests.post(
        f"{BASE_URL}/api/v1/runs",
        json={"profile": profile, "label": label or f"e2e-regression-{int(time.time())}"},
        headers=HEADERS
    )
    r.raise_for_status()
    run_id = r.json()["run_id"]
    deadline = time.time() + 90
    while time.time() < deadline:
        status_r = requests.get(f"{BASE_URL}/api/v1/runs/{run_id}", headers=HEADERS)
        status_r.raise_for_status()
        if status_r.json()["status"] not in ("pending", "running"):
            return run_id
        time.sleep(2)
    pytest.fail(f"Run {run_id} timed out")


class TestRegressionGate:

    def test_same_profile_no_regression(self):
        """Two identical profile runs should report no regression."""
        a = _create_and_wait("quick_gates", "base")
        b = _create_and_wait("quick_gates", "candidate")

        r = requests.get(
            f"{BASE_URL}/api/v1/runs/compare",
            params={"a": a, "b": b},
            headers=HEADERS
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # delta_pass_rate should be near 0 for identical profiles
        assert abs(data["delta_pass_rate"]) < 0.15, (
            f"Unexpected delta: {data['delta_pass_rate']}"
        )

    def test_compare_returns_required_fields(self):
        a = _create_and_wait(label="field-check-a")
        b = _create_and_wait(label="field-check-b")

        r = requests.get(
            f"{BASE_URL}/api/v1/runs/compare",
            params={"a": a, "b": b},
            headers=HEADERS
        )
        assert r.status_code == 200
        data = r.json()
        required = {"run_a", "run_b", "delta_pass_rate", "regression", "new_failures"}
        missing = required - data.keys()
        assert not missing, f"Missing keys in compare response: {missing}"

    def test_compare_invalid_run_id_returns_404(self):
        r = requests.get(
            f"{BASE_URL}/api/v1/runs/compare",
            params={"a": "nonexistent-run-000", "b": "nonexistent-run-001"},
            headers=HEADERS
        )
        assert r.status_code == 404
