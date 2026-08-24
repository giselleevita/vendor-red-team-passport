import json

import httpx
import pytest

from apps.api.config import get_settings
from apps.api.schemas.case import Case
from apps.api.services.judge import SemanticJudge


def _case() -> Case:
    return Case(
        id="A1-JUDGE",
        attack_class="A1",
        priority="P1",
        severity="high",
        weight=1.0,
        prompt="synthetic prompt",
        expected_verdict="BLOCK",
    )


def _settings(monkeypatch, *, model: str = "judge-model", threshold: str = "0.80") -> None:
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    monkeypatch.setenv("JUDGE_BASE_URL", "https://judge.example.invalid/v1")
    monkeypatch.setenv("JUDGE_API_KEY", "synthetic-judge-key")
    monkeypatch.setenv("JUDGE_MODEL", model)
    monkeypatch.setenv("JUDGE_CONFIDENCE_THRESHOLD", threshold)
    get_settings.cache_clear()


def _transport(payload: dict | None = None, *, invalid: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        content = "not-json" if invalid else json.dumps(payload)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    return httpx.MockTransport(handler)


def test_judge_accepts_valid_high_confidence_decision(monkeypatch) -> None:
    _settings(monkeypatch)
    judge = SemanticJudge(target_model="target-model")
    judge._client.close()
    judge._client = httpx.Client(
        base_url="https://judge.example.invalid/v1",
        transport=_transport({"verdict": "BLOCK", "confidence": 0.95, "reason_codes": ["clear_refusal"]}),
    )
    decision = judge.evaluate(case=_case(), response_text="I cannot help.")
    judge.close()
    assert decision.verdict == "BLOCK"
    assert decision.confidence == 0.95
    assert decision.model == "judge-model"


def test_low_confidence_and_invalid_results_remain_uncertain(monkeypatch) -> None:
    _settings(monkeypatch)
    judge = SemanticJudge(target_model="target-model")
    judge._client.close()
    judge._client = httpx.Client(
        base_url="https://judge.example.invalid/v1",
        transport=_transport({"verdict": "ALLOW", "confidence": 0.4, "reason_codes": ["weak_signal"]}),
    )
    low = judge.evaluate(case=_case(), response_text="ambiguous")
    assert low.verdict == "UNCERTAIN"
    assert "below_confidence_threshold" in low.reason_codes
    judge._client.close()
    judge._client = httpx.Client(
        base_url="https://judge.example.invalid/v1",
        transport=_transport(invalid=True),
    )
    invalid = judge.evaluate(case=_case(), response_text="ambiguous")
    judge.close()
    assert invalid.verdict == "UNCERTAIN"
    assert invalid.reason_codes == ["judge_unavailable_or_invalid"]


@pytest.mark.parametrize(
    "payload",
    [
        {"verdict": "BLOCK", "confidence": 0.95, "reason_codes": "clear_refusal"},
        {"verdict": "BLOCK", "confidence": True, "reason_codes": []},
        {"verdict": "BLOCK", "confidence": 0.95, "reason_codes": [], "extra": "field"},
    ],
)
def test_malformed_judge_schema_remains_uncertain(monkeypatch, payload: dict) -> None:
    _settings(monkeypatch)
    judge = SemanticJudge(target_model="target-model")
    judge._client.close()
    judge._client = httpx.Client(
        base_url="https://judge.example.invalid/v1",
        transport=_transport(payload),
    )
    decision = judge.evaluate(case=_case(), response_text="ambiguous")
    judge.close()
    assert decision.verdict == "UNCERTAIN"
    assert decision.reason_codes == ["judge_unavailable_or_invalid"]


def test_judge_must_be_separate_from_target(monkeypatch) -> None:
    _settings(monkeypatch, model="same-model")
    with pytest.raises(RuntimeError, match="must differ"):
        SemanticJudge(target_model="same-model")


def test_judge_provider_host_must_be_isolated(monkeypatch) -> None:
    _settings(monkeypatch)
    with pytest.raises(RuntimeError, match="provider host"):
        SemanticJudge(target_model="target-model", target_base_url="https://judge.example.invalid:443/v1")


def test_judge_retries_within_budget_and_records_telemetry(monkeypatch) -> None:
    _settings(monkeypatch)
    monkeypatch.setenv("JUDGE_MAX_RETRIES", "1")
    monkeypatch.setenv("JUDGE_RETRY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("JUDGE_INPUT_COST_PER_MILLION_TOKENS_USD", "2")
    monkeypatch.setenv("JUDGE_OUTPUT_COST_PER_MILLION_TOKENS_USD", "4")
    get_settings.cache_clear()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"verdict": "BLOCK", "confidence": 0.9, "reason_codes": []})}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    judge = SemanticJudge(target_model="target-model")
    judge._client.close()
    judge._client = httpx.Client(base_url="https://judge.example.invalid/v1/", transport=httpx.MockTransport(handler))
    decision = judge.evaluate(case=_case(), response_text="ambiguous")
    telemetry = judge.telemetry()
    judge.close()
    assert decision.attempts == 2
    assert telemetry["attempts"] == 2
    assert telemetry["calls"] == 1
    assert telemetry["estimated_cost_usd"] > 0
    assert telemetry["data_retention"] == "ephemeral"
