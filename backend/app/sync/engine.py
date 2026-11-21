"""Sync engine: pulls Infloww data into the local store with exact coverage tracking.

Rules
  * A (dataset, scope, UTC day) is fetched when it has no coverage, or when it is not yet "settled"
    (fetched less than `settled_after_h` after the day ended) and the last fetch is older than `recent_ttl_s`.
  * Days are fetched in contiguous runs of <= 31 days (API limit) and clamped to the API's history limit.
  * Rows for a run are replaced in ONE transaction, only after the run (all pages) succeeded.
  * One failing dataset/creator never aborts the others; failures are recorded for the API Status page.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from app.core.config import Settings
from app.core.dates import UTC, contiguous_runs, day_end_ms, day_start_ms, days_between, today_utc, window_end_ms
from app.infloww import normalize as N
from app.infloww.client import InflowwClient, InflowwError
from app.infloww.registry import MAX_HISTORY_DAYS, MAX_REPORT_IDS
from app.store.db import Database

log = logging.getLogger("sync")

WINDOWED = ("transactions", "refunds", "sales_records", "emp_sales", "emp_chat", "creator_reports")
REFERENCE_TTL_S = 3600
LINKS_TTL_S = 3600
SCRIPT_TTL_S = 3600
INVOICE_TTL_S = 6 * 3600
LINK_TYPES = ("TRACKING", "TRIAL", "CAMPAIGN")


@dataclass
class Job:
    key: str
    started: float
    datasets: list[str]
    start: str | None = None
    end: str | None = None
    done: int = 0
    total: int = 0
    finished: float | None = None
    errors: list[dict] = field(default_factory=list)
    links: bool = False


class SyncEngine:
    def __init__(self, db: Database, client: InflowwClient, settings: Settings):
        self.db = db
        self.client = client
        self.s = settings
        self.jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._ref_lock = asyncio.Lock()
        self.capabilities: dict[str, dict] = {}   # dataset -> {"available": bool, "reason": str}
        self.loop: asyncio.AbstractEventLoop | None = None
        self._script_cache: dict[str, dict] = {}
        self._script_tasks: dict[str, asyncio.Future] = {}
        self._msg_task: asyncio.Future | None = None
        self.message_errors: list[dict] = []

    # ------------------------------------------------------------------ bookkeeping
    def _mark_capability(self, dataset: str, err: InflowwError | None) -> None:
        if err is None:
            self.capabilities[dataset] = {"available": True, "reason": None, "checked": time.time()}
        elif err.kind == "forbidden":
            self.capabilities[dataset] = {"available": False, "reason": f"403 Forbidden — API key scope does not include this data ({err})", "checked": time.time()}

    def _record_error(self, dataset: str, scope: str, err: Exception) -> dict:
        kind = getattr(err, "kind", "internal")
        e = {"ts": time.time(), "dataset": dataset, "scope": scope, "kind": kind, "message": str(err)[:400]}
        with self.db.write() as c:
            c.execute("INSERT INTO sync_errors VALUES (?,?,?,?,?)", (e["ts"], dataset, scope, kind, e["message"]))
            c.execute("DELETE FROM sync_errors WHERE ts < ?", (time.time() - 7 * 86400,))
        if isinstance(err, InflowwError):
            self._mark_capability(dataset, err)
        log.warning("sync %s/%s failed: %s", dataset, scope, err)
        return e

    def _dataset_fresh(self, dataset: str, scope: str, ttl: float) -> bool:
        row = self.db.one("SELECT fetched_at, status FROM dataset_sync WHERE dataset=? AND scope=?", (dataset, scope))
        return bool(row and row["status"] == "ok" and time.time() - row["fetched_at"] < ttl)

    def _set_dataset(self, c, dataset: str, scope: str, status: str, records: int | None = None, error: str | None = None) -> None:
        c.execute(
            "INSERT INTO dataset_sync VALUES (?,?,?,?,?,?) ON CONFLICT(dataset,scope) DO UPDATE SET "
            "fetched_at=CASE WHEN excluded.status='ok' THEN excluded.fetched_at ELSE dataset_sync.fetched_at END, "
            "status=excluded.status, error=excluded.error, records=COALESCE(excluded.records, dataset_sync.records)",
            (dataset, scope, time.time(), status, error, records),
        )

    def stale_days(self, dataset: str, scope: str, days: list[date]) -> list[date]:
        if not days:
            return []
        rows = self.db.query(
            "SELECT day, fetched_at FROM coverage WHERE dataset=? AND scope=? AND day BETWEEN ? AND ?",
            (dataset, scope, min(days).isoformat(), max(days).isoformat()),
        )
        cov = {r["day"]: r["fetched_at"] for r in rows}
        now = time.time()
        out = []
        for d in days:
            f = cov.get(d.isoformat())
            if f is None:
                out.append(d)
                continue
            settled_at = day_end_ms(d) / 1000 + self.s.settled_after_h * 3600
            if f < settled_at and now - f > self.s.recent_ttl_s:
                out.append(d)
        return out

    def coverage_summary(self, dataset: str, scopes: list[str], start: date, end: date) -> dict:
        days = self._clamp(dataset, days_between(start, end))
        if not scopes or not days:
            return {"dataset": dataset, "complete": not scopes, "missing_days": 0, "expected": 0, "oldest_fetch": None, "newest_fetch": None}
        q = ",".join("?" * len(scopes))
        rows = self.db.query(
            f"SELECT COUNT(*) n, MIN(fetched_at) oldest, MAX(fetched_at) newest FROM coverage "
            f"WHERE dataset=? AND scope IN ({q}) AND day BETWEEN ? AND ?",
            (dataset, *scopes, days[0].isoformat(), days[-1].isoformat()),
        )[0]
        expected = len(days) * len(scopes)
        return {
            "dataset": dataset, "complete": rows["n"] >= expected, "covered": rows["n"], "expected": expected,
            "missing_days": expected - rows["n"], "oldest_fetch": rows["oldest"], "newest_fetch": rows["newest"],
            "clamped_start": days[0].isoformat(), "requested_start": start.isoformat(),
        }

    def _clamp(self, dataset: str, days: list[date]) -> list[date]:
        earliest = today_utc() - timedelta(days=MAX_HISTORY_DAYS - 1)
        return [d for d in days if earliest <= d <= today_utc()]

    # ------------------------------------------------------------------ reference data
    def creator_ids(self, include_disconnected: bool = False) -> list[str]:
        sql = "SELECT id FROM creators" + ("" if include_disconnected else " WHERE connected=1") + " ORDER BY name"
        return [r["id"] for r in self.db.query(sql)]

    def employee_ids(self) -> list[int]:
        return [r["employee_id"] for r in self.db.query("SELECT employee_id FROM employees ORDER BY employee_id")]

    async def sync_reference(self, force: bool = False) -> list[dict]:
        errors: list[dict] = []
        async with self._ref_lock:
            now = time.time()
            if force or not self._dataset_fresh("creators", "agency", REFERENCE_TTL_S):
                try:
                    items = await self.client.paginate("/v1/creators", {"platformCode": self.s.infloww_platform_code})
                    rows = [N.creator_row(c, True, now) for c in items if c.get("id") is not None]
                    with self.db.write() as c:
                        c.execute("UPDATE creators SET connected=0")
                        c.executemany(
                            "INSERT INTO creators VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                            "platform_pid=excluded.platform_pid, name=excluded.name, nick_name=excluded.nick_name, user_name=excluded.user_name, "
                            "tag_name=excluded.tag_name, connected=1, status=COALESCE(creators.status, excluded.status), created_ms=excluded.created_ms, fetched_at=excluded.fetched_at",
                            rows,
                        )
                        self._set_dataset(c, "creators", "agency", "ok", len(rows))
                    self._mark_capability("creators", None)
                except Exception as e:
                    errors.append(self._record_error("creators", "agency", e))
                    with self.db.write() as c:
                        self._set_dataset(c, "creators", "agency", "error", error=str(e)[:300])

            if force or not self._dataset_fresh("all_creators", "agency", REFERENCE_TTL_S):
                try:
                    items = await self.client.paginate("/v1/all-creators", {"platformCode": self.s.infloww_platform_code})
                    with self.db.write() as c:
                        for it in items:
                            if it.get("id") is None:
                                continue
                            status = it.get("status")
                            c.execute(
                                "INSERT INTO creators VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                                "status=excluded.status, deleted_ms=excluded.deleted_ms, platform_pid=COALESCE(creators.platform_pid, excluded.platform_pid), "
                                "name=COALESCE(creators.name, excluded.name)",
                                N.creator_row(it, status == "connected", now),
                            )
                        self._set_dataset(c, "all_creators", "agency", "ok", len(items))
                    self._mark_capability("all_creators", None)
                except Exception as e:
                    errors.append(self._record_error("all_creators", "agency", e))
                    with self.db.write() as c:
                        self._set_dataset(c, "all_creators", "agency", "error", error=str(e)[:300])

            if force or not self._dataset_fresh("employees", "agency", REFERENCE_TTL_S):
                try:
                    items = await self.client.paginate("/v1/employees", {})
                    rows = [(N.to_int(e.get("employeeId")), e.get("employeeName"), e.get("status"), N.to_int(e.get("createdTime")),
                             N.to_int(e.get("deletedTime")), now) for e in items if e.get("employeeId") is not None]
                    with self.db.write() as c:
                        c.execute("DELETE FROM employees")
                        c.executemany("INSERT INTO employees VALUES (?,?,?,?,?,?)", rows)
                        self._set_dataset(c, "employees", "agency", "ok", len(rows))
                    self._mark_capability("employees", None)
                except Exception as e:
                    errors.append(self._record_error("employees", "agency", e))
                    with self.db.write() as c:
                        self._set_dataset(c, "employees", "agency", "error", error=str(e)[:300])

            if force or not self._dataset_fresh("assignments", "agency", REFERENCE_TTL_S):
                emp_ids = self.employee_ids()

                async def one(eid: int):
                    items = await self.client.paginate("/v1/employees/assigned-creators", {"employeeId": eid})
                    return eid, [str(i.get("creatorId")) for i in items if i.get("creatorId") is not None]

                results = await asyncio.gather(*(one(e) for e in emp_ids), return_exceptions=True)
                ok = [r for r in results if not isinstance(r, Exception)]
                for eid, r in zip(emp_ids, results):
                    if isinstance(r, Exception):
                        errors.append(self._record_error("assignments", str(eid), r))
                with self.db.write() as c:
                    for eid, cids in ok:
                        c.execute("DELETE FROM employee_creators WHERE employee_id=?", (eid,))
                        c.executemany("INSERT OR IGNORE INTO employee_creators VALUES (?,?)", [(eid, cid) for cid in cids])
                    self._set_dataset(c, "assignments", "agency", "ok" if len(ok) == len(emp_ids) else "partial", sum(len(x[1]) for x in ok))
        return errors

    # ------------------------------------------------------------------ windowed datasets
    async def _sync_creator_window(self, dataset: str, path: str, creator_id: str, run: tuple[date, date]) -> int:
        a, b = run
        params = {"platformCode": self.s.infloww_platform_code, "creatorId": creator_id,
                  "startTime": day_start_ms(a), "endTime": window_end_ms(b)}
        items = await self.client.paginate(path, params)
        if dataset == "transactions":
            rows = [r for r in (N.transaction_row(t, creator_id) for t in items) if r]
            table, ncols, daycol = "transactions", 15, "day"
        elif dataset == "refunds":
            rows = [r for r in (N.refund_row(t, creator_id) for t in items) if r]
            table, ncols, daycol = "refunds", 11, "day"
        else:
            rows = [r for r in (N.sales_record_row(t, creator_id) for t in items) if r]
            table, ncols, daycol = "sales_records", 17, "day"
        now = time.time()
        with self.db.write() as c:
            c.execute(f"DELETE FROM {table} WHERE creator_id=? AND {daycol} BETWEEN ? AND ?", (creator_id, a.isoformat(), b.isoformat()))
            c.executemany(f"INSERT OR REPLACE INTO {table} VALUES ({','.join('?' * ncols)})", rows)
            c.executemany("INSERT OR REPLACE INTO coverage VALUES (?,?,?,?)",
                          [(dataset, creator_id, d.isoformat(), now) for d in days_between(a, b)])
        return len(rows)

    async def _sync_employee_report(self, dataset: str, emp_batch: list[int], run: tuple[date, date]) -> int:
        a, b = run
        path = "/v1/employee-report/employee-sales-summary" if dataset == "emp_sales" else "/v1/employee-report/employee-chat-summary"
        body = await self.client.get(path, {"platformCode": self.s.infloww_platform_code, "employeeIds": emp_batch,
                                            "startTime": a.isoformat(), "endTime": b.isoformat()})
        items = (body.get("data") or {}).get("list") or []
        if body.get("hasMore"):
            # Not documented as paginated, but be safe: follow cursor if present.
            items = await self._follow(path, {"platformCode": self.s.infloww_platform_code, "employeeIds": emp_batch,
                                              "startTime": a.isoformat(), "endTime": b.isoformat()}, body)
        table = "emp_sales_daily" if dataset == "emp_sales" else "emp_chat_daily"
        rows = [N.emp_sales_row(r) if dataset == "emp_sales" else N.emp_chat_row(r) for r in items]
        rows = [r for r in rows if r[0] is not None and r[1]]
        now = time.time()
        q = ",".join("?" * len(emp_batch))
        with self.db.write() as c:
            c.execute(f"DELETE FROM {table} WHERE employee_id IN ({q}) AND day BETWEEN ? AND ?", (*emp_batch, a.isoformat(), b.isoformat()))
            if rows:
                c.executemany(f"INSERT OR REPLACE INTO {table} VALUES ({','.join('?' * len(rows[0]))})", rows)
            c.executemany("INSERT OR REPLACE INTO coverage VALUES (?,?,?,?)",
                          [(dataset, str(e), d.isoformat(), now) for e in emp_batch for d in days_between(a, b)])
        return len(rows)

    async def _follow(self, path: str, params: dict, first: dict) -> list[dict]:
        items = list((first.get("data") or {}).get("list") or [])
        cursor, more, guard = first.get("cursor"), first.get("hasMore"), 0
        while more and cursor and guard < 500:
            body = await self.client.get(path, {**params, "cursor": cursor})
            items.extend((body.get("data") or {}).get("list") or [])
            cursor, more, guard = body.get("cursor"), body.get("hasMore"), guard + 1
        return items

    async def _sync_creator_reports(self, creator_batch: list[str], run: tuple[date, date]) -> int:
        a, b = run
        pid_rows = self.db.query(f"SELECT id, platform_pid FROM creators WHERE id IN ({','.join('?' * len(creator_batch))})", creator_batch)
        pids = [r["platform_pid"] for r in pid_rows if r["platform_pid"] is not None]
        total = 0
        collected: list[tuple] = []
        for path, fields in N.CREATOR_REPORTS.items():
            body = await self.client.get(path, {"platformCode": self.s.infloww_platform_code, "creatorIds": creator_batch,
                                                "startTime": a.isoformat(), "endTime": b.isoformat()})
            for r in (body.get("data") or {}).get("list") or []:
                collected.extend(N.creator_daily_rows(r, fields))
        now = time.time()
        with self.db.write() as c:
            if pids:
                c.execute(f"DELETE FROM creator_daily WHERE platform_pid IN ({','.join('?' * len(pids))}) AND day BETWEEN ? AND ?",
                          (*pids, a.isoformat(), b.isoformat()))
            c.executemany("INSERT OR REPLACE INTO creator_daily VALUES (?,?,?,?)", collected)
            c.executemany("INSERT OR REPLACE INTO coverage VALUES (?,?,?,?)",
                          [("creator_reports", cid, d.isoformat(), now) for cid in creator_batch for d in days_between(a, b)])
        total += len(collected)
        return total

    def plan(self, datasets: list[str], start: date, end: date, creator_ids: list[str] | None = None) -> list[tuple]:
        """Return a list of work units (dataset, scope(s), run)."""
        days_all = days_between(start, end)
        creators = creator_ids or self.creator_ids()
        all_creators = creator_ids or self.creator_ids(include_disconnected=True)
        emps = self.employee_ids()
        units: list[tuple] = []
        for ds in datasets:
            days = self._clamp(ds, days_all)
            if ds in ("transactions", "refunds"):
                for cid in creators:
                    for run in contiguous_runs(self.stale_days(ds, cid, days)):
                        units.append((ds, cid, run))
            elif ds == "sales_records":
                for cid in all_creators:
                    for run in contiguous_runs(self.stale_days(ds, cid, days)):
                        units.append((ds, cid, run))
            elif ds in ("emp_sales", "emp_chat"):
                for i in range(0, len(emps), MAX_REPORT_IDS):
                    batch = emps[i:i + MAX_REPORT_IDS]
                    stale = sorted({d for e in batch for d in self.stale_days(ds, str(e), days)})
                    for run in contiguous_runs(stale):
                        units.append((ds, batch, run))
            elif ds == "creator_reports":
                for i in range(0, len(creators), MAX_REPORT_IDS):
                    batch = creators[i:i + MAX_REPORT_IDS]
                    stale = sorted({d for c in batch for d in self.stale_days(ds, c, days)})
                    for run in contiguous_runs(stale):
                        units.append((ds, batch, run))
        return units

    async def run_units(self, units: list[tuple], job: Job | None = None) -> list[dict]:
        errors: list[dict] = []
        paths = {"transactions": "/v1/transactions", "refunds": "/v1/refunds", "sales_records": "/v1/transaction-perf/details"}

        async def do(unit):
            ds, scope, run = unit
            try:
                if ds in paths:
                    await self._sync_creator_window(ds, paths[ds], scope, run)
                elif ds in ("emp_sales", "emp_chat"):
                    await self._sync_employee_report(ds, scope, run)
                elif ds == "creator_reports":
                    await self._sync_creator_reports(scope, run)
                self._mark_capability(ds, None)
            except Exception as e:  # noqa: BLE001 — isolate failures per unit
                errors.append(self._record_error(ds, str(scope), e))
            finally:
                if job:
                    job.done += 1

        await asyncio.gather(*(do(u) for u in units))
        return errors

    async def ensure(self, start: date, end: date, datasets: list[str] | None = None, creator_ids: list[str] | None = None) -> list[dict]:
        errors = await self.sync_reference()
        units = self.plan(datasets or list(WINDOWED), start, end, creator_ids)
        return errors + await self.run_units(units)

    # ------------------------------------------------------------------ non-windowed datasets
    async def sync_links(self, creator_ids: list[str] | None = None, force: bool = False) -> list[dict]:
        errors: list[dict] = []
        creators = creator_ids or self.creator_ids()
        end = today_utc()
        start = end - timedelta(days=self.s.link_lookback_days - 1)
        runs = contiguous_runs(days_between(start, end))

        async def one(cid: str, lt: str):
            scope = f"{cid}:{lt}"
            if not force and self._dataset_fresh("links", scope, LINKS_TTL_S):
                return
            try:
                items: list[dict] = []
                for a, b in runs:
                    items += await self.client.paginate("/v1/links", {
                        "platformCode": self.s.infloww_platform_code, "creatorId": cid, "linkType": lt,
                        "startTime": day_start_ms(a), "endTime": window_end_ms(b)})
                now = time.time()
                rows = {(lt, str(i.get("id"))): N.link_row(i, lt, cid, now) for i in items if i.get("id") is not None}
                with self.db.write() as c:
                    c.execute("DELETE FROM links WHERE creator_id=? AND link_type=?", (cid, lt))
                    c.executemany(f"INSERT OR REPLACE INTO links VALUES ({','.join('?' * 29)})", list(rows.values()))
                    self._set_dataset(c, "links", scope, "ok", len(rows))
                self._mark_capability("links", None)
            except Exception as e:  # noqa: BLE001
                errors.append(self._record_error("links", scope, e))
                with self.db.write() as c:
                    self._set_dataset(c, "links", scope, "error", error=str(e)[:300])

        await asyncio.gather(*(one(c, lt) for c in creators for lt in LINK_TYPES))
        return errors

    async def sync_invoices(self, force: bool = False) -> list[dict]:
        if not force and self._dataset_fresh("invoices", "agency", INVOICE_TTL_S):
            return []
        end = today_utc().replace(day=1)
        start = (end - timedelta(days=330)).replace(day=1)
        try:
            body = await self.client.get("/v1/invoice-data/monthly-billing",
                                         {"startTime": start.strftime("%Y-%m"), "endTime": end.strftime("%Y-%m")})
            now = time.time()
            rows = [N.invoice_row(i, now) for i in (body.get("data") or {}).get("list") or []]
            with self.db.write() as c:
                c.executemany(f"INSERT OR REPLACE INTO invoices VALUES ({','.join('?' * 13)})", rows)
                self._set_dataset(c, "invoices", "agency", "ok", len(rows))
            self._mark_capability("invoices", None)
            return []
        except Exception as e:  # noqa: BLE001
            with self.db.write() as c:
                self._set_dataset(c, "invoices", "agency", "error", error=str(e)[:300])
            return [self._record_error("invoices", "agency", e)]

    async def sync_messages(self, start: date, end: date, creator_ids: list[str] | None = None) -> list[dict]:
        errors: list[dict] = []
        creators = creator_ids or self.creator_ids()
        days = self._clamp("messages", days_between(start, end))
        kinds = {"automated": "/v1/automated-messages", "priority_mass": "/v1/priority-mass-messages"}

        async def one(kind: str, cid: str, run: tuple[date, date]):
            a, b = run
            try:
                items = await self.client.paginate(kinds[kind], {"platformCode": self.s.infloww_platform_code, "creatorId": cid,
                                                                 "startTime": day_start_ms(a), "endTime": window_end_ms(b)})
                rows = [r for r in (N.message_rows(m, kind, cid) for m in items) if r]
                now = time.time()
                with self.db.write() as c:
                    c.execute("DELETE FROM messages WHERE kind=? AND creator_id=? AND day BETWEEN ? AND ?", (kind, cid, a.isoformat(), b.isoformat()))
                    c.executemany(f"INSERT OR REPLACE INTO messages VALUES ({','.join('?' * 13)})", rows)
                    c.executemany("INSERT OR REPLACE INTO coverage VALUES (?,?,?,?)",
                                  [(f"messages_{kind}", cid, d.isoformat(), now) for d in days_between(a, b)])
                self._mark_capability(f"messages_{kind}", None)
            except Exception as e:  # noqa: BLE001
                errors.append(self._record_error(f"messages_{kind}", cid, e))

        tasks = [one(k, c, run) for k in kinds for c in creators
                 for run in contiguous_runs(self.stale_days(f"messages_{k}", c, days))]
        await asyncio.gather(*tasks)
        return errors

    def refresh_messages(self, start: date, end: date, creator_ids: list[str] | None = None) -> bool:
        """Kick a background message sync if any day in range is stale. Returns True while one is running,
        so the request never waits on the API (cached rows are served meanwhile)."""
        t = self._msg_task
        if t is not None and not t.done():
            return True
        creators = creator_ids or self.creator_ids()
        days = self._clamp("messages", days_between(start, end))
        if not any(self.stale_days(f"messages_{k}", c, days) for k in ("automated", "priority_mass") for c in creators):
            return False

        async def run():
            self.message_errors = (self.message_errors + await self.sync_messages(start, end, creator_ids))[-50:]
        self._msg_task = asyncio.ensure_future(run())
        return True

    async def creator_chat_summary(self, creator_ids: list[str], start: date, end: date) -> list[dict]:
        """chat-summary has no date dimension, so it is fetched per requested range (<=31 days per call, summed)."""
        days = self._clamp("chat", days_between(start, end))
        if not days or not creator_ids:
            return []
        out: dict[int, dict] = {}
        for i in range(0, len(creator_ids), MAX_REPORT_IDS):
            batch = creator_ids[i:i + MAX_REPORT_IDS]
            for a, b in contiguous_runs(days):
                body = await self.client.get("/v1/creator-report/chat-summary", {
                    "platformCode": self.s.infloww_platform_code, "creatorIds": batch, "startTime": a.isoformat(), "endTime": b.isoformat()})
                for r in (body.get("data") or {}).get("list") or []:
                    pid = N.to_int(r.get("platformPid"))
                    if pid is None:
                        continue
                    o = out.setdefault(pid, {"platform_pid": pid, "messages_sent": 0, "ppvs_sent": 0, "fans_chatted_sum": 0,
                                             "_reply_weighted": 0.0, "_reply_w": 0})
                    ms = N.to_int(r.get("messagesSent")) or 0
                    o["messages_sent"] += ms
                    o["ppvs_sent"] += N.to_int(r.get("ppvsSent")) or 0
                    o["fans_chatted_sum"] += N.to_int(r.get("fansChatted")) or 0
                    rt = N.to_int(r.get("replyTime"))
                    if rt is not None:
                        o["_reply_weighted"] += rt * max(ms, 1)
                        o["_reply_w"] += max(ms, 1)
        res = []
        for o in out.values():
            o["reply_ms"] = o["_reply_weighted"] / o["_reply_w"] if o["_reply_w"] else None
            o.pop("_reply_weighted"); o.pop("_reply_w")
            res.append(o)
        return res

    async def script_stats(self, creator_id: str) -> dict:
        tags = await self.client.paginate("/v1/script-tag", {"platformCode": self.s.infloww_platform_code, "creatorId": creator_id})
        seqs = await self.client.paginate("/v1/script-sequence", {"platformCode": self.s.infloww_platform_code, "creatorId": creator_id})

        async def stat(path, key, i):
            body = await self.client.get(path, {"platformCode": self.s.infloww_platform_code, "creatorId": creator_id, key: i["id"]})
            return body.get("data") or {}

        stats = await asyncio.gather(*(stat("/v1/script-tag/statistics", "tagId", t) for t in tags),
                                     *(stat("/v1/script-sequence/statistics", "sequenceId", s) for s in seqs), return_exceptions=True)
        tag_stats, seq_stats = stats[:len(tags)], stats[len(tags):]

        def merge(items, stats, name_key):
            out = []
            for it, st in zip(items, stats):
                row = {"id": it.get("id"), "name": it.get(name_key)}
                if isinstance(st, Exception):
                    row["error"] = str(st)
                else:
                    row.update({"send_count": N.to_int(st.get("sendCount")), "paid_sends": N.to_int(st.get("payUsedCount")),
                                "purchases": N.to_int(st.get("purchaseCount")), "revenue": N.to_int(st.get("revenueAmount"))})
                out.append(row)
            return out

        return {"tags": merge(tags, tag_stats, "tagName"), "sequences": merge(seqs, seq_stats, "name"), "fetched_at": time.time()}

    async def script_stats_cached(self, creator_id: str) -> dict:
        """Script stats are all-time and cost one API call per tag/sequence, so serve them from a
        server-side cache: fresh (<1h) -> instant; stale -> instant + refresh in background; none -> fetch."""
        hit = self._script_cache.get(creator_id)
        if hit and time.time() - hit["fetched_at"] < SCRIPT_TTL_S:
            return hit
        if hit:
            self._refresh_scripts(creator_id)
            return {**hit, "refreshing": True}
        return await self._refresh_scripts(creator_id)

    def _refresh_scripts(self, creator_id: str) -> "asyncio.Future[dict]":
        task = self._script_tasks.get(creator_id)
        if task is None or task.done():
            async def run() -> dict:
                data = await self.script_stats(creator_id)
                self._script_cache[creator_id] = data
                return data
            task = asyncio.ensure_future(run())
            self._script_tasks[creator_id] = task
        return task

    async def warm_scripts(self) -> None:
        for cid in self.creator_ids():
            hit = self._script_cache.get(cid)
            if hit and time.time() - hit["fetched_at"] < SCRIPT_TTL_S:
                continue
            try:
                await self._refresh_scripts(cid)
            except Exception as e:  # noqa: BLE001
                self._record_error("scripts", cid, e)

    # ------------------------------------------------------------------ background jobs
    def trigger(self, start: date, end: date, datasets: list[str] | None = None, include_links: bool = False) -> Job:
        key = f"{start}:{end}:{','.join(sorted(WINDOWED if datasets is None else datasets))}:{include_links}"
        existing = self.jobs.get(key)
        if existing and existing.finished is None:
            return existing
        job = Job(key=key, started=time.time(), datasets=list(WINDOWED if datasets is None else datasets), start=start.isoformat(),
                  end=end.isoformat(), links=include_links)
        self.jobs[key] = job

        async def runner():
            try:
                job.errors += await self.sync_reference()
                units = self.plan(job.datasets, start, end)
                job.total = len(units) + (1 if include_links else 0)
                job.errors += await self.run_units(units, job)
                if include_links:
                    job.errors += await self.sync_links()
                    job.errors += await self.sync_invoices()
                    job.done += 1
            except Exception as e:  # noqa: BLE001
                job.errors.append(self._record_error("job", key, e))
            finally:
                job.finished = time.time()
                # keep only recent jobs
                for k in [k for k, j in self.jobs.items() if j.finished and time.time() - j.finished > 3600]:
                    self.jobs.pop(k, None)

        try:
            asyncio.get_running_loop()
            self._tasks[key] = asyncio.create_task(runner())
        except RuntimeError:
            # Called from a worker thread (sync FastAPI route): schedule onto the server loop.
            if self.loop is None:
                job.finished = time.time()
                job.errors.append({"kind": "internal", "message": "sync loop not running"})
                return job
            self._tasks[key] = asyncio.run_coroutine_threadsafe(runner(), self.loop)  # type: ignore[assignment]
        return job

    def running(self) -> list[Job]:
        return [j for j in self.jobs.values() if j.finished is None]

    def syncing(self, datasets: list[str] | None = None, links: bool = False) -> bool:
        """True only while a job that touches these datasets (or links) is running, so a page doesn't
        show "Syncing…" because some unrelated background job is busy."""
        want = set(datasets or [])
        return any((links and j.links) or (want & set(j.datasets)) for j in self.running())

    def links_stale(self, creator_ids: list[str] | None = None) -> bool:
        return any(not self._dataset_fresh("links", f"{c}:{lt}", LINKS_TTL_S)
                   for c in (creator_ids or self.creator_ids()) for lt in LINK_TYPES)

    def needs_sync(self, datasets: list[str], start: date, end: date) -> bool:
        if not self._dataset_fresh("creators", "agency", REFERENCE_TTL_S):
            return True
        return bool(self.plan(datasets, start, end))

    async def background_loop(self) -> None:
        await asyncio.sleep(2)
        while True:
            if self.s.configured:
                end = today_utc()
                start = end - timedelta(days=self.s.default_lookback_days - 1)
                job = self.trigger(start, end, include_links=True)
                while job.finished is None:
                    await asyncio.sleep(5)
                # fan history (transactions only) for LTV / segmentation
                hstart = end - timedelta(days=self.s.fan_history_days - 1)
                job = self.trigger(hstart, end, ["transactions"])
                while job.finished is None:
                    await asyncio.sleep(5)
                await self.warm_scripts()
            await asyncio.sleep(self.s.background_interval_s)
