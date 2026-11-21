"""Sync correctness + metric reconciliation against the raw (fake) API data."""
from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta

from app.analytics import creators as C
from app.analytics import employees as E
from app.analytics import fans as F
from app.analytics import marketing as M
from app.analytics import revenue as R
from app.analytics.common import Filters, growth
from app.core.dates import day_end_ms, day_start_ms, today_utc


def _raw_sum(fake, start: date, end: date, field="amount", statuses=("done", "loading"), types=None, creators=None):
    a, b = day_start_ms(start), day_end_ms(end)
    tot = 0
    for cid, rows in fake.tx.items():
        if creators and cid not in creators:
            continue
        for t in rows:
            if a <= int(t["createdTime"]) <= b and t["status"] in statuses and (types is None or t["type"] in types):
                tot += int(t[field])
    return tot


def test_windows_never_exceed_31_days(synced, fake):
    for m, path, q in fake.calls:
        if "startTime" in q and path not in ("/v1/invoice-data/monthly-billing",):
            st, et = q["startTime"][0], q["endTime"][0]
            if st.isdigit():
                assert int(et) - int(st) < 31 * 86400_000, (path, q)
            else:
                assert (date.fromisoformat(et) - date.fromisoformat(st)).days < 31, (path, q)


def test_coverage_complete_and_second_sync_is_noop(synced, fake):
    end = today_utc()
    start = end - timedelta(days=59)
    cov = synced.coverage_summary("transactions", synced.creator_ids(), start, end)
    assert cov["complete"] and cov["missing_days"] == 0
    n = len(fake.calls)
    units = synced.plan(["transactions", "refunds", "sales_records", "emp_sales", "emp_chat", "creator_reports"], start, end)
    assert units == []          # everything freshly covered
    asyncio.run(synced.run_units(units))
    assert len(fake.calls) == n


def test_unsettled_days_refetched_after_ttl(synced):
    end = today_utc()
    start = end - timedelta(days=59)
    with synced.db.write() as c:
        c.execute("UPDATE coverage SET fetched_at=fetched_at-?", (synced.s.recent_ttl_s + 5,))
    days = synced.stale_days("transactions", synced.creator_ids()[0], [end - timedelta(days=i) for i in range(60)])
    assert end in days                       # today is never settled
    assert (end - timedelta(days=10)) not in days  # old days settled long ago... only if fetched after settle time
    # older days were fetched "now-ttl" which is after their settle time -> settled, not refetched


def test_revenue_totals_reconcile_with_raw(synced, fake):
    end = today_utc()
    start = end - timedelta(days=29)
    t = R.totals(synced.db, Filters(start, end))
    assert t["gross"] == _raw_sum(fake, start, end)
    assert t["net"] == _raw_sum(fake, start, end, "net")
    assert t["reversed"] == _raw_sum(fake, start, end, statuses=("undo",))
    assert t["pending_return"] == _raw_sum(fake, start, end, statuses=("pending_return",))
    assert t["tips"] == _raw_sum(fake, start, end, types=("Tips",))
    assert t["subscription"] == _raw_sum(fake, start, end, types=("Subscription", "Recurring Subscription"))
    br = R.breakdown(synced.db, Filters(start, end))
    assert sum(b["gross"] for b in br) == t["gross"]          # no double counting across categories
    tr = R.trend(synced.db, Filters(start, end))
    assert len(tr) == 30 and sum(x["gross"] for x in tr) == t["gross"]
    wk = R.trend(synced.db, Filters(start, end), "week")
    assert sum(x["gross"] for x in wk) == t["gross"]


def test_creator_filter_and_net_basis(synced, fake):
    end = today_utc()
    start = end - timedelta(days=13)
    t = R.totals(synced.db, Filters(start, end, ("1001",), "net"))
    assert t["value"] == _raw_sum(fake, start, end, "net", creators={"1001"})
    rows = C.directory(synced.db, Filters(start, end, None, "net"))
    assert sum(r["revenue"] for r in rows) == _raw_sum(fake, start, end, "net")
    assert abs(sum(r["share_of_agency"] for r in rows) - 100) < 1e-6


def test_growth_handles_zero_baseline():
    assert growth(100, 0)["value"] is None and growth(100, 0)["reason"]
    assert growth(0, 0)["reason"] == "no activity in either period"
    assert growth(150, 100)["value"] == 50


def test_refunds_by_refund_date(synced, fake):
    end = today_utc()
    start = end - timedelta(days=59)
    t = R.totals(synced.db, Filters(start, end))
    expected = sum(r["paymentAmount"] for rows in fake.refunds.values() for r in rows
                   if day_start_ms(start) <= int(r["refundTime"]) <= day_end_ms(end))
    assert t["refunds"] == expected > 0


