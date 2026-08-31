from __future__ import annotations

from apps.api.assets import read_text


def map_compliance(failed_cases: list[dict]) -> dict:
    """
    Build a compliance/control mapping from the bundled crosswalk.
    This is a communication aid for procurement and audit trails, not legal certification.
    """
    failed_classes = {str(f.get("attack_class", "")).strip() for f in failed_cases if f.get("attack_class")}

    crosswalk_source = "builtin:compliance/crosswalk.v1.yaml"
    try:
        import yaml  # type: ignore

        crosswalk = yaml.safe_load(read_text(crosswalk_source))
    except Exception:
        # Fail safe: return empty mapping rather than breaking runs.
        return {"_meta": {"crosswalk": crosswalk_source, "loaded": False}, "frameworks": {}}

    if not isinstance(crosswalk, dict):
        return {"_meta": {"crosswalk": crosswalk_source, "loaded": False}, "frameworks": {}}

    frameworks: dict[str, list[dict]] = {}
    for framework, controls in crosswalk.items():
        if not isinstance(controls, list):
            continue
        out_controls = []
        for c in controls:
            if not isinstance(c, dict):
                continue
            control = c.get("control")
            linked = c.get("linked_classes") or []
            linked_classes = [str(x).strip().upper() for x in linked if str(x).strip()]
            hit = sorted(set(linked_classes).intersection(failed_classes))
            out_controls.append(
                {
                    "control": control,
                    "status": "FAIL" if hit else "PASS",
                    "linked_classes": linked_classes,
                    "failed_classes_hit": hit,
                }
            )
        frameworks[str(framework)] = out_controls

    # Keep frameworks at top-level for backwards readability (and include metadata).
    return {"_meta": {"crosswalk": crosswalk_source, "loaded": True}, **frameworks}
