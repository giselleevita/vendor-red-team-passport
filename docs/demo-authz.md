# Demo: AuthN/AuthZ + Tenant Isolation (10 Minuten)

## Voraussetzungen
- `.env` enthält `AUTH_ENABLED=true` und `AUTH_JWT_HS256_SECRET`.
- API läuft lokal auf `http://127.0.0.1:8000`.

Lokale Demo-Tokens:
```bash
export AUTH_JWT_HS256_SECRET=local-demo-secret
export VIEWER_TOKEN=$(python scripts/make_demo_jwt.py --roles viewer)
export OPERATOR_TOKEN=$(python scripts/make_demo_jwt.py --roles operator,viewer)
```

## Ablauf
1. Ohne Token:
```bash
curl -i http://127.0.0.1:8000/profiles
```
Erwartung: `401`.

2. Mit Viewer-Token auf Read:
```bash
curl -i -H "Authorization: Bearer $VIEWER_TOKEN" http://127.0.0.1:8000/profiles
```
Erwartung: `200`.

3. Mit Viewer-Token auf Write:
```bash
curl -i -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $VIEWER_TOKEN" \
  -d '{"profile":"quick_gates"}' http://127.0.0.1:8000/runs
```
Erwartung: `403`.

4. Mit Operator-Token:
```bash
curl -i -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -d '{"profile":"quick_gates"}' http://127.0.0.1:8000/runs
```
Erwartung: `200` und `run_id` im Body.

5. Audit-Events prüfen:
```bash
tail -n 20 reports/audit/events.log
```
Erwartung: `authn`, `authz`, `run.create`, `profile.read` Events mit `allow/deny`.
