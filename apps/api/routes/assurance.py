from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.api.schemas.assurance import (
    AssessmentCreateRequest,
    AssessmentDecision,
    AssessmentDecisionRequest,
    AssessmentRecord,
    AssessmentRunLinkRequest,
    AssessmentStatus,
)
from apps.api.services.assurance import list_assessments_for_tenant, load_assessment, save_assessment
from apps.api.services.audit import log_audit_event
from apps.api.services.auth import RequestContext, hash_subject, require_roles
from apps.api.services.run_store import load_passport, load_run_meta, run_accessible_by_tenant

router = APIRouter(prefix="/assessments", tags=["assurance"])


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _owned_assessment(assessment_id: str, tenant_id: str) -> AssessmentRecord:
    try:
        record = load_assessment(assessment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if record is None or record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="assessment not found")
    return record


def _require_tenant_run(run_id: str, tenant_id: str) -> None:
    try:
        accessible = run_accessible_by_tenant(run_id, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not accessible:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")


def _audit(request: Request, ctx: RequestContext, action: str, assessment_id: str) -> None:
    log_audit_event(
        action=action,
        result="allow",
        actor=hash_subject(ctx.subject),
        tenant_id=ctx.tenant_id,
        resource=f"/assessments/{assessment_id}",
        method=request.method,
    )


def _save_update(record: AssessmentRecord, previous_updated_at: datetime) -> None:
    try:
        save_assessment(record, expected_updated_at=previous_updated_at)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail="assessment was updated by another reviewer") from exc


@router.post("", status_code=201)
def create_assessment(
    payload: AssessmentCreateRequest,
    request: Request,
    ctx: RequestContext = Depends(require_roles("operator", "admin")),
) -> dict:
    for run_id in payload.linked_run_ids:
        _require_tenant_run(run_id, ctx.tenant_id)
    now = _now()
    record = AssessmentRecord(
        assessment_id=str(uuid.uuid4()),
        tenant_id=ctx.tenant_id,
        vendor_name=payload.vendor_name,
        system_name=payload.system_name,
        use_case=payload.use_case,
        owner=payload.owner,
        risk_tier=payload.risk_tier,
        data_classification=payload.data_classification,
        review_due_at=payload.review_due_at,
        linked_run_ids=payload.linked_run_ids,
        created_at=now,
        updated_at=now,
        created_by=hash_subject(ctx.subject),
    )
    save_assessment(record)
    _audit(request, ctx, "assessment.create", record.assessment_id)
    return record.model_dump(mode="json")


@router.get("")
def list_assessments(
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    records = list_assessments_for_tenant(ctx.tenant_id)
    return {"items": [record.model_dump(mode="json") for record in records], "count": len(records)}


@router.get("/{assessment_id}")
def get_assessment(
    assessment_id: str,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    return _owned_assessment(assessment_id, ctx.tenant_id).model_dump(mode="json")


@router.post("/{assessment_id}/runs")
def link_run(
    assessment_id: str,
    payload: AssessmentRunLinkRequest,
    request: Request,
    ctx: RequestContext = Depends(require_roles("operator", "admin")),
) -> dict:
    record = _owned_assessment(assessment_id, ctx.tenant_id)
    if record.status != AssessmentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="runs can only be linked while an assessment is draft")
    _require_tenant_run(payload.run_id, ctx.tenant_id)
    if payload.run_id not in record.linked_run_ids:
        previous_updated_at = record.updated_at
        record.linked_run_ids.append(payload.run_id)
        record.updated_at = _now()
        _save_update(record, previous_updated_at)
    _audit(request, ctx, "assessment.run.link", record.assessment_id)
    return record.model_dump(mode="json")


@router.post("/{assessment_id}/submit")
def submit_assessment(
    assessment_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_roles("operator", "admin")),
) -> dict:
    record = _owned_assessment(assessment_id, ctx.tenant_id)
    if record.status != AssessmentStatus.DRAFT:
        raise HTTPException(status_code=409, detail="only draft assessments can be submitted")
    if not record.linked_run_ids:
        raise HTTPException(status_code=409, detail="at least one Passport run is required before review")
    previous_updated_at = record.updated_at
    record.status = AssessmentStatus.IN_REVIEW
    record.updated_at = _now()
    _save_update(record, previous_updated_at)
    _audit(request, ctx, "assessment.submit", record.assessment_id)
    return record.model_dump(mode="json")


@router.post("/{assessment_id}/decision")
def decide_assessment(
    assessment_id: str,
    payload: AssessmentDecisionRequest,
    request: Request,
    ctx: RequestContext = Depends(require_roles("auditor", "admin")),
) -> dict:
    record = _owned_assessment(assessment_id, ctx.tenant_id)
    if record.status != AssessmentStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="assessment must be in review before a decision")
    if payload.verdict == AssessmentStatus.APPROVED_WITH_CONDITIONS and not payload.conditions:
        raise HTTPException(status_code=422, detail="approved_with_conditions requires at least one condition")
    if payload.verdict != AssessmentStatus.APPROVED_WITH_CONDITIONS and payload.conditions:
        raise HTTPException(status_code=422, detail="conditions are only valid for approved_with_conditions")
    now = _now()
    previous_updated_at = record.updated_at
    record.decisions.append(
        AssessmentDecision(
            verdict=payload.verdict,
            rationale=payload.rationale,
            conditions=payload.conditions,
            decided_at=now,
            decided_by=hash_subject(ctx.subject),
        )
    )
    record.status = payload.verdict
    record.updated_at = now
    _save_update(record, previous_updated_at)
    _audit(request, ctx, "assessment.decision", record.assessment_id)
    return record.model_dump(mode="json")


@router.get("/{assessment_id}/evidence-package")
def get_evidence_package(
    assessment_id: str,
    request: Request,
    ctx: RequestContext = Depends(require_roles("viewer", "auditor", "operator", "admin")),
) -> dict:
    record = _owned_assessment(assessment_id, ctx.tenant_id)
    run_evidence = []
    for run_id in record.linked_run_ids:
        if not run_accessible_by_tenant(run_id, ctx.tenant_id):
            continue
        passport = load_passport(run_id)
        meta = load_run_meta(run_id) or {}
        if passport is None:
            continue
        run_evidence.append(
            {
                "run_id": run_id,
                "model": meta.get("model", ""),
                "created_at_utc": meta.get("created_at_utc", ""),
                "summary": passport.summary.model_dump(mode="json"),
            }
        )
    package = {
        "schema_version": "assurance-evidence.v1",
        "generated_at": _now().isoformat(),
        "assessment": record.model_dump(mode="json"),
        "run_evidence": run_evidence,
        "limitations": [
            "This package summarizes linked Passport runs; it is not a certification.",
            "Raw prompts and model responses are intentionally excluded.",
        ],
    }
    _audit(request, ctx, "assessment.evidence.export", record.assessment_id)
    return package
