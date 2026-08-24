import json
from pathlib import Path


def test_static_demo_is_synthetic_and_safe() -> None:
    site = Path("site")
    html = (site / "index.html").read_text(encoding="utf-8")
    passport = json.loads((site / "passport.json").read_text(encoding="utf-8"))
    assert passport["synthetic"] is True
    assert passport["schema_version"] == "passport.v2"
    assert "Vendor A (synthetic)" in html
    assert "No real vendor output" in html
    lowered = (html + json.dumps(passport)).lower()
    assert "moonshotai" not in lowered
    assert "nousresearch" not in lowered
    assert "sk-proj-" not in lowered


def test_static_demo_local_links_exist() -> None:
    assert Path("site/passport.json").exists()
    assert 'href="passport.json"' in Path("site/index.html").read_text(encoding="utf-8")
