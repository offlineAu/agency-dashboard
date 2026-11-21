# Infloww API Inventory

_Generated from `docs/spec/infloww-openapi.yaml` (Infloww API v1.4) by `backend/scripts/gen_api_docs.py`. Do not edit by hand._

## Global conventions (from the spec)

- **Base URL:** `https://openapi.infloww.com` (paths include `/v1`).
- **Auth headers (every request):** `Authorization: <raw API key>` (no `Bearer` prefix) and `x-oid: <agency OID>`.
- **Methods:** every documented operation is `GET`. The spec contains no POST/PUT/PATCH/DELETE (verified by `tests/test_registry_and_security.py`).
- **Rate limit:** 1,000 queries/minute per agency across all keys; `/v1/invoice-data/monthly-billing` is 10 QPM.
- **Pagination:** `cursor` + `limit` request params; response `cursor` + `hasMore`. `limit` default 10, max 100 (max 10 for message endpoints).
- **Time windows:** max 31 days per request. Revenue/report data retained ~1 year (366 days). Datetime endpoints take unix ms or ISO-8601 UTC; report endpoints take `YYYY-MM-DD`.
- **Errors:** JSON `{"errorMessage": "…"}` with 400 / 401 (`invalid api key`) / 403 (incl. `Your ip address is not allowed`) / 429 / 500. Include response header `x-request-id` when contacting support.
- **Latency:** OnlyFans→Infloww sync (1h–24h depending on data) + ~1h Infloww→API.
- **Key scope:** creators must be explicitly added to the key; only `/v1/transaction-perf/details` returns deleted/unlinked creators.

## Endpoints

