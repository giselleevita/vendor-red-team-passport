from pydantic import BaseModel


class CaseResult(BaseModel):
    case_id: str
    attack_class: str
    expected_verdict: str
    actual_verdict: str
    passed: bool
    response_excerpt: str
    error: str | None = None
    latency_ms: int | None = None


class RunSummary(BaseModel):
    total_cases: int
    passed_cases: int
    pass_rate: float
