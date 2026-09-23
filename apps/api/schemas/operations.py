from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class ScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    profile: str = Field(default="quick_gates", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
    cadence_minutes: int = Field(ge=1, le=525_600)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    next_run_at: AwareDatetime | None = None
    enabled: bool = True


class ScheduleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cadence_minutes: int | None = Field(default=None, ge=1, le=525_600)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)
    next_run_at: AwareDatetime | None = None
    enabled: bool | None = None


class ScheduleRecord(BaseModel):
    schema_version: Literal["schedule.v1"] = "schedule.v1"
    schedule_id: str
    tenant_id: str
    assessment_id: str
    profile: str
    cadence_minutes: int
    timezone: str
    enabled: bool
    next_run_at: datetime
    last_run_at: datetime | None = None
    last_job_id: str | None = None
    last_run_id: str | None = None
    last_status: str = "pending"
    claim_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str


class WebhookCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=1, max_length=500)
    secret_env: str = Field(pattern=r"^VENDOR_RTP_WEBHOOK_SECRET_[A-Z0-9_]{1,64}$")
    key_id: str = Field(min_length=1, max_length=80)
    enabled: bool = True

    @field_validator("name", "url", "secret_env", "key_id")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class WebhookRecord(BaseModel):
    schema_version: Literal["webhook-destination.v1"] = "webhook-destination.v1"
    webhook_id: str
    tenant_id: str
    name: str
    url: str
    secret_env: str
    key_id: str
    enabled: bool
    created_at: datetime
    created_by: str


class WebhookUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=80)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    secret_env: str | None = Field(default=None, pattern=r"^VENDOR_RTP_WEBHOOK_SECRET_[A-Z0-9_]{1,64}$")
    key_id: str | None = Field(default=None, min_length=1, max_length=80)
    enabled: bool | None = None


class DeliveryRecord(BaseModel):
    schema_version: Literal["webhook-event.v1"] = "webhook-event.v1"
    delivery_id: str
    event_id: str
    tenant_id: str
    webhook_id: str
    event_type: str
    payload: dict
    status: Literal["queued", "succeeded", "retry", "dead_letter"] = "queued"
    attempt_count: int = 0
    next_attempt_at: datetime | None = None
    last_error: str = ""
    created_at: datetime
    updated_at: datetime
