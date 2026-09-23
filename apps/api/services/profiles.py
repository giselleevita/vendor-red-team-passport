from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from apps.api.assets import builtin_profile, builtin_profiles_dir, default_agent_suite, default_case_suite


def profiles_dir() -> Path:
    return builtin_profiles_dir()


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError("PyYAML is required to load YAML profiles. Install with `pip install -e .`") from e
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid profile format: expected mapping at {path}")
    return data


def _contains_secret_key(value: object) -> bool:
    blocked = {"api_key", "token", "authorization", "password", "secret"}
    if isinstance(value, dict):
        return any(str(key).lower() in blocked or _contains_secret_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_secret_key(item) for item in value)
    return False


def load_profile(name_or_path: str, *, allow_external_paths: bool = True) -> dict:
    """
    Load a run profile from disk.

    Supported:
    - absolute/relative file path (.yaml/.yml/.json)
    - short name resolved under ./profiles/<name>.(yaml|yml|json)
    """
    raw = (name_or_path or "").strip()
    if not raw:
        raise ValueError("profile name/path is empty")

    base = profiles_dir().resolve()
    if not allow_external_paths:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", raw) or raw in {".", ".."}:
            raise ValueError("invalid profile name")
        path = builtin_profile(raw)
    else:
        p = Path(raw).expanduser()
        if p.exists():
            path = p.resolve()
        else:
            path = builtin_profile(raw)

    if not allow_external_paths and not _is_within(base, path):
        raise PermissionError(f"profile path outside allowed profiles directory: {path.resolve()}")

    if path.suffix.lower() in (".yaml", ".yml"):
        data = _load_yaml(path)
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"invalid profile format: expected mapping at {path}")
    else:
        raise ValueError(f"unsupported profile extension: {path.suffix}")

    data.setdefault("name", path.stem)
    data.setdefault("source_path", str(path))
    data.setdefault("provider", "featherless")
    provider = str(data["provider"]).strip().lower()
    if provider not in {"featherless", "openai-compatible"}:
        raise ValueError(f"unsupported profile provider: {provider}")
    data["provider"] = provider
    if _contains_secret_key(data):
        raise ValueError("profiles cannot contain provider credentials")

    suite_path = (data.get("suite_path") or "").strip()
    if suite_path:
        sp = Path(suite_path)
        if not sp.is_absolute():
            if sp.as_posix() == "data/cases/cases.v1.json":
                data["suite_path"] = str(default_case_suite())
            else:
                data["suite_path"] = str((path.parent / sp).resolve())

    scenario_suite_path = (data.get("scenario_suite_path") or "").strip()
    if scenario_suite_path:
        sp = Path(scenario_suite_path)
        if not sp.is_absolute():
            if sp.as_posix() == "data/scenarios/defensive.v1.json":
                data["scenario_suite_path"] = str(default_agent_suite())
            else:
                data["scenario_suite_path"] = str((path.parent / sp).resolve())

    return data


@lru_cache(maxsize=1)
def list_profiles() -> list[dict]:
    base = profiles_dir()
    if not base.exists():
        return []

    items = []
    for path in sorted(base.glob("*.y*ml")) + sorted(base.glob("*.json")):
        try:
            data = load_profile(str(path))
            items.append(
                {
                    "name": data.get("name") or path.stem,
                    "description": data.get("description", ""),
                    "provider": data.get("provider", "featherless"),
                    "base_url": data.get("base_url", "configured by environment"),
                    "source_path": data.get("source_path", str(path)),
                }
            )
        except Exception:  # noqa: BLE001, S112 -- invalid profile files are omitted from the listing
            continue
    return items
