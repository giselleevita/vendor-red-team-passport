from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import socket
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from apps.api.assets import default_case_suite
from apps.api.config import get_settings
from apps.api.schemas.operations import DeliveryRecord, ScheduleRecord, WebhookRecord
from apps.api.services.assurance import (
    _store_lock,
    assessments_dir,
    list_assessments_for_tenant,
    load_assessment,
    save_assessment,
)
from apps.api.services.continuous import evaluate_assessment, refresh_expiry
from apps.api.services.jobs import create_job, load_job
from apps.api.services.profiles import load_profile


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _records_dir(kind: str) -> Path:
    root = assessments_dir() / kind
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("unknown timezone") from exc
    return value


def validate_webhook_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("webhook URL must be HTTPS and must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("webhook URL must not contain a query string or fragment")
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith((".localhost", ".local", ".internal")):
        raise ValueError("webhook URL must not target a local hostname")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None and not literal.is_global:
        raise ValueError("webhook URL must not target a private or reserved address")
    allowed = {item.strip().rstrip(".").lower() for item in get_settings().webhook_allowed_hosts.split(",") if item.strip()}
    if allowed and hostname not in allowed:
        raise ValueError("webhook hostname is not allowlisted")
    return value


def _validate_public_resolution(url: str) -> None:
    hostname = urlsplit(url).hostname or ""
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("webhook hostname could not be resolved") from exc
    if not addresses:
        raise ValueError("webhook hostname could not be resolved")
    if any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("webhook hostname resolved to a private or reserved address")


def save_schedule(record: ScheduleRecord) -> None:
    with _store_lock():
        _write_json(_records_dir("schedules") / f"{record.schedule_id}.json", record.model_dump(mode="json"))


def load_schedule(schedule_id: str) -> ScheduleRecord | None:
    path = _records_dir("schedules") / f"{schedule_id}.json"
    return ScheduleRecord.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def list_schedules(tenant_id: str) -> list[ScheduleRecord]:
    records = []
    for path in _records_dir("schedules").glob("*.json"):
        try:
            record = ScheduleRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if record.tenant_id == tenant_id:
            records.append(record)
    return sorted(records, key=lambda item: item.next_run_at)


def _schedule_job(record: ScheduleRecord, *, now: datetime, force: bool = False) -> dict:
    slot = now.replace(second=0, microsecond=0).isoformat()
    job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"vendor-rtp:{record.schedule_id}:{slot}"))
    run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"vendor-rtp-run:{record.schedule_id}:{slot}"))
    existing = load_job(job_id)
    if existing:
        return existing
    profile = load_profile(record.profile, allow_external_paths=False)
    settings = get_settings()
    return create_job(job_id, {
        "run_id": run_id,
        "tenant_id": record.tenant_id,
        "created_by": "scheduler",
        "model": str(profile.get("model") or settings.default_model),
        "profile": str(profile.get("name") or record.profile),
        "profile_ref": record.profile,
        "a9_mode": str(profile.get("a9_mode") or "auto"),
        "only_classes": profile.get("only_classes") or [],
        "suite_path": str(profile.get("suite_path") or default_case_suite()),
        "params": profile.get("params") or {},
        "attempt_count": 0,
        "max_attempts": max(1, int(settings.run_job_max_attempts)),
        "next_attempt_at": None,
        "schedule_id": record.schedule_id,
        "assessment_id": record.assessment_id,
        "forced": force,
    })


def trigger_schedule(schedule_id: str, *, now: datetime | None = None, force: bool = False) -> dict:
    current = now or _now()
    with _store_lock():
        record = load_schedule(schedule_id)
        if record is None:
            raise FileNotFoundError("schedule not found")
        if not force and (not record.enabled or record.next_run_at > current):
            raise ValueError("schedule is not due")
        job = _schedule_job(record, now=current, force=force)
        record.last_job_id = str(job["job_id"])
        record.last_run_id = str(job["run_id"])
        record.last_run_at = current
        record.last_status = "queued"
        record.next_run_at = max(record.next_run_at, current) + timedelta(minutes=record.cadence_minutes)
        record.claim_expires_at = None
        record.updated_at = current
        _write_json(_records_dir("schedules") / f"{record.schedule_id}.json", record.model_dump(mode="json"))
        return job


