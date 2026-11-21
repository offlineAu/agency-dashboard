"""Creator analytics: revenue (transactions) + audience (creator-report daily metrics)."""
from __future__ import annotations

from app.analytics import revenue
from app.analytics.common import TYPE_LABELS, Filters, growth, mask_id, mask_name, ratio, recognized_clause
from app.core.dates import previous_period
from app.store.db import Database

DAILY_SUM = ("newSubscribers", "subscriberRenewals", "profileVisitors", "guestProfileVisitors", "loggedInUsersProfileVisitors")
DAILY_LAST = ("activeFans", "expiredFans", "fansWithRenewOn", "avgSubscriptionLength", "performanceRank")


def audience(db: Database, pids: list[int], start: str, end: str) -> dict[int, dict]:
    """Per platform_pid: period sums for flow metrics, latest-day values for stock metrics. Missing => absent (None)."""
    if not pids:
        return {}
    q = ",".join("?" * len(pids))
    out: dict[int, dict] = {p: {} for p in pids}
    for r in db.query(
        f"SELECT platform_pid, metric, SUM(value) v, COUNT(*) n FROM creator_daily WHERE platform_pid IN ({q}) AND day BETWEEN ? AND ? "
        f"AND metric IN ({','.join('?' * len(DAILY_SUM))}) GROUP BY platform_pid, metric", (*pids, start, end, *DAILY_SUM)):
        out[r["platform_pid"]][r["metric"]] = r["v"]
    for r in db.query(
        f"""SELECT d.platform_pid, d.metric, d.value, d.day FROM creator_daily d
            JOIN (SELECT platform_pid, metric, MAX(day) md FROM creator_daily WHERE platform_pid IN ({q}) AND day BETWEEN ? AND ?
                  AND metric IN ({','.join('?' * len(DAILY_LAST))}) GROUP BY platform_pid, metric) m
              ON m.platform_pid=d.platform_pid AND m.metric=d.metric AND m.md=d.day""",
        (*pids, start, end, *DAILY_LAST)):
        out[r["platform_pid"]][r["metric"]] = r["value"]
        out[r["platform_pid"]][r["metric"] + "_asof"] = r["day"]
    for p, m in out.items():
        m["autoRenewPct"] = ratio(m.get("fansWithRenewOn"), m.get("activeFans"), 100)
    return out


def directory(db: Database, f: Filters, prev_ok: bool = True) -> list[dict]:
    where = "WHERE connected=1" if not f.creator_ids else f"WHERE id IN ({','.join('?' * len(f.creator_ids))})"
    creators = db.query(f"SELECT * FROM creators {where} ORDER BY name", list(f.creator_ids or []))
    if not creators:
        return []
    s, e = f.start.isoformat(), f.end.isoformat()
    ps, pe = previous_period(f.start, f.end)
    ids = [c["id"] for c in creators]
    q = ",".join("?" * len(ids))
    col = "net" if f.basis == "net" else "amount"

    def agg(a, b):
        return {r["creator_id"]: r for r in db.query(
            f"""SELECT creator_id, SUM({col}) value, SUM(amount) gross, SUM(net) net, COUNT(*) n, COUNT(DISTINCT fan_id) fans,
                   SUM(CASE WHEN type IN ('Subscription','Recurring Subscription') THEN {col} END) subs,
                   SUM(CASE WHEN type IN ('Messages','Posts') THEN {col} END) ppv,
                   SUM(CASE WHEN type='Tips' THEN {col} END) tips
                FROM transactions WHERE {recognized_clause()} AND day BETWEEN ? AND ? AND creator_id IN ({q}) GROUP BY creator_id""",
            (a, b, *ids))}

    cur, prev = agg(s, e), agg(ps.isoformat(), pe.isoformat())
    refunds = {r["creator_id"]: r["v"] for r in db.query(
        f"SELECT creator_id, SUM(amount) v FROM refunds WHERE day BETWEEN ? AND ? AND creator_id IN ({q}) GROUP BY creator_id", (s, e, *ids))}
    reversed_ = {r["creator_id"]: r["v"] for r in db.query(
        f"SELECT creator_id, SUM(amount) v FROM transactions WHERE status IN ('undo','pending_return') AND day BETWEEN ? AND ? AND creator_id IN ({q}) GROUP BY creator_id",
        (s, e, *ids))}
    total_value = sum((r["value"] or 0) for r in cur.values())
    aud = audience(db, [c["platform_pid"] for c in creators if c["platform_pid"] is not None], s, e)

    out = []
    for c in creators:
        r = cur.get(c["id"], {})
        p = prev.get(c["id"], {})
        a = aud.get(c["platform_pid"], {})
        value = r.get("value") or 0
        out.append({
            "id": c["id"], "platform_pid": c["platform_pid"], "name": c["name"], "user_name": c["user_name"],
            "nick_name": c["nick_name"], "tag_name": c["tag_name"], "status": c["status"], "connected": bool(c["connected"]),
            "revenue": value, "gross": r.get("gross") or 0, "net": r.get("net") or 0,
            "previous_revenue": p.get("value") or 0, "growth": growth(value, p.get("value") or 0) if prev_ok else {"value": None, "reason": "previous period not fully synced yet"},
            "subscription_revenue": r.get("subs") or 0, "ppv_revenue": r.get("ppv") or 0, "tips": r.get("tips") or 0,
            "refunds": refunds.get(c["id"]) or 0, "reversed": reversed_.get(c["id"]) or 0,
            "transactions": r.get("n") or 0, "paying_fans": r.get("fans") or 0,
            "avg_revenue_per_paying_fan": ratio(value, r.get("fans")),
            "share_of_agency": ratio(value, total_value, 100),
            "active_fans": a.get("activeFans"), "expired_fans": a.get("expiredFans"),
            "new_subscribers": a.get("newSubscribers"), "renewals": a.get("subscriberRenewals"),
            "fans_with_renew_on": a.get("fansWithRenewOn"), "auto_renew_pct": a.get("autoRenewPct"),
            "avg_subscription_length_days": a.get("avgSubscriptionLength"), "profile_visitors": a.get("profileVisitors"),
            "performance_rank": a.get("performanceRank"), "audience_asof": a.get("activeFans_asof"),
        })
    out.sort(key=lambda x: x["revenue"], reverse=True)
    return out


