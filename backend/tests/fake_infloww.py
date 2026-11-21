"""Spec-faithful fake of the Infloww API for automated tests (and the explicitly-labelled fixture dev server).

Enforces the documented contract so the client/sync code is tested against the rules, not just shapes:
  * `Authorization` must equal the raw key (no Bearer) and `x-oid` must match -> else 401.
  * Only GET -> else 405.  `limit` above the endpoint max -> 400.  Time windows > 31 days -> 400.
  * Cursor pagination with `cursor` + `hasMore`; creator/employee report IDs max 10.
All data is synthetic and deterministic (seeded). It never represents real people.
"""
from __future__ import annotations

import json
import random
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx

KEY = "test-key-0123456789"
OID = "999000111"
UTC = timezone.utc


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _parse_time(v: str) -> int:
    if v.isdigit():
        return int(v)
    if len(v) == 10:
        return _ms(datetime.fromisoformat(v).replace(tzinfo=UTC))
    return _ms(datetime.fromisoformat(v.replace("Z", "+00:00")))


class FakeInfloww:
    def __init__(self, seed: int = 7, days: int = 120, today: date | None = None, creators: int = 3, employees: int = 4,
                 tx_per_day: int = 12):
        self.rng = random.Random(seed)
        self.today = today or datetime.now(UTC).date()
        self.calls: list[tuple[str, str, dict]] = []
        self.fail_next: dict[str, list[int]] = {}   # path -> list of status codes to return first
        self.forbidden: set[str] = set()
        self.creators = [{"id": str(1000 + i), "name": f"Creator {chr(65 + i)}", "nickName": f"C{chr(65 + i)}", "userName": f"creator_{i}",
                          "tagName": None, "createdTime": str(_ms(datetime(2025, 1, 1, tzinfo=UTC))), "platformPid": 500000 + i}
                         for i in range(creators)]
        self.deleted = [{"id": "1999", "name": "Old Creator", "nickName": None, "userName": "old", "tagName": None, "status": "deleted",
                         "platformPid": 599999, "createdTime": "1700000000000", "deletedTime": "1730000000000"}]
        self.employees = [{"employeeId": 70 + i, "employeeName": f"Chatter {i + 1}", "status": "Activated",
                           "createdTime": "1700000000000", "deletedTime": None} for i in range(employees)]
        self.assign = {70 + i: [self.creators[i % creators]["id"], self.creators[(i + 1) % creators]["id"]] for i in range(employees)}
        types = ["Subscription", "Recurring Subscription", "Messages", "Messages", "Messages", "Posts", "Tips", "Tips", "Streams"]
        statuses = ["done"] * 12 + ["loading", "loading", "undo", "pending_return"]
        fans = [f"onlyfans-{10000000 + i}" for i in range(150)]
        self.tx: dict[str, list[dict]] = {c["id"]: [] for c in self.creators}
        self.sales: dict[str, list[dict]] = {c["id"]: [] for c in self.creators + self.deleted}
        n = 0
        for d in range(days):
            day = self.today - timedelta(days=d)
            for c in self.creators:
                for _ in range(self.rng.randint(tx_per_day // 2, tx_per_day)):
                    n += 1
                    t = self.rng.choice(types)
                    amt = {"Subscription": 999, "Recurring Subscription": 999, "Tips": self.rng.choice([500, 1000, 2500, 5000])}.get(
                        t, self.rng.choice([700, 1200, 1500, 2500, 4000]))
                    day0 = datetime(day.year, day.month, day.day, tzinfo=UTC)
                    sec = self.rng.randint(0, 86399)
                    elapsed = int((datetime.now(UTC) - day0).total_seconds()) - 60
                    if elapsed < 86400:  # today: real data can't be in the future
                        sec = sec * max(elapsed, 0) // 86400
                    ts = day0 + timedelta(seconds=sec)
                    fan = self.rng.choice(fans[: 40] if self.rng.random() < 0.5 else fans)
                    st = self.rng.choice(statuses)
                    row = {"id": str(n), "transactionId": f"of-{n}", "fanId": fan, "fanName": f"Fan {fan[-3:]}", "platformPid": c["platformPid"],
                           "createdTime": str(_ms(ts)), "tipSource": "Chat" if t == "Tips" else None, "type": t, "status": st,
                           "amount": str(amt), "fee": str(amt // 5), "net": str(amt - amt // 5), "currency": "USD"}
                    self.tx[c["id"]].append(row)
                    emp = self.rng.choice([e["employeeId"] for e in self.employees] + [None])
                    self.sales[c["id"]].append({
                        "id": n, "transactionId": row["transactionId"], "platformPid": c["platformPid"], "fanId": fan, "fanName": row["fanName"],
                        "createdTime": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "type": t.replace("Recurring Subscription", "RecurringSubscription"),
                        "tipSource": row["tipSource"], "status": st, "amount": amt, "fee": amt // 5, "net": amt - amt // 5,
                        "salesRule": "Unassigned" if emp is None else self.rng.choice(["Message sender", "Last chatter", "Employee on shift"]),
                        "attributeEmployeeId": emp, "salesAmount": 0 if emp is None else amt, "currency": "USD"})
        self.refunds = {c["id"]: [{"id": f"r{c['id']}{i}", "transactionId": f"of-r{i}", "fanId": fans[i], "paymentTime": str(_ms(datetime.combine(self.today - timedelta(days=i + 3), datetime.min.time(), UTC))),
                                   "refundTime": str(_ms(datetime.combine(self.today - timedelta(days=i), datetime.min.time(), UTC)) + 3600_000),
                                   "paymentStatus": "done", "paymentAmount": 1500, "transactionType": "chat_messages", "currency": "USD"} for i in range(0, 40, 9)]
                        for c in self.creators}
        self.links = {}
        for c in self.creators:
            self.links[(c["id"], "TRACKING")] = [
                {"id": str(int(c["id"]) * 10 + i), "name": f"{src} promo", "code": f"c{i}", "clickCount": clicks, "subCount": subs, "finishedFlag": False,
                 "source": src, "autoDefaultList": False, "defaultListName": None, "relTagNames": [], "earningsGross": earn, "earningsNet": int(earn * .8),
                 "payingFansCount": subs // 3, "subscriptionCVR": f"{subs / clicks * 100:.2f}", "spendingCVR": "33.0", "epcGross": earn // clicks,
                 "epcNet": earn * .8 / clicks, "aepsGross": earn // max(subs, 1), "aepsNet": int(earn * .8) // max(subs, 1), "currency": "USD",
                 "createdTime": str(_ms(datetime.combine(self.today - timedelta(days=40 + i), datetime.min.time(), UTC))), "expiredTime": None,
                 "updatedTime": str(_ms(datetime.now(UTC)))}
                for i, (src, clicks, subs, earn) in enumerate([("TikTok", 5000, 350, 450000), ("Reddit", 3200, 180, 270000), ("Instagram", 2100, 20, 12000)])]
            self.links[(c["id"], "TRIAL")] = [
                {"id": str(8000 + int(c["id"])), "name": "Free trial", "code": "t1", "subDuration": 7, "subLimit": 0, "subCount": 120, "finishedFlag": False,
                 "source": "Twitter", "autoDefaultList": False, "defaultListName": None, "relTagNames": [], "spendClaim": "25.0", "payingFansCount": 30,
                 "earningsGross": 90000, "earningsNet": 72000, "aepsGross": 750, "aepsNet": 600, "currency": "USD",
                 "createdTime": str(_ms(datetime.combine(self.today - timedelta(days=10), datetime.min.time(), UTC))), "expiredTime": None, "updatedTime": None}]
            self.links[(c["id"], "CAMPAIGN")] = []

    # ------------------------------------------------------------------ transport
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = urlparse(str(request.url)).path
        q = parse_qs(urlparse(str(request.url)).query)
        self.calls.append((request.method, path, {k: v for k, v in q.items()}))
        if request.method != "GET":
            return self._err(405, "Method Not Allowed")
        if request.headers.get("Authorization") != KEY or request.headers.get("x-oid") != OID:
            return self._err(401, "invalid api key")
        if path in self.forbidden:
            return self._err(403, "permission denied")
        if self.fail_next.get(path):
            code = self.fail_next[path].pop(0)
            return self._err(code, "Too Many Requests" if code == 429 else "Internal Server Error")
        one = lambda k, d=None: (q.get(k) or [d])[0]  # noqa: E731
        limit = int(one("limit", "10"))
        maxl = 10 if path in ("/v1/automated-messages", "/v1/priority-mass-messages") else 100
        if limit > maxl:
            return self._err(400, f"limit must be less than or equal to {maxl}")
        st, et = one("startTime"), one("endTime")
        if et and et.isdigit() and len(et) > 10 and int(et) > time.time() * 1000:
            return self._err(400, "Parameter 'endTime' must be a past or present time")
        if st and et and path != "/v1/invoice-data/monthly-billing":
            a, b = _parse_time(st), _parse_time(et)
            if len(st) == 10:
                b += 86400_000 - 1
            if b - a > 31 * 86400_000:
                return self._err(400, "Query range is limited to 31 days per request")
        ids = q.get("creatorIds") or q.get("employeeIds")
        if ids and len(ids) > 10:
            return self._err(400, "Maximum of 10 ids")

        if path == "/v1/creators":
            return self._page(self.creators, q, limit)
        if path == "/v1/all-creators":
            return self._page([{**c, "status": "connected"} for c in self.creators] + self.deleted, q, limit)
        if path == "/v1/employees":
            return self._page(self.employees, q, limit)
        if path == "/v1/employees/assigned-creators":
            eid = int(one("employeeId"))
            return self._page([{"platformCode": "OnlyFans", "employeeId": eid, "creatorId": int(c)} for c in self.assign.get(eid, [])], q, limit)
        cid = one("creatorId")
        if path in ("/v1/transactions", "/v1/transaction-perf/details", "/v1/refunds"):
            if cid not in self.tx and not (path == "/v1/transaction-perf/details" and cid in self.sales):
                return self._err(400, "creatorId is invalid")
            src = {"/v1/transactions": self.tx, "/v1/transaction-perf/details": self.sales, "/v1/refunds": self.refunds}[path].get(cid, [])
            key = "refundTime" if path == "/v1/refunds" else "createdTime"
            rows = [r for r in src if a <= _parse_time(str(r[key])) <= b]
            return self._page(rows, q, limit)
        if path == "/v1/links":
            return self._page(self.links.get((cid, one("linkType")), []), q, limit, extra={"linkType": one("linkType")})
        if path == "/v1/linkfans":
            return self._page([{"id": one("linkId"), "fanId": f"onlyfans-1000000{i}", "fanName": f"Fan {i}", "subscriptionEarningGross": 999,
                                "messagesEarningGross": 1500 * i, "tipsEarningGross": 0, "postsEarningGross": 0, "streamsEarningGross": 0,
                                "currency": "USD", "subscribedTime": "1750000000000"} for i in range(5)], q, limit)
        if path.startswith("/v1/creator-report/"):
            cids = q.get("creatorIds", [])
            pids = [c["platformPid"] for c in self.creators if c["id"] in cids]
            rows = []
            if path == "/v1/creator-report/chat-summary":
                rows = [{"platformPid": p, "replyTime": 120000, "fansChatted": 45, "messagesSent": 120, "ppvsSent": 15} for p in pids]
            else:
                d0, d1 = date.fromisoformat(st), date.fromisoformat(et)
                for p in pids:
                    for i in range((d1 - d0).days + 1):
                        d = (d0 + timedelta(days=i)).isoformat()
                        base = {"platformPid": p, "date": d}
                        rows.append({**base, **{
                            "/v1/creator-report/fans/count": {"activeFans": 1000 + i + p % 7, "expiredFans": 300 + i},
                            "/v1/creator-report/fans/subscriber-count": {"newSubscribers": 10 + i % 5, "subscriberRenewals": 4},
                            "/v1/creator-report/fans/renew-on": {"fansWithRenewOn": 400 + i},
                            "/v1/creator-report/fans/avg-subscription-length": {"avgSubscriptionLength": 45},
                            "/v1/creator-report/reach/profile-visitor-count": {"profileVisitors": 200, "guestProfileVisitors": 50, "loggedInUsersProfileVisitors": 150},
                            "/v1/creator-report/rank": {"performanceRank": 0.5},
                        }[path]})
            return self._json({"data": {"platformCode": "OnlyFans", "list": rows}})
        if path.startswith("/v1/employee-report/"):
            eids = [int(x) for x in q.get("employeeIds", [])]
            d0, d1 = date.fromisoformat(st), date.fromisoformat(et)
            rows = []
            for e in eids:
                for c in self.creators:
                    if c["id"] not in self.assign.get(e, []):
                        continue
                    for i in range((d1 - d0).days + 1):
                        d = (d0 + timedelta(days=i)).isoformat()
                        if "sales" in path:
                            rows.append({"employeeId": e, "date": d, "platformPid": c["platformPid"], "salesAmount": 10000 + e * 10, "ppvSalesAmount": 6000,
                                         "tipsSalesAmount": 2000, "directMessageSalesAmount": 7000, "priorityMassMessageSalesAmount": 2000,
                                         "massMessageSalesAmount": 1000, "currency": "USD"})
                        else:
                            rows.append({"employeeId": e, "date": d, "platformPid": c["platformPid"], "directMessagesSent": 200, "directPpvsSent": 20,
                                         "goldenRatio": "10.00", "ppvsUnlocked": 5, "unlockRate": "25.00", "fansChatted": 40, "characterCount": 9000,
                                         "responseTimeBasedOnScheduledHours": 90000, "responseTimeBasedOnClockedHours": 60000})
            return self._json({"data": {"platformCode": "OnlyFans", "list": rows}})
        if path == "/v1/invoice-data/monthly-billing":
            return self._json({"data": {"list": [{"billingId": "b1", "invoiceId": "i1", "billingPeriod": self.today.strftime("%Y-%m"), "currency": "USD",
                                                  "subscription": 29900, "discount": 0, "igic": None, "total": 29900, "deductions": 0,
                                                  "balanceDue": 29900, "paid": 29900, "pending": 0}]}})
        if path in ("/v1/automated-messages", "/v1/priority-mass-messages"):
            rows = [{("automatedMessageId" if "automated" in path else "priorityMassMessageId"): int(cid) * 10 + i, "employeeId": 70 + i, "status": "Completed",
                     "sentTime": str(_ms(datetime.combine(self.today - timedelta(days=i), datetime.min.time(), UTC))), "price": 1500,
                     "totalNumberOfTimeSent": 100, "totalNumberOfPurchases": 7, "totalRevenue": 10500,
                     ("collections" if "automated" in path else "collection"): ([{"messages": [{"messageContent": "hi"}]}] if "automated" in path else {"messages": [{"messageContent": "hey"}]})}
                    for i in range(3)]
            return self._page(rows, q, limit)
        if path in ("/v1/script-tag", "/v1/script-sequence"):
            return self._page([{"id": 1, "tagName": "Openers", "name": "Welcome"}], q, limit)
        if path.endswith("/statistics"):
            return self._json({"data": {"sendCount": 100, "payUsedCount": 20, "purchaseCount": 8, "revenueAmount": 12000}})
        return self._err(404, "not found")

    def _page(self, rows: list, q: dict, limit: int, extra: dict | None = None) -> httpx.Response:
        off = int((q.get("cursor") or ["0"])[0])
        chunk = rows[off: off + limit]
        more = off + limit < len(rows)
        return self._json({"data": {"platformCode": "OnlyFans", "list": chunk, **(extra or {})}, "cursor": str(off + limit) if more else None, "hasMore": more})

    @staticmethod
    def _json(body: dict, status: int = 200) -> httpx.Response:
        return httpx.Response(status, content=json.dumps(body), headers={"content-type": "application/json", "x-request-id": "req-test"})

    def _err(self, status: int, msg: str) -> httpx.Response:
        return self._json({"errorMessage": msg}, status)
