"""Access built-in package assets without depending on the source checkout."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

BUILTIN_PREFIX = "builtin:"
DEFAULT_SUITE = "builtin:cases/cases.v1.json"


def builtin_asset(relative_path: str):
    normalized = relative_path.strip().lstrip("/")
    if not normalized or ".." in Path(normalized).parts:
        raise ValueError("invalid built-in asset path")
    asset = files("apps.api.resources").joinpath(normalized)
    if not asset.is_file():
        raise FileNotFoundError(f"built-in asset not found: {normalized}")
    return asset


def read_text(source: str | Path) -> str:
    """Read either an explicit external file or a built-in package asset."""
    value = str(source)
    if value.startswith(BUILTIN_PREFIX):
        return builtin_asset(value.removeprefix(BUILTIN_PREFIX)).read_text(encoding="utf-8")
    return Path(value).expanduser().read_text(encoding="utf-8")


def builtin_profile_source(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized or any(part in {".", ".."} for part in Path(normalized).parts):
        raise ValueError("invalid profile name")
    return f"{BUILTIN_PREFIX}profiles/{normalized}.yaml"


def list_builtin_profiles() -> list[str]:
    return sorted(item.name.removesuffix(".yaml") for item in files("apps.api.resources").joinpath("profiles").iterdir())
