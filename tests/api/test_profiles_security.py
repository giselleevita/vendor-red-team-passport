from pathlib import Path

import pytest

from apps.api.services.profiles import load_profile, profiles_dir


def test_profile_name_cannot_traverse_outside_profiles_directory(tmp_path: Path) -> None:
    outside = profiles_dir().parent / "outside-profile.yaml"
    outside.write_text("name: outside\n", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="invalid profile name"):
            load_profile("../outside-profile", allow_external_paths=False)
    finally:
        outside.unlink(missing_ok=True)


def test_explicit_external_profile_is_rejected_when_disabled(tmp_path: Path) -> None:
    outside = tmp_path / "external.yaml"
    outside.write_text("name: outside\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid profile name"):
        load_profile(str(outside), allow_external_paths=False)


def test_nested_profile_credentials_are_rejected(tmp_path: Path) -> None:
    profile = tmp_path / "unsafe.yaml"
    profile.write_text(
        "provider: openai-compatible\ntarget:\n  type: http-json-app\n  api_key: must-not-be-here\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="credentials"):
        load_profile(str(profile))
