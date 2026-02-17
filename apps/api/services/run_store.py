from __future__ import annotations

import json
import os
from pathlib import Path

from apps.api.schemas.passport import Passport


def _repo_root() -> Path:
    # apps/api/services/run_store.py -> repo root is 3 parents up.
    return Path(__file__).resolve().parents[3]


def reports_dir() -> Path:
    """
    Resolve where to store/read artifacts from.

    Precedence:
    1) VENDOR_RTP_REPORTS_DIR env var
    2) ./reports (cwd) if it exists
    3) <repo_root>/reports
    """
    override = (os.environ.get("VENDOR_RTP_REPORTS_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()

    cwd_reports = Path.cwd() / "reports"
    if cwd_reports.exists():
        return cwd_reports.resolve()

    return (_repo_root() / "reports").resolve()


def runs_dir() -> Path:
    return reports_dir() / "runs"


def run_dir(run_id: str) -> Path:
    return runs_dir() / run_id


def cases_dir(run_id: str) -> Path:
    return run_dir(run_id) / "cases"


def save_run_meta(run_id: str, meta: dict) -> Path:
    d = run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "run.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path


def save_case_evidence(run_id: str, case_id: str, evidence: dict) -> Path:
    d = cases_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{case_id}.json"
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    return path


def list_case_ids(run_id: str) -> list[str]:
    d = cases_dir(run_id)
    if not d.exists():
        return []
    # Case IDs can include '-' so derive from filename.
    return sorted([p.stem for p in d.glob("*.json") if p.is_file()])


def load_case_evidence(run_id: str, case_id: str) -> dict | None:
    path = cases_dir(run_id) / f"{case_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def iter_case_evidence(run_id: str) -> list[dict]:
    evidences: list[dict] = []
    for case_id in list_case_ids(run_id):
        d = load_case_evidence(run_id, case_id)
        if isinstance(d, dict):
            evidences.append(d)
    return evidences


def save_passport_html(run_id: str, html: str) -> Path:
    d = run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "passport.html"
    path.write_text(html, encoding="utf-8")
    return path


def save_passport(run_id: str, passport: Passport) -> Path:
    d = run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / "passport.json"
    path.write_text(json.dumps(passport.model_dump(), indent=2), encoding="utf-8")
    return path


def save_json_artifact(run_id: str, filename: str, payload: dict) -> Path:
    d = run_dir(run_id)
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_passport(run_id: str) -> Passport | None:
    path = run_dir(run_id) / "passport.json"
    if not path.exists():
        return None
    return Passport.model_validate_json(path.read_text(encoding="utf-8"))


def list_run_ids() -> list[str]:
    root = runs_dir()
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def load_run_meta(run_id: str) -> dict | None:
    path = run_dir(run_id) / "run.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
