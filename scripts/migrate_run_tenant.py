from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.config import get_settings
from apps.api.services.run_store import list_run_ids, run_dir


def _load_mapping(path: str) -> dict[str, str]:
    if not path:
        return {}
    p = Path(path)
    rows: dict[str, str] = {}
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"run_id", "tenant_id"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise SystemExit(f"mapping csv must contain headers: {sorted(required)}")
        for r in reader:
            run_id = str(r.get("run_id", "")).strip()
            tenant_id = str(r.get("tenant_id", "")).strip()
            if run_id and tenant_id:
                rows[run_id] = tenant_id
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--default-tenant", default="", help="Default tenant_id for runs without tenant_id")
    ap.add_argument("--mapping-csv", default="", help="Optional CSV with columns run_id,tenant_id")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = ap.parse_args()

    settings = get_settings()
    default_tenant = (args.default_tenant or "").strip() or settings.auth_legacy_default_tenant_id
    mapping = _load_mapping(args.mapping_csv)

    total = 0
    changed = 0
    skipped = 0
    updates: list[dict] = []

    for rid in list_run_ids():
        total += 1
        path = run_dir(rid) / "run.json"
        if not path.exists():
            skipped += 1
            continue
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            skipped += 1
            continue
        if not isinstance(meta, dict):
            skipped += 1
            continue

        current = str(meta.get("tenant_id", "")).strip()
        if current:
            continue

        tenant = mapping.get(rid, default_tenant)
        if not tenant:
            skipped += 1
            continue

        meta["tenant_id"] = tenant
        changed += 1
        updates.append({"run_id": rid, "tenant_id": tenant, "path": str(path)})
        if args.apply:
            path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "total_runs": total,
                "changed_runs": changed,
                "skipped_runs": skipped,
                "default_tenant": default_tenant,
                "mapping_entries": len(mapping),
                "updates": updates[:20],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
