from __future__ import annotations

import json

import httpx
import pytest

from apps.api.services.featherless_client import FeatherlessClient


def _client(handler) -> FeatherlessClient:
    client = FeatherlessClient(base_url="https://provider.example/v1", api_key="test-key")
    client.min_interval = 0
    client.backoff_base = 0
    client.max_sleep = 0
    client._client.close()
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_chat_and_model_listing_use_openai_compatible_contract() -> None:
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "model-a"}, {"id": 7}, {}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "safe response"}}]})

    with _client(handler) as client:
        assert client.list_models() == ["model-a"]
        assert client.chat(
            "prompt", model="model-a", system="system", temperature=0.2, max_tokens=12,
            response_format={"type": "json_object"},
        ) == "safe response"
    payload = json.loads(captured[-1].content)
    assert payload["messages"][0]["role"] == "system"
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["max_tokens"] == 12


def test_chat_retries_rate_limit_and_server_error() -> None:
    statuses = iter([429, 503, 200])

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(statuses)
        if status == 200:
            return httpx.Response(200, json={"choices": [{"message": {"content": "recovered"}}]})
        return httpx.Response(status, headers={"retry-after": "invalid"}, text="retry", request=request)

    with _client(handler) as client:
        client.max_retries = 3
        assert client.chat("prompt") == "recovered"


def test_structured_output_rejection_is_explicit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="json_schema response_format unsupported", request=request)

    with _client(handler) as client:
        client.max_retries = 0
        with pytest.raises(httpx.HTTPStatusError, match="unsupported"):
            client.chat("prompt", response_format={"type": "json_schema"})


def test_capability_probes_are_conservative(monkeypatch) -> None:
    client = FeatherlessClient(base_url="https://provider.example/v1", api_key="test-key")
    monkeypatch.setattr(client, "chat", lambda *args, **kwargs: '{"ok": true}')
    assert client.supports_response_format()
    monkeypatch.setattr(client, "chat", lambda *args, **kwargs: '{"risk": 1, "verdict": "ok"}')
    assert client.supports_a9_risk_verdict_schema()
    monkeypatch.setattr(client, "chat", lambda *args, **kwargs: "not json")
    assert not client.supports_response_format()
    assert not client.supports_a9_risk_verdict_schema()
    client.close()


def test_missing_key_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="FEATHERLESS_API_KEY"):
        FeatherlessClient(base_url="https://provider.example/v1", api_key="")
