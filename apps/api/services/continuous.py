from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from importlib import resources
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from apps.api.schemas.assurance import AssessmentRecord, AssessmentStatus
from apps.api.services.regression import regression_gate
from apps.api.services.run_store import load_json_artifact, load_passport, load_run_meta

Outcome = Literal["PASS", "FAIL", "UNKNOWN"]


class PolicyRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_release_gate: Literal["PASS"] = "PASS"
    max_review_required: int = Field(default=0, ge=0)
    allowed_regression_severity: Literal["none", "noncritical", "any"] = "none"
    mandatory_evidence: list[str] = Field(default_factory=lambda: ["passport", "manifest"])
    approval_duration_days: int = Field(default=90, ge=1, le=730)
    reassessment_frequency_days: int = Field(default=30, ge=1, le=365)


class AssurancePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["policy.v1"]
    policy_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,79}$")
    version: str = Field(min_length=1, max_length=40)
    risk_tiers: list[str]
    data_classifications: list[str]
    rules: PolicyRules


def _canonical(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def policy_digest(policy: AssurancePolicy) -> str:
    return "sha256:" + hashlib.sha256(_canonical(policy.model_dump(mode="json")).encode()).hexdigest()


def list_policies() -> list[AssurancePolicy]:
    policies: list[AssurancePolicy] = []
    for item in resources.files("data.policies").iterdir():
        if item.name.endswith((".yaml", ".yml")):
            policies.append(AssurancePolicy.model_validate(yaml.safe_load(item.read_text(encoding="utf-8"))))
    return sorted(policies, key=lambda item: item.policy_id)


def select_policy(*, risk_tier: str, data_classification: str, policy_id: str | None = None) -> AssurancePolicy:
    risk_tier = str(getattr(risk_tier, "value", risk_tier)).lower()
    data_classification = str(getattr(data_classification, "value", data_classification)).lower()
    matches = [
        policy
        for policy in list_policies()
        if risk_tier in policy.risk_tiers and data_classification in policy.data_classifications
    ]
    if policy_id:
        matches = [policy for policy in matches if policy.policy_id == policy_id]
    elif len(matches) > 1:
        preferred = "strict" if risk_tier in {"high", "critical"} or data_classification in {"confidential", "restricted"} else "standard"
        matches = [policy for policy in matches if policy.policy_id == preferred]
    if len(matches) != 1:
        raise ValueError("no unique assurance policy matches this assessment")
    return matches[0]


def _passport_dict(run_id: str) -> dict | None:
    try:
        passport = load_passport(run_id)
    except (OSError, ValueError):
        return None
    return passport.model_dump(mode="json") if passport is not None else None


def _version_snapshot(run_id: str, passport: dict) -> dict:
    try:
        meta = load_run_meta(run_id) or {}
    except (OSError, ValueError):
        meta = {}
    return {
        "run_id": run_id,
        "model": meta.get("model", ""),
        "provider": meta.get("provider", meta.get("profile", "")),
        "profile": meta.get("profile", ""),
        "suite_version": passport.get("suite_version", meta.get("suite_version", "")),
        "evaluator_version": passport.get("evaluator_version", ""),
        "taxonomy_version": passport.get("taxonomy_version", ""),
    }


def evaluate_assessment(assessment: AssessmentRecord, candidate_run_id: str, *, policy_id: str | None = None, now: datetime | None = None) -> dict:
    evaluated_at = now or datetime.now(tz=UTC)
    policy = select_policy(risk_tier=str(assessment.risk_tier), data_classification=str(assessment.data_classification), policy_id=policy_id)
    reasons: list[str] = []
    baseline_id = assessment.baseline_run_id or ""
    baseline = _passport_dict(baseline_id) if baseline_id else None
    candidate = _passport_dict(candidate_run_id)
    outcome: Outcome = "PASS"
    drift: dict = {"schema_version": "drift.v1", "baseline_run_id": baseline_id, "candidate_run_id": candidate_run_id, "outcome": "UNKNOWN", "regressions": [], "improvements": []}
    if baseline is None or candidate is None:
        outcome = "UNKNOWN"
        reasons.append("EVIDENCE_MISSING")
    else:
        for evidence_name in policy.rules.mandatory_evidence:
            if evidence_name == "passport":
                continue
            filename = f"{evidence_name}.json"
            try:
                baseline_evidence = load_json_artifact(baseline_id, filename)
                candidate_evidence = load_json_artifact(candidate_run_id, filename)
            except (OSError, ValueError):
                baseline_evidence = candidate_evidence = None
            if not isinstance(baseline_evidence, dict) or not isinstance(candidate_evidence, dict):
                outcome = "UNKNOWN"
                reasons.append(f"MANDATORY_EVIDENCE_MISSING_{evidence_name.upper()}")
        bver = _version_snapshot(baseline_id, baseline)
        cver = _version_snapshot(candidate_run_id, candidate)
        drift["baseline_versions"] = bver
        drift["candidate_versions"] = cver
        comparable = all(not bver.get(key) or not cver.get(key) or bver[key] == cver[key] for key in ("evaluator_version", "taxonomy_version", "suite_version"))
        if not comparable:
            outcome = "UNKNOWN"
            reasons.append("INCOMPATIBLE_EVALUATION_VERSION")
        else:
            decision = regression_gate(baseline=baseline, candidate=candidate, fail_on="any")
            drift.update(decision.report)
            drift["outcome"] = "PASS" if decision.ok else "FAIL"
            drift["regressions"] = decision.reasons
            if not decision.ok and policy.rules.allowed_regression_severity == "none":
                outcome = "FAIL"
                reasons.append("DRIFT_REGRESSION")
        summary = candidate.get("summary") if isinstance(candidate.get("summary"), dict) else {}
        if summary.get("release_gate") != policy.rules.required_release_gate:
            outcome = "FAIL"
            reasons.append("RELEASE_GATE_FAILED")
        if int(summary.get("review_required_count") or 0) > policy.rules.max_review_required:
            outcome = "FAIL"
            reasons.append("REVIEW_REQUIRED_LIMIT_EXCEEDED")
    if assessment.review_due_at and evaluated_at >= assessment.review_due_at:
        outcome = "FAIL"
        reasons.append("APPROVAL_EXPIRED")
    return {
        "schema_version": "policy-evaluation.v1",
        "evaluation_id": hashlib.sha256(f"{assessment.assessment_id}:{candidate_run_id}:{evaluated_at.isoformat()}".encode()).hexdigest()[:32],
        "assessment_id": assessment.assessment_id,
        "evaluated_at": evaluated_at.isoformat(),
        "outcome": outcome,
        "reason_codes": sorted(set(reasons)),
        "policy": {"policy_id": policy.policy_id, "version": policy.version, "digest": policy_digest(policy)},
        "drift": drift,
    }


def refresh_expiry(record: AssessmentRecord, *, now: datetime | None = None) -> bool:
    checked_at = now or datetime.now(tz=UTC)
    expired = bool(record.review_due_at and checked_at >= record.review_due_at and record.status in {AssessmentStatus.APPROVED, AssessmentStatus.APPROVED_WITH_CONDITIONS})
    if expired:
        record.status = AssessmentStatus.EXPIRED
        record.expired = True
    return expired
