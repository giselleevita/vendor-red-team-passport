# AI Vendor Red-Team Passport

[![CI](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/ci.yml/badge.svg)](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/ci.yml)
[![Deploy](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/deploy.yml/badge.svg)](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/deploy.yml)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-proprietary-lightgrey)

Defense-oriented, analyst-first security evaluation tool for LLM APIs.

## MVP Scope
- LLM-API-only evaluations
- 10 attack classes (A1-A10), reproducible test cases
- Deterministic scoring gates
- Passport report output in JSON + HTML (shareable)
- Sanitized-only evidence pack per run (no raw model outputs persisted)
- Web dashboard at `/ui`

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
- `http://127.0.0.1:8000/api/v1/health` (health)

## API Endpoints
- `GET /api/v1/health`
- `POST /runs`
- `GET /runs/jobs/{job_id}`
- `GET /passports/{run_id}`
- `GET /profiles`
- `GET /metrics`

## Deployment

See [`SECRETS_SETUP.md`](SECRETS_SETUP.md) for Railway variables and [`ops/runbook.md`](ops/runbook.md) for production ops.

To enable auto-deploy: add `RAILWAY_TOKEN` to GitHub → Settings → Secrets → Actions.

## Notes
This project is for defensive testing in authorized lab environments only.
