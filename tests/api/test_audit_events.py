import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app


def _load_events(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_profile_read_writes_allow_audit_event(tmp_path: Path, monkeypatch, auth_header) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    client = TestClient(app)
    response = client.get("/profiles/quick_gates", headers=auth_header(roles=["viewer"]))
    assert response.status_code == 200

    events_path = tmp_path / "reports" / "audit" / "events.log"
    assert events_path.exists()
    events = _load_events(events_path)
    assert any(e.get("action") == "profile.read" and e.get("result") == "allow" for e in events)


def test_missing_token_writes_authn_deny_event(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    client = TestClient(app)
    response = client.get("/profiles")
    assert response.status_code == 401

    events_path = tmp_path / "reports" / "audit" / "events.log"
    assert events_path.exists()
    events = _load_events(events_path)
    assert any(e.get("action") == "authn" and e.get("result") == "deny" for e in events)
