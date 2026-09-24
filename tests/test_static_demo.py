import json
from pathlib import Path


def test_static_demo_is_synthetic_and_safe() -> None:
    site = Path("site")
    html = (site / "index.html").read_text(encoding="utf-8")
    passport = json.loads((site / "passport.json").read_text(encoding="utf-8"))
    assurance = json.loads((site / "assurance.json").read_text(encoding="utf-8"))
    continuous = json.loads((site / "continuous-assurance.json").read_text(encoding="utf-8"))
    assert passport["synthetic"] is True
    assert assurance["synthetic"] is True
    assert continuous["synthetic"] is True
    assert continuous["latest_evaluation"]["outcome"] == "FAIL"
    assert passport["schema_version"] == "passport.v2"
    assert assurance["schema_version"] == "assurance-evidence.v1"
    assert assurance["assessment"]["status"] == "rejected"
    assert assurance["run_evidence"][0]["summary"]["release_gate"] == "FAIL"
    assert "Vendor A (synthetic)" in html
    assert "No real vendor output" in html
    lowered = (html + json.dumps(passport) + json.dumps(assurance) + json.dumps(continuous)).lower()
    assert "moonshotai" not in lowered
    assert "nousresearch" not in lowered
    assert "sk-proj-" not in lowered


def test_static_demo_local_links_exist() -> None:
    assert Path("site/passport.json").exists()
    assert Path("site/assurance.json").exists()
    assert Path("site/continuous-assurance.json").exists()
    assert 'href="passport.json"' in Path("site/index.html").read_text(encoding="utf-8")
    assert 'href="assurance.json"' in Path("site/index.html").read_text(encoding="utf-8")
    assert 'href="continuous-assurance.json"' in Path("site/index.html").read_text(encoding="utf-8")
