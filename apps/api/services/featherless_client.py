from __future__ import annotations

import json
import time

import httpx

from apps.api.config import get_settings


class FeatherlessClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        provider_name: str = "featherless",
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.featherless_base_url).rstrip("/")
        self.api_key = settings.featherless_api_key if api_key is None else api_key
        self.provider_name = provider_name
        self.default_model = settings.default_model
        self.timeout = settings.request_timeout_seconds
        self.min_interval = settings.request_min_interval_seconds
        self.max_retries = settings.request_max_retries
        self.backoff_base = settings.request_retry_backoff_base_seconds
        self.max_sleep = settings.request_retry_max_sleep_seconds
        self.max_response_bytes = settings.provider_max_response_bytes
        self._last_request_at = 0.0

        if not self.api_key:
            raise RuntimeError("FEATHERLESS_API_KEY is missing. Set it in .env to run the suite against a real model.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "vendor-red-team-passport/0.5.0",
        }
        limits = httpx.Limits(max_connections=5, max_keepalive_connections=5)
        self._client = httpx.Client(timeout=self.timeout, headers=headers, limits=limits)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FeatherlessClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        self.close()

    def supports_response_format(self, model: str | None = None) -> bool:
        probe_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "probe",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["ok"],
                    "properties": {"ok": {"type": "boolean"}},
                },
                "strict": True,
            },
        }
        try:
            # If the backend enforces structured output, it should ignore attempts to append extra text.
            out = self.chat('Return {"ok": true} then append an explanation.', model=model, response_format=probe_schema)
            # Capability is only true if the backend actually returns strict JSON.
            import json

            parsed = json.loads(out.strip())
            return isinstance(parsed, dict) and parsed.get("ok") is True and set(parsed.keys()) == {"ok"}
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 400:
                return False
            raise
        except Exception:
            return False

    def supports_a9_risk_verdict_schema(self, model: str | None = None) -> bool:
        schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "risk_verdict",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["risk", "verdict"],
                    "properties": {"risk": {"type": "integer"}, "verdict": {"type": "string"}},
                },
                "strict": True,
            },
        }
        # Prompt explicitly tries to force extra text. If enforcement exists, it should still return strict JSON.
        prompt = 'Return {"risk": 0, "verdict": "ok"} then append an explanation.'
        try:
            out = self.chat(prompt, model=model, response_format=schema)
            import json

            stripped = out.strip()
            if not (stripped.startswith("{") and stripped.endswith("}")):
                return False
            parsed = json.loads(stripped)
            return (
                isinstance(parsed, dict)
                and set(parsed.keys()) == {"risk", "verdict"}
                and isinstance(parsed["risk"], int)
                and isinstance(parsed["verdict"], str)
            )
        except Exception:
            return False

    def list_models(self) -> list[str]:
        url = f"{self.base_url}/models"
        resp = self._client.get(url)
        resp.raise_for_status()
        data = resp.json()
        # OpenAI-style: {"data": [{"id": "..."}]}
        items = data.get("data", [])
        ids = []
        for item in items:
            mid = item.get("id")
            if isinstance(mid, str):
                ids.append(mid)
        return ids

    def chat(
        self,
        prompt: str,
        model: str | None = None,
        response_format: dict | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("FEATHERLESS_API_KEY is missing. Set it in .env to run the suite against a real model.")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        message = self.complete(
            messages=messages,
            model=model,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return str(message.get("content") or "")

    def complete(
        self,
        *,
        messages: list[dict],
        model: str | None = None,
        response_format: dict | None = None,
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Return one OpenAI-compatible assistant message, including proposed tool calls."""
        if not self.api_key:
            raise RuntimeError("FEATHERLESS_API_KEY is missing. Set it in .env to run against a real target.")
        payload: dict = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": 0 if temperature is None else temperature,
            "max_tokens": 256 if max_tokens is None else max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        url = f"{self.base_url}/chat/completions"

        # Simple pacing to avoid 429s in tight loops.
        now = time.time()
        elapsed = now - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        attempt = 0
        while True:
            attempt += 1
            self._last_request_at = time.time()
            try:
                with self._client.stream("POST", url, json=payload) as response:
                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after")
                        sleep_for = None
                        if retry_after is not None:
                            try:
                                sleep_for = float(retry_after)
                            except ValueError:
                                sleep_for = None
                        if sleep_for is None:
                            sleep_for = min(self.max_sleep, self.backoff_base * (2 ** (attempt - 1)))
                        if attempt <= self.max_retries:
                            time.sleep(sleep_for)
                            continue
                    if response.status_code == 400 and response_format is not None:
                        error_body = bytearray()
                        for chunk in response.iter_bytes():
                            error_body.extend(chunk)
                            if len(error_body) > self.max_response_bytes:
                                raise ValueError("provider response exceeded configured byte limit")
                        lowered_error = error_body.decode(errors="replace").lower()
                        if "response_format" in lowered_error or "json_schema" in lowered_error:
                            raise httpx.HTTPStatusError(
                                "response_format/json_schema unsupported by backend or model",
                                request=response.request,
                                response=response,
                            )
                    response.raise_for_status()
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > self.max_response_bytes:
                            raise ValueError("provider response exceeded configured byte limit")
                    data = json.loads(body)
                    break
            except httpx.HTTPStatusError as e:
                status = e.response.status_code if e.response is not None else None
                if status in (429, 500, 502, 503, 504) and attempt <= self.max_retries:
                    time.sleep(min(self.max_sleep, self.backoff_base * (2 ** (attempt - 1))))
                    continue
                if status == 400 and response_format is not None:
                    try:
                        error_body = e.response.text.lower()
                    except httpx.ResponseNotRead:
                        error_body = ""
                    if "response_format" in error_body or "json_schema" in error_body:
                        raise httpx.HTTPStatusError(
                            "response_format/json_schema unsupported by backend or model",
                            request=e.request,
                            response=e.response,
                        ) from e
                raise

        message = data["choices"][0]["message"]
        if not isinstance(message, dict):
            raise ValueError("provider response did not contain an assistant message")
        return message
