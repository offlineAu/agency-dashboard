"""Chatter / employee analytics.

Attribution rule: revenue shown for an employee is ONLY what Infloww attributes to them
(employee-sales-summary, per the agency's Infloww sales settings, and transaction-perf salesRule).
Creator revenue is never spread across chatters; unattributed sales are reported as such.
Revenue per hour is NOT computed: the API exposes response times but no worked/clocked hours.
"""
from __future__ import annotations

from app.analytics.common import Filters, growth, ratio
from app.core.dates import previous_period
from app.store.db import Database


def _pid_filter(db: Database, f: Filters) -> tuple[str, list]:
    if not f.creator_ids:
        return "", []
    pids = [r["platform_pid"] for r in db.query(
        f"SELECT platform_pid FROM creators WHERE id IN ({','.join('?' * len(f.creator_ids))})", list(f.creator_ids))]
    if not pids:
        return " AND 1=0", []
    return f" AND platform_pid IN ({','.join('?' * len(pids))})", pids


def leaderboard(db: Database, f: Filters, prev_ok: bool = True) -> list[dict]:
    s, e = f.start.isoformat(), f.end.isoformat()
    pc, pp = _pid_filter(db, f)
    ps, pe = previous_period(f.start, f.end)
    sales = {r["employee_id"]: r for r in db.query(
        f"""SELECT employee_id, SUM(sales) sales, SUM(ppv) ppv, SUM(tips) tips, SUM(direct_msg) direct_msg,
                   SUM(priority_mass) priority_mass, SUM(mass) mass, COUNT(DISTINCT day) active_days
            FROM emp_sales_daily WHERE day BETWEEN ? AND ? {pc} GROUP BY employee_id""", (s, e, *pp))}
    prev = {r["employee_id"]: r["sales"] for r in db.query(
        f"SELECT employee_id, SUM(sales) sales FROM emp_sales_daily WHERE day BETWEEN ? AND ? {pc} GROUP BY employee_id",
        (ps.isoformat(), pe.isoformat(), *pp))}
    chat = {r["employee_id"]: r for r in db.query(
        f"""SELECT employee_id, SUM(dms_sent) dms_sent, SUM(dm_ppvs_sent) ppvs_sent, SUM(ppvs_unlocked) ppvs_unlocked,
                   SUM(fans_chatted) fans_chatted_daily_sum, SUM(characters) characters,
                   SUM(CASE WHEN resp_scheduled_ms IS NOT NULL THEN resp_scheduled_ms * dms_sent END) rs_w,
                   SUM(CASE WHEN resp_scheduled_ms IS NOT NULL THEN dms_sent END) rs_n,
                   SUM(CASE WHEN resp_clocked_ms IS NOT NULL THEN resp_clocked_ms * dms_sent END) rc_w,
                   SUM(CASE WHEN resp_clocked_ms IS NOT NULL THEN dms_sent END) rc_n,
                   COUNT(DISTINCT day) chat_days
            FROM emp_chat_daily WHERE day BETWEEN ? AND ? {pc} GROUP BY employee_id""", (s, e, *pp))}
    assigned = {}
    for r in db.query("SELECT ec.employee_id, ec.creator_id, c.name FROM employee_creators ec LEFT JOIN creators c ON c.id=ec.creator_id"):
        assigned.setdefault(r["employee_id"], []).append({"id": r["creator_id"], "name": r["name"]})
    out = []
    for emp in db.query("SELECT * FROM employees ORDER BY name"):
        eid = emp["employee_id"]
        sl, ch = sales.get(eid, {}), chat.get(eid, {})
        if f.creator_ids and not sl and not ch:
            continue
        sv = sl.get("sales")
        out.append({
            "employee_id": eid, "name": emp["name"], "status": emp["status"],
            "assigned_creators": assigned.get(eid, []),
            "sales": sv, "ppv_sales": sl.get("ppv"), "tips_sales": sl.get("tips"), "direct_message_sales": sl.get("direct_msg"),
            "priority_mass_sales": sl.get("priority_mass"), "mass_message_sales": sl.get("mass"),
            "previous_sales": prev.get(eid), "growth": ({"value": None, "reason": "previous period not fully synced yet"} if not prev_ok
                       else growth(sv, prev.get(eid) or 0) if sv is not None else {"value": None, "reason": "no sales data"}),
            "messages_sent": ch.get("dms_sent"), "ppvs_sent": ch.get("ppvs_sent"), "ppvs_unlocked": ch.get("ppvs_unlocked"),
            "unlock_rate": ratio(ch.get("ppvs_unlocked"), ch.get("ppvs_sent"), 100),
            "golden_ratio": ratio(ch.get("ppvs_sent"), ch.get("dms_sent"), 100),
            "fans_chatted_daily_sum": ch.get("fans_chatted_daily_sum"),
            "characters": ch.get("characters"),
            "avg_response_scheduled_ms": ratio(ch.get("rs_w"), ch.get("rs_n")),
            "avg_response_clocked_ms": ratio(ch.get("rc_w"), ch.get("rc_n")),
            "sales_per_message": ratio(sv, ch.get("dms_sent")),
            "sales_per_ppv_sent": ratio(sl.get("ppv"), ch.get("ppvs_sent")),
            "active_days": max(sl.get("active_days") or 0, ch.get("chat_days") or 0),
            "revenue_per_hour": None,
        })
    out.sort(key=lambda x: (x["sales"] or 0), reverse=True)
    for i, o in enumerate(out, 1):
        o["rank"] = i
    return out


