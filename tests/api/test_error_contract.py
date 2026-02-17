from fastapi.testclient import TestClient

from apps.api.main import app


def test_error_contract_401_includes_standard_fields() -> None:
    client = TestClient(app)
    response = client.get("/profiles")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "unauthorized"
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["correlation_id"], str) and body["correlation_id"]
    assert "X-Correlation-ID" in response.headers


def test_error_contract_422_validation_includes_standard_fields(auth_header) -> None:
    client = TestClient(app)
    response = client.post(
        "/runs",
        json={"a9_mode": "invalid-mode"},
        headers=auth_header(roles=["operator"]),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "request validation failed"
    assert isinstance(body["correlation_id"], str) and body["correlation_id"]
    assert isinstance(body["detail"], list)


def test_success_has_correlation_header() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