def process_due_schedules(*, limit: int = 20, now: datetime | None = None) -> int:
    current = now or _now()
    due: list[str] = []
    for path in _records_dir("schedules").glob("*.json"):
        try:
            record = ScheduleRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if record.enabled and record.next_run_at <= current:
            due.append(record.schedule_id)
    processed = 0
    for schedule_id in sorted(due)[: max(1, limit)]:
        try:
            trigger_schedule(schedule_id, now=current)
            processed += 1
        except ValueError:
            continue
    return processed


def complete_scheduled_job(job: dict, *, succeeded: bool) -> dict | None:
    schedule_id = str(job.get("schedule_id", ""))
    assessment_id = str(job.get("assessment_id", ""))
    if not schedule_id or not assessment_id:
        return None
    record = load_schedule(schedule_id)
    assessment = load_assessment(assessment_id)
    if record is None or assessment is None or record.tenant_id != assessment.tenant_id:
        return None
    record.last_status = "succeeded" if succeeded else "failed"
    record.updated_at = _now()
    save_schedule(record)
    if not succeeded:
        emit_event(record.tenant_id, "reassessment.failed", {"assessment_id": assessment_id, "schedule_id": schedule_id})
        return None
    result = evaluate_assessment(assessment, str(job.get("run_id", "")))
    previous = assessment.updated_at
    assessment.last_evaluation = result
    assessment.evaluation_history.append(result)
    assessment.evaluation_history = assessment.evaluation_history[-100:]
    assessment.updated_at = _now()
    save_assessment(assessment, expected_updated_at=previous)
    if result["outcome"] != "PASS":
        event_type = "drift.failed" if "DRIFT_REGRESSION" in result["reason_codes"] else "policy.failed"
        emit_event(record.tenant_id, event_type, {"assessment_id": assessment_id, "evaluation": result})
    return result


def save_webhook(record: WebhookRecord) -> None:
    with _store_lock():
        _write_json(_records_dir("webhooks") / f"{record.webhook_id}.json", record.model_dump(mode="json"))


def load_webhook(webhook_id: str) -> WebhookRecord | None:
    path = _records_dir("webhooks") / f"{webhook_id}.json"
    return WebhookRecord.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def list_webhooks(tenant_id: str) -> list[WebhookRecord]:
    records = []
    for path in _records_dir("webhooks").glob("*.json"):
        try:
            record = WebhookRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if record.tenant_id == tenant_id:
            records.append(record)
    return sorted(records, key=lambda item: item.name)


def emit_event(tenant_id: str, event_type: str, payload: dict) -> list[DeliveryRecord]:
    now = _now()
    event_id = str(uuid.uuid4())
    created = []
    for webhook in list_webhooks(tenant_id):
        if not webhook.enabled:
            continue
        delivery = DeliveryRecord(delivery_id=str(uuid.uuid4()), event_id=event_id, tenant_id=tenant_id, webhook_id=webhook.webhook_id, event_type=event_type, payload=payload, created_at=now, updated_at=now)
        _write_json(_records_dir("deliveries") / f"{delivery.delivery_id}.json", delivery.model_dump(mode="json"))
        created.append(delivery)
    return created


def list_deliveries(tenant_id: str) -> list[DeliveryRecord]:
    records = []
    for path in _records_dir("deliveries").glob("*.json"):
        try:
            record = DeliveryRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if record.tenant_id == tenant_id:
            records.append(record)
    return sorted(records, key=lambda item: item.created_at, reverse=True)


def process_due_deliveries(*, limit: int = 20, now: datetime | None = None) -> int:
    current = now or _now()
    due: list[DeliveryRecord] = []
    for path in _records_dir("deliveries").glob("*.json"):
        try:
            record = DeliveryRecord.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if record.status == "queued" or (record.status == "retry" and (record.next_attempt_at is None or record.next_attempt_at <= current)):
            due.append(record)
    processed = 0
    for record in sorted(due, key=lambda item: item.created_at)[: max(1, limit)]:
        try:
            deliver_webhook(record.delivery_id, now=current)
        except ValueError:
            continue
        processed += 1
    return processed


