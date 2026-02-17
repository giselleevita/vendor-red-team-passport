from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.run_store import run_dir


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_json(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="", help="Run id under reports/runs/")
    ap.add_argument("--manifest", default="", help="Path to manifest.json (optional)")
    args = ap.parse_args()

    if args.manifest:
        manifest_path = Path(args.manifest)
        root = manifest_path.parent
    elif args.run_id:
        root = run_dir(args.run_id)
        manifest_path = root / "manifest.json"
    else:
        raise SystemExit("provide --run-id or --manifest")

    if not manifest_path.exists():
        raise SystemExit(f"missing manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files") or []
    if not isinstance(files, list):
        raise SystemExit("invalid manifest: files must be a list")

    ok = True
    missing = []
    mismatched = []

    for f in files:
        if not isinstance(f, dict):
            continue
        rel = f.get("path")
        expected = f.get("sha256")
        if not isinstance(rel, str) or not isinstance(expected, str):
            continue
        p = root / rel
        if not p.exists():
            ok = False
            missing.append(rel)
            continue
        actual = _sha256_file(p)
        if actual != expected:
            ok = False
            mismatched.append({"path": rel, "expected": expected, "actual": actual})

    # Optional HMAC verification if both key and field exist.
    key = (os.environ.get("VENDOR_RTP_MANIFEST_HMAC_KEY") or "").strip()
    hmac_expected = manifest.get("hmac_sha256")
    if key and isinstance(hmac_expected, str):
        base = {k: manifest[k] for k in ("version", "run_id", "generated_at_utc", "files", "notes") if k in manifest}
        canonical = _canonical_json(base)
        hmac_actual = hmac.new(key.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        if hmac_actual != hmac_expected:
            ok = False
            mismatched.append({"path": "manifest.hmac", "expected": hmac_expected, "actual": hmac_actual})

    print(f"manifest_verify: {'PASS' if ok else 'FAIL'} ({manifest_path})")
    if missing:
        print("missing_files:")
        for p in missing:
            print(f"- {p}")
    if mismatched:
        print("mismatches:")
        for m in mismatched:
            print(f"- {m['path']}: expected={m['expected']} actual={m['actual']}")

    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()

