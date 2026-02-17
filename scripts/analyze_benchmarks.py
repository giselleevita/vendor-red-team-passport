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


def safe_snippet(text: str, limit: int = 160) -> str:
    t = (text or "").replace("\n", " ").strip()
    if not t:
        return ""
    if REDACT_SECRET.search(t):
        return "<redacted: secret-like content>"
    if "```" in t:
        return "<redacted: code-block output>"
    return t[:limit]


def summarize_passport(passport_path: Path) -> dict:
    d = json.loads(passport_path.read_text(encoding="utf-8"))
    summary = d["summary"]
    failed = d.get("failed_cases", [])

    by_class = Counter(f["attack_class"] for f in failed)
    by_actual = Counter(f.get("actual") for f in failed)

    critical = [f for f in failed if f["attack_class"] in {"A4", "A5", "A6"}]
    critical_by_class = Counter(f["attack_class"] for f in critical)

    # Only show representative snippets for A4/A5/A6. Avoid copying offensive content into summaries.
    reps = {}
    for cls in ["A4", "A5", "A6", "A9"]:
        items = [f for f in failed if f["attack_class"] == cls]
        reps[cls] = [
            {
                "case_id": f["case_id"],
                "actual": f.get("actual"),
                "error": (f.get("error") or "")[:120],
                "snippet": safe_snippet(f.get("response_excerpt", "")),
            }
            for f in items[:3]
        ]

    return {
        "summary": summary,
        "fail_counts_by_class": dict(by_class.most_common()),
        "fail_counts_by_actual": dict(by_actual.most_common()),
        "critical_fail_counts": dict(critical_by_class.most_common()),
        "representative_failures": reps,
        "remediation_plan": remediation_plan(dict(by_class), summary),
    }


def remediation_plan(fail_counts_by_class: dict, summary: dict) -> list[dict]:
    # Vendor-side remediation guidance for procurement-ready reporting.
    items = []

    def add(cls: str, title: str, actions: list[str]) -> None:
        if fail_counts_by_class.get(cls, 0) <= 0:
            return
        items.append({"attack_class": cls, "title": title, "actions": actions})

    add(
        "A4",
        "Prevent System-Prompt / Hidden-Instruction Leakage",
        [
            "Enforce strict non-disclosure of system/developer prompts (runtime guardrails).",
            "Add leak detectors for phrases like 'knowledge cutoff', 'BEGIN you are', and policy text; block/redact before returning.",
            "Regression-test prompt-leak cases per release (A4 suite).",
        ],
    )
    add(
        "A5",
        "Block Secret/Credential Exfiltration and Secret Generation",
        [
            "Refuse requests for keys/tokens and avoid generating secrets (e.g., JWT signing keys).",
            "Add output scanners for secret-like patterns (JWT_SECRET=, Bearer, PEM blocks) and hard-fail/replace with refusal.",
            "Document policy: no credentials, no token recovery, no 'fresh secrets'.",
        ],
    )
    add(
        "A6",
        "Ensure Session/Tenant Isolation Guarantees",
        [
            "Refuse cross-session/other-tenant recall attempts with consistent denial templates.",
            "Disable or strictly scope memory features; confirm no training-time memorization leakage for sensitive domains.",
            "Add tests for cross-session leakage prompts (A6 suite) and treat any 'recall' as a release blocker.",
        ],
    )
    add(
        "A9",
        "Improve Structured Output Reliability (JSON-only)",
        [
            "If supported, enforce structured outputs at the provider layer; otherwise use a strict JSON-only contract + server-side validation/retry.",
            "Reject any output with code fences, extra text, extra keys, or wrong types (risk must be integer).",
            "Provide a vendor 'JSON mode' capability statement for integration teams.",
        ],
    )

    # Generic hardening if high-level gates fail.
    if summary.get("release_gate") == "FAIL":
        items.append(
            {
                "attack_class": "GATE",
                "title": "Release Gate Not Met",
                "actions": [
                    "Do not approve for sensitive deployments while A4/A5/A6 failures exist.",
                    "Re-run the full suite after remediation with identical parameters to confirm regression closure.",
                ],
            }
        )

    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--benchmark",
        default="",
        help="Benchmark JSON file. If omitted, picks the most recently modified reports/benchmarks/benchmark*.json",
    )
    args = ap.parse_args()

    if args.benchmark:
        bench = Path(args.benchmark)
    else:
        candidates = sorted(Path("reports/benchmarks").glob("benchmark*.json"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            raise SystemExit("no benchmark*.json found under reports/benchmarks/")
        bench = candidates[-1]
    if not bench.exists():
        raise SystemExit(f"missing {bench}")
    b = json.loads(bench.read_text(encoding="utf-8"))

    stem = bench.stem
    out_json = bench.parent / f"executive_summary.{stem}.json"
    out_md = bench.parent / f"executive_summary.{stem}.md"

    results = b.get("results", [])
    models = [r.get("model", "") for r in results]
    data = {}
    for r in results:
        model = r.get("model", "")
        run_id = r.get("run_id") or model
        passport_path = runs_dir() / run_id / "passport.json"
        summary = summarize_passport(passport_path)
        summary["run_id"] = run_id
        data[model] = summary

    out_json.write_text(json.dumps({"benchmark": str(bench), "models": data}, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Executive Summary (Vendor Red-Team Passport)")
    lines.append("")
    lines.append(f"Benchmark: `{bench}`")
    lines.append("")
    for model in models:
        s = data[model]["summary"]
        run_id = data[model].get("run_id", model)
        lines.append(f"## {model}")
        lines.append(f"- run_id: `{run_id}`")
        lines.append(f"- Gate: `{s['release_gate']}`")
        lines.append(f"- Overall: `{s['overall_score']}` | P1: `{s['p1_pass_rate']}` | P2: `{s['p2_pass_rate']}`")
        lines.append(
            f"- A9: mode=`{s.get('a9_mode_used')}` strict_supported=`{s.get('a9_strict_supported')}` schema_validity=`{s.get('a9_schema_validity')}`"
        )
        lines.append(f"- Critical failures (A4/A5/A6): `{s['critical_failures']}`")
        lines.append("")
        lines.append("Top failure classes:")
        top = list(data[model]["fail_counts_by_class"].items())[:5]
        for cls, n in top:
            lines.append(f"- `{cls}`: {n}")
        lines.append("")
        lines.append("Critical failure samples (sanitized):")
        for cls in ["A4", "A5", "A6"]:
            reps = data[model]["representative_failures"][cls]
            if not reps:
                continue
            lines.append(f"- `{cls}`:")
            for r in reps:
                snippet = r["snippet"] or "<no snippet>"
                lines.append(f"  - {r['case_id']}: actual={r['actual']} err={('yes' if r['error'] else 'no')} snippet={snippet}")
        lines.append("")
        lines.append("Remediation plan (vendor-side):")
        for item in data[model]["remediation_plan"]:
            lines.append(f"- `{item['attack_class']}` {item['title']}")
            for a in item["actions"]:
                lines.append(f"  - {a}")
        lines.append("")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_md} and {out_json}")


if __name__ == "__main__":
    main()
