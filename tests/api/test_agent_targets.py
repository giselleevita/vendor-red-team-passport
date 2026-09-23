from __future__ import annotations

import json

import httpx
import pytest

from apps.api.schemas.scenario import SimulatedTool
from apps.api.services.agent_targets import (
    HttpJsonAppTarget,
    OpenAICompatibleAgentTarget,
    ScriptedAgentTarget,
    create_agent_target,
)


def _tool() -> SimulatedTool:
    return SimulatedTool(
        name="search_docs",
        description="Synthetic search",
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
        authorization="allowed",
        result_fixture={"matches": []},
    )


class _FakeCompletionClient:
    provider_name = "fake-openai"

    def __init__(self) -> None:
        self.entered = False
        self.closed = False
        self.captured = {}

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.closed = True

    def complete(self, **kwargs):
        self.captured = kwargs
        return {
            "content": None,
            "tool_calls": [
                {
                    "id": "call-1",
                    "function": {"name": "search_docs", "arguments": '{"query":"retention"}'},
                },
                {
                    "id": "call-2",
                    "function": {"name": "search_docs", "arguments": "not-json"},
                },
            ],
        }


def test_openai_agent_target_parses_tool_calls_without_executing_them() -> None:
    client = _FakeCompletionClient()
    target = OpenAICompatibleAgentTarget(client)  # type: ignore[arg-type]
    with target:
        response = target.respond(
            scenario_id="S01",
            mutation="none",
            turn_index=0,
            messages=[{"role": "user", "content": "synthetic"}],
            tools=[_tool()],
            model="test-model",
        )
    assert client.entered and client.closed
    assert response.tool_calls[0].arguments == {"query": "retention"}
    assert response.tool_calls[1].arguments == {"_malformed_json": True}
    assert client.captured["tools"][0]["function"]["name"] == "search_docs"


def test_http_json_target_uses_fixed_contract_and_response_limit() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"content": "safe", "tool_calls": []})

    target = HttpJsonAppTarget(base_url="https://app.example", path="/agent-test", api_key="fixture-key")
    target.client.close()
    target.client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    with target:
        response = target.respond(
            scenario_id="S01",
            mutation="spacing",
            turn_index=0,
            messages=[{"role": "user", "content": "synthetic"}],
            tools=[],
            model="app",
        )
    assert response.content == "safe"
    assert captured["simulation_only"] is True

    oversized = HttpJsonAppTarget(base_url="https://app.example", path="/agent-test", api_key="")
    oversized.max_response_bytes = 4
    oversized.client.close()
    oversized.client = httpx.Client(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"content": "too long"}))
    )
    with oversized, pytest.raises(ValueError, match="byte limit"):
        oversized.respond(
            scenario_id="S01",
            mutation="none",
            turn_index=0,
            messages=[],
            tools=[],
            model="app",
        )


def test_agent_target_factory_restricts_script_paths_and_types() -> None:
    target = create_agent_target(
        {"target": {"type": "scripted", "script_path": "data/scenarios/defensive_demo.responses.json"}}
    )
    assert isinstance(target, ScriptedAgentTarget)
    with pytest.raises(ValueError, match="data/scenarios"):
        create_agent_target({"target": {"type": "scripted", "script_path": "README.md"}})
    with pytest.raises(ValueError, match="unsupported"):
        create_agent_target({"target": {"type": "live-shell"}})
    with pytest.raises(ValueError, match="target mapping"):
        create_agent_target({})
