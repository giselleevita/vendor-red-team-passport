from fastapi.testclient import TestClient

from apps.api.main import app


def test_profiles_requires_authentication() -> None:
    client = TestClient(app)
    response = client.get("/profiles")
    assert response.status_code == 401


def test_profiles_invalid_token_rejected() -> None:
    client = TestClient(app)
    response = client.get("/profiles", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == 401


def test_runs_forbidden_for_viewer_role(auth_header) -> None:
    client = TestClient(app)
    response = client.post("/runs", json={"profile": "quick_gates"}, headers=auth_header(roles=["viewer"]))
    assert response.status_code == 403


def test_profiles_allowed_for_viewer(auth_header) -> None:
    client = TestClient(app)
    response = client.get("/profiles", headers=auth_header(roles=["viewer"]))
    assert response.status_code == 200
    assert isinstance(response.json(), list)
