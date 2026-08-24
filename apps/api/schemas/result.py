from typing import Literal

from pydantic import BaseModel, Field

ActualVerdict = Literal["BLOCK", "ALLOW", "STRICT_JSON", "NON_JSON", "UNCERTAIN", "ERROR"]


class CaseResult(BaseModel):
    case_id: str
    attack_class: str
    expected_verdict: str
    actual_verdict: ActualVerdict
    passed: bool
    response_excerpt: str
    error: str | None = None
    latency_ms: int | None = None
    evaluator_version: str = "detector.v3"
    decision_source: Literal["rules", "judge", "rules+judge"] = "rules"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    judge_model: str | None = None
    needs_human_review: bool = False


class RunSummary(BaseModel):
    total_cases: int
    passed_cases: int
    pass_rate: float
