# Vendor Red Team Passport — Web Dashboard

Single-page dashboard for the VRT Passport API.

## Quick start

```bash
# 1. Start the API (from repo root)
docker-compose up

# 2. Open the dashboard
open apps/web/index.html
# or serve locally:
python -m http.server 3000 --directory apps/web
```

## Configuration

The dashboard ships with `http://localhost:8000` as the default API base URL.  
Click **Settings** in the sidebar to change the URL and API key — settings are held in memory only (no localStorage).

## Features

| View | Description |
|---|---|
| Dashboard | KPI cards + recent runs table |
| Runs | Full run history, create new runs |
| Profiles | Available attack class profiles |
| Passports | Signed evidence bundles per run |
| Compare | Delta analysis between two runs |
| Settings | API URL and key configuration |
