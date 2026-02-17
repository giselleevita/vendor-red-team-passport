from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from apps.api.main import app
from apps.api.services.run_store import validate_run_id


def test_validate_run_id_rejects_path_chars() -> None:
    for rid in ("..\\evil", "../evil", "x/y", "x\\y"):
        with pytest.raises(ValueError):
            validate_run_id(rid)


def test_passport_invalid_run_id_returns_400(auth_header) -> None:
    client = TestClient(app)
    response = client.get("/passports/bad%5Crun", headers=auth_header(roles=["viewer"]))
    assert response.status_code == 400
    assert "invalid run_id" in response.json()["detail"]


def test_create_run_rejects_external_profile_path(tmp_path: Path, auth_header) -> None:
    ext_profile = tmp_path / "external_profile.json"
    ext_profile.write_text('{"model":"x"}', encoding="utf-8")

    client = TestClient(app)
    response = client.post("/runs", json={"profile": str(ext_profile)}, headers=auth_header(roles=["operator"]))
    assert response.status_code == 400
    assert "outside allowed profiles directory" in response.json()["detail"]
