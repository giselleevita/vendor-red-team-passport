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
VRTP_API_KEY=<openssl rand -hex 32>
SECRET_KEY=<openssl rand -hex 32>
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

### Optional

```env
DEFAULT_MODEL=meta-llama/Llama-3.1-8B-Instruct
VRTP_MAX_CONCURRENT=4
VRTP_TIMEOUT=60
LOG_LEVEL=INFO
```

> ⚠️ `PORT` wird von Railway automatisch gesetzt — nicht manuell eintragen.

## 3. Secrets generieren (lokal)

```bash
openssl rand -hex 32   # für VRTP_API_KEY
openssl rand -hex 32   # für SECRET_KEY
```

## 4. Featherless API Key

1. [featherless.ai/register](https://featherless.ai/register)
2. [featherless.ai/account/api-keys](https://featherless.ai/account/api-keys)
3. Key in Railway als `FEATHERLESS_API_KEY` eintragen
