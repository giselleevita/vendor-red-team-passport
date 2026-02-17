from fastapi.testclient import TestClient

from apps.api.main import app


def test_metrics_endpoint_exposes_request_counters(auth_header) -> None:
    client = TestClient(app)
    r1 = client.get("/health")
    assert r1.status_code == 200

    r2 = client.get("/profiles")
    assert r2.status_code == 401

    r3 = client.get("/profiles", headers=auth_header(roles=["viewer"]))
    assert r3.status_code == 200

    metrics = client.get("/metrics", params={"fmt": "json"}, headers=auth_header(roles=["auditor"]))
    assert metrics.status_code == 200
    body = metrics.json()
    assert "http_requests_total" in body
    assert "http_request_duration_ms" in body

    rows = body["http_requests_total"]
    assert any(r["route"] == "/health" and r["status_code"] == 200 for r in rows)
    assert any(r["route"] == "/profiles" and r["status_code"] == 401 for r in rows)
    assert any(r["route"] == "/profiles" and r["status_code"] == 200 for r in rows)

