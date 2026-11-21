# Security Audit

| Requirement | Implementation | Verified by |
|---|---|---|
| API key stays on the backend | Read from `INFLOWW_API_KEY` (env / `backend/.env`) as a `SecretStr`. The frontend has no Infloww code and calls only `/api/*`. | `e2e/run.mjs` asserts the browser makes zero requests to `*.infloww.com`. A grep of `frontend/dist` for the key and for `infloww.com` finds nothing (see TEST_REPORT). |
| No credentials in Git | `.gitignore` covers `.env`, `.env.*` (except `.env.example`) and `backend/data/`. | `git check-ignore backend/.env` |
| No credentials in logs | The client never logs headers. The httpx logger is set to WARNING. A root `RedactFilter` scrubs the key from any log line. Telemetry stores sanitised params only. | `test_credentials_never_logged_or_recorded` |
| No credentials in API responses | `/api/status` shows a masked OID only. The unhandled-exception handler returns a generic message. | `test_routes_ok` asserts that neither key nor OID appears in any response |
| **Read-only towards Infloww** | (1) `InflowwClient.request()` rejects non-GET methods. (2) An httpx request hook rejects non-GET at the transport level. (3) Only allowlisted paths. (4) The spec itself is all-GET. | `test_client_refuses_mutating_methods` (POST/PUT/PATCH/DELETE through both layers), `test_client_refuses_unlisted_endpoint`, `test_spec_is_get_only_and_registry_matches_spec`, `test_no_mutating_http_calls_in_source` (static scan) |
| Local write routes can't reach Infloww | The PUT/POST/DELETE routes touch only local SQLite tables (settings, campaign costs) or trigger GET-only syncs. | code review; routes live in `system.py` |
| Input validation | Dates parsed as `date`, range ≤ 366 days, `start ≤ end`. Creator IDs must be numeric. `basis` is matched against a pattern. Settings models are bounded (pct 0–100 etc.). All SQL is parameterised. | `test_bad_inputs_rejected` |
| Protect backend routes | Optional `DASHBOARD_ACCESS_TOKEN`, checked with a constant-time compare. The SPA prompts for it and keeps it in sessionStorage. `/api/health` stays open for liveness checks. | `test_access_token_enforced` |
| CORS | Allowlist from `CORS_ORIGINS`, defaulting to the Vite dev origins. Not needed in production (same origin). | config |
| Security headers | `nosniff`, `no-referrer`, `X-Frame-Options: DENY`, `Cache-Control: no-store` on `/api`. `noindex` meta tag. | middleware |
| Fan data minimisation | Fan names and IDs are masked server-side. Top spenders are paginated on the server (max 100 per page), so the full fan list never reaches the browser. Exports are pseudonymised. | `test_fan_segments_follow_thresholds` (mask check) |
| Rate-limit hygiene | 600 QPM client-side budget (the agency limit of 1,000 is shared across all keys), 10 QPM for invoices, concurrency 6, backoff on 429. | `test_retry_on_429_and_500_then_success` |

## Findings and actions
- **P0 – exposed key.** The original brief said the key had been pasted into a conversation. **Rotate it in Infloww** and put the new one in `backend/.env` only.
- **P1 – IP allowlisting.** Infloww may answer 403 `Your ip address is not allowed`. If so, add the deployment's egress IP to the key's allowlist in Infloww.
- **P2 – deployment.** Set `DASHBOARD_ACCESS_TOKEN` (or put the app behind SSO or a VPN). The dashboard shows revenue and pseudonymised fan data.
- **Residual – SQLite file.** The SQLite file contains synced revenue and fan IDs (unmasked at rest). Keep it on an encrypted disk or volume and don't commit it (`backend/data/` is ignored).


## Photo uploads (added 2026-11-21)
- `PUT /api/avatars/{creator|employee}/{numeric id}` stores a photo on this server only (`data/avatars/`). Nothing is sent to Infloww.
- The file type is decided by magic bytes (PNG, JPEG or WebP only), not by the client's Content-Type. SVG and HTML are rejected (415). The size cap is 2 MB (413).
- The kind and ID are validated (digits only), so no path built from user input can escape the folder. Writes are atomic (temp file, then rename).
- Photos are served with the image's own media type plus `nosniff`, and the routes require the same dashboard token as every other `/api` route.
