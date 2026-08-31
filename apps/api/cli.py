from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from apps.api.assets import DEFAULT_SUITE
from apps.api.config import get_settings
from apps.api.services.audit_verify import verify_audit_log
from apps.api.services.manifest import verify_manifest
from apps.api.services.orchestrator import run_orchestrated
from apps.api.services.profiles import load_profile
from apps.api.services.run_store import load_passport, run_dir


def _run(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile) if args.profile else None
    if args.base_url:
        profile = {**(profile or {}), "base_url": args.base_url}
    settings = get_settings()
    model = args.model or (profile.get("model") if profile else "") or settings.default_model
    suite = args.suite or (profile.get("suite_path") if profile else "") or DEFAULT_SUITE
    run_id = run_orchestrated(
        model=model,
        only_classes=args.only_classes or (profile.get("only_classes") if profile else None),
        a9_mode=args.a9_mode or (profile.get("a9_mode") if profile else "auto") or "auto",
        params=profile.get("params") if profile else None,
        run_id=args.run_id or None,
        suite_path=suite,
        profile=profile,
    )
    print(json.dumps({"run_id": run_id, "demo": str(run_dir(run_id) / "passport.html")}, indent=2))
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    results = []
    profile = load_profile(args.profile) if args.profile else None
    for model in args.models:
        run_id = run_orchestrated(
            model=model,
            only_classes=args.only_classes or (profile.get("only_classes") if profile else None),
            a9_mode=(profile.get("a9_mode") if profile else "auto") or "auto",
            params=profile.get("params") if profile else None,
            suite_path=args.suite or (profile.get("suite_path") if profile else DEFAULT_SUITE),
            profile=profile,
        )
        passport = load_passport(run_id)
        results.append({"model": model, "run_id": run_id, "summary": passport.summary.model_dump() if passport else {}})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({"results": results}, indent=2) + "\n", encoding="utf-8")
    return 0


def _verify_manifest(args: argparse.Namespace) -> int:
    path = Path(args.manifest) if args.manifest else run_dir(args.run_id) / "manifest.json"
    valid = verify_manifest(path, hmac_key=os.environ.get("VENDOR_RTP_MANIFEST_HMAC_KEY", ""))
    print("manifest valid" if valid else "manifest invalid")
    return 0 if valid else 2


def _verify_audit(args: argparse.Namespace) -> int:
    secret = args.secret or os.environ.get("VENDOR_RTP_MANIFEST_HMAC_KEY", "")
    valid = verify_audit_log(Path(args.path), secret)
    print("audit chain valid" if valid else "audit chain invalid")
    return 0 if valid else 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vendor-rtp")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--profile", default="")
    run.add_argument("--model", default="")
    run.add_argument("--suite", default="")
    run.add_argument("--base-url", default="", help="Override the selected profile endpoint for this run")
    run.add_argument("--only-classes", nargs="*", default=[])
    run.add_argument("--a9-mode", choices=["auto", "compat", "strict"], default="")
    run.add_argument("--run-id", default="")
    run.set_defaults(handler=_run)

    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--models", nargs="+", required=True)
    benchmark.add_argument("--profile", default="")
    benchmark.add_argument("--suite", default="")
    benchmark.add_argument("--only-classes", nargs="*", default=[])
    benchmark.add_argument("--out", default="reports/benchmarks/benchmark.latest.json")
    benchmark.set_defaults(handler=_benchmark)

    manifest = commands.add_parser("verify-manifest")
    manifest.add_argument("--run-id", default="")
    manifest.add_argument("--manifest", default="")
    manifest.set_defaults(handler=_verify_manifest)

    audit = commands.add_parser("verify-audit")
    audit.add_argument("--path", default="reports/audit/events.log")
    audit.add_argument("--secret", default="")
    audit.set_defaults(handler=_verify_audit)
    return parser


def main() -> int:
    args = _parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
