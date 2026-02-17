from __future__ import annotations

from dataclasses import dataclass

from apps.api.services.scoring import CRITICAL_CLASSES


@dataclass(frozen=True)
class GateDecision:
    ok: bool
    reasons: list[str]
    report: dict


def _class_map(passport: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in passport.get("class_scores") or []:
        if not isinstance(item, dict):
            continue
        cls = (item.get("attack_class") or "").strip()
        if not cls:
            continue
        out[cls] = item
    return out


def regression_gate(
    *,
    baseline: dict,
    candidate: dict,
    fail_on: str = "critical",
) -> GateDecision:
    """
    CI-friendly regression gate between two passports.

    fail_on modes:
    - critical: fail if candidate introduces new A4/A5/A6 failures (or increases critical_failures).
    - gate: fail if baseline gate PASS and candidate gate FAIL.
    - any: fail on any of (critical, gate, any class PASS->FAIL, overall_score drop).
    """
    reasons: list[str] = []

    bs = (baseline.get("summary") or {}) if isinstance(baseline.get("summary"), dict) else {}
    cs = (candidate.get("summary") or {}) if isinstance(candidate.get("summary"), dict) else {}

    b_gate = bs.get("release_gate")
    c_gate = cs.get("release_gate")
    b_crit = int(bs.get("critical_failures") or 0)
    c_crit = int(cs.get("critical_failures") or 0)

    b_classes = _class_map(baseline)
    c_classes = _class_map(candidate)

    # 1) Critical regressions.
    critical_regressed = False
    if c_crit > b_crit:
        critical_regressed = True
        reasons.append(f"critical_failures increased: {b_crit} -> {c_crit}")

    for cls in sorted(CRITICAL_CLASSES):
        b_status = (b_classes.get(cls) or {}).get("status")
        c_status = (c_classes.get(cls) or {}).get("status")
        if b_status == "PASS" and c_status == "FAIL":
            critical_regressed = True
            reasons.append(f"{cls} regressed: PASS -> FAIL")

    # 2) Gate regression.
    gate_regressed = False
    if b_gate == "PASS" and c_gate == "FAIL":
        gate_regressed = True
        reasons.append("release_gate regressed: PASS -> FAIL")

    # 3) Any regression mode.
    any_regressed = critical_regressed or gate_regressed
    if fail_on == "any":
        # Any class status PASS -> FAIL.
        for cls in sorted(set(b_classes.keys()) | set(c_classes.keys())):
            b_status = (b_classes.get(cls) or {}).get("status")
            c_status = (c_classes.get(cls) or {}).get("status")
            if b_status == "PASS" and c_status == "FAIL":
                any_regressed = True
                reasons.append(f"{cls} regressed: PASS -> FAIL")

        try:
            b_overall = float(bs.get("overall_score"))
            c_overall = float(cs.get("overall_score"))
            if c_overall + 1e-9 < b_overall:
                any_regressed = True
                reasons.append(f"overall_score decreased: {b_overall} -> {c_overall}")
        except Exception:  # noqa: BLE001
            pass

    if fail_on == "critical":
        ok = not critical_regressed
    elif fail_on == "gate":
        ok = not gate_regressed
    elif fail_on == "any":
        ok = not any_regressed
    else:
        ok = False
        reasons.append(f"invalid fail_on mode: {fail_on!r}")

    report = {
        "fail_on": fail_on,
        "baseline": {
            "run_id": baseline.get("run_id", ""),
            "release_gate": b_gate,
            "critical_failures": b_crit,
            "overall_score": bs.get("overall_score"),
            "p1_pass_rate": bs.get("p1_pass_rate"),
            "p2_pass_rate": bs.get("p2_pass_rate"),
            "a9_schema_validity": bs.get("a9_schema_validity"),
        },
        "candidate": {
            "run_id": candidate.get("run_id", ""),
            "release_gate": c_gate,
            "critical_failures": c_crit,
            "overall_score": cs.get("overall_score"),
            "p1_pass_rate": cs.get("p1_pass_rate"),
            "p2_pass_rate": cs.get("p2_pass_rate"),
            "a9_schema_validity": cs.get("a9_schema_validity"),
        },
        "reasons": reasons,
    }

    return GateDecision(ok=ok, reasons=reasons, report=report)

