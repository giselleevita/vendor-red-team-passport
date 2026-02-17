from pydantic import BaseModel


class PassportSummary(BaseModel):
    overall_score: float
    p1_pass_rate: float
    p2_pass_rate: float
    a9_schema_validity: float
    a9_mode_used: str
    a9_strict_supported: bool
    critical_failures: int
    release_gate: str


class Passport(BaseModel):
    run_id: str
    summary: PassportSummary
    class_scores: list[dict]
    failed_cases: list[dict]
    executive_verdict: dict
