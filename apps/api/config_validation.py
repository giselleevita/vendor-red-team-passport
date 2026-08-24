"""
Configuration validation at startup.

This module ensures that critical secrets and configuration are properly set
before the application starts. Failing validation prevents deployment of
insecure configurations (e.g., empty JWT secrets).
"""

from __future__ import annotations

from urllib.parse import urlparse

from apps.api.config import get_settings


def validate_auth_secrets() -> None:
    """
    Validate that authentication secrets are properly configured.

    Raises:
        RuntimeError: If AUTH_ENABLED=true but secrets are missing/invalid.
    """
    settings = get_settings()

    if not settings.auth_enabled:
        # Auth disabled, no validation needed (but not recommended for production)
        return

    errors = []

    # Check JWT secret
    secret = settings.auth_jwt_hs256_secret or ""
    if not secret.strip():
        errors.append(
            "AUTH_JWT_HS256_SECRET is empty but AUTH_ENABLED=true. "
            "Generate a secret with:\n"
            "  python -c 'import secrets; print(secrets.token_urlsafe(32))'\n"
            "Then set AUTH_JWT_HS256_SECRET in your .env file."
        )
    elif len(secret) < 32:
        errors.append(
            f"AUTH_JWT_HS256_SECRET must be at least 32 characters (got {len(secret)}). "
            "A weak secret compromises token signature verification. "
            "Generate with:\n"
            "  python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if not settings.auth_jwt_issuer.strip():
        errors.append("AUTH_JWT_ISSUER is required when authentication is enabled.")
    if not settings.auth_jwt_audience.strip():
        errors.append("AUTH_JWT_AUDIENCE is required when authentication is enabled.")

    if errors:
        raise RuntimeError(
            "❌ FATAL: Authentication configuration is invalid.\n\n"
            + "\n".join(f"  • {e}" for e in errors)
            + "\n\nFix these errors in your .env file and restart the application."
        )


def validate_api_credentials() -> None:
    """
    Validate that external API credentials are configured.

    Raises:
        RuntimeError: If required API keys are missing.
    """
    settings = get_settings()

    errors = []

    # Check Featherless API key
    if not (settings.featherless_api_key or "").strip():
        errors.append(
            "FEATHERLESS_API_KEY is empty. Get an API key from:\n"
            "  https://featherless.ai/api-keys\n"
            "Then set FEATHERLESS_API_KEY in your .env file."
        )

    if errors:
        raise RuntimeError(
            "❌ FATAL: API credentials are missing.\n\n"
            + "\n".join(f"  • {e}" for e in errors)
            + "\n\nGet the required credentials and update your .env file."
        )


def validate_job_store_config() -> None:
    """
    Validate that job store backend is properly configured.

    Raises:
        RuntimeError: If backend is "sql" but DSN is missing.
    """
    settings = get_settings()

    backend = (settings.job_store_backend or "file").strip().lower()

    if backend == "sql" and not (settings.job_store_dsn or "").strip():
        raise RuntimeError(
                "❌ FATAL: JOB_STORE_BACKEND=sql but JOB_STORE_DSN is empty.\n\n"
                "Set JOB_STORE_DSN in your .env file. Examples:\n"
                "  sqlite:///./jobs.db\n"
                "  postgresql://user:password@localhost:5432/vendor_rtp\n\n"
                "You must also have a PostgreSQL/SQLite database running."
        )


def validate_judge_config() -> None:
    settings = get_settings()
    if not settings.judge_enabled:
        return
    missing = [
        name
        for name, value in {
            "JUDGE_BASE_URL": settings.judge_base_url,
            "JUDGE_API_KEY": settings.judge_api_key,
            "JUDGE_MODEL": settings.judge_model,
        }.items()
        if not value.strip()
    ]
    if missing:
        raise RuntimeError(f"Judge enabled but required settings are missing: {', '.join(missing)}")
    parsed = urlparse(settings.judge_base_url)
    local_host = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local_host):
        raise RuntimeError("JUDGE_BASE_URL must use HTTPS, except for an explicit localhost development URL.")
    if not 0.5 <= settings.judge_confidence_threshold <= 1.0:
        raise RuntimeError("JUDGE_CONFIDENCE_THRESHOLD must be between 0.5 and 1.0.")


def validate_all() -> None:
    """
    Run all validation checks.

    Raises:
        RuntimeError: If any validation check fails.
    """
    validate_auth_secrets()
    validate_job_store_config()
    validate_judge_config()