| Method | Path | Summary | Query params (`*` required) | Window | Paginated | Read-only | Priority | Used for |
|---|---|---|---|---|---|---|---|---|
| GET | `/v1/creators` | Connected creators | `cursor` (number), `limit` (number, max 100), `platformCode` (string, enum OnlyFans) | none | yes | yes (GET) | Critical | Creator directory, filters, sync reference |
| GET | `/v1/all-creators` | All creators | `platformCode` (string, enum OnlyFans), `cursor` (number), `limit` (number, max 100) | none | yes | yes (GET) | Critical | Creator status incl. deleted (scope-dependent) |
| GET | `/v1/transactions` | Transactions | `startTime`* (string), `endTime`* (string), `creatorId`* (number), `cursor` (number), `limit` (number, max 100), `platformCode` (string, enum OnlyFans) | datetime | yes | yes (GET) | Critical | All revenue metrics, fan intelligence |
| GET | `/v1/refunds` | Refunds | `creatorId`* (number), `startTime`* (string), `endTime`* (string), `limit` (number, max 100), `cursor` (number), `platformCode` (string, enum OnlyFans) | datetime | yes | yes (GET) | Critical | Refunds (financials, creators) |
| GET | `/v1/links` | Tracking links, free trial links and profile promotions | `creatorId`* (number), `startTime`* (string), `endTime`* (string), `cursor` (number), `limit` (number, max 100), `platformCode` (string, enum OnlyFans), `linkType`* (string, enum CAMPAIGN/TRIAL/TRACKING), `status` (string, enum ACTIVE/DEACTIVATED) | datetime | yes | yes (GET) | Critical | Marketing module |
| GET | `/v1/linkfans` | Fans from tracking links, free trial links and profile promotions | `creatorId`* (number), `cursor` (number), `limit` (number, max 100), `linkType`* (string, enum CAMPAIGN/TRIAL/TRACKING), `linkId`* (number), `platformCode` (string, enum OnlyFans) | none | yes | yes (GET) | Critical | Marketing → fans per link (live, on demand) |
| GET | `/v1/automated-messages` | Automated messages | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `startTime`* (string), `cursor` (number), `limit` (number, max 10), `endTime`* (string), `employeeIds` (array, ≤100 items) | datetime | yes | yes (GET) | Medium | Analytics → message performance |
| GET | `/v1/priority-mass-messages` | Priority mass messages | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `startTime`* (string), `cursor` (number), `limit` (number, max 10), `endTime`* (string), `employeeIds` (array, ≤100 items) | datetime | yes | yes (GET) | Medium | Analytics → message performance |
| GET | `/v1/transaction-perf/details` | Sales records (all creators) | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `startTime`* (string), `endTime`* (string), `cursor` (number), `limit` (number, max 100) | datetime | yes | yes (GET) | Critical | Chatter attribution quality (salesRule) |
| GET | `/v1/invoice-data/monthly-billing` | Invoice | `startTime`* (string), `endTime`* (string) | month | no | yes (GET) | Medium | Financials → Infloww invoices |
| GET | `/v1/transaction-perf/manual-assignment/details` | Reassigned sales log | `startTime`* (string), `endTime`* (string), `cursor` (number), `limit` (number, max 100) | datetime | yes | yes (GET) | Critical | Not surfaced yet (audit trail of reassignments) — probed only |
| GET | `/v1/creator-report/chat-summary` | Messages sent statistics | `platformCode` (string, enum OnlyFans), `creatorIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | High | Creator detail → engagement (live, per range) |
| GET | `/v1/creator-report/fans/count` | Fans' status | `platformCode` (string, enum OnlyFans), `creatorIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | High | Active / expired fans |
| GET | `/v1/creator-report/fans/subscriber-count` | New and renewed fans | `platformCode` (string, enum OnlyFans), `creatorIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | High | New subscribers / renewals |
| GET | `/v1/creator-report/fans/renew-on` | Fans with renew on | `platformCode` (string, enum OnlyFans), `creatorIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | High | Auto-renew % |
| GET | `/v1/creator-report/fans/avg-subscription-length` | Fans' subscription length | `platformCode` (string, enum OnlyFans), `creatorIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | High | Avg subscription length |
| GET | `/v1/creator-report/reach/profile-visitor-count` | Profile visitors | `platformCode` (string, enum OnlyFans), `creatorIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | High | Profile visitors |
| GET | `/v1/creator-report/rank` | Platform ranking | `platformCode` (string, enum OnlyFans), `creatorIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | High | Performance rank |
| GET | `/v1/creator/status-change-log` | Creator Infloww status log | `platformCode` (string, enum OnlyFans), `startTime`* (string), `endTime`* (string), `creatorIds`* (array, ≤10 items), `cursor` (number), `limit` (number, max 100) | datetime | yes | yes (GET) | Critical | Not surfaced yet — probed only |
| GET | `/v1/employees` | Employees | `cursor` (number), `limit` (number, max 100), `employeeIds` (array, ≤100 items) | none | yes | yes (GET) | High | Chatter directory |
| GET | `/v1/employees/assigned-creators` | Employee's assigned creators | `employeeId`* (number), `cursor` (number), `limit` (number, max 100) | none | yes | yes (GET) | High | Chatter → creator assignments |
| GET | `/v1/employee-report/employee-sales-summary` | Sales statistics | `platformCode` (string, enum OnlyFans), `employeeIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | Critical | Chatter sales (attributed) |
| GET | `/v1/employee-report/employee-chat-summary` | Chatting statistics | `platformCode` (string, enum OnlyFans), `employeeIds`* (array, ≤10 items), `startTime`* (string), `endTime`* (string) | date | no | yes (GET) | Critical | Chatter productivity / response time |
| GET | `/v1/scripts` | Scripts | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `filterType`* (string, enum TAG/SEQUENCE), `filterId`* (integer), `cursor` (number), `limit` (number, max 100) | none | yes | yes (GET) | Low | Not used (tag/sequence stats used instead) |
| GET | `/v1/script/statistics` | Script statistics | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `scriptId`* (integer) | none | no | yes (GET) | Low | Not used |
| GET | `/v1/script-tag` | Scripts' tags | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `cursor` (number), `limit` (number, max 100) | none | yes | yes (GET) | Low | Analytics → script performance |
| GET | `/v1/script-tag/statistics` | Scripts' tag statistics | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `tagId`* (integer) | none | no | yes (GET) | Low | Analytics → script performance |
| GET | `/v1/script-sequence` | Sequence | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `cursor` (number), `limit` (number, max 100) | none | yes | yes (GET) | Low | Analytics → script performance |
| GET | `/v1/script-sequence/statistics` | Sequence statistics | `platformCode` (string, enum OnlyFans), `creatorId`* (number), `sequenceId`* (integer) | none | no | yes (GET) | Low | Analytics → script performance |

## Endpoint notes (verbatim from spec descriptions)

- **`/v1/creators`** — Get a paginated list of connected creators.  > Please note there is a synchronization delay of up to 1 hour for OnlyFans data.
- **`/v1/all-creators`** — Get a paginated list of all creators under your agency, including connected, disconnected, not connected, 2FA required, and deleted creators.  > This endpoint requires the "All Creators" scope permission. Unlike `/v1/creators`, it returns all creators regardless of their connection status.
- **`/v1/transactions`** — Pull a paginated list of revenue transactions for your connected creators.  > When synchronizing OnlyFans data, there is a delay of up to 1 hour. Transaction orders with a "loading" status are synchronized every 12 hours.
- **`/v1/refunds`** — Pull a paginated list of all refund amounts associated with a connected creator.  > When synchronizing OnlyFans data, there is a delay of up to 1 hour.
- **`/v1/links`** — Pull a paginated list of tracking links, free trial links and profile promotions, and associated raw data.  > When synchronizing OnlyFans data, expect a delay of up to 2 hours. > Only data from creators that are actively connected to Infloww can be pulled.
- **`/v1/linkfans`** — Pull a paginated list of fans that had clicked on the creator's tracking links, free trial links and profile promotions.  > When synchronizing OnlyFans data, there is a delay of up to 4 hours.
- **`/v1/automated-messages`** — Pull a paginated list of automated messages sent. Includes rules and conditions set, message contents, and performance metrics, with filters for creator, employee, and date range.
- **`/v1/priority-mass-messages`** — Pull a paginated list of priority mass messages sent. Includes rules and conditions set, message contents, and performance metrics, with filters for creator, employee, and date range.
- **`/v1/transaction-perf/details`** — Pull a paginated list of transaction performance details with sales attribution data. Each transaction includes the employee attribution rule, attributed employee, and attributed sales amount.  Creator scope required: **All creators** > This endpoint supports querying all creators, including deleted or unlinked creators. Query range is limited to 31 days per request and up to 366 days in the past. Only one creator ID can be queried per request.
- **`/v1/invoice-data/monthly-billing`** — Retrieves the monthly billing and invoice summary for a specified agency. The query supports a maximum date range of up to one year.  > Data latency: no delay compared to the Infloww app.  > Rate limit: 10 QPM (queries per minute) for this endpoint.
- **`/v1/transaction-perf/manual-assignment/details`** — Retrieves manual assignment records for sales transactions within an organization (agency). Each record details the operation type (whether the sales transaction was assigned or unassigned to the chatter) and the resulting employee attribution changes.  Organization scope required. > Query range is limited to 31 days per request and up to 366 days in the past.  > Data latency: no delay compared to the Infloww app.
- **`/v1/creator-report/chat-summary`** — Pull chat activity summary for up to 10 creators. Includes message counts, reply times, and PPV metrics.  > Data is aggregated by day. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/creator-report/fans/count`** — Pull daily active and expired fans counts for up to 10 creators.  > Data is aggregated by day. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/creator-report/fans/subscriber-count`** — Pull daily new subscriber and renewal counts for up to 10 creators.  > Data is aggregated by day. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/creator-report/fans/renew-on`** — Pull daily count of fans with auto-renew enabled for up to 10 creators.  > Data is aggregated by day. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/creator-report/fans/avg-subscription-length`** — Pull daily average subscription length for up to 10 creators.  > Data is aggregated by day. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/creator-report/reach/profile-visitor-count`** — Pull daily profile visitor counts for up to 10 creators.  > Data is aggregated by day. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/creator-report/rank`** — Pull daily performance ranking trajectory for up to 10 creators.  > Data is aggregated by day. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/creator/status-change-log`** — Query creator status change logs (bind/unbind/2FA etc.). Only supports data from June 1, 2026 onwards.  > Data latency: no delay.
- **`/v1/employees`** — Pull a paginated list of employees under your agency. Results can optionally be filtered by a list of employee IDs.  > If `employeeIds` is not provided, all employees are returned.
- **`/v1/employees/assigned-creators`** — Pull a paginated list of creators assigned to a specific employee.  > Only creators on OnlyFans are currently supported.
- **`/v1/employee-report/employee-sales-summary`** — Pull daily sales breakdown by employee and creator.  > Data is aggregated by day per employee and creator. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/employee-report/employee-chat-summary`** — Pull daily chat breakdown by employee and creator.  > Data is aggregated by day per employee and creator. Query range is limited to 31 days per request and up to 366 days in the past.
- **`/v1/scripts`** — Pull a paginated list of scripts for a creator, filtered by tag or sequence.  > Full historical data is available.  > Data latency: no delay compared to the Infloww app.
- **`/v1/script/statistics`** — Pull cumulative performance statistics for a script.  > Full historical data is available.  > Data latency: no delay compared to the Infloww app.
- **`/v1/script-tag`** — Pull a paginated list of script tags for a creator.  > Full historical data is available.  > Data latency: no delay compared to the Infloww app.
- **`/v1/script-tag/statistics`** — Pull cumulative performance statistics for a script tag.  > Full historical data is available.  > Data latency: no delay compared to the Infloww app.
- **`/v1/script-sequence`** — Pull a paginated list of script sequences for a creator.  > Full historical data is available.  > Data latency: no delay compared to the Infloww app.
- **`/v1/script-sequence/statistics`** — Pull cumulative performance statistics for a script sequence.  > Full historical data is available.  > Data latency: no delay compared to the Infloww app.