def process_expired_approvals(*, now: datetime | None = None) -> int:
    current = now or _now()
    processed = 0
    for path in assessments_dir().glob("*.json"):
        try:
            assessment = load_assessment(path.stem)
        except ValueError:
            continue
        if assessment is None:
            continue
        previous = assessment.updated_at
        if refresh_expiry(assessment, now=current):
            assessment.updated_at = current
            save_assessment(assessment, expected_updated_at=previous)
            emit_event(assessment.tenant_id, "approval.expired", {"assessment_id": assessment.assessment_id})
            processed += 1
    return processed


def deliver_webhook(delivery_id: str, *, now: datetime | None = None) -> DeliveryRecord:
    path = _records_dir("deliveries") / f"{delivery_id}.json"
    if not path.exists():
        raise FileNotFoundError("delivery not found")
    delivery = DeliveryRecord.model_validate_json(path.read_text(encoding="utf-8"))
    if delivery.status == "succeeded":
        return delivery
    webhook = load_webhook(delivery.webhook_id)
    if webhook is None or webhook.tenant_id != delivery.tenant_id or not webhook.enabled:
        raise ValueError("webhook unavailable")
    secret = os.getenv(webhook.secret_env, "")
    if not secret:
        raise ValueError("webhook signing secret unavailable")
    _validate_public_resolution(webhook.url)
    current = now or _now()
    body = json.dumps({"schema_version": "webhook-event.v1", "event_id": delivery.event_id, "event_type": delivery.event_type, "created_at": delivery.created_at.isoformat(), "data": delivery.payload}, sort_keys=True, separators=(",", ":"))
    timestamp = str(int(current.timestamp()))
    signature = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
    delivery.attempt_count += 1
    try:
        response = httpx.post(webhook.url, content=body, headers={"Content-Type": "application/json", "X-Vendor-RTP-Event-ID": delivery.event_id, "X-Vendor-RTP-Timestamp": timestamp, "X-Vendor-RTP-Key-ID": webhook.key_id, "X-Vendor-RTP-Signature": f"v1={signature}"}, timeout=10.0, follow_redirects=False)
        response.raise_for_status()
        delivery.status = "succeeded"
        delivery.last_error = ""
        delivery.next_attempt_at = None
    except Exception as exc:  # noqa: BLE001
        delivery.last_error = type(exc).__name__[:120]
        if delivery.attempt_count >= 5:
            delivery.status = "dead_letter"
            delivery.next_attempt_at = None
        else:
            delivery.status = "retry"
            delivery.next_attempt_at = current + timedelta(seconds=min(300, 2 ** delivery.attempt_count))
    delivery.updated_at = current
    _write_json(path, delivery.model_dump(mode="json"))
    return delivery


def portfolio(tenant_id: str, *, now: datetime | None = None) -> list[dict]:
    current = now or _now()
    schedules = {schedule.assessment_id: schedule for schedule in list_schedules(tenant_id)}
    items = []
    priorities = {"expired": 0, "failed": 1, "review_required": 2, "due": 3, "healthy": 4}
    for assessment in list_assessments_for_tenant(tenant_id):
        previous = assessment.updated_at
        if refresh_expiry(assessment, now=current):
            assessment.updated_at = current
            save_assessment(assessment, expected_updated_at=previous)
            emit_event(tenant_id, "approval.expired", {"assessment_id": assessment.assessment_id})
        evaluation = assessment.last_evaluation or {}
        schedule = schedules.get(assessment.assessment_id)
        state = "healthy"
        if assessment.expired:
            state = "expired"
        elif evaluation.get("outcome") in {"FAIL", "UNKNOWN"}:
            state = "failed"
        elif "REVIEW_REQUIRED_LIMIT_EXCEEDED" in evaluation.get("reason_codes", []):
            state = "review_required"
        elif schedule and schedule.next_run_at <= current + timedelta(days=7):
            state = "due"
        items.append({"assessment_id": assessment.assessment_id, "vendor_name": assessment.vendor_name, "system_name": assessment.system_name, "risk_tier": assessment.risk_tier, "state": state, "last_evaluation": evaluation, "next_run_at": schedule.next_run_at.isoformat() if schedule else None, "priority": priorities[state]})
    return sorted(items, key=lambda item: (item["priority"], item["next_run_at"] or "9999"))
