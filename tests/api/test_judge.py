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


def test_judge_must_be_separate_from_target(monkeypatch) -> None:
    _settings(monkeypatch, model="same-model")
    with pytest.raises(RuntimeError, match="must differ"):
        SemanticJudge(target_model="same-model")
