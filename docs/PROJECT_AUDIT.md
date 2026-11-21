# Project Audit (starting state)

Date: 2026-11-20

- **Repository:** `agency-dashboard`, a single "Initial commit" with no files. Greenfield: no existing framework, code, tests, deployment config or docs.
- **Toolchain on this machine:** Node 24.21, npm, Homebrew. The system Python was 3.9.6, so Python 3.12 was installed through Homebrew. Docker is not installed.
- **Credentials:** none in the environment. The key mentioned in the brief was not included in the text provided, and the brief requires it to be rotated anyway.
- **API documentation:** the Stoplight site (`infloww-openapi.stoplight.io`) renders client-side and its content API was not reachable. Third-party sources say the docs need an access code. The user then supplied the OpenAPI export, now at `docs/spec/infloww-openapi.yaml` (OpenAPI 3.1, Infloww API v1.4, 29 GET endpoints).
- **API reachability without credentials:** every request returns a Cloudflare 403. See `API_CONNECTION_REPORT.md`.

## Decisions
| Topic | Decision | Reason |
|---|---|---|
| Stack | FastAPI + httpx + Pydantic; React + TS + Vite + Tailwind + Recharts | As recommended in the brief |
| shadcn/ui | Not used. A small set of components written specifically for this app | Fewer dependencies; the dark analytics look needed custom components either way |
| Persistence | SQLite cache with per-day coverage | API limits (31-day windows, per-creator calls, 1-year retention, 1,000 QPM shared) make querying the API live on every page view impractical. Also needed for LTV and comparisons. |
| Deployment | Single container (Render Blueprint provided) | Keeps the key and the API same-origin and private |
| Mock data | Only in tests and an explicitly labelled fixture server | The brief forbids mock data in production |
