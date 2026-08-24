from __future__ import annotations

from typing import Protocol, runtime_checkable
from urllib.parse import urlparse

from apps.api.config import get_settings
from apps.api.services.featherless_client import FeatherlessClient


@runtime_checkable
class ModelProvider(Protocol):
    provider_name: str
    base_url: str

    def __enter__(self) -> ModelProvider: ...

    def __exit__(self, exc_type, exc, tb) -> None: ...

    def chat(self, prompt: str, **kwargs) -> str: ...

    def supports_a9_risk_verdict_schema(self, model: str | None = None) -> bool: ...


def _validated_endpoint(value: str) -> str:
    parsed = urlparse(value)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise ValueError("provider base_url must use HTTPS except for localhost development")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("provider base_url cannot contain credentials, query, or fragment")
    return value.rstrip("/")


def create_provider(profile: dict | None = None) -> ModelProvider:
    settings = get_settings()
    profile = profile or {}
    provider = str(profile.get("provider") or "featherless").strip().lower()
    if provider not in {"featherless", "openai-compatible"}:
        raise ValueError(f"unsupported provider adapter: {provider}")
    endpoint = _validated_endpoint(str(profile.get("base_url") or settings.featherless_base_url).strip())
    key = settings.featherless_api_key if provider == "featherless" else settings.target_api_key
    if not key:
        variable = "FEATHERLESS_API_KEY" if provider == "featherless" else "TARGET_API_KEY"
        raise RuntimeError(f"{variable} is missing for provider adapter {provider}")
    return FeatherlessClient(base_url=endpoint, api_key=key, provider_name=provider)
