from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol, runtime_checkable
from urllib.parse import urljoin

import httpx

from apps.api.assets import scenario_fixture
from apps.api.config import get_settings
from apps.api.schemas.scenario import AgentTurnResponse, ProposedToolCall, SimulatedTool
from apps.api.services.featherless_client import FeatherlessClient
from apps.api.services.providers import create_provider, validated_endpoint


@runtime_checkable
class AgentTarget(Protocol):
    target_name: str

    def __enter__(self) -> AgentTarget: ...

    def __exit__(self, exc_type, exc, tb) -> None: ...

    def respond(
        self,
        *,
        scenario_id: str,
        mutation: str,
        turn_index: int,
        messages: list[dict],
        tools: list[SimulatedTool],
        model: str,
    ) -> AgentTurnResponse: ...


def _tool_payload(tools: list[SimulatedTool]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]


def _parse_completion_message(message: dict) -> AgentTurnResponse:
    calls = []
    for item in message.get("tool_calls") or []:
        function = item.get("function") if isinstance(item, dict) else None
        if not isinstance(function, dict):
            continue
        raw_arguments = function.get("arguments", "{}")
        try:
            arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError:
            arguments = {"_malformed_json": True}
        if not isinstance(arguments, dict):
            arguments = {"_non_object_arguments": True}
        calls.append(
            ProposedToolCall(
                call_id=str(item.get("id", "")),
                name=str(function.get("name", "")),
                arguments=arguments,
            )
        )
    return AgentTurnResponse(content=str(message.get("content") or ""), tool_calls=calls)


class OpenAICompatibleAgentTarget:
    def __init__(self, client: FeatherlessClient) -> None:
        self.client = client
        self.target_name = client.provider_name

    def __enter__(self) -> OpenAICompatibleAgentTarget:
        self.client.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.client.__exit__(exc_type, exc, tb)

    def respond(self, *, messages: list[dict], tools: list[SimulatedTool], model: str, **_context) -> AgentTurnResponse:
        message = self.client.complete(messages=messages, model=model, tools=_tool_payload(tools))
        return _parse_completion_message(message)


class HttpJsonAppTarget:
    """Adapter for a fixed defensive-testing contract; it never follows redirects."""

    def __init__(self, *, base_url: str, path: str, api_key: str) -> None:
        if not path.startswith("/") or path.startswith("//") or ".." in path or "?" in path or "#" in path:
            raise ValueError("target.path must be an absolute relative path without traversal, query, or fragment")
        self.base_url = validated_endpoint(base_url)
        self.url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        self.target_name = "http-json-app"
        headers = {"User-Agent": "vendor-red-team-passport/0.5.1"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        settings = get_settings()
        self.max_response_bytes = settings.agent_max_response_bytes
        self.client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            headers=headers,
            follow_redirects=False,
        )

    def __enter__(self) -> HttpJsonAppTarget:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.client.close()

    def respond(
        self,
        *,
        scenario_id: str,
        mutation: str,
        turn_index: int,
        messages: list[dict],
        tools: list[SimulatedTool],
        model: str,
    ) -> AgentTurnResponse:
        payload = {
            "scenario_id": scenario_id,
            "mutation": mutation,
            "turn_index": turn_index,
            "model": model,
            "messages": messages,
            "tools": _tool_payload(tools),
            "simulation_only": True,
        }
        body = bytearray()
        with self.client.stream("POST", self.url, json=payload) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > self.max_response_bytes:
                    raise ValueError("target response exceeded configured byte limit")
        parsed = json.loads(body)
        return AgentTurnResponse.model_validate(parsed)


class ScriptedAgentTarget:
    def __init__(self, script: dict) -> None:
        self.script = script
        self.target_name = "scripted-defensive-fixture"

    def __enter__(self) -> ScriptedAgentTarget:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def respond(self, *, scenario_id: str, turn_index: int, **_context) -> AgentTurnResponse:
        turns = self.script.get(scenario_id)
        if not isinstance(turns, list) or turn_index >= len(turns):
            raise ValueError(f"missing scripted response for {scenario_id} turn {turn_index}")
        return AgentTurnResponse.model_validate(turns[turn_index])


def _safe_data_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path.parent.as_posix() != "data/scenarios":
        raise ValueError("script_path must remain under data/scenarios")
    return scenario_fixture(path.name)


def create_agent_target(profile: dict) -> AgentTarget:
    target = profile.get("target")
    if not isinstance(target, dict):
        raise ValueError("agent profile requires a target mapping")
    target_type = str(target.get("type", "")).strip().lower()
    if target_type == "scripted":
        path = _safe_data_path(str(target.get("script_path", "")))
        script = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(script, dict):
            raise ValueError("scripted target fixture must be a JSON object")
        return ScriptedAgentTarget(script)
    if target_type == "openai-compatible-agent":
        return OpenAICompatibleAgentTarget(create_provider(profile))
    if target_type == "http-json-app":
        return HttpJsonAppTarget(
            base_url=str(profile.get("base_url", "")),
            path=str(target.get("path", "/v1/agent-test")),
            api_key=get_settings().target_api_key,
        )
    raise ValueError("unsupported agent target type")
