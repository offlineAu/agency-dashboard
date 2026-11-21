"""Fan intelligence derived from synced transactions.

The Infloww API has NO fan-list endpoint. Fans are therefore known only through:
  * transactions (any fan who paid something in the synced history window), and
  * creator-report daily counts (active / expired / new / renewals / auto-renew) — aggregate only.
Consequences, surfaced in the API response under `limitations`:
  * Free subscribers who never paid are invisible at fan level.
  * Per-fan "expired" status is not available (only aggregate expired counts).
  * Lifetime value = spend within the synced history window (API retains <= ~1 year).
Segments use transparent, configurable thresholds (see METRIC_DEFINITIONS.md).
"""
from __future__ import annotations

from datetime import date, timedelta

from app.analytics.common import Filters, mask_id, mask_name, ratio, recognized_clause
from app.store.db import Database

DEFAULTS = {"vip_cents": 100_000, "high_value_cents": 25_000, "new_days": 30, "at_risk_active_days": 30, "at_risk_lookback_days": 90}


def thresholds(db: Database) -> dict:
    return {k: int(db.get_setting(f"fans.{k}", v)) for k, v in DEFAULTS.items()}


def history_bounds(db: Database, creator_ids: tuple[str, ...] | None) -> tuple[date | None, date | None]:
    """Earliest day from which transaction coverage is continuous up to today, across the scoped creators."""
    scopes = list(creator_ids) if creator_ids else [r["id"] for r in db.query("SELECT id FROM creators WHERE connected=1")]
    if not scopes:
        return None, None
    starts = []
    for sc in scopes:
        days = [r["day"] for r in db.query("SELECT day FROM coverage WHERE dataset='transactions' AND scope=? ORDER BY day DESC", (sc,))]
        if not days:
            return None, None
        cur = date.fromisoformat(days[0])
        earliest = cur
        for d in days[1:]:
            dd = date.fromisoformat(d)
            if (earliest - dd).days == 1:
                earliest = dd
            else:
                break
        starts.append((earliest, cur))
    return max(s for s, _ in starts), min(e for _, e in starts)


def _fan_rows(db: Database, f: Filters, hist_start: date, as_of: date) -> list[dict]:
    cc = f" AND creator_id IN ({','.join('?' * len(f.creator_ids))})" if f.creator_ids else ""
    cp = list(f.creator_ids or [])
    col = "net" if f.basis == "net" else "amount"
    return db.query(
        f"""SELECT fan_id, MAX(fan_name) fan_name, COUNT(DISTINCT creator_id) creators,
                   SUM({col}) lifetime, MIN(day) first_day, MAX(day) last_day, COUNT(*) purchases,
                   SUM(CASE WHEN day BETWEEN ? AND ? THEN {col} ELSE 0 END) period_spend,
                   SUM(CASE WHEN day BETWEEN ? AND ? THEN 1 ELSE 0 END) period_purchases,
                   SUM(CASE WHEN type NOT IN ('Subscription','Recurring Subscription') THEN {col} ELSE 0 END) non_sub_spend,
                   SUM(CASE WHEN type IN ('Messages','Posts') THEN 1 ELSE 0 END) ppv_purchases,
                   SUM(CASE WHEN type='Tips' THEN {col} ELSE 0 END) tips,
                   SUM(CASE WHEN type IN ('Subscription','Recurring Subscription') THEN {col} ELSE 0 END) sub_spend,
                   COUNT(DISTINCT strftime('%Y-%m', day)) active_months
            FROM transactions WHERE {recognized_clause()} AND fan_id IS NOT NULL AND day BETWEEN ? AND ? {cc}
            GROUP BY fan_id""",
        (f.start.isoformat(), f.end.isoformat(), f.start.isoformat(), f.end.isoformat(), hist_start.isoformat(), as_of.isoformat(), *cp))


