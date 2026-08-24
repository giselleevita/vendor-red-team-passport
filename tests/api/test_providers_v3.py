from __future__ import annotations

import pytest

from apps.api.config import get_settings
from apps.api.services.providers import create_provider


def test_openai_compatible_profile_uses_environment_secret(monkeypatch) -> None:
    monkeypatch.setenv("TARGET_API_KEY", "target-secret")
    get_settings.cache_clear()
    provider = create_provider(
        {"provider": "openai-compatible", "base_url": "https://target.example/v1"}
    )
    assert provider.provider_name == "openai-compatible"
    assert provider.base_url == "https://target.example/v1"
    provider.close()


@pytest.mark.parametrize(
    "endpoint",
    ["http://remote.example/v1", "https://user:pass@example.com/v1", "https://example.com/v1?key=x"],
)
def test_provider_endpoint_rejects_unsafe_url_shapes(monkeypatch, endpoint: str) -> None:
    monkeypatch.setenv("TARGET_API_KEY", "target-secret")
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        create_provider({"provider": "openai-compatible", "base_url": endpoint})


def test_provider_rejects_unknown_adapter(monkeypatch) -> None:
    monkeypatch.setenv("TARGET_API_KEY", "target-secret")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="unsupported"):
        create_provider({"provider": "unknown", "base_url": "https://example.com/v1"})
