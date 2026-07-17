# Contributing

Thank you for your interest in the AI Vendor Red-Team Passport project.

This tool is for **defensive security evaluation in authorized lab environments only**.
All contributions must be consistent with that scope.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

Start the API:
```bash
uvicorn apps.api.main:app --reload --port 8000
```

Run tests:
```bash
pytest tests/
```

Lint:
```bash
ruff check .
```

## Branch naming

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/description` | `feat/attack-class-a11` |
| Bug fix | `fix/description` | `fix/scoring-gate-threshold` |
| Docs | `docs/description` | `docs/passport-schema` |
| CI/ops | `ci/description` | `ci/add-deploy-workflow` |

## Issue labels

- `bug` — something is broken
- `enhancement` — new feature or attack class
- `docs` — documentation gap
- `security` — security-scope relevant change
- `ci` — CI/CD related

## PR checklist

- [ ] `pytest tests/` passes
- [ ] New attack classes have corresponding test cases
- [ ] `.env.example` updated if new env vars added
- [ ] No real credentials or API keys committed
- [ ] Scope stays within authorized defensive testing

## License

This project is licensed under the Apache License 2.0. Contributions are accepted under the project license terms.
