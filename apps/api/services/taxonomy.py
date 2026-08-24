from __future__ import annotations

TAXONOMY_VERSION = "taxonomy.v2-owasp-2025"
EVALUATION_POLICY_VERSION = "evaluation.v2"

OWASP_GENAI_2025 = {
    "LLM01:2025": "Prompt Injection",
    "LLM02:2025": "Sensitive Information Disclosure",
    "LLM05:2025": "Improper Output Handling",
    "LLM07:2025": "System Prompt Leakage",
    "LLM10:2025": "Unbounded Consumption",
}


def class_taxonomy() -> dict[str, dict]:
    """Return the versioned communication crosswalk; this is never a certification claim."""
    common_nist = ["MEASURE", "MANAGE"]
    return {
        "A1": {"label": "Direct prompt injection", "owasp": ["LLM01:2025"], "relationship": "direct", "rationale": "Tests direct instruction override attempts.", "nist_ai_rmf": common_nist},
        "A2": {"label": "Jailbreak and role-play", "owasp": ["LLM01:2025"], "relationship": "direct", "rationale": "Tests persona and contextual attempts to bypass policy.", "nist_ai_rmf": common_nist},
        "A3": {"label": "Obfuscated prompt injection", "owasp": ["LLM01:2025"], "relationship": "direct", "rationale": "Tests encoded, Unicode, and transformed injection attempts.", "nist_ai_rmf": common_nist},
        "A4": {"label": "System prompt leakage", "owasp": ["LLM07:2025"], "relationship": "direct", "rationale": "Tests disclosure of hidden system and developer instructions.", "nist_ai_rmf": common_nist},
        "A5": {"label": "Secret exfiltration", "owasp": ["LLM02:2025"], "relationship": "direct", "rationale": "Tests disclosure or fabrication of credentials and secret material.", "nist_ai_rmf": common_nist},
        "A6": {"label": "Cross-session disclosure", "owasp": ["LLM02:2025"], "relationship": "direct", "rationale": "Tests attempts to retrieve data attributed to other users or sessions.", "nist_ai_rmf": common_nist},
        "A7": {"label": "Malware enablement", "owasp": [], "relationship": "policy-safety", "rationale": "Content-safety evaluation; no direct OWASP GenAI Top 10 coverage claimed.", "nist_ai_rmf": common_nist},
        "A8": {"label": "Unsafe transformation and social engineering", "owasp": [], "relationship": "policy-safety", "rationale": "Content-safety evaluation; no direct OWASP GenAI Top 10 coverage claimed.", "nist_ai_rmf": common_nist},
        "A9": {"label": "Structured output reliability", "owasp": ["LLM05:2025"], "relationship": "related", "rationale": "Schema enforcement supports safer output handling but does not prove full LLM05 coverage.", "nist_ai_rmf": common_nist},
        "A10": {"label": "Token and resource abuse", "owasp": ["LLM10:2025"], "relationship": "direct", "rationale": "Tests requests intended to trigger unbounded generation or resource use.", "nist_ai_rmf": common_nist},
    }
