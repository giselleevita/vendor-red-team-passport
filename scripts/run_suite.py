from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.assets import DEFAULT_SUITE
from apps.api.services.evaluator import evaluate_suite, load_case_suite
from apps.api.services.scoring import compute_scores


def main() -> None:
    cases_path = DEFAULT_SUITE
    suite = load_case_suite(cases_path)
    results = evaluate_suite(cases_path)
    scores = compute_scores(suite.cases, results)
    print("Run complete")
    print(scores)


if __name__ == "__main__":
    main()
