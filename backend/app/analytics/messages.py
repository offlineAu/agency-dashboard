"""Message analytics: automated messages + priority mass messages (/v1/automated-messages, /v1/priority-mass-messages)."""
from __future__ import annotations

from app.analytics.common import Filters, ratio
from app.store.db import Database


def overview(db: Database, f: Filters) -> dict:
    s, e = f.start.isoformat(), f.end.isoformat()
    cc = f" AND m.creator_id IN ({','.join('?' * len(f.creator_ids))})" if f.creator_ids else ""
    cp = list(f.creator_ids or [])
    by_kind = db.query(
        f"""SELECT kind, COUNT(*) n, SUM(times_sent) sent, SUM(purchases) purchases, SUM(revenue) revenue
            FROM messages m WHERE day BETWEEN ? AND ? {cc} GROUP BY kind""", (s, e, *cp))
    for k in by_kind:
        k["revenue_per_send"] = ratio(k["revenue"], k["sent"])
        k["purchase_rate"] = ratio(k["purchases"], k["sent"], 100)
    by_emp = db.query(
        f"""SELECT m.employee_id, e.name, COUNT(*) n, SUM(times_sent) sent, SUM(purchases) purchases, SUM(revenue) revenue
            FROM messages m LEFT JOIN employees e ON e.employee_id=m.employee_id WHERE day BETWEEN ? AND ? {cc}
            GROUP BY m.employee_id ORDER BY revenue DESC""", (s, e, *cp))
    items = db.query(
        f"""SELECT m.*, c.name creator_name, e.name employee_name FROM messages m
            LEFT JOIN creators c ON c.id=m.creator_id LEFT JOIN employees e ON e.employee_id=m.employee_id
            WHERE day BETWEEN ? AND ? {cc} ORDER BY revenue DESC LIMIT 200""", (s, e, *cp))
    for i in items:
        i["purchase_rate"] = ratio(i["purchases"], i["times_sent"], 100)
    return {"by_kind": by_kind, "by_employee": by_emp, "items": items}