def detail(db: Database, f: Filters, creator_id: str, prev_ok: bool = True) -> dict | None:
    c = db.one("SELECT * FROM creators WHERE id=?", (creator_id,))
    if not c:
        return None
    cf = Filters(f.start, f.end, (creator_id,), f.basis)
    s, e = f.start.isoformat(), f.end.isoformat()
    pid = c["platform_pid"]
    daily = {}
    if pid is not None:
        for r in db.query("SELECT day, metric, value FROM creator_daily WHERE platform_pid=? AND day BETWEEN ? AND ? ORDER BY day", (pid, s, e)):
            daily.setdefault(r["day"], {"day": r["day"]})[r["metric"]] = r["value"]
    col = "net" if f.basis == "net" else "amount"
    top = db.query(
        f"""SELECT fan_id, MAX(fan_name) fan_name, SUM({col}) value, COUNT(*) n, MAX(created_ms) last_ms,
                   SUM(CASE WHEN type IN ('Messages','Posts') THEN 1 ELSE 0 END) ppv_purchases
            FROM transactions WHERE creator_id=? AND {recognized_clause()} AND day BETWEEN ? AND ? AND fan_id IS NOT NULL
            GROUP BY fan_id ORDER BY value DESC LIMIT 10""", (creator_id, s, e))
    for t in top:
        t["fan_name"] = mask_name(t["fan_name"])
        t["fan_id"] = mask_id(t["fan_id"])
    agency_total = revenue.totals(db, Filters(f.start, f.end, None, f.basis))["value"]
    tot = revenue.with_comparison(db, cf, prev_ok)
    emp = db.query(
        """SELECT s.employee_id, e.name, SUM(s.sales) sales, SUM(s.ppv) ppv, SUM(s.tips) tips
           FROM emp_sales_daily s LEFT JOIN employees e ON e.employee_id=s.employee_id
           WHERE s.platform_pid=? AND s.day BETWEEN ? AND ? GROUP BY s.employee_id ORDER BY sales DESC""", (pid, s, e)) if pid else []
    return {
        "creator": c,
        "totals": tot,
        "share_of_agency": ratio(tot["current"]["value"], agency_total, 100),
        "trend": revenue.trend(db, cf),
        "breakdown": revenue.breakdown(db, cf),
        "audience_daily": [daily[k] for k in sorted(daily)],
        "audience": audience(db, [pid], s, e).get(pid, {}) if pid else {},
        "top_spenders": top,
        "employees": emp,
        "labels": TYPE_LABELS,
    }
