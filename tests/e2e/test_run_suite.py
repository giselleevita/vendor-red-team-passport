from apps.api.services.evaluator import evaluate_suite


class DummyClient:
    def chat(self, prompt: str, model=None, response_format=None, system=None) -> str:  # noqa: ANN001
        if response_format is not None:
            return "{\"risk\": 1, \"verdict\": \"ok\"}"
        if system is not None:
            return "{\"risk\": 1, \"verdict\": \"ok\"}"
        return "I can't help with that request."


def test_run_suite_has_results() -> None:
    results = evaluate_suite("data/cases/cases.v1.json", client=DummyClient())
    assert len(results) > 0
