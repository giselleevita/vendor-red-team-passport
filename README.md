# AI Vendor Red-Team Passport

[![CI](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/ci.yml/badge.svg)](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/ci.yml)
[![Deploy](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/deploy.yml/badge.svg)](https://github.com/giselleevita/vendor-red-team-passport/actions/workflows/deploy.yml)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-proprietary-lightgrey)

> Defense-oriented, analyst-first security evaluation tool for LLM APIs.

Vendor Red-Team Passport automates structured adversarial testing of LLM APIs and generates a portable **Passport Report** — a signed, shareable JSON + HTML document capturing attack coverage, scoring gates, and sanitized evidence.

Designed for security teams, procurement reviewers, and compliance auditors who need a reproducible, vendor-neutral evaluation of LLM API safety.

---

## What It Does

- Runs **10 attack classes (A1–A10)** against any LLM API endpoint
- Scores each class against deterministic gates (pass / fail / partial)
- Generates a **Passport Report** in JSON + HTML, shareable without raw model output
- Provides a web dashboard (`/ui`) for run management and comparison
- Supports multi-model benchmark comparison (`/compare`)
- Maps results to OWASP Top 10 for LLMs and NIST AI RMF

---

## Attack Classes

| ID | Class | Description |
|---|---|---|
| A1 | Prompt Injection | Direct and indirect instruction override attempts |
| A2 | Jailbreak | Persona switching, roleplay, hypothetical framing |
| A3 | Data Exfiltration | System prompt leakage, context extraction |
| A4 | Excessive Agency | Unauthorized tool calls, scope creep |
| A5 | Insecure Output | Code execution, XSS, markdown injection in output |
| A6 | Training Data Probing | Membership inference, verbatim reproduction |
| A7 | Denial of Service | Resource exhaustion, repetition loops |
| A8 | Model Inversion | Extracting parameters or fine-tuning signals |
| A9 | Supply Chain | Third-party plugin and tool trust abuse |
| A10 | Sensitive Data Handling | PII, credentials, regulated data in model output |

---

## Passport Report

Each run produces:
- `passport.json` — machine-readable results with scores, gate outcomes, OWASP crosswalk
- `passport.html` — human-readable report for stakeholder sharing
- Sanitized evidence only — no raw model outputs are persisted

Sample reports: `docs/samples/`

---

## Architecture

```
Analyst / CI
    ↓
FastAPI (apps/api/)
    ↓
Run Manager → Attack Runner (A1–A10)
    ↓               ↓
Job Store        Scoring Engine
(file / sql)         ↓
                 Passport Builder
                 (JSON + HTML)
```

---

## Quick Start

```bash
git clone https://github.com/giselleevita/vendor-red-team-passport
cd vendor-red-team-passport
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn apps.api.main:app --reload --port 8000
```

Open:
- `http://127.0.0.1:8000/` — Web dashboard
- `http://127.0.0.1:8000/api/v1/health` — Health check

### Docker

```bash
docker compose up -d --build
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/runs` | Start a new evaluation run |
| `GET` | `/runs/jobs/{job_id}` | Poll run status |
| `GET` | `/passports/{run_id}` | Retrieve passport report |
| `GET` | `/profiles` | List available vendor profiles |
| `GET` | `/metrics` | Aggregated scoring metrics |
| `GET` | `/compare` | Multi-model benchmark comparison |

---

## Vendor Profiles

Profiles live in `profiles/` as YAML files. Each profile defines:
- Target API endpoint and authentication
- Attack class selection (subset or all A1–A10)
- Scoring gate thresholds
- OWASP/NIST crosswalk overrides

No code changes required to add a new vendor target — drop a YAML in `profiles/`.

---

## Deployment

See [`SECRETS_SETUP.md`](SECRETS_SETUP.md) for Railway/Render environment variables and [`ops/runbook.md`](ops/runbook.md) for production ops.

To enable auto-deploy via Railway: add `RAILWAY_TOKEN` to GitHub → Settings → Secrets → Actions.

Render deployment config: `render.yaml`

---

## Compliance Crosswalk

| Framework | Mapping |
|---|---|
| OWASP Top 10 for LLMs | A1–A10 mapped to LLM01–LLM10 |
| NIST AI RMF | Govern, Map, Measure, Manage |
| ISO/IEC 42001 | AI risk assessment and documentation |

---

## Roadmap

- [x] 10 attack class framework (A1–A10)
- [x] Passport report (JSON + HTML)
- [x] FastAPI backend + web dashboard
- [x] Docker + Railway/Render deployment
- [x] Sanitized evidence pack (no raw outputs)
- [ ] Complete A1–A10 deterministic test cases (#2)
- [ ] Multi-model comparison UI on `/compare` (#3)
- [ ] v0.1.0 release tag + sample passport in `docs/samples/` (#4)
- [ ] SIEM/webhook export for passport results
- [ ] CLI runner (`passport run --profile vendor.yaml`)

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## Ethics & Scope

This tool is for **defensive testing in authorized lab environments only**.
Do not run against APIs without explicit written authorization.
All evidence is sanitized — raw model outputs are never persisted.

---

## License

Proprietary. Contact for licensing terms.
