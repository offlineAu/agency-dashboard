# Deployment Guide

## 0. Before anything else
1. **Rotate the Infloww API key.** The original was shared in a conversation.
2. In Infloww → API key settings, check that the key's **creator scope** includes every creator (newly added or relinked creators are not added automatically). Choose **All employees**, and **All creators** scope if you want deleted creators' sales history.
3. If the key has an IP allowlist, add your server's egress IP.

## 1. Local development
```bash
# backend
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env                       # paste the key after INFLOWW_API_KEY=
.venv/bin/python -m scripts.probe_api      # verify connectivity → docs/API_CONNECTION_REPORT.md
.venv/bin/uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173  (proxies /api → :8000)
```
The first page load starts a background sync: 30 days for all datasets, then 180 days of transactions for fan LTV. Progress is shown on **API Status**.

**UI work without a key:** `.venv/bin/python -m scripts.fixture_server` runs the backend on synthetic data. Every page then shows a yellow **FIXTURE DATA** banner, and it uses a separate database file.

## 2. Environment variables
| Variable | Required | Default | Notes |
|---|---|---|---|
| `INFLOWW_API_KEY` | yes | — | Secret. Backend only. |
| `INFLOWW_AGENCY_OID` | yes | — | Sent as `x-oid`. |
| `DASHBOARD_ACCESS_TOKEN` | **yes in production** | empty (no auth) | Shared token the SPA asks for. |
| `DATABASE_PATH` | no | `backend/data/agency.db` | Put it on a persistent, encrypted volume. |
| `INFLOWW_ARRAY_STYLE` | no | `repeat` | Set to `comma` if the probe says so. |
| `INFLOWW_QPM` | no | 600 | The agency limit is 1,000 across all keys. |
| `DEFAULT_LOOKBACK_DAYS` / `FAN_HISTORY_DAYS` / `LINK_LOOKBACK_DAYS` | no | 30 / 180 / 365 | |
| `BACKGROUND_SYNC`, `BACKGROUND_INTERVAL_S` | no | true / 900 | |
| `CORS_ORIGINS` | no | Vite dev origins | Not needed when the frontend and API share an origin. |

## 3. Production: single container (recommended)
`Dockerfile` builds the SPA and serves it from FastAPI, so the app, the API and the key all stay in one private service.
```bash
docker build -t agency-intelligence .
docker run -p 8000:8000 -v agency-data:/data \
  -e INFLOWW_API_KEY=... -e INFLOWW_AGENCY_OID=... -e DASHBOARD_ACCESS_TOKEN=... agency-intelligence
```
**Render:** `render.yaml` is a ready Blueprint (Docker web service, 1 GB disk at `/data`, health check `/api/health`). Set `INFLOWW_API_KEY` and `INFLOWW_AGENCY_OID` in the dashboard, then copy the generated `DASHBOARD_ACCESS_TOKEN`. Railway and Fly work the same way with the Dockerfile and a volume.

**Split hosting (Vercel frontend + Render/Railway backend):** possible, but you must also:
- set `CORS_ORIGINS` to the Vercel origin, and
- add a Vercel rewrite of `/api/(.*)` to the backend URL, so the browser still only talks to its own origin.

The single container is simpler and avoids exposing the backend URL.

Run one instance only. The sync engine and SQLite are single-writer.

## 4. Post-deploy checklist
- Open the app. It should ask for the access token.
- On **API Status**, **Test connection** should report "Connected — Infloww returned creator data".
- **Sync now** → coverage bars reach 100% for the default window.
- Overview totals should match the Infloww app's creator report for the same UTC range. Remember Infloww's 1–24h delay, and that this dashboard uses UTC days.
- Set the commission and cost rules in **Settings** if you want profit estimates.
