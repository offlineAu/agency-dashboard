# Agency Intelligence

Read-only analytics for an OnlyFans management agency, powered by the [Infloww API](https://openapi.infloww.com). It covers revenue, creators, chatter attribution, fan value, campaign ROI, financials, reports and API health.

- **Backend:** FastAPI. It syncs Infloww data into SQLite, tracking coverage per UTC day, and exposes `/api`. The Infloww key never leaves the server, and only GET requests to documented endpoints are possible.
- **Frontend:** React + TypeScript + Vite + Tailwind + Recharts. Dark theme, responsive, with filters stored in the URL.

## Quick start
```bash
cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # paste your ROTATED Infloww key; OID is prefilled
.venv/bin/python -m scripts.probe_api        # verify live access → docs/API_CONNECTION_REPORT.md
.venv/bin/uvicorn app.main:app --port 8000

cd ../frontend && npm install && npm run dev  # http://localhost:5173
```
No key yet? `.venv/bin/python -m scripts.fixture_server` serves **synthetic** data under a permanent "FIXTURE DATA" banner.

## Tests
```bash
cd backend && .venv/bin/python -m pytest -q          # 68 tests
cd frontend && npm run e2e                            # 34 browser checks (needs the fixture server; some checks use fixture names)
```

## Docs
| Doc | Contents |
|---|---|
| [API inventory](docs/INFLOWW_API_INVENTORY.md) · [schemas](docs/API_RESPONSE_SCHEMAS.md) | Generated from `docs/spec/infloww-openapi.yaml` |
| [Capability matrix](docs/API_CAPABILITY_MATRIX.md) | What the API can and can't support, per feature |
| [Metric definitions](docs/METRIC_DEFINITIONS.md) | Every formula and recognition rule |
| [Architecture](docs/ARCHITECTURE.md) · [Security](docs/SECURITY_AUDIT.md) | How it's built and secured |
| [Deployment](docs/DEPLOYMENT_GUIDE.md) | Docker / Render |
| [Test report](docs/TEST_REPORT.md) · [Final report](docs/FINAL_COMPLETION_REPORT.md) | Status and evidence |