def segment(row: dict, th: dict, as_of: date, hist_start: date) -> tuple[str, str | None]:
    """Returns (value_segment, lifecycle). Lifecycle is None when history is too short to judge."""
    lt = row["lifetime"] or 0
    if lt >= th["vip_cents"]:
        value = "VIP"
    elif lt >= th["high_value_cents"]:
        value = "High Value"
    elif (row["non_sub_spend"] or 0) > 0:
        value = "Regular"
    else:
        value = "Non-spender"   # paid subscription only: no PPV / tips / other purchases recorded
    history_days = (as_of - hist_start).days + 1
    first, last = date.fromisoformat(row["first_day"]), date.fromisoformat(row["last_day"])
    lifecycle = None
    if history_days >= th["new_days"] * 2 and (as_of - first).days < th["new_days"]:
        lifecycle = "New"
    elif history_days >= th["at_risk_lookback_days"]:
        if (as_of - last).days >= th["at_risk_active_days"]:
            lifecycle = "At Risk" if (as_of - last).days < th["at_risk_lookback_days"] else "Lapsed"
        else:
            lifecycle = "Active"
    elif (as_of - last).days < th["at_risk_active_days"]:
        lifecycle = "Active"
    return value, lifecycle


def analyze(db: Database, f: Filters) -> dict:
    th = thresholds(db)
    hs, he = history_bounds(db, f.creator_ids)
    if hs is None:
        return {"available": False, "reason": "No synced transaction history yet", "thresholds": th}
    as_of = min(he, date.today())
    rows = _fan_rows(db, f, hs, as_of)
    seg_counts: dict[str, dict] = {}
    life_counts: dict[str, int] = {}
    for r in rows:
        v, l = segment(r, th, as_of, hs)
        r["segment"], r["lifecycle"] = v, l
        sc = seg_counts.setdefault(v, {"segment": v, "fans": 0, "lifetime": 0, "period_spend": 0})
        sc["fans"] += 1
        sc["lifetime"] += r["lifetime"] or 0
        sc["period_spend"] += r["period_spend"] or 0
        life_counts[l or "Unknown (insufficient history)"] = life_counts.get(l or "Unknown (insufficient history)", 0) + 1
    period_fans = [r for r in rows if (r["period_purchases"] or 0) > 0]
    total_lt = sum(r["lifetime"] or 0 for r in rows)
    buckets = [(0, 1_000), (1_000, 5_000), (5_000, 10_000), (10_000, 25_000), (25_000, 50_000), (50_000, 100_000), (100_000, None)]
    dist = []
    for lo, hi in buckets:
        n = sum(1 for r in rows if (r["lifetime"] or 0) >= lo and (hi is None or (r["lifetime"] or 0) < hi))
        dist.append({"min": lo, "max": hi, "fans": n})
    # first-purchase acquisition per day (only meaningful after history start)
    acq: dict[str, int] = {}
    for r in rows:
        if r["first_day"] > hs.isoformat():
            acq[r["first_day"]] = acq.get(r["first_day"], 0) + 1
    returning = sum(1 for r in period_fans if r["first_day"] < f.start.isoformat())
    by_creator = db.query(
        f"""SELECT t.creator_id, c.name, COUNT(DISTINCT t.fan_id) fans, SUM({'t.net' if f.basis == 'net' else 't.amount'}) spend
            FROM transactions t LEFT JOIN creators c ON c.id=t.creator_id
            WHERE {recognized_clause('t')} AND t.day BETWEEN ? AND ? {('AND t.creator_id IN (' + ','.join('?' * len(f.creator_ids)) + ')') if f.creator_ids else ''}
            GROUP BY t.creator_id ORDER BY spend DESC""", (f.start.isoformat(), f.end.isoformat(), *(f.creator_ids or [])))
    return {
        "available": True,
        "history": {"start": hs.isoformat(), "end": he.isoformat(), "days": (he - hs).days + 1},
        "thresholds": th,
        "totals": {
            "known_paying_fans": len(rows),
            "paying_fans_in_period": len(period_fans),
            "new_paying_fans_in_period": len(period_fans) - returning,
            "returning_paying_fans_in_period": returning,
            "avg_ltv": ratio(total_lt, len(rows)),
            "avg_spend_in_period": ratio(sum(r["period_spend"] or 0 for r in period_fans), len(period_fans)),
            "avg_purchases_per_fan": ratio(sum(r["purchases"] for r in rows), len(rows)),
            "ppv_buyers": sum(1 for r in rows if (r["ppv_purchases"] or 0) > 0),
        },
        "segments": sorted(seg_counts.values(), key=lambda s: ["VIP", "High Value", "Regular", "Non-spender"].index(s["segment"])),
        "lifecycle": [{"lifecycle": k, "fans": v} for k, v in sorted(life_counts.items())],
        "distribution": dist,
        "acquisition": [{"day": k, "fans": v} for k, v in sorted(acq.items()) if f.start.isoformat() <= k <= f.end.isoformat()],
        "by_creator": by_creator,
        "_rows": rows,
        "limitations": [
            "No fan-list endpoint exists: only fans with at least one paid transaction in the synced window are visible.",
            "Per-fan subscription/expiry/auto-renew status is not exposed; use the aggregate audience counts instead.",
            f"Lifetime value = spend since {hs.isoformat()} (synced history), not true all-time spend.",
            "'Non-spender' = fans whose only recorded payments are subscriptions (free subscribers who never paid cannot be seen).",
        ],
    }


