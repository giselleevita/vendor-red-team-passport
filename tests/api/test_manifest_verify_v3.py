from __future__ import annotations

import json

from apps.api.services.manifest import build_and_save_manifest, verify_manifest
from apps.api.services.run_store import run_dir, save_json_artifact


def test_manifest_verifier_checks_hash_size_hmac_and_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VENDOR_RTP_REPORTS_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("VENDOR_RTP_MANIFEST_HMAC_KEY", "manifest-secret")
    save_json_artifact("run-1", "policy.json", {"version": "test"})
    path = build_and_save_manifest("run-1")
    assert verify_manifest(path, hmac_key="manifest-secret")
    artifact = run_dir("run-1") / "policy.json"
    artifact.write_text("{}", encoding="utf-8")
    assert not verify_manifest(path, hmac_key="manifest-secret")

    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../outside.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert not verify_manifest(path)