def test_employee_sales_are_only_infloww_attributed(synced, fake):
    end = today_utc()
    start = end - timedelta(days=6)
    lb = E.leaderboard(synced.db, Filters(start, end))
    by = {r["employee_id"]: r for r in lb}
    for eid, cids in fake.assign.items():
        assert by[eid]["sales"] == (10000 + eid * 10) * len(cids) * 7
        assert by[eid]["revenue_per_hour"] is None
    att = E.attribution(synced.db, Filters(start, end))
    assert att["unassigned_amount"] > 0 and 0 < att["attributed_share"] < 100
    # deleted creator's sales records are synced (transaction-perf supports all creators)
    assert synced.db.scalar("SELECT COUNT(*) FROM coverage WHERE dataset='sales_records' AND scope='1999'") > 0


def test_fan_segments_follow_thresholds(synced):
    end = today_utc()
    start = end - timedelta(days=29)
    res = F.analyze(synced.db, Filters(start, end))
    assert res["available"]
    th = res["thresholds"]
    for r in res["_rows"]:
        if r["lifetime"] >= th["vip_cents"]:
            assert r["segment"] == "VIP"
        elif r["lifetime"] >= th["high_value_cents"]:
            assert r["segment"] == "High Value"
        elif r["non_sub_spend"] > 0:
            assert r["segment"] == "Regular"
        else:
            assert r["segment"] == "Non-spender"
    # 60 days of history < 90-day lookback: At Risk must NOT be asserted without enough history
    assert not any(r["lifecycle"] == "At Risk" for r in res["_rows"])
    page = F.top_spenders(synced.db, Filters(start, end), 1, 10)
    assert len(page["items"]) == 10 and "•" in (page["items"][0]["fan_name"] or "•")


def test_marketing_formulas(synced):
    with synced.db.write() as c:
        c.execute("INSERT INTO campaign_costs VALUES ('TRACKING', '10001', 100000, '2026-01-01', 'test', ?)", (time.time(),))
    res = M.links(synced.db, ("1000",))
    link = next(i for i in res["items"] if i["id"] == "10001")
    assert link["clicks"] == 3200 and link["subscribers"] == 180 and link["earnings"] == 270000
    assert link["cpc"] == 100000 / 3200
    assert link["cps"] == 100000 / 180
    assert link["profit"] == 170000 and link["roi"] == 170.0
    other = next(i for i in res["items"] if i["id"] == "10000")
    assert other["cost"] is None and other["roi"] is None and other["cpc"] is None   # no cost => no fabricated ROI
    assert any("Instagram" in (u["name"] or "") for u in res["underperforming"])
    trial = next(i for i in res["items"] if i["link_type"] == "TRIAL")
    assert trial["clicks"] is None and trial["subscribers"] == 120


def test_failed_refetch_does_not_destroy_existing_rows(synced, fake):
    end = today_utc()
    before = synced.db.scalar("SELECT COUNT(*) FROM transactions WHERE creator_id='1000' AND day=?", (end.isoformat(),))
    with synced.db.write() as c:
        c.execute("UPDATE coverage SET fetched_at=0 WHERE dataset='transactions' AND scope='1000' AND day=?", (end.isoformat(),))
    fake.fail_next["/v1/transactions"] = [500, 500, 500, 500]
    errs = asyncio.run(synced.run_units(synced.plan(["transactions"], end, end, ["1000"])))
    assert errs and errs[0]["kind"] == "server"
    after = synced.db.scalar("SELECT COUNT(*) FROM transactions WHERE creator_id='1000' AND day=?", (end.isoformat(),))
    assert after == before


def test_forbidden_scope_marks_capability(engine, fake):
    fake.forbidden.add("/v1/all-creators")
    asyncio.run(engine.sync_reference())
    assert engine.capabilities["all_creators"]["available"] is False
    assert engine.creator_ids()   # connected creators still synced


def test_missing_values_stay_null(engine, db):
    from app.infloww.normalize import emp_chat_row, to_int
    assert to_int(None) is None and to_int("") is None
    row = emp_chat_row({"employeeId": 1, "date": "2026-01-01", "platformPid": 2})
    assert row[3] is None and row[11] is None


def test_growth_withheld_when_previous_period_not_synced(engine, fake):
    """Regression: an unsynced previous period must not be treated as $0 ('new vs zero' / bogus growth)."""
    end = today_utc()
    start = end - timedelta(days=6)
    asyncio.run(engine.ensure(start, end, ["transactions", "refunds"]))   # current period only
    res = R.with_comparison(engine.db, Filters(start, end), prev_ok=False)
    assert all(g["value"] is None and "not fully synced" in g["reason"] for g in res["growth"].values())
    ps = start - timedelta(days=7)
    cov = engine.coverage_summary("transactions", engine.creator_ids(), ps, start - timedelta(days=1))
    assert not cov["complete"]
