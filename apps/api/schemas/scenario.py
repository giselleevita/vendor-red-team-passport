from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SimulatedTool(StrictModel):
    name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    description: str = Field(min_length=1, max_length=300)
    input_schema: dict[str, Any]
    authorization: Literal["allowed", "denied"]
    result_fixture: Any = None

    @field_validator("input_schema")
    @classmethod
    def schema_is_local_and_bounded(cls, value: dict[str, Any]) -> dict[str, Any]:
        encoded = str(value)
        if len(encoded) > 10_000:
            raise ValueError("tool input_schema exceeds 10000 characters")

        def contains_ref(node: object) -> bool:
            if isinstance(node, dict):
                return "$ref" in node or any(contains_ref(item) for item in node.values())
            if isinstance(node, list):
                return any(contains_ref(item) for item in node)
            return False

        if contains_ref(value):
            raise ValueError("tool input_schema cannot contain $ref")
        if value.get("type") != "object":
            raise ValueError("tool input_schema root type must be object")
        return value


class ScenarioTurn(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    untrusted_context: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message cannot be blank")
        return cleaned

    @field_validator("untrusted_context")
    @classmethod
    def context_is_bounded(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 4000 for item in value):
            raise ValueError("untrusted context entries must contain 1..4000 characters")
        return [item.strip() for item in value]


class AgentScenario(StrictModel):
    id: str = Field(pattern=r"^S[0-9]{2,3}$")
    title: str = Field(min_length=1, max_length=160)
    category: Literal[
        "indirect_prompt_injection",
        "tool_authorization",
        "argument_validation",
        "cross_turn_escalation",
        "sensitive_data_disclosure",
        "resource_control",
    ]
    priority: Literal["P1", "P2"]
    severity: Literal["low", "medium", "high", "critical"]
    expected_outcome: Literal["refuse", "safe_response", "authorized_tool_call"]
    required_tool: str | None = None
    turns: list[ScenarioTurn] = Field(min_length=1, max_length=8)
    tools: list[SimulatedTool] = Field(default_factory=list, max_length=12)
    canaries: list[str] = Field(default_factory=list, max_length=10)
    mutations: list[Literal["none", "spacing", "base64"]] = Field(default_factory=lambda: ["none"], max_length=3)
    max_tool_calls: int = Field(default=4, ge=0, le=8)
    enabled: bool = True

    @field_validator("canaries")
    @classmethod
    def canaries_are_synthetic_and_bounded(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item or len(item) > 120 or not item.startswith("VRTP_CANARY_") for item in cleaned):
            raise ValueError("canaries must be bounded synthetic values beginning with VRTP_CANARY_")
        return cleaned

    @field_validator("mutations")
    @classmethod
    def mutations_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("mutations must be unique")
        return value

    @model_validator(mode="after")
    def required_tool_is_valid(self) -> AgentScenario:
        names = {tool.name for tool in self.tools}
        if self.expected_outcome == "authorized_tool_call":
            if not self.required_tool or self.required_tool not in names:
                raise ValueError("authorized_tool_call requires a declared required_tool")
            declared = next(tool for tool in self.tools if tool.name == self.required_tool)
            if declared.authorization != "allowed":
                raise ValueError("required_tool must be authorized")
        elif self.required_tool is not None:
            raise ValueError("required_tool is only valid for authorized_tool_call")
        return self


class AgentScenarioSuite(StrictModel):
    schema_version: Literal["agent-scenarios.v1"]
    suite_version: str = Field(min_length=1, max_length=40)
    generated_at: str
    scenarios: list[AgentScenario] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def scenario_ids_are_unique(self) -> AgentScenarioSuite:
        ids = [scenario.id for scenario in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario ids must be unique")
        return self


class ProposedToolCall(StrictModel):
    call_id: str = Field(default="", max_length=120)
    name: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentTurnResponse(StrictModel):
    content: str = Field(default="", max_length=100_000)
    tool_calls: list[ProposedToolCall] = Field(default_factory=list, max_length=20)


class ToolCallEvidence(StrictModel):
    name: str
    argument_keys: list[str]
    arguments_sha256: str
    authorized: bool
    schema_valid: bool


class AgentScenarioResult(StrictModel):
    scenario_id: str
    category: str
    mutation: str
    status: Literal["PASS", "FAIL", "UNCERTAIN", "ERROR"]
    passed: bool
    violations: list[str] = Field(default_factory=list)
    remediation: list[dict[str, str]] = Field(default_factory=list)
    response_excerpt: str = ""
    tool_calls: list[ToolCallEvidence] = Field(default_factory=list)
    latency_ms: int
    needs_human_review: bool = False
    error: str | None = None
