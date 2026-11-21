"""Revenue analytics from /v1/transactions and /v1/refunds (synced)."""
from __future__ import annotations

from datetime import date, timedelta

from app.analytics.common import (withhold, PPV_TYPES, SUBSCRIPTION_TYPES, TYPE_LABELS, Filters, creator_clause, growth,
                                  recognized_clause)
from app.core.dates import days_between, previous_period
from app.store.db import Database


def totals(db: Database, f: Filters) -> dict:
    cc, cp = creator_clause(f)
    row = db.one(
        f"""SELECT
              SUM(CASE WHEN {recognized_clause()} THEN amount END) gross,
              SUM(CASE WHEN {recognized_clause()} THEN net END) net,
              SUM(CASE WHEN {recognized_clause()} THEN fee END) fees,
              SUM(CASE WHEN status='loading' THEN amount END) gross_loading,
              SUM(CASE WHEN status='undo' THEN amount END) reversed,
              SUM(CASE WHEN status='pending_return' THEN amount END) pending_return,
              COUNT(CASE WHEN {recognized_clause()} THEN 1 END) tx_count,
              COUNT(DISTINCT CASE WHEN {recognized_clause()} THEN fan_id END) paying_fans,
              GROUP_CONCAT(DISTINCT currency) currencies
            FROM transactions WHERE day BETWEEN ? AND ? {cc}""",
        (f.start.isoformat(), f.end.isoformat(), *cp),
    ) or {}
    by_type = {r["type"]: r for r in db.query(
        f"""SELECT type, SUM(amount) gross, SUM(net) net, COUNT(*) n FROM transactions
            WHERE day BETWEEN ? AND ? AND {recognized_clause()} {cc} GROUP BY type""",
        (f.start.isoformat(), f.end.isoformat(), *cp))}
    rf = db.one(
        f"""SELECT SUM(amount) refunds, COUNT(*) n FROM refunds WHERE day BETWEEN ? AND ? {cc}""",
        (f.start.isoformat(), f.end.isoformat(), *cp)) or {}

    def tsum(types, col):
        vals = [by_type[t][col] for t in types if t in by_type and by_type[t][col] is not None]
        return sum(vals) if vals else 0

    col = "net" if f.basis == "net" else "gross"
    currencies = sorted({c for c in (row.get("currencies") or "").split(",") if c})
    return {
        "gross": row.get("gross") or 0,
        "net": row.get("net") or 0,
        "platform_fees": row.get("fees") or 0,
        "value": (row.get("net") if f.basis == "net" else row.get("gross")) or 0,
        "gross_pending_clearance": row.get("gross_loading") or 0,
        "reversed": row.get("reversed") or 0,
        "pending_return": row.get("pending_return") or 0,
        "refunds": rf.get("refunds") or 0,
        "refund_count": rf.get("n") or 0,
        "transactions": row.get("tx_count") or 0,
        "paying_fans": row.get("paying_fans") or 0,
        "subscription": tsum(SUBSCRIPTION_TYPES, col),
        "subscription_new": tsum(("Subscription",), col),
        "subscription_recurring": tsum(("Recurring Subscription",), col),
        "ppv": tsum(PPV_TYPES, col),
        "ppv_messages": tsum(("Messages",), col),
        "ppv_posts": tsum(("Posts",), col),
        "tips": tsum(("Tips",), col),
        "streams": tsum(("Streams",), col),
        "referrals": tsum(("Referrals",), col),
        "unknown": tsum(("Unknown",), col),
        "currencies": currencies,
        "mixed_currency": len(currencies) > 1,
    }


def breakdown(db: Database, f: Filters) -> list[dict]:
    cc, cp = creator_clause(f)
    rows = db.query(
        f"""SELECT type, SUM(amount) gross, SUM(net) net, COUNT(*) n FROM transactions
            WHERE day BETWEEN ? AND ? AND {recognized_clause()} {cc} GROUP BY type ORDER BY SUM(amount) DESC""",
        (f.start.isoformat(), f.end.isoformat(), *cp))
    total = sum((r["net"] if f.basis == "net" else r["gross"]) or 0 for r in rows)
    out = []
    for r in rows:
        v = (r["net"] if f.basis == "net" else r["gross"]) or 0
        out.append({"type": r["type"], "label": TYPE_LABELS.get(r["type"], r["type"]), "gross": r["gross"] or 0,
                    "net": r["net"] or 0, "value": v, "count": r["n"], "share": v / total * 100 if total else None})
    return out


