import json
from pathlib import Path

from jsonschema import validate


def test_case_suite_matches_schema() -> None:
    schema = json.loads(Path("data/cases/schema.case.json").read_text(encoding="utf-8"))
    data = json.loads(Path("data/cases/cases.v1.json").read_text(encoding="utf-8"))
    validate(instance=data, schema=schema)
