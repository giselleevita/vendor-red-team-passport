from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

_SAFE_ASSET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def _resource_path(package: str, name: str) -> Path:
    if not _SAFE_ASSET_NAME.fullmatch(name) or name in {".", ".."}:
        raise ValueError("invalid packaged asset name")
    resource = files(package).joinpath(name)
    if not resource.is_file():
        raise FileNotFoundError(f"packaged asset not found: {package}/{name}")
    return Path(str(resource))


def default_case_suite() -> Path:
    return _resource_path("data.cases", "cases.v1.json")


def default_agent_suite() -> Path:
    return _resource_path("data.scenarios", "defensive.v1.json")


def compliance_crosswalk() -> Path:
    return _resource_path("data.compliance", "crosswalk.v1.yaml")


def scenario_fixture(name: str) -> Path:
    return _resource_path("data.scenarios", name)


def builtin_profile(name: str) -> Path:
    for suffix in (".yaml", ".yml", ".json"):
        candidate = name if name.endswith(suffix) else f"{name}{suffix}"
        try:
            return _resource_path("profiles", candidate)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"profile not found: {name}")


def builtin_profiles_dir() -> Path:
    return Path(str(files("profiles")))
