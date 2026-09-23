from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field, field_validator


class AssessmentStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    REJECTED = "rejected"


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AssessmentCreateRequest(BaseModel):
    vendor_name: str = Field(min_length=1, max_length=120)
    system_name: str = Field(min_length=1, max_length=120)
    use_case: str = Field(min_length=1, max_length=500)
    owner: str = Field(min_length=1, max_length=120)
    risk_tier: RiskTier
    data_classification: DataClassification
    review_due_at: AwareDatetime | None = None
    linked_run_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("vendor_name", "system_name", "use_case", "owner")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value cannot be blank")
        return cleaned

    @field_validator("linked_run_ids")
    @classmethod
    def unique_run_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("linked_run_ids must be unique")
        return cleaned


class AssessmentRunLinkRequest(BaseModel):
    run_id: str = Field(min_length=1, max_length=120)

    @field_validator("run_id")
    @classmethod
    def strip_run_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("run_id cannot be blank")
        return cleaned


class AssessmentDecisionRequest(BaseModel):
    verdict: AssessmentStatus
    rationale: str = Field(min_length=10, max_length=2000)
    conditions: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("verdict")
    @classmethod
    def verdict_must_be_terminal(cls, value: AssessmentStatus) -> AssessmentStatus:
        if value not in {
            AssessmentStatus.APPROVED,
            AssessmentStatus.APPROVED_WITH_CONDITIONS,
            AssessmentStatus.REJECTED,
        }:
            raise ValueError("verdict must be approved, approved_with_conditions, or rejected")
        return value

    @field_validator("rationale")
    @classmethod
    def strip_rationale(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("rationale must be at least 10 characters")
        return cleaned

    @field_validator("conditions")
    @classmethod
    def normalize_conditions(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if any(len(item) > 500 for item in cleaned):
            raise ValueError("each condition must be at most 500 characters")
        return cleaned


class AssessmentDecision(BaseModel):
    verdict: AssessmentStatus
    rationale: str
    conditions: list[str] = Field(default_factory=list)
    decided_at: datetime
    decided_by: str


class AssessmentRecord(BaseModel):
    schema_version: str = "assurance.v1"
    assessment_id: str
    tenant_id: str
    vendor_name: str
    system_name: str
    use_case: str
    owner: str
    risk_tier: RiskTier
    data_classification: DataClassification
    status: AssessmentStatus = AssessmentStatus.DRAFT
    review_due_at: datetime | None = None
    linked_run_ids: list[str] = Field(default_factory=list)
    decisions: list[AssessmentDecision] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    created_by: str
