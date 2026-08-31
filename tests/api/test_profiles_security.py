from pathlib import Path

import pytest

from apps.api.services.profiles import load_profile


def test_profile_name_cannot_traverse_outside_profiles_directory() -> None:
    with pytest.raises(ValueError, match="invalid profile name"):
        load_profile("../outside-profile", allow_external_paths=False)


def test_explicit_external_profile_is_rejected_when_disabled(tmp_path: Path) -> None:
    outside = tmp_path / "external.yaml"
    outside.write_text("name: outside\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid profile name"):
        load_profile(str(outside), allow_external_paths=False)
