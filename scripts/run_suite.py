from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.evaluator import evaluate_suite, load_case_suite
from apps.api.services.scoring import compute_scores


def main() -> None:
    cases_path = Path("data/cases/cases.v1.json")
    suite = load_case_suite(cases_path)
    results = evaluate_suite(cases_path)
    scores = compute_scores(suite.cases, results)
    print("Run complete")
    print(scores)


if __name__ == "__main__":
    main()
