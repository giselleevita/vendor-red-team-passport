import time

import jwt
from fastapi.testclient import TestClient

from apps.api.main import app

SECRET = "test-secret-at-least-32-characters"  # noqa: S105 -- synthetic test-only signing key


def _payload() -> dict:
    now = int(time.time())
    return {
        "sub": "user-1",
        "tenant_id": "tenant-default",
        "roles": ["viewer"],
        "iat": now,
        "exp": now + 3600,
        "iss": "vendor-rtp-tests",
        "aud": "vendor-rtp-api",
    }


def _request(payload: dict, *, algorithm: str = "HS256", key: str = SECRET):
    token = jwt.encode(payload, key, algorithm=algorithm)
    return TestClient(app).get("/profiles", headers={"Authorization": f"Bearer {token}"})


def test_missing_expiration_is_rejected() -> None:
    payload = _payload()
    payload.pop("exp")
    response = _request(payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid bearer token"


def test_missing_issuer_or_audience_is_rejected() -> None:
    for claim in ("iss", "aud"):
        payload = _payload()
        payload.pop(claim)
        assert _request(payload).status_code == 401


def test_malformed_roles_claim_is_rejected() -> None:
    payload = _payload()
    payload["roles"] = "viewer"
    assert _request(payload).status_code == 401


def test_none_algorithm_is_rejected() -> None:
    token = jwt.encode(_payload(), key="", algorithm="none")
    response = TestClient(app).get("/profiles", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_expired_token_is_rejected() -> None:
    payload = _payload()
    payload["iat"] = int(time.time()) - 7200
    payload["exp"] = int(time.time()) - 3600
    assert _request(payload).status_code == 401
