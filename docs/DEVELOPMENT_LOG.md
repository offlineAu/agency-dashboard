# Development Log

## Iteration 1 — Discovery (2026-11-20)
- **Investigated:**
  - Empty repo.
  - The Stoplight docs are client-rendered and gated, so no spec was downloadable at first.
  - The API returns a Cloudflare 403 without credentials.
  - No key in the environment.
- **Blocked:** asked the user for the spec and the key. The spec arrived (`infloww-openapi.yaml`, v1.4); the key is still pending.
- **Findings from the spec:**
  - The whole API is GET-only, authenticated with a raw `Authorization` key plus `x-oid`.
  - Limits: 1,000 QPM per agency, 31-day windows, about 1 year of retention, at most 10 IDs per report call.
  - There is no fan list, no promotional spend data and no worked hours.
  - Chatter attribution exists through `salesRule`.

## Iteration 2 — Backend
- **Implemented:** registry, read-only client, monitor, normaliser, SQLite store, sync engine, analytics modules, routes, reports, a spec-faithful fake, and 58 tests.
- **Failures found and fixed:**
  - `executescript` broke manual transactions. Fixed by switching to autocommit connections.
  - `asyncio.create_task` was called from sync routes running in the threadpool, causing a runtime error. Fixed by scheduling onto the server loop thread-safely.
  - The fake data had colliding link IDs.
  - A test merged query parameters incorrectly.

## Iteration 3 — Frontend
- **Implemented:** the full SPA (13 routes), global URL filters, a chart kit with a palette validated for colour-vision deficiency, and the browser suite.
- **Failures found and fixed:**
  - Generic inference in the table component.
  - The Playwright runner hung, so the checks moved to the Playwright library.
  - The search test also matched rows in the matrix table.
- **Visual review fixes:**
  - The Marketing badge said "Synced never". It now uses link sync times.
  - Multi-series charts lacked legends; they now get one automatically.

## Iteration 4 — Data-integrity review
- **Defect:** growth compared against a previous period that had never been synced, so missing data counted as $0. That produced false "new vs. zero" labels and wrong growth figures.
- **Fix:** the sync now always covers the previous period. Growth is withheld, with a reason shown, until that period is complete. Two regression tests were added.
- **Tests:** backend 60/60, browser 32/32.

## Iteration 5 — Live connection (2026-11-21)
- **Defect:** the first probe returned 404 on every endpoint. `.env.example` set `INFLOWW_BASE_URL=https://openapi.infloww.com/v1`, but the spec's server is the bare host and its paths already include `/v1`, so requests went to `/v1/v1/...`.
- **Fix:** corrected the template and the local `.env`. The config now strips a trailing `/v1`. Regression test added (backend 61/61).
- **Live probe:** 27/27 endpoints OK. Arrays use repeated parameters, invoice months are `yyyy-MM`, chat-summary returns one aggregate row per request, and `cursor`/`hasMore` are top-level (as the client expects).
- The probe's sample creator had no transactions in the last 7 days. A 30-day check across all 8 connected creators found transactions for every one.
- **Defect:** the first live sync got HTTP 400 "Parameter 'endTime' must be a past or present time" on 212 requests (transactions, refunds, sales records, links). Windows that included today sent the end of the day, which is in the future.
- **Fix:** `window_end_ms()` caps unix-ms `endTime` at now minus 5s, used for all three call sites. The fake now rejects future `endTime` and no longer generates transactions dated in the future. Regression test added (backend 62/62).
- **Result:** the 30-day sync completed with no errors other than retried 429s. Amounts confirmed in cents (spec: "smallest unit"), USD only.
- **UI:** the Marketing subtitle now says link metrics are lifetime totals and ignore the date range. The $581K attributed there sits next to $48K of 30-day revenue, which was misleading without that note.


## Iteration 6 — Performance + redesign (2026-11-21)
- **Slow Analytics:** script statistics cost one API call per tag or sequence. Infloww throttles short bursts even under 1,000 QPM, and every 429 waited at least 15s, so one creator took 32.7s.
  - Fix: the rate limiter now spaces requests evenly (60/qpm). `Retry-After` is honoured, with exponential backoff otherwise.
  - Script stats now have a 1h server cache (stale results served while refreshing) and are pre-warmed by the background loop.
  - The messages route no longer waits on the API; it starts a background refresh instead.
- **Marketing "syncing forever", then "Synced 1h ago":** the syncing flag was true while *any* job ran, even ones that don't touch links, and stale links were never refreshed on demand.
  - Fix: the syncing flag is now job-scoped (by dataset or links). Marketing starts a links-only refresh when data is older than 1h.
  - The badge now shows the most recent sync ("Synced X ago · refreshing") instead of the oldest settled day.
- **Chart bug:** axes were missing on time-series charts because Recharts ignores axes wrapped in a fragment. They're now rendered inline.
- **Redesign:**
  - Light theme by default, with dark as an option (both use validated chart palettes; the choice persists).
  - New sidebar and header: greeting, quick search, alerts bell.
  - Overview gets a hero banner, a top-creator spotlight, KPI sparklines, a donut, an attribution gauge and gradient bars.
- **Photos:** the API has no profile images, so creator and chatter photos can be uploaded and stored on this server only (`/api/avatars`). Until then, everyone gets an initials avatar.

## Remaining
- Reconcile one creator × one month against the Infloww app (UTC day boundary).
- Docker build and deployment. Docker isn't installed here, and no hosting credentials have been provided.
