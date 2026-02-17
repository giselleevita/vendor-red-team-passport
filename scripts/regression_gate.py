from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.regression import regression_gate
from apps.api.services.run_store import iter_case_evidence, load_passport, run_dir
from apps.api.services.scoring import CRITICAL_CLASSES


def _top_new_critical_failures(*, baseline: dict, candidate_run_id: str, limit: int = 6) -> list[dict]:
    """
    Heuristic: show candidate critical failures. We avoid diffing by case_id because suites can change.
    Evidence is sanitized-only.
    """
    _ = baseline  # reserved for later diffing
    evidences = iter_case_evidence(candidate_run_id)
    failed = [e for e in evidences if not e.get("passed", True) and e.get("attack_class") in CRITICAL_CLASSES]
    failed.sort(key=lambda x: (x.get("attack_class", ""), x.get("case_id", "")))
    out = []
    for e in failed[:limit]:
        case_id = e.get("case_id", "")
        out.append(
            {
                "attack_class": e.get("attack_class", ""),
                "case_id": case_id,
                "actual": e.get("actual_verdict", ""),
                "evidence_url": f"/reports/runs/{candidate_run_id}/cases/{case_id}.json" if case_id else "",
            }
        )
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="Baseline run_id under reports/runs/")
    ap.add_argument("--candidate", required=True, help="Candidate run_id under reports/runs/")
    ap.add_argument("--fail-on", default="critical", choices=["critical", "gate", "any"])
    ap.add_argument("--json-out", default="", help="Optional JSON output path for CI artifacts")
    args = ap.parse_args()

    b = load_passport(args.baseline)
    c = load_passport(args.candidate)
    if b is None:
        raise SystemExit(f"baseline run_id not found: {args.baseline} ({run_dir(args.baseline)})")
    if c is None:
        raise SystemExit(f"candidate run_id not found: {args.candidate} ({run_dir(args.candidate)})")

    decision = regression_gate(baseline=b.model_dump(), candidate=c.model_dump(), fail_on=args.fail_on)

    report = decision.report | {
        "baseline_run_dir": str(run_dir(args.baseline)),
        "candidate_run_dir": str(run_dir(args.candidate)),
        "top_candidate_critical_failures": _top_new_critical_failures(
            baseline=b.model_dump(), candidate_run_id=args.candidate
        ),
    }

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    # Human output (CI logs).
    print(f"regression_gate: {'PASS' if decision.ok else 'FAIL'} (mode={args.fail_on})")
    print(f"baseline:  {args.baseline} gate={report['baseline']['release_gate']} crit={report['baseline']['critical_failures']}")
    print(f"candidate: {args.candidate} gate={report['candidate']['release_gate']} crit={report['candidate']['critical_failures']}")
    if decision.reasons:
        print("reasons:")
        for r in decision.reasons:
            print(f"- {r}")
    if report["top_candidate_critical_failures"]:
        print("top_candidate_critical_failures (sanitized evidence links):")
        for e in report["top_candidate_critical_failures"]:
            print(f"- {e['attack_class']} {e['case_id']} actual={e['actual']} evidence={e['evidence_url']}")

    raise SystemExit(0 if decision.ok else 2)


if __name__ == "__main__":
    main()

