# VRTP — Production Runbook

## Deploy

```bash
# Trigger via git push
git push origin main

# Monitor in GitHub Actions
# https://github.com/giselleevita/vendor-red-team-passport/actions
```

## Healthcheck

Railway activates the deployment only after this returns HTTP 200:

```bash
curl -i https://your-vrtp.up.railway.app/api/v1/health
```

Expected response:
```json
{"status": "ok"}
```

## Smoke Test — Run eine Evaluation

```bash
# 1. Health prüfen
curl https://your-vrtp.up.railway.app/api/v1/health

# 2. Run starten
curl -sS -X POST https://your-vrtp.up.railway.app/runs \
  -H "Authorization: Bearer $VRTP_API_KEY" \
  -H "content-type: application/json" \
  -d '{"profile":"quick_gates","model":"meta-llama/Llama-3.1-8B-Instruct"}'

# 3. Job status pollen
curl https://your-vrtp.up.railway.app/runs/jobs/<job_id> \
  -H "Authorization: Bearer $VRTP_API_KEY"

# 4. Passport abrufen
curl https://your-vrtp.up.railway.app/passports/<run_id> \
  -H "Authorization: Bearer $VRTP_API_KEY"
```

## E2E Tests gegen Live-URL

```bash
VRTP_BASE_URL=https://your-vrtp.up.railway.app \
VRTP_API_KEY=<your-key> \
pytest tests/e2e/ -v
```

## Rollback

1. Railway → Project → vrtp-api → Deployments
2. Click previous successful deployment → **Redeploy**
