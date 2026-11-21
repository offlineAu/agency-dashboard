# Implementation Plan

Executed in the order the brief recommends. Status as of 2026-11-20.

| # | Phase | Status |
|---|---|---|
| 1 | API discovery: spec obtained, inventory, schemas, capability matrix generated | ✅ |
| 2 | Read-only client: auth, allowlist, retries, rate limit, pagination, telemetry | ✅ (tested against a spec-faithful fake) |
| 3 | Live connection verification | ✅ 27/27 endpoints (2026-11-21); first 30-day sync complete |
| 4 | Sync engine + SQLite store with coverage tracking | ✅ |
| 5 | Executive overview | ✅ |
| 6 | Creator directory, detail, comparison | ✅ |
| 7 | Chatter leaderboard, detail, attribution, matrix | ✅ |
| 8 | Fan intelligence (segments, LTV, top spenders, server-paginated) | ✅ |
| 9 | Marketing (links, trials, promotions, local costs, ROI, flags, link fans) | ✅ |
| 10 | Financials (reported vs estimates, invoices) | ✅ |
| 11 | Reports: 8 types × CSV / XLSX / PDF | ✅ |
| 12 | UI/UX: dark theme, responsive, filters in URL, loading/empty/error states | ✅ |
| 13 | API Status & data quality page | ✅ |
| 14 | Security review & read-only guarantees | ✅ |
| 15 | Automated tests: backend 62, browser 32 | ✅ |
| 16 | Deployment config: Dockerfile, render.yaml | ✅ written, ⏳ not built or deployed |

## Next steps once the key is available
1. Run `scripts/probe_api.py`. Apply its findings: `INFLOWW_ARRAY_STYLE`, invoice month format, `/v1/links` window semantics.
2. Do a first full sync. Reconcile one creator × one month against the Infloww app's creator report, keeping the UTC day boundary in mind.
3. Possible extensions: daily link snapshots (campaign trends over time), a view of the manual-reassignment audit log, and a creator status-change timeline.
