# Free Tier Production Stack

Dieser Stack ist vollständig kostenlos und production-tauglich für Pilots und frühe Kunden.

## Services

| Service | Was | Kosten | Link |
|---|---|---|---|
| **Render.com** | API Hosting (Docker) | Free (schläft nach 15 Min) | [render.com](https://render.com) |
| **Neon.tech** | Postgres Datenbank | Free (0.5 GB) | [neon.tech](https://neon.tech) |
| **Featherless.ai** | LLM Inference | Free Tier | [featherless.ai](https://featherless.ai) |
| **GitHub Actions** | CI/CD | Free (2000 min/Mo) | [github.com](https://github.com) |

## Deploy auf Render

### Option A: Blueprint (empfohlen)
1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
2. GitHub Repo: `giselleevita/vendor-red-team-passport`
3. Render liest `render.yaml` automatisch
4. Environment Variables setzen (siehe `SECRETS_SETUP.md`)
5. Deploy klicken ✔️

### Option B: Manuell
1. [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**
2. GitHub Repo auswählen
3. Runtime: **Docker**
4. Health Check Path: `/api/v1/health`
5. Environment Variables aus `SECRETS_SETUP.md` eintragen

## Neon Postgres (empfohlen)

1. [neon.tech](https://neon.tech) → Sign up (GitHub Login)
2. **New Project** → Region: `eu-central-1` (Frankfurt)
3. Connection string kopieren
4. Als `DATABASE_URL` in Render eintragen

## Featherless Free Tier

1. [featherless.ai/register](https://featherless.ai/register) → Sign up
2. [featherless.ai/account/api-keys](https://featherless.ai/account/api-keys) → Key erstellen
3. Als `FEATHERLESS_API_KEY` in Render eintragen

## Limits des Free Tiers

- Render Free: Service schläft nach 15 Min ohne Traffic → Kaltstart ~30 Sek
- Neon Free: 0.5 GB Storage, pausiert nach Inaktivität
- Featherless Free: begrenzte Requests/Monat
- GitHub Actions: 2000 Min CI/CD pro Monat

> ✅ Für Investor Demos und erste Kunden ist das mehr als ausreichend.
