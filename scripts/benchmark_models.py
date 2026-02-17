from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys

from apps.api.services.orchestrator import run_orchestrated
from apps.api.services.run_store import load_passport


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True, help="One or more Featherless model names")
    ap.add_argument("--cases", default="data/cases/cases.v1.json")
    ap.add_argument("--profile", default="", help="Profile name/path (optional)")
    ap.add_argument("--out", default="reports/benchmarks/benchmark.latest.json")
    ap.add_argument("--only-class", default="", help="If set, run only a single attack class (e.g. A9)")
    ap.add_argument(
        "--only-classes",
        nargs="*",
        default=[],
        help="If set, run only these attack classes (e.g. --only-classes A4 A5 A6 A9)",
    )
    args = ap.parse_args()

    results = []
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    profile = None
    if args.profile:
        from apps.api.services.profiles import load_profile

        profile = load_profile(args.profile)

    suite_path = args.cases
    if profile and args.cases == "data/cases/cases.v1.json" and profile.get("suite_path"):
        suite_path = str(profile["suite_path"])

    only_classes = None
    if args.only_class:
        only_classes = [args.only_class]
    elif args.only_classes:
        only_classes = list(args.only_classes)
    elif profile and profile.get("only_classes"):
        only_classes = list(profile.get("only_classes") or []) or None

    ts = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for idx, model in enumerate(args.models, start=1):
        print(f"=== Running model {idx}/{len(args.models)}: {model} ===")
        safe_model = model.replace("/", "_").replace(":", "_")
        run_id = f"{safe_model}.{ts}"
        a9_mode = (profile.get("a9_mode") if profile else "") or "auto"
        params = (profile.get("params") if profile else None) or None

        run_orchestrated(
            model=model,
            only_classes=only_classes,
            a9_mode=a9_mode,
            params=params,
            run_id=run_id,
            suite_path=suite_path,
            profile=profile,
        )

        passport = load_passport(run_id)
        if passport is None:
            raise SystemExit(f"missing passport for run_id={run_id}")

        results.append({"model": model, "run_id": run_id, "summary": passport.summary.model_dump()})

        # Write intermediate results after each model so long runs still leave artifacts.
        out_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")

    print(f"Wrote {out_path}")

    # Auto-generate executive summary + one-pager for the written benchmark.
    subprocess.run([sys.executable, "scripts/analyze_benchmarks.py", "--benchmark", str(out_path)], check=True)
    subprocess.run([sys.executable, "scripts/procurement_one_pager.py", "--benchmark", str(out_path)], check=True)


if __name__ == "__main__":
    main()
