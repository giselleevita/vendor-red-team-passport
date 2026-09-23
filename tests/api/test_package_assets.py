from __future__ import annotations

from apps.api.assets import compliance_crosswalk, default_agent_suite, default_case_suite, scenario_fixture
from apps.api.services.profiles import load_profile


def test_required_runtime_assets_are_packaged() -> None:
    assert default_case_suite().is_file()
    assert default_agent_suite().is_file()
    assert compliance_crosswalk().is_file()
    assert scenario_fixture("defensive_demo.responses.json").is_file()


def test_builtin_agent_profile_resolves_packaged_assets() -> None:
    profile = load_profile("agent_defensive_demo", allow_external_paths=False)
    assert profile["scenario_suite_path"] == str(default_agent_suite())
