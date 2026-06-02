from pathlib import Path

import pytest

from apps.api.services import profiles


def test_load_profile_allows_named_profile_within_repo(monkeypatch, tmp_path: Path) -> None:
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(parents=True)
    (profiles_root / "quick_gates.yaml").write_text("suite_path: data/cases/cases.v1.json\n", encoding="utf-8")
    monkeypatch.setattr(profiles, "_repo_root", lambda: tmp_path)

    profile = profiles.load_profile("quick_gates", allow_external_paths=False)

    assert profile["name"] == "quick_gates"
    assert profile["source_path"] == str((profiles_root / "quick_gates.yaml").resolve())


def test_load_profile_rejects_external_absolute_paths_when_disabled(monkeypatch, tmp_path: Path) -> None:
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(parents=True)
    outside = tmp_path / "outside.yaml"
    outside.write_text("suite_path: data/cases/cases.v1.json\n", encoding="utf-8")
    monkeypatch.setattr(profiles, "_repo_root", lambda: tmp_path)

    with pytest.raises(PermissionError):
        profiles.load_profile(str(outside.resolve()), allow_external_paths=False)


def test_load_profile_rejects_symlink_escape_when_external_paths_disabled(monkeypatch, tmp_path: Path) -> None:
    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir(parents=True)
    outside = tmp_path / "outside.yaml"
    outside.write_text("suite_path: data/cases/cases.v1.json\n", encoding="utf-8")
    escaped = profiles_root / "escaped.yaml"
    escaped.symlink_to(outside)
    monkeypatch.setattr(profiles, "_repo_root", lambda: tmp_path)

    with pytest.raises(PermissionError):
        profiles.load_profile(str(escaped), allow_external_paths=False)