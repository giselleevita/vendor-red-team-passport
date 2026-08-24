import pytest

from apps.api.config import get_settings
from apps.api.config_validation import validate_auth_secrets, validate_judge_config


def test_auth_requires_issuer_and_audience(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_JWT_ISSUER", "")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="AUTH_JWT_ISSUER"):
        validate_auth_secrets()


def test_enabled_judge_requires_complete_https_config(monkeypatch) -> None:
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    monkeypatch.setenv("JUDGE_BASE_URL", "")
    monkeypatch.setenv("JUDGE_API_KEY", "")
    monkeypatch.setenv("JUDGE_MODEL", "")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="required settings"):
        validate_judge_config()

    monkeypatch.setenv("JUDGE_BASE_URL", "http://judge.example.invalid/v1")
    monkeypatch.setenv("JUDGE_API_KEY", "synthetic")
    monkeypatch.setenv("JUDGE_MODEL", "judge-model")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="HTTPS"):
        validate_judge_config()


def test_local_http_judge_is_allowed_for_development(monkeypatch) -> None:
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    monkeypatch.setenv("JUDGE_BASE_URL", "http://127.0.0.1:9000/v1")
    monkeypatch.setenv("JUDGE_API_KEY", "synthetic")
    monkeypatch.setenv("JUDGE_MODEL", "judge-model")
    monkeypatch.setenv("JUDGE_CONFIDENCE_THRESHOLD", "0.8")
    get_settings.cache_clear()
    validate_judge_config()


def test_judge_confidence_threshold_is_bounded(monkeypatch) -> None:
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    monkeypatch.setenv("JUDGE_BASE_URL", "https://judge.example.invalid/v1")
    monkeypatch.setenv("JUDGE_API_KEY", "synthetic")
    monkeypatch.setenv("JUDGE_MODEL", "judge-model")
    monkeypatch.setenv("JUDGE_CONFIDENCE_THRESHOLD", "0.2")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="between 0.5 and 1.0"):
        validate_judge_config()


def test_judge_rejects_credentials_in_url_and_negative_cost(monkeypatch) -> None:
    monkeypatch.setenv("JUDGE_ENABLED", "true")
    monkeypatch.setenv("JUDGE_BASE_URL", "https://user:pass@judge.example.invalid/v1")
    monkeypatch.setenv("JUDGE_API_KEY", "synthetic")
    monkeypatch.setenv("JUDGE_MODEL", "judge-model")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="cannot contain credentials"):
        validate_judge_config()

    monkeypatch.setenv("JUDGE_BASE_URL", "https://judge.example.invalid/v1")
    monkeypatch.setenv("JUDGE_INPUT_COST_PER_MILLION_TOKENS_USD", "-1")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="cannot be negative"):
        validate_judge_config()
