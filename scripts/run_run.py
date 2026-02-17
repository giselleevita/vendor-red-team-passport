from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.config import get_settings
from apps.api.services.orchestrator import run_orchestrated
from apps.api.services.profiles import load_profile
from apps.api.services.run_store import reports_dir, run_dir


def _safe_stem(s: str) -> str:
    s = s.strip().replace("/", "_").replace(":", "_")
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s[:80] if len(s) > 80 else s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="", help="Profile name/path (e.g. quick_gates, full_suite)")
    ap.add_argument("--model", default="", help="Featherless model name (default: DEFAULT_MODEL from .env)")
    ap.add_argument("--suite", default="data/cases/cases.v1.json", help="Case suite JSON path")
    ap.add_argument(
        "--only-classes",
        nargs="*",
        default=[],
        help="If set, run only these attack classes (e.g. A4 A5 A6 A9)",
    )
    ap.add_argument("--a9-mode", default="profile", choices=["profile", "auto", "compat", "strict"])
    ap.add_argument("--run-id", default="", help="Optional run_id. If omitted, a timestamped id is generated.")
    args = ap.parse_args()

    settings = get_settings()
    profile = load_profile(args.profile) if args.profile else None

    model = (args.model or "").strip() or (profile.get("model") if profile else "") or settings.default_model
    suite_path = (args.suite or "").strip() or (profile.get("suite_path") if profile else "") or "data/cases/cases.v1.json"

    only_classes = None
    if args.only_classes:
        only_classes = [c.strip().upper() for c in (args.only_classes or []) if c.strip()] or None
    elif profile and profile.get("only_classes"):
        only_classes = [str(c).strip().upper() for c in (profile.get("only_classes") or []) if str(c).strip()] or None

    a9_mode = args.a9_mode
    if a9_mode == "profile":
        a9_mode = (profile.get("a9_mode") if profile else "") or "auto"

    params = (profile.get("params") if profile else None) or None

    if args.run_id.strip():
        run_id = args.run_id.strip()
    else:
        ts = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_id = f"{_safe_stem(model)}.{ts}"

    run_orchestrated(
        model=model,
        only_classes=only_classes,
        a9_mode=a9_mode,
        params=params,
        run_id=run_id,
        suite_path=suite_path,
        profile=profile,
    )

    # Convenience pointers for CI/local workflows.
    rd = reports_dir()
    (rd / "last_run_id.txt").write_text(run_id + "\n", encoding="utf-8")
    (rd / "last_run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "model": model,
                "profile": (profile.get("name") if profile else ""),
                "only_classes": only_classes or [],
                "suite": suite_path,
                "a9_mode": a9_mode,
                "params": params or {},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    out = {
        "run_id": run_id,
        "run_dir": str(run_dir(run_id)),
        "passport_html": str(run_dir(run_id) / "passport.html"),
        "passport_json": str(run_dir(run_id) / "passport.json"),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
