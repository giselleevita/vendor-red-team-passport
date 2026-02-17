from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    featherless_api_key: str = ""
    featherless_base_url: str = "https://api.featherless.ai/v1"
    default_model: str = "moonshotai/Kimi-K2-Instruct"
    request_timeout_seconds: int = 45
    request_min_interval_seconds: float = 1.0
    request_max_retries: int = 6
    request_retry_backoff_base_seconds: float = 1.0
    request_retry_max_sleep_seconds: float = 20.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
