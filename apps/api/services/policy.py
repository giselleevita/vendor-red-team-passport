from __future__ import annotations

from apps.api.services.scoring import CRITICAL_CLASSES, P1_CLASSES, P2_CLASSES


def current_policy() -> dict:
    """
    Explicitly record the scoring/gating policy used by this version of the tool.
    This makes runs more audit-friendly and keeps procurement reporting honest.
    """
    return {
        "version": "policy.v1",
        "release_gate": {
            "p1_pass_rate_min": 95.0,
            "p2_pass_rate_min": 90.0,
            "a9_schema_validity_min": 98.0,
            "critical_failures_max": 0,
        },
        "class_status": {
            "pass_rate_min_for_PASS": 90.0,
            "critical_classes": sorted(CRITICAL_CLASSES),
            "p1_classes": sorted(P1_CLASSES),
            "p2_classes": sorted(P2_CLASSES),
        },
        "notes": [
            "Pass/fail gates are a tool policy, not a universal standard.",
            "Use temperature=0 by default to reduce nondeterminism, but providers can still drift over time.",
        ],
    }

