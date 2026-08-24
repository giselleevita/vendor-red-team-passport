from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path

from apps.api.services.run_store import run_dir, save_json_artifact


def _utc_now_iso() -> str:
    return dt.datetime.now(tz=dt.timezone.utc).isoformat()


def _sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            n += len(chunk)
            h.update(chunk)
    return h.hexdigest(), n


def _canonical_json(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def build_manifest(*, run_id: str) -> dict:
    """
    Tamper-evident manifest for all run artifacts under reports/runs/<run_id>/.

    If `VENDOR_RTP_MANIFEST_HMAC_KEY` is set, an HMAC-SHA256 signature is included.
    """
    root = run_dir(run_id)
    if not root.exists():
        raise FileNotFoundError(f"missing run_dir: {root}")

    # Hash all files except the manifest itself.
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == "manifest.json":
            continue
        sha, nbytes = _sha256_file(path)
        files.append({"path": rel, "sha256": sha, "bytes": nbytes})

    base = {
        "version": "manifest.v1",
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "files": files,
        "notes": [
            "Manifest lists sha256 for run artifacts (sanitized-only evidence).",
            "If you store VENDOR_RTP_MANIFEST_HMAC_KEY securely, the hmac_sha256 field enables tamper-evidence.",
        ],
    }

    canonical = _canonical_json(base)
    manifest_sha256 = hashlib.sha256(canonical).hexdigest()
    manifest = dict(base)
    manifest["manifest_sha256"] = manifest_sha256

    key = (os.environ.get("VENDOR_RTP_MANIFEST_HMAC_KEY") or "").strip()
    if key:
        manifest["hmac_sha256"] = hmac.new(key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()

    return manifest


def build_and_save_manifest(run_id: str) -> Path:
    manifest = build_manifest(run_id=run_id)
    return save_json_artifact(run_id, "manifest.json", manifest)


def verify_manifest(manifest_path: Path, *, hmac_key: str = "") -> bool:
    """Verify manifest metadata, safe relative paths, hashes, sizes, and optional HMAC."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        root = manifest_path.parent.resolve()
        base = {key: manifest[key] for key in ("version", "run_id", "generated_at_utc", "files", "notes")}
        canonical = _canonical_json(base)
        if not hmac.compare_digest(hashlib.sha256(canonical).hexdigest(), manifest["manifest_sha256"]):
            return False
        if hmac_key:
            expected = hmac.new(hmac_key.encode(), canonical, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, manifest["hmac_sha256"]):
                return False
        for item in manifest["files"]:
            relative = Path(item["path"])
            if relative.is_absolute() or ".." in relative.parts:
                return False
            artifact = (root / relative).resolve()
            artifact.relative_to(root)
            digest, size = _sha256_file(artifact)
            if not hmac.compare_digest(digest, item["sha256"]) or size != int(item["bytes"]):
                return False
        return True
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
