from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.config import get_settings
from apps.api.main import app


def test_streaming_limit_rejects_chunked_body_without_content_length(monkeypatch) -> None:
    monkeypatch.setenv("REQUEST_MAX_BODY_BYTES", "1024")
    get_settings.cache_clear()
    client = TestClient(app)

    def chunks():
        yield b"a" * 700
        yield b"b" * 700

    response = client.post("/runs", content=chunks(), headers={"transfer-encoding": "chunked"})
    assert response.status_code == 413
    assert response.json()["message"] == "request payload too large"