def trend(db: Database, f: Filters, employee_id: int | None = None) -> list[dict]:
    pc, pp = _pid_filter(db, f)
    ec, ep = ("AND employee_id=?", [employee_id]) if employee_id is not None else ("", [])
    return db.query(
        f"""SELECT day, SUM(sales) sales, SUM(ppv) ppv, SUM(tips) tips FROM emp_sales_daily
            WHERE day BETWEEN ? AND ? {pc} {ec} GROUP BY day ORDER BY day""", (f.start.isoformat(), f.end.isoformat(), *pp, *ep))


def matrix(db: Database, f: Filters) -> dict:
    pc, pp = _pid_filter(db, f)
    rows = db.query(
        f"""SELECT s.employee_id, e.name employee, s.platform_pid, c.id creator_id, c.name creator, SUM(s.sales) sales
            FROM emp_sales_daily s LEFT JOIN employees e ON e.employee_id=s.employee_id
            LEFT JOIN creators c ON c.platform_pid=s.platform_pid
            WHERE s.day BETWEEN ? AND ? {pc.replace('platform_pid', 's.platform_pid')} GROUP BY s.employee_id, s.platform_pid""",
        (f.start.isoformat(), f.end.isoformat(), *pp))
    return {"cells": rows}


def attribution(db: Database, f: Filters) -> dict:
    """How sales were attributed (transaction-perf/details salesRule) — exposes unattributed revenue explicitly."""
    s, e = f.start.isoformat(), f.end.isoformat()
    cc = f" AND creator_id IN ({','.join('?' * len(f.creator_ids))})" if f.creator_ids else ""
    cp = list(f.creator_ids or [])
    rules = db.query(
        f"""SELECT COALESCE(sales_rule,'(none)') rule, COUNT(*) n, SUM(amount) amount, SUM(sales_amount) sales_amount
            FROM sales_records WHERE day BETWEEN ? AND ? AND status IN ('done','loading') {cc} GROUP BY rule ORDER BY amount DESC""",
        (s, e, *cp))
    total = sum(r["amount"] or 0 for r in rules)
    unassigned = sum(r["amount"] or 0 for r in rules if r["rule"] in ("Unassigned", "(none)"))
    by_emp = db.query(
        f"""SELECT r.employee_id, e.name, COUNT(*) n, SUM(r.sales_amount) sales_amount FROM sales_records r
            LEFT JOIN employees e ON e.employee_id=r.employee_id
            WHERE r.day BETWEEN ? AND ? AND r.status IN ('done','loading') AND r.employee_id IS NOT NULL {cc.replace('creator_id', 'r.creator_id')}
            GROUP BY r.employee_id ORDER BY sales_amount DESC""", (s, e, *cp))
    return {"rules": rules, "total_amount": total, "unassigned_amount": unassigned,
            "attributed_share": ratio(total - unassigned, total, 100), "by_employee": by_emp}


def detail(db: Database, f: Filters, employee_id: int, prev_ok: bool = True) -> dict | None:
    emp = db.one("SELECT * FROM employees WHERE employee_id=?", (employee_id,))
    if not emp:
        return None
    row = next((r for r in leaderboard(db, Filters(f.start, f.end, None, f.basis), prev_ok) if r["employee_id"] == employee_id), None)
    by_creator = db.query(
        """SELECT s.platform_pid, c.id creator_id, c.name creator, SUM(s.sales) sales, SUM(s.ppv) ppv, SUM(s.tips) tips
           FROM emp_sales_daily s LEFT JOIN creators c ON c.platform_pid=s.platform_pid
           WHERE s.employee_id=? AND s.day BETWEEN ? AND ? GROUP BY s.platform_pid ORDER BY sales DESC""",
        (employee_id, f.start.isoformat(), f.end.isoformat()))
    chat_daily = db.query(
        """SELECT day, SUM(dms_sent) messages, SUM(dm_ppvs_sent) ppvs_sent, SUM(ppvs_unlocked) ppvs_unlocked, SUM(fans_chatted) fans_chatted
           FROM emp_chat_daily WHERE employee_id=? AND day BETWEEN ? AND ? GROUP BY day ORDER BY day""",
        (employee_id, f.start.isoformat(), f.end.isoformat()))
    return {"employee": emp, "summary": row, "trend": trend(db, f, employee_id), "by_creator": by_creator, "chat_daily": chat_daily}
