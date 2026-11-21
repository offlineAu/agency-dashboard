"""End-to-end: fake Infloww -> client -> sync -> analytics -> HTTP routes -> exports."""
from __future__ import annotations

import io
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.dates import today_utc
from tests.fake_infloww import KEY, OID


@pytest.fixture
def api(synced, db, client):
    from app.main import create_app
    app = create_app()
    app.state.db = db
    app.state.client = client
    with TestClient(app) as tc:
        synced.loop = app.state.sync.loop   # reuse the pre-synced engine on the server loop
        app.state.sync = synced
        yield tc


def q(days=30):
    end = today_utc()
    return {"start": (end - timedelta(days=days - 1)).isoformat(), "end": end.isoformat()}


def test_health(api):
    assert api.get("/api/health").json()["status"] == "ok"
    r = api.get("/api/health/infloww").json()
    assert r["status"] == "ok" and r["has_business_data"]


def test_overview_matches_analytics(api, synced):
    from app.analytics import revenue as R
    from app.analytics.common import Filters
    from datetime import date
    p = q()
    body = api.get("/api/dashboard/overview", params=p).json()
    t = R.totals(synced.db, Filters(date.fromisoformat(p["start"]), date.fromisoformat(p["end"])))
    assert body["kpis"]["revenue"]["current"]["gross"] == t["gross"]
    assert body["meta"]["complete"] is True and body["meta"]["period"]["timezone"] == "UTC"
    assert body["kpis"]["active_creators"] == 3
    assert len(body["trend"]) == 30


@pytest.mark.parametrize("path", ["/api/creators", "/api/employees", "/api/employees/matrix", "/api/fans", "/api/fans/top-spenders",
                                  "/api/campaigns", "/api/finance", "/api/messages", "/api/dashboard/revenue", "/api/status", "/api/meta",
                                  "/api/settings", "/api/creators/1000", "/api/employees/70", "/api/creators/compare?ids=1000,1001"])
def test_routes_ok(api, path):
    from urllib.parse import parse_qsl
    path, _, qs = path.partition("?")
    r = api.get(path, params={**q(), **dict(parse_qsl(qs))})
    assert r.status_code == 200, r.text
    assert KEY not in r.text and OID not in r.text


def test_bad_inputs_rejected(api):
    assert api.get("/api/creators", params={"start": "2026-02-01", "end": "2026-01-01"}).status_code == 400
    assert api.get("/api/creators", params={"creators": "1; DROP TABLE"}).status_code == 400
    assert api.get("/api/creators/abc").status_code == 400
    assert api.get("/api/creators", params={"basis": "profit"}).status_code == 422


@pytest.mark.parametrize("kind", ["daily", "weekly", "monthly", "creators", "employees", "fans", "campaigns", "revenue-sources"])
def test_exports(api, kind):
    j = api.get(f"/api/reports/{kind}", params=q()).json()
    assert j["rows"] is not None and any(h[0] == "Generated" for h in j["header"])
    csv_r = api.get(f"/api/reports/{kind}", params={**q(), "format": "csv"})
    assert csv_r.status_code == 200 and "Reporting period" in csv_r.text and "Definition" in csv_r.text
    x = api.get(f"/api/reports/{kind}", params={**q(), "format": "xlsx"})
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(x.content))
    assert wb.active.max_row > 5
    pdf = api.get(f"/api/reports/{kind}", params={**q(), "format": "pdf"})
    assert pdf.content[:4] == b"%PDF"


def test_daily_export_total_matches_dashboard(api):
    p = q()
    j = api.get("/api/reports/daily", params=p).json()
    ov = api.get("/api/dashboard/overview", params=p).json()
    assert j["totals"]["gross"] == ov["kpis"]["revenue"]["current"]["gross"]


def test_local_settings_and_costs(api):
    r = api.put("/api/settings/finance", json={"agency_commission_pct": 40, "chatter_commission_pct": 8, "commission_base": "net"})
    assert r.status_code == 200 and r.json()["agency_commission_pct"] == 40
    fin = api.get("/api/finance", params=q()).json()
    est = {e["key"]: e for e in fin["estimates"]}
    assert est["agency_commission"]["value"] == pytest.approx(fin["totals"]["current"]["net"] * 0.4)
    assert est["agency_commission"]["source"] == "estimate"
    r = api.put("/api/settings/campaign-costs/TRACKING/10000", json={"cost_cents": 50000, "spent_on": today_utc().isoformat()})
    assert r.status_code == 200
    camp = api.get("/api/campaigns", params=q()).json()
    link = next(i for i in camp["items"] if i["id"] == "10000")
    assert link["cost"] == 50000 and link["roi"] == pytest.approx((450000 - 50000) / 50000 * 100)
    assert api.put("/api/settings/fans", json={"vip_cents": 100, "high_value_cents": 500}).status_code == 400


