# Test Report

Run date: 2026-11-20. Environment: macOS, Python 3.12.16, Node 24.21.0, Chromium (Playwright 1.52).

## Backend — `cd backend && .venv/bin/python -m pytest -q`
**62 passed, 0 failed.** Added on 2026-11-21: base-URL `/v1` stripping, and `endTime` never in the future.

| Suite | What it proves |
|---|---|
| `test_registry_and_security.py` | Spec is GET-only and the allowlist matches it exactly. Page-size caps match the spec. Exact auth headers (raw key, no Bearer; `x-oid`). POST/PUT/PATCH/DELETE are refused at both client layers, and no request reaches the network. Unlisted paths are refused. Static scan finds no mutating HTTP calls. Credentials never appear in logs or telemetry. 429/500 are retried and then succeed. 401 is not retried. A missing config raises a typed error with no request sent. Full pagination with no duplicates. Both array encodings work. |
| `test_sync_and_analytics.py` | No request window exceeds 31 days. Coverage is complete after a sync and a second sync makes no calls. The settled/unsettled refetch logic works. **Revenue totals, net, reversed, pending return, tips and subscriptions reconcile exactly with raw API rows.** The breakdown sums to the total (no double counting). Daily and weekly trends sum to the total. The creator filter and net basis work. Zero-baseline growth is handled. Refunds are dated by refund date. Chatter sales equal Infloww attribution exactly, with unassigned revenue reported. Deleted creators' sales records are synced. Fan segments follow the thresholds. At Risk is never assigned without enough history. Fan names are masked. CPC, CPS, profit and ROI formulas are correct, and links without a cost get no ROI. **A failed re-fetch leaves existing rows intact.** A 403 scope error is flagged as an unavailable capability while other data still syncs. Missing values stay NULL. **Regression: growth is withheld while the previous period isn't synced.** |
| `test_api.py` | Health checks, including the live-probe shape. The overview KPI equals the analytics function. 15 routes return 200 and never echo the key or OID. Bad inputs are rejected. **All 8 reports × 3 formats** produce valid output, and the XLSX and PDF files parse. The daily report total equals the dashboard total. Local settings drive the estimates. Cost entry produces the expected ROI. The access token is enforced. A missing configuration is reported honestly. Previous-period completeness is exposed. |

## Browser — `cd frontend && npm run e2e` (against `scripts.fixture_server` + `npm run dev`)
**32 passed, 0 failed.**
- All 13 routes render at **desktop (1440×900) and mobile (Pixel 7)**. Each one passes four checks: the correct H1, no error state, no console errors, and no horizontal overflow.
- Across those 26 page loads, the browser made **zero requests to `*.infloww.com`**.
- Interactions covered:
  - The date preset changes both the KPIs and the URL.
  - The gross/net toggle and the creator filter survive navigation.
  - Table search filters rows.
  - Entering a campaign cost produces an ROI.
  - CSV, XLSX and PDF downloads all work.
  - The mobile nav drawer works.
- Full-page screenshots are saved in `frontend/e2e/screens/` and were reviewed by eye. Review found two defects, both fixed: the Marketing freshness badge showed "Synced never", and multi-series charts had no legend.

## Build and bundle
- `npm run build` passes with no type errors (`tsc -b`), and the bundle is about 900 KB.
- Searching `frontend/dist` for `infloww.com` or for the key value finds nothing. The only hit is the help text naming the `INFLOWW_API_KEY` variable.

## Not tested
- **Live Infloww API: not tested (no key available).** Run `scripts/probe_api.py` once the key is in place.
- **Docker image: not built** (Docker isn't installed on this machine).
- The Playwright *test runner* (`playwright test`) hung on startup in this sandbox. The same checks run reliably through the Playwright library in `e2e/run.mjs`.


## Live run (2026-11-21, real Infloww data)
- Live probe: 27/27 endpoints OK.
- First 30-day sync complete: transactions, refunds, creator reports and chatter data all fully covered. No errors other than retried 429s.
- Every GET API route returns 200. All 24 report downloads (8 kinds × CSV, XLSX, PDF) succeed.
- Browser suite against the live backend: 25/32. All 7 failures look up fixture-only IDs or names (creator `1000`, chatter `70`, "Creator B", "TikTok promo"). Real creator and chatter detail pages were checked separately and render correctly, and an unknown ID shows an error state. The full suite stays fixture-based.

## Performance & redesign pass (2026-11-21)
- Backend **68/68**. New tests: rate-limiter spacing, `Retry-After` handling, messages route never blocks on the API, script stats served from cache, Marketing "syncing" ignores unrelated jobs, and photo upload validation (magic bytes, 2 MB cap, ID validation).
- Browser **34/34** on fixture data. New checks: the theme toggle persists across reloads, and quick search jumps to a creator.
- Live timings: script stats 32.7s → 4.8s cold and about 1ms cached (they're also pre-warmed in the background). Messages about 5ms. A full links refresh takes about 40s in the background, with existing data shown meanwhile.
