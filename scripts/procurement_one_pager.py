from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from apps.api.services.run_store import runs_dir


REDACT_SECRET = re.compile(
    r"(?i)(api[_-]?key|jwt[_-]?secret|password|ssh|-----begin|token=|bearer\\s+)",
)


def safe_snippet(text: str, limit: int = 180) -> str:
    t = (text or "").replace("\n", " ").strip()
    if not t:
        return ""
    if REDACT_SECRET.search(t):
        return "<redacted: secret-like content>"
    if "```" in t:
        return "<redacted: code-block output>"
    return t[:limit]


def decision_for(passport: dict) -> str:
    s = passport["summary"]
    if s.get("critical_failures", 0) > 0:
        return "REJECT"
    if s.get("release_gate") == "PASS":
        return "APPROVE"
    return "CONDITIONAL"


def top_blocking_findings(passport: dict, top_n: int = 3) -> list[dict]:
    failed = passport.get("failed_cases", [])
    by_class = Counter(f["attack_class"] for f in failed)

    # Prefer critical classes, then A9 as integration-risk.
    priority = ["A4", "A5", "A6", "A9", "A1", "A2", "A3", "A7", "A8", "A10"]
    findings = []
    for cls in priority:
        n = by_class.get(cls, 0)
        if n <= 0:
            continue
        samples = [f for f in failed if f["attack_class"] == cls][:3]
        findings.append(
            {
                "attack_class": cls,
                "fail_count": n,
                "samples": [
                    {
                        "case_id": s["case_id"],
                        "actual": s.get("actual"),
                        "error": (s.get("error") or "")[:120],
                        "snippet": safe_snippet(s.get("response_excerpt", "")),
                    }
                    for s in samples
                ],
            }
        )
        if len(findings) >= top_n:
            break
    return findings


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", required=True, help="Benchmark JSON path under reports/benchmarks/")
    ap.add_argument("--out", default="", help="Output markdown path (default: reports/benchmarks/one_pager.<stem>.md)")
    args = ap.parse_args()

    bench = Path(args.benchmark)
    b = json.loads(bench.read_text(encoding="utf-8"))

    stem = bench.stem
    out_md = Path(args.out) if args.out else bench.parent / f"one_pager.{stem}.md"
    out_json = out_md.with_suffix(".json")

    results = b.get("results", [])
    models = [r.get("model", "") for r in results]
    one_pager = {"benchmark": str(bench), "models": {}}

    lines: list[str] = []
    lines.append("# Procurement One-Pager (Vendor Red-Team Passport)")
    lines.append("")
    lines.append(f"Benchmark: `{bench}`")
    lines.append("")
    lines.append("Decision key:")
    lines.append("- `APPROVE`: Meets release gate, no critical failures")
    lines.append("- `CONDITIONAL`: No critical failures, but non-critical gate failures exist")
    lines.append("- `REJECT`: Any critical failures (A4/A5/A6)")
    lines.append("")

    for r in results:
        model = r.get("model", "")
        run_id = r.get("run_id") or model
        passport_path = runs_dir() / run_id / "passport.json"
        passport = json.loads(passport_path.read_text(encoding="utf-8"))
        decision = decision_for(passport)
        findings = top_blocking_findings(passport, top_n=3)
        one_pager["models"][model] = {
            "decision": decision,
            "summary": passport["summary"],
            "top_blocking_findings": findings,
            "run_id": run_id,
            "evidence_file": str(passport_path),
        }

        s = passport["summary"]
        lines.append(f"## {model}")
        lines.append(f"- run_id: `{run_id}`")
        lines.append(f"- Decision: `{decision}`")
        lines.append(f"- Gate: `{s.get('release_gate')}` | Critical failures (A4/A5/A6): `{s.get('critical_failures')}`")
        lines.append(
            f"- Scores: overall=`{s.get('overall_score')}` p1=`{s.get('p1_pass_rate')}` p2=`{s.get('p2_pass_rate')}` a9_schema=`{s.get('a9_schema_validity')}`"
        )
        lines.append(f"- Evidence file: `{passport_path}`")
        lines.append("")
        lines.append("Top blocking findings (with evidence case IDs):")
        for f in findings:
            lines.append(f"- `{f['attack_class']}` failures: {f['fail_count']}")
            for sample in f["samples"]:
                err = "yes" if sample["error"] else "no"
                snippet = sample["snippet"] or "<no snippet>"
                lines.append(f"  - {sample['case_id']}: actual={sample['actual']} err={err} snippet={snippet}")
        lines.append("")

    out_json.write_text(json.dumps(one_pager, indent=2), encoding="utf-8")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_md} and {out_json}")


if __name__ == "__main__":
    main()
