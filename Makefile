.PHONY: setup test run quick-gates full-suite high-sensitivity regression verify-manifest lint

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -e .[dev]

test:
	. .venv/bin/activate && pytest -q

run:
	. .venv/bin/activate && uvicorn apps.api.main:app --reload --port 8000

# CI/local fast check. Override model: `make quick-gates MODEL=...`
quick-gates:
	. .venv/bin/activate && python scripts/run_run.py --profile quick_gates --model "$(MODEL)"

# Full suite (can take longer depending on pacing/rate limits). Override model: `make full-suite MODEL=...`
full-suite:
	. .venv/bin/activate && python scripts/run_run.py --profile full_suite --model "$(MODEL)"

# High-sensitivity profile for regulated deployments.
high-sensitivity:
	. .venv/bin/activate && python scripts/run_run.py --profile high_sensitivity --model "$(MODEL)"

# Compare two runs and fail CI on regressions:
# `make regression BASELINE=<run_id> CANDIDATE=<run_id>`
regression:
	@test -n "$(BASELINE)" || (echo "BASELINE is required" && exit 2)
	@test -n "$(CANDIDATE)" || (echo "CANDIDATE is required" && exit 2)
	. .venv/bin/activate && python scripts/regression_gate.py --baseline "$(BASELINE)" --candidate "$(CANDIDATE)" --fail-on critical

# Verify manifest integrity for a run:
# `make verify-manifest RUN_ID=<run_id>`
verify-manifest:
	@test -n "$(RUN_ID)" || (echo "RUN_ID is required" && exit 2)
	. .venv/bin/activate && python scripts/verify_manifest.py --run-id "$(RUN_ID)"