def bucket_key(d: date, granularity: str) -> str:
    if granularity == "week":
        return (d - timedelta(days=d.weekday())).isoformat()
    if granularity == "month":
        return d.replace(day=1).isoformat()
    return d.isoformat()


def _bucket_expr(granularity: str) -> str:
    if granularity == "week":   # ISO-ish week starting Monday
        return "date(day, '-' || ((CAST(strftime('%w', day) AS INTEGER) + 6) % 7) || ' days')"
    if granularity == "month":
        return "strftime('%Y-%m-01', day)"
    return "day"


def trend(db: Database, f: Filters, granularity: str = "day", by_type: bool = False) -> list[dict]:
    cc, cp = creator_clause(f)
    b = _bucket_expr(granularity)
    rows = db.query(
        f"""SELECT {b} bucket, type, SUM(amount) gross, SUM(net) net, COUNT(*) n FROM transactions
            WHERE day BETWEEN ? AND ? AND {recognized_clause()} {cc} GROUP BY bucket, type""",
        (f.start.isoformat(), f.end.isoformat(), *cp))
    # zero-fill buckets inside the period (zero here is real: coverage is reported separately)
    buckets: dict[str, dict] = {}
    for d in days_between(f.start, f.end):
        key = bucket_key(d, granularity)
        buckets.setdefault(key, {"bucket": key, "gross": 0, "net": 0, "count": 0})
    for r in rows:
        o = buckets.setdefault(r["bucket"], {"bucket": r["bucket"], "gross": 0, "net": 0, "count": 0})
        o["gross"] += r["gross"] or 0
        o["net"] += r["net"] or 0
        o["count"] += r["n"]
        if by_type:
            o[r["type"]] = o.get(r["type"], 0) + ((r["net"] if f.basis == "net" else r["gross"]) or 0)
    out = sorted(buckets.values(), key=lambda x: x["bucket"])
    for o in out:
        o["value"] = o["net"] if f.basis == "net" else o["gross"]
    return out


def by_creator(db: Database, f: Filters) -> list[dict]:
    cc, cp = creator_clause(f, "t.creator_id")
    col = "t.net" if f.basis == "net" else "t.amount"
    return db.query(
        f"""SELECT t.creator_id, c.name, c.user_name, SUM({col}) value, SUM(t.amount) gross, SUM(t.net) net,
                   COUNT(*) transactions, COUNT(DISTINCT t.fan_id) paying_fans
            FROM transactions t LEFT JOIN creators c ON c.id = t.creator_id
            WHERE t.day BETWEEN ? AND ? AND {recognized_clause('t')} {cc}
            GROUP BY t.creator_id ORDER BY value DESC""",
        (f.start.isoformat(), f.end.isoformat(), *cp))


def with_comparison(db: Database, f: Filters, prev_ok: bool = True) -> dict:
    cur = totals(db, f)
    ps, pe = previous_period(f.start, f.end)
    prev = totals(db, Filters(ps, pe, f.creator_ids, f.basis))
    keys = ("gross", "net", "value", "subscription", "ppv", "tips", "refunds", "paying_fans", "transactions")
    return {"current": cur, "previous": prev, "previous_period": {"start": ps.isoformat(), "end": pe.isoformat()},
            "previous_complete": prev_ok,
            "growth": {k: growth(cur[k], prev[k]) for k in keys} if prev_ok else withhold(keys)}


def daily_series(db: Database, f: Filters, creator_id: str) -> list[dict]:
    return trend(db, Filters(f.start, f.end, (creator_id,), f.basis))


def latest_day(db: Database) -> date | None:
    d = db.scalar("SELECT MAX(day) FROM transactions")
    return date.fromisoformat(d) if d else None
