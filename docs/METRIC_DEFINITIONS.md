# Metric Definitions

All money values are integers in the smallest currency unit (cents) end to end, and are formatted only in the UI and exports. All day buckets are **UTC**. Each metric is labelled by where it comes from: **API** (an Infloww field), **Derived** (computed from API fields), or **Local** (uses settings that never leave this app).

## Revenue recognition

| Transaction `status` | Treatment |
|---|---|
| `done` | Recognised revenue |
| `loading` | Recognised (earned but not yet cleared on OnlyFans; Infloww re-syncs these every 12h). Shown separately as "not yet cleared". |
| `undo` | **Excluded.** Reported as "Reversed". The API doesn't say whether a reversal was a refund or a chargeback. |
| `pending_return` | **Excluded.** Reported as "Pending return". |

- **Gross revenue** = Σ `amount` over recognised transactions in the period. *API*
- **Net revenue** = Σ `net` (after the OnlyFans platform fee). *API*
- **Platform fees** = Σ `fee`. *API*
- **Refunds** = Σ `/v1/refunds.paymentAmount`, dated by `refundTime`. *API*
- **Source categories:** `Subscription` → New subscriptions; `Recurring Subscription` → Recurring; `Messages` → PPV messages; `Posts` → PPV posts; `Tips`; `Streams` → Live streams; `Referrals`; `Unknown`. The categories don't overlap, so they always sum to the total (this is tested).
- **Growth %** = (current − previous) ÷ |previous| × 100, where "previous" is the period of equal length just before the selected one. Growth shows **"—"** with a reason in three cases: the previous value is 0, the previous period is not fully synced, or the data is unavailable. *Derived*
- **Gross/net toggle:** switches every revenue figure on screen between `amount` and `net`. Link earnings switch between `earningsGross` and `earningsNet`.

## Creators

- **Active fans, expired fans, fans with renew on, average subscription length, performance rank:** value on the **latest reported day** inside the period, from creator reports. *API*
- **New subscribers, renewals, profile visitors:** summed over the period. *API*
- **Auto-renew %** = fansWithRenewOn ÷ activeFans × 100 (same day). *Derived*
- **Average revenue per paying fan** = revenue ÷ distinct `fanId` with a recognised transaction. *Derived*
- **Share of agency** = creator revenue ÷ agency revenue × 100. *Derived*

## Chatters

- **Attributed sales** = Σ `employee-sales-summary.salesAmount`, attributed by Infloww according to the agency's own sales settings. Creator revenue is **never** split across chatters. *API*
- **Attribution coverage** = (sales-record amount − amount where `salesRule` is Unassigned) ÷ sales-record amount × 100. *Derived*
- **Unlock rate** = Σ ppvsUnlocked ÷ Σ directPpvsSent × 100; **Golden ratio** = Σ directPpvsSent ÷ Σ directMessagesSent × 100. Both are recomputed from summed counts rather than averaged from daily percentages. *Derived*
- **Average reply time** = daily `responseTimeBasedOn{Clocked,Scheduled}Hours`, weighted by messages sent. *Derived*
- **Fans chatted** = sum of *daily* unique fans, so a fan chatted with on several days is counted once per day. *API*
- **Revenue per hour:** **not available**, because the API exposes no worked or clocked hours.

## Fans

The history window for fans is the continuous run of synced transaction days ending today, across the selected creators. It defaults to 180 days, and the API keeps about 1 year.

- **Lifetime value (LTV)** = recognised spend within that history window. *Derived*
- **Value segment** (thresholds editable in Settings): **VIP** ≥ $1,000; **High Value** ≥ $250; **Regular** = any PPV, tip or other non-subscription purchase; **Non-spender** = subscription payments only. *Derived + Local*
- **Lifecycle:** **New** = first purchase within the last 30 days (only assigned when ≥ 60 days of history exist). **Active** = purchased in the last 30 days. **At Risk** = last purchase 30–90 days ago (only assigned when ≥ 90 days of history exist). **Lapsed** = no purchase for 90+ days. Otherwise lifecycle is "Unknown (insufficient history)". *Derived + Local*
- **Returning paying fans** = paying in the period, with a first purchase before the period start. *Derived*
- Fan names and IDs are **masked** in every response (first initial, last 4 ID digits).

## Marketing (Infloww tracking-link definitions)

| Metric | Formula | Source |
|---|---|---|
| Subscription CVR | subscribers ÷ clicks × 100 (API `subscriptionCVR`) | API |
| Spending CVR | API `spendingCVR` (fans who spent ÷ subscribers) | API |
| EPC | earnings ÷ clicks (API `epcGross` / `epcNet`) | API |
| AEPS | earnings ÷ subscribers (API `aepsGross` / `aepsNet`) | API |
| CPC | cost ÷ clicks | Local |
| CPS | cost ÷ subscribers | Local |
| Profit | earnings − cost | Local |
| ROI | profit ÷ cost × 100 | Local |

- Link figures are **cumulative over each link's lifetime**, not limited to the selected period.
- **Attribution is rolling:** a fan's revenue counts toward their *most recent* tracking or free-trial link, not necessarily the first one that brought them in.
- For free-trial links, "subscribers" means **trial claims**, not paid subscriptions.
- When a denominator is zero or a cost is missing, the metric shows "—", never 0.
- **Underperforming** flags: negative ROI; tracking-link CVR below half the median of links with ≥ 100 clicks; or ≥ 200 clicks with zero subscribers.

## Finance estimates (Local; always labelled "Estimate")

- **Agency commission** = commission % × (net or gross, as configured)
- **Chatter pay** = chatter % × attributed sales
- **Marketing spend** = locally entered campaign costs whose spend date falls in the period
- **Other costs** = monthly amount × days ÷ 30.4375
- **Estimated operating profit** = commission − chatter pay − marketing spend − other costs

None of these are shown until the agency sets the inputs.
