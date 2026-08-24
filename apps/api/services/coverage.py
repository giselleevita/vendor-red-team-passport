from __future__ import annotations

from collections import defaultdict

from apps.api.services.taxonomy import OWASP_GENAI_2025, TAXONOMY_VERSION, class_taxonomy


def class_to_controls() -> dict[str, dict]:
    return class_taxonomy()


def build_coverage_report(*, evaluated_classes: list[str]) -> dict:
    mapping = class_taxonomy()
    evaluated = sorted({value for value in evaluated_classes if value})
    owasp_counts: dict[str, int] = defaultdict(int)
    nist_counts: dict[str, int] = defaultdict(int)
    rows = []
    for attack_class in evaluated:
        item = mapping.get(attack_class, {})
        owasp = list(item.get("owasp", []))
        nist = list(item.get("nist_ai_rmf", []))
        for identifier in owasp:
            owasp_counts[identifier] += 1
        for function in nist:
            nist_counts[function] += 1
        rows.append(
            {
                "attack_class": attack_class,
                "label": item.get("label", ""),
                "relationship": item.get("relationship", "unmapped"),
                "rationale": item.get("rationale", ""),
                "owasp": [
                    {"id": identifier, "name": OWASP_GENAI_2025.get(identifier, "")}
                    for identifier in owasp
                ],
                "nist_ai_rmf": nist,
            }
        )
    return {
        "version": "coverage.v2",
        "taxonomy_version": TAXONOMY_VERSION,
        "standards": {
            "owasp": "OWASP Top 10 for LLM Applications 2025",
            "nist_ai_rmf": "NIST AI RMF 1.0 (AI 100-1)",
        },
        "evaluated_classes": evaluated,
        "by_attack_class": rows,
        "summary": {
            "owasp_genai_2025": [
                {
                    "id": key,
                    "name": OWASP_GENAI_2025.get(key, ""),
                    "covered_by_classes": count,
                }
                for key, count in sorted(owasp_counts.items())
            ],
            "nist_ai_rmf": [
                {"function": key, "covered_by_classes": count}
                for key, count in sorted(nist_counts.items())
            ],
            "suite_process_functions": ["GOVERN", "MAP"],
        },
        "notes": [
            "Mappings are versioned communication aids, not certification or complete framework coverage.",
            "A7 and A8 are policy-safety tests and intentionally make no direct OWASP coverage claim.",
            "NIST SP 800-53 control identifiers are outside this function-level AI RMF crosswalk.",
        ],
    }
