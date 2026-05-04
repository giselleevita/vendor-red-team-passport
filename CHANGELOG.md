# Changelog

## v1.0.0 — 2026-05-04

First production-ready release of the AI Vendor Red Team Passport API.

### 🚀 Features

- **Attack Profile Engine** — modular red-team profiles (jailbreak, prompt injection, PII leakage, refusal bypass, instruction override)
- **Passport System** — cryptographically signed evidence bundles per model run; portable proof of safety evaluation
- **Run API** — `POST /api/v1/runs` with async polling; full run lifecycle management
- **Compare API** — delta report between two runs (`/api/v1/runs/{a}/compare/{b}`); regression detection
- **Web Dashboard** — single-page UI at `/ui`; KPIs, run history, profile browser, passport viewer, regression compare
- **Prometheus metrics** — `/api/v1/metrics` endpoint for observability
- **Health endpoint** — `/api/v1/health`

### 🛠 Infrastructure

- Dockerfile for production builds (Python 3.11-slim)
- `railway.toml` — one-click Railway deployment
- `railway.env.example` — all environment variables documented
- E2E smoke tests (`tests/e2e/test_smoke.py`)
- CI regression gate (`tests/e2e/test_regression_ci.py`)

### 🔐 Security

- API key auth on all routes (`VRTP_API_KEY`)
- JWT-signed passport claims (`SECRET_KEY`)
- Rate limiting middleware
- CORS configurable per origin

### 📦 Dependencies

- FastAPI + Uvicorn
- Featherless.ai (serverless open-weight LLM inference)
- SQLite (default) / PostgreSQL (production)

### Known Limitations

- Filesystem storage for reports (use Railway Volume or S3 for multi-instance)
- Single worker instance (horizontal scaling in v1.1)
