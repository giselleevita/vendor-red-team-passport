from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows path is exercised in platform CI
    fcntl = None
    import msvcrt

from apps.api.schemas.assurance import AssessmentRecord
from apps.api.services.run_store import reports_dir

_ASSESSMENT_ID_RE = re.compile(r"^[a-f0-9-]{36}$")


def assessments_dir() -> Path:
    return reports_dir() / "assessments"


def validate_assessment_id(assessment_id: str) -> str:
    value = (assessment_id or "").strip().lower()
    if not _ASSESSMENT_ID_RE.fullmatch(value):
        raise ValueError("invalid assessment_id")
    return value


def _assessment_path(assessment_id: str) -> Path:
    return assessments_dir() / f"{validate_assessment_id(assessment_id)}.json"


@contextmanager
def _store_lock():
    root = assessments_dir()
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".store.lock").open("a+b") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            return
        handle.seek(0)
        if handle.read(1) == b"":
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def save_assessment(record: AssessmentRecord, *, expected_updated_at: datetime | None = None) -> None:
    path = _assessment_path(record.assessment_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with _store_lock():
        if expected_updated_at is not None:
            if not path.exists():
                raise RuntimeError("assessment changed during update")
            current = AssessmentRecord.model_validate_json(path.read_text(encoding="utf-8"))
            if current.updated_at != expected_updated_at:
                raise RuntimeError("assessment changed during update")
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)


def load_assessment(assessment_id: str) -> AssessmentRecord | None:
    path = _assessment_path(assessment_id)
    if not path.exists():
        return None
    return AssessmentRecord.model_validate_json(path.read_text(encoding="utf-8"))


def list_assessments_for_tenant(tenant_id: str) -> list[AssessmentRecord]:
    root = assessments_dir()
    if not root.exists():
        return []
    records: list[AssessmentRecord] = []
    for path in root.glob("*.json"):
        try:
            record = AssessmentRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except (ValueError, json.JSONDecodeError):
            continue
        if record.tenant_id == tenant_id:
            records.append(record)
    return sorted(records, key=lambda item: item.updated_at, reverse=True)