def top_spenders(db: Database, f: Filters, page: int = 1, page_size: int = 25, sort: str = "lifetime", segment_filter: str | None = None,
                 search: str | None = None, reveal: bool = False) -> dict:
    res = analyze(db, f)
    if not res.get("available"):
        return {"available": False, "reason": res.get("reason"), "items": [], "total": 0}
    rows = res["_rows"]
    if segment_filter:
        rows = [r for r in rows if r["segment"] == segment_filter or r["lifecycle"] == segment_filter]
    if search:
        s = search.lower()
        rows = [r for r in rows if s in (r["fan_id"] or "").lower() or s in (r["fan_name"] or "").lower()]
    key = sort if sort in ("lifetime", "period_spend", "purchases", "last_day", "tips", "ppv_purchases") else "lifetime"
    rows = sorted(rows, key=lambda r: (r.get(key) or 0), reverse=True)
    total = len(rows)
    page_rows = rows[(page - 1) * page_size: page * page_size]
    items = []
    for r in page_rows:
        it = {k: r[k] for k in ("lifetime", "period_spend", "purchases", "period_purchases", "ppv_purchases", "tips", "sub_spend",
                                "first_day", "last_day", "creators", "active_months", "segment", "lifecycle")}
        it["fan_ref"] = r["fan_id"] if reveal else mask_id(r["fan_id"])
        it["fan_name"] = r["fan_name"] if reveal else mask_name(r["fan_name"])
        items.append(it)
    return {"available": True, "items": items, "total": total, "page": page, "page_size": page_size, "history": res["history"]}


def audience_totals(db: Database, f: Filters) -> dict:
    """Aggregate subscriber counts from creator reports (latest day in range per creator; flows summed)."""
    from app.analytics.creators import audience
    where = f"WHERE id IN ({','.join('?' * len(f.creator_ids))})" if f.creator_ids else "WHERE connected=1"
    pids = [r["platform_pid"] for r in db.query(f"SELECT platform_pid FROM creators {where}", list(f.creator_ids or [])) if r["platform_pid"]]
    aud = audience(db, pids, f.start.isoformat(), f.end.isoformat())

    def tot(k):
        vals = [a.get(k) for a in aud.values() if a.get(k) is not None]
        return sum(vals) if vals else None

    trend = db.query(
        f"""SELECT day, metric, SUM(value) v FROM creator_daily WHERE platform_pid IN ({','.join('?' * len(pids)) or 'NULL'})
            AND day BETWEEN ? AND ? AND metric IN ('activeFans','expiredFans','newSubscribers','subscriberRenewals','fansWithRenewOn')
            GROUP BY day, metric ORDER BY day""", (*pids, f.start.isoformat(), f.end.isoformat())) if pids else []
    series: dict[str, dict] = {}
    for r in trend:
        series.setdefault(r["day"], {"day": r["day"]})[r["metric"]] = r["v"]
    reporting = sum(1 for a in aud.values() if a.get("activeFans") is not None)
    return {
        "active_fans": tot("activeFans"), "expired_fans": tot("expiredFans"), "new_subscribers": tot("newSubscribers"),
        "renewals": tot("subscriberRenewals"), "fans_with_renew_on": tot("fansWithRenewOn"),
        "auto_renew_pct": ratio(tot("fansWithRenewOn"), tot("activeFans"), 100),
        "creators_reporting": reporting, "creators_total": len(pids),
        "trend": [series[k] for k in sorted(series)],
    }


def recent_cutoff(as_of: date, days: int) -> date:
    return as_of - timedelta(days=days)
