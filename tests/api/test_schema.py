import json

from jsonschema import validate

from apps.api.assets import read_text


def test_case_suite_matches_schema() -> None:
    schema = json.loads(read_text("builtin:cases/schema.case.json"))
    data = json.loads(read_text("builtin:cases/cases.v1.json"))
    validate(instance=data, schema=schema)
