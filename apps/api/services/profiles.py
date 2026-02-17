from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def _repo_root() -> Path:
    # apps/api/services/profiles.py -> repo root is 3 parents up.
    return Path(__file__).resolve().parents[3]


def profiles_dir() -> Path:
    return _repo_root() / "profiles"


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
    p = Path(raw).expanduser()
    if p.exists():
        path = p.resolve()
        if not allow_external_paths and not _is_within(base, path):
            raise PermissionError(f"profile path outside allowed profiles directory: {path}")
    else:
        candidates = [base / f"{raw}.yaml", base / f"{raw}.yml", base / f"{raw}.json"]
        path = next((c for c in candidates if c.exists()), None)
        if path is None:
            raise FileNotFoundError(f"profile not found: {raw} (looked in {base})")

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

    suite_path = (data.get("suite_path") or "").strip()
    if suite_path:
        sp = Path(suite_path)
        if not sp.is_absolute():
            data["suite_path"] = str((_repo_root() / sp).resolve())

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
                    "source_path": data.get("source_path", str(path)),
                }
            )
        except Exception:
            continue
    return items
