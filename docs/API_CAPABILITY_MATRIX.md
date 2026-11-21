# API Capability Matrix

Maps every dashboard feature requested in the brief to the Infloww endpoint(s) that support it, and states plainly where the API cannot support it. Source: `docs/spec/infloww-openapi.yaml` (v1.4). **Live verification status: pending an API key** (see `API_CONNECTION_REPORT.md`).

Legend: ✅ supported by API data · 🧮 derived from API data (formula documented in `METRIC_DEFINITIONS.md`) · ✏️ requires local input (never sent to Infloww) · ❌ not available from the API (shown as unavailable, never fabricated)

## Discovery matrix (brief §5)

| Data category | Endpoint(s) | Status |
|---|---|---|
| Agency | `x-oid` header only; no agency-metadata endpoint. Invoices give billing info | ✅ partial |
| Creators | `/v1/creators`, `/v1/all-creators`, `/v1/creator/status-change-log` | ✅ |
| Earnings | `/v1/transactions` (gross `amount`, `fee`, `net`, `type`, `status`) | ✅ |
| Employees | `/v1/employees`, `/v1/employees/assigned-creators` | ✅ |
| Fans | No fan-list endpoint. Fans visible via transactions, `/v1/linkfans`, and aggregate creator reports | ✅ partial |
| Transactions | `/v1/transactions`, `/v1/refunds`, `/v1/transaction-perf/details` | ✅ |
| Tracking links | `/v1/links` (TRACKING / TRIAL / CAMPAIGN), `/v1/linkfans` | ✅ (no cost data) |
| Reports | `/v1/creator-report/*`, `/v1/employee-report/*` (daily) | ✅ |
| Shifts | Only response times "based on scheduled/clocked hours" — no hours worked | ❌ |
| Analytics | Message + script statistics endpoints | ✅ |

## Module 1 — Executive overview

| Metric | Source | Status |
|---|---|---|
| Gross revenue | transactions `amount`, status done/loading | ✅ |
| Net revenue | transactions `net` (after OnlyFans fee) | ✅ |
| Revenue growth | same, previous equal-length period (withheld until that period is synced) | 🧮 |
| Active creators | `/v1/creators` | ✅ |
| Active subscribers | creator-report `activeFans` (latest day) | ✅ |
| New subscribers | creator-report `newSubscribers` | ✅ |
| Chatter-generated revenue | employee-sales-summary `salesAmount` (Infloww-attributed) | ✅ |
| PPV revenue | transaction types `Messages` + `Posts` | ✅ |
| Subscription revenue | types `Subscription` + `Recurring Subscription` | ✅ |
| Tips | type `Tips` | ✅ |
| Refunds / chargebacks | `/v1/refunds` + status `undo` / `pending_return`. Refund vs chargeback is **not** distinguished | ✅ / ❌ split |
| Agency commission | local commission % | ✏️ |
| Top teams | no team entity in API | ❌ (chatters ranked individually) |

## Module 2 — Creators

| Metric | Source | Status |
|---|---|---|
| Name, IDs, status | creators / all-creators | ✅ |
| Current / expired subscribers | fans/count | ✅ |
| New subscribers, renewals | fans/subscriber-count | ✅ |
| Renewal rate | auto-renew % = renew-on ÷ activeFans | 🧮 (a true cohort renewal rate is not derivable) |
| Revenue, breakdown, growth, tips, PPV, refunds | transactions, refunds | ✅ / 🧮 |
| Avg revenue per fan | revenue ÷ distinct paying fans | 🧮 |
| Avg subscription length | fans/avg-subscription-length | ✅ |
| Top spenders | transactions grouped by fanId (pseudonymised) | 🧮 |
| PPV conversion | chat-summary `ppvsSent` vs PPV-message revenue | 🧮 (unlocks at creator level not exposed; at chatter level yes) |
| Engagement | chat-summary (messages, fans chatted, reply time), profile visitors, rank | ✅ |
| Contribution to agency | share of total | 🧮 |
| Side-by-side comparison | — | 🧮 |

## Module 3 — Chatters

| Metric | Source | Status |
|---|---|---|
| Total / PPV / tips sales | employee-sales-summary | ✅ |
| Messages sent, PPVs sent, PPVs unlocked, unlock rate, golden ratio | employee-chat-summary | ✅ |
| Fans chatted | employee-chat-summary (daily unique → summed) | ✅ (summed caveat) |
| Avg reply time | `responseTimeBasedOn{Scheduled,Clocked}Hours` | ✅ |
| Attribution rule per sale | transaction-perf/details `salesRule` | ✅ |
| Shift hours, revenue per hour | — | ❌ |
| Wages | — | ✏️ (commission % estimate only) |
| Creator × chatter matrix | sales summary by `platformPid` | ✅ |

## Module 4 — Fans

| Metric | Source | Status |
|---|---|---|
| Total / active / expired fans | creator reports (aggregate) | ✅ |
| Per-fan subscription status, expiry, auto-renew | — | ❌ |
| Top spenders, LTV, spend per fan, frequency, PPV activity | transactions (synced history ≤ ~1y) | 🧮 |
| Segments VIP / High Value / Regular / Non-spender | spend thresholds | 🧮 + ✏️ thresholds |
| New / Active / At Risk / Lapsed | first/last purchase, only when history is long enough | 🧮 |
| Expired (per fan) | — | ❌ |
| Free subscribers who never paid | — | ❌ (invisible at fan level) |

## Module 5 — Marketing

| Metric | Source | Status |
|---|---|---|
| Clicks, subs, earnings (gross/net), paying fans | links | ✅ |
| Subscription CVR, spending CVR, EPC, AEPS | links (API-provided) | ✅ |
| Spend, CPC, CPS, profit, ROI | — | ✏️ |
| Free-trial claims vs paid | linkType TRIAL `subCount` = claims | ✅ |
| Attribution model | most recent tracking/trial link (rolling) | ✅ documented |
| Per-link fans and their spend | linkfans | ✅ |
| Campaign trend over time | links expose cumulative totals only | ❌ (would need daily snapshots; not implemented) |

## Module 6 — Finance

| Item | Status |
|---|---|
| Gross, net, platform fees, by type | ✅ |
| Refunds, reversed, pending return | ✅ |
| Chargebacks (separately) | ❌ |
| Infloww invoices | ✅ |
| Marketing cost, chatter pay, other costs, commission, operating profit | ✏️ estimates, labelled |

## Modules 7–8

Reports (CSV/XLSX/PDF): built on the same functions. Monitoring: per-endpoint telemetry, per-day coverage, sync errors, scope (403) detection.