def test_access_token_enforced(api, monkeypatch):
    monkeypatch.setenv("DASHBOARD_ACCESS_TOKEN", "s3cret-token")
    config.get_settings.cache_clear()
    assert api.get("/api/creators").status_code == 401
    assert api.get("/api/creators", headers={"X-Dashboard-Token": "nope"}).status_code == 401
    assert api.get("/api/creators", headers={"X-Dashboard-Token": "s3cret-token"}).status_code == 200
    assert api.get("/api/health").status_code == 200          # liveness stays open


def test_not_configured_reports_honestly(api, monkeypatch):
    monkeypatch.setenv("INFLOWW_API_KEY", "")
    config.get_settings.cache_clear()
    assert api.get("/api/health/infloww").json()["status"] == "not_configured"
    assert api.post("/api/sync", json={}).status_code == 409


def test_freshness_reports_previous_period_completeness(api):
    end = today_utc()
    # synced fixture covers 60 days; a 60-day window's previous period is NOT synced
    body = api.get("/api/dashboard/overview", params={"start": (end - timedelta(days=59)).isoformat(), "end": end.isoformat()}).json()
    assert body["meta"]["previous_complete"] is False
    assert body["kpis"]["revenue"]["growth"]["gross"]["value"] is None
    body = api.get("/api/dashboard/overview", params=q(14)).json()
    assert body["meta"]["previous_complete"] is True
    assert body["kpis"]["revenue"]["growth"]["gross"]["value"] is not None


def test_messages_request_never_waits_on_the_api(api):
    import time
    r = api.get("/api/messages", params=q(7)).json()
    assert r["meta"]["syncing"] is True          # kicked a background refresh, returned immediately
    for _ in range(100):
        r = api.get("/api/messages", params=q(7)).json()
        if not r["meta"]["syncing"]:
            break
        time.sleep(0.05)
    assert r["meta"]["syncing"] is False and r["errors"] == []


def test_script_stats_served_from_cache(api, fake, synced):
    cid = synced.creator_ids()[0]
    first = api.get(f"/api/creators/{cid}/scripts").json()
    n = len([c for c in fake.calls if "script" in c[1]])
    second = api.get(f"/api/creators/{cid}/scripts").json()
    assert first["available"] and second["fetched_at"] == first["fetched_at"]
    assert len([c for c in fake.calls if "script" in c[1]]) == n   # no new API calls


def test_marketing_not_syncing_because_of_unrelated_job(api, synced):
    import time
    from app.sync.engine import Job
    synced.jobs["busy"] = Job(key="busy", started=time.time(), datasets=["transactions"])  # unrelated, still running
    try:
        m = api.get("/api/campaigns", params=q()).json()["meta"]
        assert m["syncing"] is False and m["complete"] is True
        o = api.get("/api/dashboard/overview", params=q()).json()["meta"]
        assert o["syncing"] is True                  # overview does depend on transactions
    finally:
        synced.jobs.pop("busy")


def test_avatar_upload_validates_and_round_trips(api, synced):
    cid = synced.creator_ids()[0]
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    assert api.put(f"/api/avatars/creator/{cid}", content=b"<svg onload=alert(1)>").status_code == 415   # sniffed, not trusted
    assert api.put(f"/api/avatars/creator/{cid}", content=b"\xff\xd8\xff" + b"0" * (2 * 1024 * 1024)).status_code == 413
    assert api.put("/api/avatars/creator/../../etc", content=png).status_code >= 400
    assert api.put("/api/avatars/creator/abc", content=png).status_code == 400
    assert api.put(f"/api/avatars/fan/{cid}", content=png).status_code == 400
    assert api.put(f"/api/avatars/creator/{cid}", content=png).json()["ok"]
    r = api.get(f"/api/avatars/creator/{cid}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content == png
    assert f"creator:{cid}" in api.get("/api/meta").json()["avatars"]
    api.delete(f"/api/avatars/creator/{cid}")
    assert api.get(f"/api/avatars/creator/{cid}").status_code == 404
