# Architecture

```
 Browser (React SPA) ──/api/*──▶ FastAPI backend ──GET only──▶ Infloww OpenAPI (openapi.infloww.com)
        ▲                          │      ▲
        │  JSON + freshness meta    ▼      │  sync engine (31-day windows, coverage per UTC day)
        └──────────────────── analytics ◀── SQLite store (cache of API responses + local settings)
```

## Backend (`backend/app`)

| Layer | Module | Responsibility |
|---|---|---|
| Config | `core/config.py` | Env-only settings (`backend/.env`). The key is a `SecretStr`. |
| Allowlist | `infloww/registry.py` | All 29 spec endpoints with window type, page-size cap and rate limit. A test checks it matches the spec. |
| Client | `infloww/client.py` | **GET only** (two independent guards). Exact auth headers, rate limiter (600 QPM default, 10 QPM for invoices), concurrency cap, retry with backoff on 429/5xx/network errors, cursor pagination with loop detection, error classification, telemetry. |
| Telemetry | `infloww/monitor.py` | Per-endpoint calls, failures, durations, records, auth and rate-limit errors, pagination errors. No credentials stored. |
| Normalisation | `infloww/normalize.py` | Raw payload → rows. Missing values stay NULL, never 0. Transaction type spellings are unified across endpoints. |
| Store | `store/db.py` | SQLite (WAL). Tables per dataset, `coverage` (dataset, scope, UTC day), `dataset_sync`, `sync_errors`, local `settings`, `campaign_costs`. |
| Sync | `sync/engine.py` | Plans stale (dataset, scope, day) units, groups them into ≤31-day runs, fetches concurrently, and replaces a run's rows **in one transaction only after full success**. Runs a background refresh loop and on-demand jobs, and records 403 scope errors as "unavailable" capabilities. |
| Analytics | `analytics/*.py` | SQL aggregations per module. A single implementation feeds both the screens and the exports. |
| API | `api/routes/*.py` | Internal REST API. Every response includes a `meta` block (coverage, freshness, syncing, unavailable datasets, previous-period completeness). |
| Reports | `reports/builder.py` | 8 report types → CSV / XLSX / PDF, each with header metadata and metric definitions. |

### Freshness model
- **Settled vs. unsettled days:** a UTC day is *settled* once it was fetched more than 30h after it ended. Unsettled days (recent, still changing upstream) are re-fetched when their copy is older than 15 minutes.
- The UI never says "live". It shows **Synced N min ago** (oldest fetch in view), **Partial · N creator-days pending**, or **Syncing…**, plus the upstream delay for each endpoint.
- Each page request kicks off a background sync for any missing or stale days in the selected period *and* the previous period. The page polls while the sync runs.

### Why a local store?
- Revenue endpoints need one request per creator per 31-day window, plus pagination at 100 rows per page.
- Querying Infloww live on every page view would be slow, would burn the agency-wide 1,000 QPM budget, and couldn't support 90-day or YoY views or fan LTV.
- The store is a cache of API responses only. It never invents rows.

## Frontend (`frontend/src`)
React 19 + TypeScript + Vite + Tailwind v4 + Recharts + TanStack Query + React Router.

- **Global filters** (date preset or custom range, creators, gross/net) live in the URL and are carried across navigation.
- `components/ui.tsx`: KPI tiles, freshness badge, empty/error/loading states, source tags (Infloww / Estimate / Local input).
- `components/DataTable.tsx`: sorting with nulls last, search, pagination, responsive column hiding.
- `components/charts.tsx`: time series with a crosshair tooltip, stacked bars, ranked bar lists, share bar. The categorical palette is validated for colour-vision deficiency on the dark surface. Each revenue type keeps a fixed colour.
- **Pages:** Overview, Creators (+ detail, compare), Chatters (+ detail), Fans, Revenue, Marketing, Analytics, Reports, API Status, Settings.

## Deployment shape
One container. FastAPI serves the built SPA from `frontend/dist` and the API under `/api`. Because everything is same-origin, no CORS setup is needed in production and the key never leaves the server. See `DEPLOYMENT_GUIDE.md`.
