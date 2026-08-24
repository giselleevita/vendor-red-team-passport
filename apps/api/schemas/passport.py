from pydantic import BaseModel, Field


class PassportSummary(BaseModel):
    overall_score: float
    p1_pass_rate: float
    p2_pass_rate: float
    a9_schema_validity: float
    a9_mode_used: str
    a9_strict_supported: bool
    critical_failures: int
    release_gate: str
    taxonomy_version: str = "taxonomy.v2-owasp-2025"
    evaluation_policy_version: str = "evaluation.v2"
    review_required_count: int = 0
    judge: dict = Field(default_factory=dict)


class Passport(BaseModel):
    run_id: str
    summary: PassportSummary
    class_scores: list[dict]
    failed_cases: list[dict]
    executive_verdict: dict
