# Secrets Setup — AI Vendor Red-Team Passport

## 1. GitHub Actions Secret

Repository → Settings → Secrets and variables → Actions → New repository secret

| Name | Value |
|---|---|
| `RAILWAY_TOKEN` | Token from [railway.app](https://railway.app) → Account Settings → Tokens → Create Token |

## 2. Railway Variables

Railway → Project → vrtp-api → Variables → Raw Editor

### Required

```env
FEATHERLESS_API_KEY=<your-key-from-featherless.ai>
AUTH_JWT_HS256_SECRET=<openssl rand -hex 32>
```

### Optional

```env
DEFAULT_MODEL=meta-llama/Llama-3.1-8B-Instruct
AUTH_ENABLED=true
RBAC_ENABLED=true
VENDOR_RTP_REPORTS_DIR=/app/reports
VENDOR_RTP_MANIFEST_HMAC_KEY=<openssl rand -hex 32>
RUN_EXECUTOR_MODE=external
```

> ⚠️ `PORT` wird von Railway automatisch gesetzt — nicht manuell eintragen.

## 3. Secrets generieren (lokal)

```bash
openssl rand -hex 32   # für AUTH_JWT_HS256_SECRET
openssl rand -hex 32   # optional für VENDOR_RTP_MANIFEST_HMAC_KEY
```

## 4. Featherless API Key

1. [featherless.ai/register](https://featherless.ai/register)
2. [featherless.ai/account/api-keys](https://featherless.ai/account/api-keys)
3. Key in Railway als `FEATHERLESS_API_KEY` eintragen
