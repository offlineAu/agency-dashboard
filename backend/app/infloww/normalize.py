"""Normalise raw Infloww payloads into store rows.

Missing values stay None (NULL) — they are never coerced to 0, so the dashboard can tell
"zero" apart from "not provided by the API".
"""
from __future__ import annotations

from app.core.dates import iso_to_ms, ms_to_day


def to_int(v) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).rstrip("%"))
    except (TypeError, ValueError):
        return None


def norm_type(t: str | None) -> str:
    """Unify transaction type spellings across endpoints ('RecurringSubscription' vs 'Recurring Subscription')."""
    if not t:
        return "Unknown"
    m = {"recurringsubscription": "Recurring Subscription"}
    key = t.replace(" ", "").lower()
    return m.get(key, t)


def creator_row(c: dict, connected: bool, now: float) -> tuple:
    return (
        str(c.get("id")), to_int(c.get("platformPid")), c.get("name"), c.get("nickName"), c.get("userName"),
        c.get("tagName"), c.get("status") or ("connected" if connected else None), 1 if connected else 0,
        to_int(c.get("createdTime")), to_int(c.get("deletedTime")), now,
    )


def transaction_row(t: dict, creator_id: str) -> tuple | None:
    ms = iso_to_ms(t.get("createdTime"))
    if ms is None or t.get("id") is None:
        return None
    return (
        f"{creator_id}:{t['id']}", creator_id, to_int(t.get("platformPid")), t.get("transactionId"), t.get("fanId"),
        t.get("fanName"), ms, ms_to_day(ms), norm_type(t.get("type")), t.get("tipSource"), t.get("status"),
        to_int(t.get("amount")), to_int(t.get("fee")), to_int(t.get("net")), t.get("currency"),
    )


def refund_row(r: dict, creator_id: str) -> tuple | None:
    ms = iso_to_ms(r.get("refundTime"))
    if ms is None or r.get("id") is None:
        return None
    return (
        f"{creator_id}:{r['id']}", creator_id, r.get("transactionId"), r.get("fanId"), iso_to_ms(r.get("paymentTime")), ms,
        ms_to_day(ms), r.get("paymentStatus"), to_int(r.get("paymentAmount")), r.get("transactionType"), r.get("currency"),
    )


def sales_record_row(s: dict, creator_id: str) -> tuple | None:
    ms = iso_to_ms(s.get("createdTime"))
    if ms is None or s.get("id") is None:
        return None
    return (
        f"{creator_id}:{s['id']}", creator_id, to_int(s.get("platformPid")), str(s.get("transactionId")), s.get("fanId"),
        ms, ms_to_day(ms), norm_type(s.get("type")), s.get("tipSource"), s.get("status"),
        to_int(s.get("amount")), to_int(s.get("fee")), to_int(s.get("net")), s.get("salesRule"),
        to_int(s.get("attributeEmployeeId")), to_int(s.get("salesAmount")), s.get("currency"),
    )


def emp_sales_row(r: dict) -> tuple:
    return (
        to_int(r.get("employeeId")), r.get("date"), to_int(r.get("platformPid")), to_int(r.get("salesAmount")),
        to_int(r.get("ppvSalesAmount")), to_int(r.get("tipsSalesAmount")), to_int(r.get("directMessageSalesAmount")),
        to_int(r.get("priorityMassMessageSalesAmount")), to_int(r.get("massMessageSalesAmount")), r.get("currency"),
    )


def emp_chat_row(r: dict) -> tuple:
    return (
        to_int(r.get("employeeId")), r.get("date"), to_int(r.get("platformPid")), to_int(r.get("directMessagesSent")),
        to_int(r.get("directPpvsSent")), to_float(r.get("goldenRatio")), to_int(r.get("ppvsUnlocked")),
        to_float(r.get("unlockRate")), to_int(r.get("fansChatted")), to_int(r.get("characterCount")),
        to_int(r.get("responseTimeBasedOnScheduledHours")), to_int(r.get("responseTimeBasedOnClockedHours")),
    )


# creator-report endpoint -> fields to store as daily metrics
CREATOR_REPORTS: dict[str, list[str]] = {
    "/v1/creator-report/fans/count": ["activeFans", "expiredFans"],
    "/v1/creator-report/fans/subscriber-count": ["newSubscribers", "subscriberRenewals"],
    "/v1/creator-report/fans/renew-on": ["fansWithRenewOn"],
    "/v1/creator-report/fans/avg-subscription-length": ["avgSubscriptionLength"],
    "/v1/creator-report/reach/profile-visitor-count": ["profileVisitors", "guestProfileVisitors", "loggedInUsersProfileVisitors"],
    "/v1/creator-report/rank": ["performanceRank"],
}


def creator_daily_rows(r: dict, fields: list[str]) -> list[tuple]:
    pid, day = to_int(r.get("platformPid")), r.get("date")
    if pid is None or not day:
        return []
    return [(pid, day, f, to_float(r.get(f))) for f in fields if r.get(f) is not None]


def link_row(l: dict, link_type: str, creator_id: str, now: float) -> tuple:
    return (
        str(l.get("id")), link_type, creator_id, l.get("name"), l.get("code"), l.get("source"), l.get("message"), l.get("type"),
        to_int(l.get("clickCount")), to_int(l.get("subCount")), to_int(l.get("subLimit")), to_int(l.get("subDuration")),
        to_int(l.get("discount")), to_int(l.get("payingFansCount")), to_int(l.get("earningsGross")), to_int(l.get("earningsNet")),
        to_float(l.get("subscriptionCVR")), to_float(l.get("spendingCVR")), to_float(l.get("spendClaim")),
        to_float(l.get("epcGross")), to_float(l.get("epcNet")), to_float(l.get("aepsGross")), to_float(l.get("aepsNet")),
        1 if l.get("finishedFlag") else 0 if l.get("finishedFlag") is not None else None, l.get("currency"),
        iso_to_ms(l.get("createdTime")), iso_to_ms(l.get("expiredTime")), iso_to_ms(l.get("updatedTime")), now,
    )


def invoice_row(i: dict, now: float) -> tuple:
    return (
        str(i.get("billingId")), i.get("invoiceId"), i.get("billingPeriod"), i.get("currency"), to_int(i.get("subscription")),
        to_int(i.get("discount")), to_int(i.get("igic")), to_int(i.get("total")), to_int(i.get("deductions")),
        to_int(i.get("balanceDue")), to_int(i.get("paid")), to_int(i.get("pending")), now,
    )


def message_rows(m: dict, kind: str, creator_id: str) -> tuple | None:
    mid = m.get("automatedMessageId") if kind == "automated" else m.get("priorityMassMessageId")
    if mid is None:
        return None
    sent = iso_to_ms(m.get("sentTime")) or iso_to_ms(m.get("createdTime"))
    cols = m.get("collections") or ([m["collection"]] if m.get("collection") else [])
    preview = None
    for c in cols:
        for msg in (c or {}).get("messages") or []:
            if msg.get("messageContent"):
                preview = str(msg["messageContent"])[:140]
                break
        if preview:
            break
    return (
        kind, str(mid), creator_id, to_int(m.get("employeeId")), m.get("status"), sent, ms_to_day(sent),
        to_int(m.get("price")), to_int(m.get("totalNumberOfTimeSent")), to_int(m.get("totalNumberOfPurchases")),
        to_int(m.get("totalRevenue")), preview, m.get("failReason"),
    )
