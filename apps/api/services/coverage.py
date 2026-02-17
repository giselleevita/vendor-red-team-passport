from __future__ import annotations

from collections import defaultdict


OWASP_LLM_TOP10 = {
    # OWASP Top 10 for LLM Applications (names are informative references).
    "LLM01": "Prompt Injection",
    "LLM02": "Insecure Output Handling",
    "LLM03": "Training Data Poisoning",
    "LLM04": "Model Denial of Service",
    "LLM05": "Supply Chain Vulnerabilities",
    "LLM06": "Sensitive Information Disclosure",
    "LLM07": "Insecure Plugin Design",
    "LLM08": "Excessive Agency",
    "LLM09": "Overreliance",
    "LLM10": "Model Theft",
}

NIST_AI_RMF_FUNCTIONS = ["GOVERN", "MAP", "MEASURE", "MANAGE"]


def class_to_controls() -> dict[str, dict]:
    """
    Heuristic crosswalk for reporting.
    This is not certification; it helps stakeholders reason about coverage.
    """
    return {
        "A1": {"owasp": ["LLM01"], "nist_ai_rmf": ["MAP", "MANAGE"], "label": "Prompt injection (direct)"},
        "A2": {"owasp": ["LLM02", "LLM09"], "nist_ai_rmf": ["MEASURE", "MANAGE"], "label": "Unsafe output handling"},
        "A3": {"owasp": ["LLM01"], "nist_ai_rmf": ["MAP", "MANAGE"], "label": "Prompt injection (obfuscated)"},
        "A4": {"owasp": ["LLM06"], "nist_ai_rmf": ["MEASURE", "MANAGE"], "label": "System prompt leakage"},
        "A5": {"owasp": ["LLM06"], "nist_ai_rmf": ["MEASURE", "MANAGE"], "label": "Secret exfiltration"},
        "A6": {"owasp": ["LLM06"], "nist_ai_rmf": ["GOVERN", "MANAGE"], "label": "Isolation / cross-session recall"},
        "A7": {"owasp": ["LLM02"], "nist_ai_rmf": ["MEASURE", "MANAGE"], "label": "Malware content generation"},
        "A8": {"owasp": ["LLM02"], "nist_ai_rmf": ["MEASURE", "MANAGE"], "label": "Social engineering / phishing"},
        "A9": {"owasp": ["LLM02"], "nist_ai_rmf": ["MEASURE", "MANAGE"], "label": "Structured output reliability"},
        "A10": {"owasp": ["LLM04"], "nist_ai_rmf": ["MAP", "MANAGE"], "label": "Model DoS / resource abuse"},
    }


def build_coverage_report(*, evaluated_classes: list[str]) -> dict:
    mapping = class_to_controls()
    evaluated = [c for c in evaluated_classes if c]

    owasp_counts = defaultdict(int)
    nist_counts = defaultdict(int)

    rows = []
    for cls in sorted(set(evaluated)):
        m = mapping.get(cls, {"owasp": [], "nist_ai_rmf": [], "label": ""})
        for o in m.get("owasp", []):
            owasp_counts[o] += 1
        for n in m.get("nist_ai_rmf", []):
            nist_counts[n] += 1
        rows.append(
            {
                "attack_class": cls,
                "label": m.get("label", ""),
                "owasp": [{"id": o, "name": OWASP_LLM_TOP10.get(o, "")} for o in m.get("owasp", [])],
                "nist_ai_rmf": m.get("nist_ai_rmf", []),
            }
        )

    return {
        "version": "coverage.v1",
        "evaluated_classes": evaluated,
        "by_attack_class": rows,
        "summary": {
            "owasp_llm_top10": [{"id": k, "name": OWASP_LLM_TOP10.get(k, ""), "covered_by_classes": int(v)} for k, v in sorted(owasp_counts.items())],
            "nist_ai_rmf": [{"function": k, "covered_by_classes": int(v)} for k, v in sorted(nist_counts.items())],
        },
        "notes": [
            "Control mappings are heuristic crosswalks for communication, not compliance certification.",
            "Coverage depends on which classes were executed (e.g. quick_gates vs full_suite).",
        ],
    }

