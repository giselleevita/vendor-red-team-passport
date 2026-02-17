from __future__ import annotations

from pathlib import Path

def _repo_root() -> Path:
    # apps/api/services/compliance_mapper.py -> repo root is 3 parents up.
    return Path(__file__).resolve().parents[3]


def map_compliance(failed_cases: list[dict]) -> dict:
    """
    Build a compliance/control mapping from the crosswalk file under data/compliance/.
    This is a communication aid for procurement and audit trails, not legal certification.
    """
    failed_classes = {str(f.get("attack_class", "")).strip() for f in failed_cases if f.get("attack_class")}

    crosswalk_path = _repo_root() / "data" / "compliance" / "crosswalk.v1.yaml"
    try:
        import yaml  # type: ignore

        crosswalk = yaml.safe_load(crosswalk_path.read_text(encoding="utf-8"))
    except Exception:
        # Fail safe: return empty mapping rather than breaking runs.
        return {"_meta": {"crosswalk": str(crosswalk_path), "loaded": False}, "frameworks": {}}

    if not isinstance(crosswalk, dict):
        return {"_meta": {"crosswalk": str(crosswalk_path), "loaded": False}, "frameworks": {}}

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
    return {"_meta": {"crosswalk": str(crosswalk_path), "loaded": True}, **frameworks}
