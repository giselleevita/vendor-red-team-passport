from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from apps.api.assets import DEFAULT_SUITE, builtin_profile_source, list_builtin_profiles, read_text


def _load_yaml(source: str | Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PyYAML is required to load YAML profiles. Install the locked dependencies.") from exc
    data = yaml.safe_load(read_text(source))
    if not isinstance(data, dict):
        raise ValueError(f"invalid profile format: expected mapping at {source}")
    return data


def _builtin_source(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name) or name in {".", ".."}:
        raise ValueError("invalid profile name")
    source = builtin_profile_source(name)
    try:
        read_text(source)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"built-in profile not found: {name}") from exc
    return source


def load_profile(name_or_path: str, *, allow_external_paths: bool = True) -> dict:
    """Load a bundled profile or an explicit external YAML/JSON profile for CLI use."""
    raw = (name_or_path or "").strip()
    if not raw:
        raise ValueError("profile name/path is empty")

    candidate = Path(raw).expanduser()
    source: str | Path
    if allow_external_paths and candidate.exists():
        source = candidate.resolve()
    else:
        source = _builtin_source(raw)

    suffix = Path(str(source).removeprefix("builtin:")).suffix.lower()
    if suffix in (".yaml", ".yml"):
        data = _load_yaml(source)
    elif suffix == ".json":
        data = json.loads(read_text(source))
        if not isinstance(data, dict):
            raise ValueError(f"invalid profile format: expected mapping at {source}")
    else:
        raise ValueError(f"unsupported profile extension: {suffix}")

    source_label = str(source)
    data.setdefault("name", Path(source_label.removeprefix("builtin:")).stem)
    data.setdefault("source_path", source_label)
    data.setdefault("provider", "featherless")
    provider = str(data["provider"]).strip().lower()
    if provider not in {"featherless", "openai-compatible"}:
        raise ValueError(f"unsupported profile provider: {provider}")
    data["provider"] = provider
    if any(key.lower() in {"api_key", "token", "authorization"} for key in data):
        raise ValueError("profiles cannot contain provider credentials")

    suite_path = str(data.get("suite_path") or "").strip()
    if not suite_path:
        data["suite_path"] = DEFAULT_SUITE
    elif Path(suite_path).is_absolute():
        data["suite_path"] = suite_path
    elif source_label.startswith("builtin:"):
        data["suite_path"] = f"builtin:{Path(suite_path).as_posix()}"
    else:
        data["suite_path"] = str((Path(source).parent / suite_path).resolve())
    return data


@lru_cache(maxsize=1)
def list_profiles() -> list[dict]:
    items = []
    for name in list_builtin_profiles():
        try:
            data = load_profile(name, allow_external_paths=False)
            items.append(
                {
                    "name": data.get("name") or name,
                    "description": data.get("description", ""),
                    "provider": data.get("provider", "featherless"),
                    "base_url": data.get("base_url", "configured by environment"),
                    "source_path": data.get("source_path", f"builtin:profiles/{name}.yaml"),
                }
            )
        except Exception:  # noqa: BLE001, S112 -- omit invalid bundled profile from listing
            continue
    return items
