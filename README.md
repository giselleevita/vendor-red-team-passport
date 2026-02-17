# AI Vendor Red-Team Passport

Defense-oriented, analyst-first security evaluation tool for LLM APIs.

## MVP Scope
- LLM-API-only evaluations
- 10 attack classes (A1-A10), reproducible test cases
- Deterministic scoring gates
- Passport report output in JSON + HTML (shareable)
- Sanitized-only evidence pack per run (no raw model outputs persisted)
- Minimal FastAPI HTML UI (runs list + compare)

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn apps.api.main:app --reload --port 8000
```

Open:
- `http://127.0.0.1:8000/` (UI)
- `http://127.0.0.1:8000/runs` (runs list)
- `http://127.0.0.1:8000/compare` (compare)

## API Endpoints
- `GET /health`
- `POST /runs` (JSON body)
- `GET /passports/{run_id}`
- `GET /profiles` (available run profiles)
- `GET /metrics` (auditor/admin; `fmt=prom|json`)

Note: all endpoints except `GET /health` require bearer authentication.

Error responses use a consistent JSON contract:
`{"code":"...", "message":"...", "correlation_id":"...", "detail": ...}`

### POST /runs body
```json
{
  "profile": "quick_gates",
  "model": "moonshotai/Kimi-K2-Instruct",
  "a9_mode": "auto",
  "params": { "temperature": 0, "max_tokens": 256 }
}
```

Profiles live under `profiles/`:
- `profiles/quick_gates.yaml`
- `profiles/full_suite.yaml`
- `profiles/high_sensitivity.yaml`

### Run Artifacts
Each run writes to `reports/runs/<run_id>/`:
- `run.json` (metadata)
- `passport.json` (machine-readable decision evidence)
- `passport.html` (shareable report)
- `policy.json` (explicit gating policy)
- `coverage.json` (heuristic OWASP/NIST crosswalk for communication)
- `compliance.json` (control mapping used in the run)
- `manifest.json` (sha256 list for run artifacts, optional HMAC signature)
- `cases/*.json` (sanitized per-case evidence)

Evidence is served locally at `GET /reports/...` (StaticFiles mount).

Verify manifest integrity:
```bash
python scripts/verify_manifest.py --run-id <run_id>
```

## Benchmarks (2+ models)
Run a benchmark and auto-generate executive summary + procurement one-pager:
```bash
python scripts/benchmark_models.py \
  --models moonshotai/Kimi-K2-Instruct meta-llama/Meta-Llama-3-8B-Instruct \
  --profile quick_gates \
  --out reports/benchmarks/benchmark.quick_gates.json
```

Outputs:
- `reports/benchmarks/benchmark*.json`
- `reports/benchmarks/executive_summary.<stem>.md`
- `reports/benchmarks/one_pager.<stem>.md`

## Notes
This project is for defensive testing in authorized lab environments only.
