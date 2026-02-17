from pydantic import BaseModel, Field


class Case(BaseModel):
    id: str
    attack_class: str
    priority: str
    severity: str
    weight: float = Field(gt=0)
    prompt: str
    expected_verdict: str
    response_schema: dict | None = None
    tags: list[str] = []
    enabled: bool = True


class CaseSuite(BaseModel):
    suite_version: str
    generated_at: str
    cases: list[Case]
