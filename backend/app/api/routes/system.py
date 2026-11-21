"""Health, API monitoring, sync control and LOCAL settings.

Note: the write routes here (PUT settings / campaign costs, POST sync) only touch the local
database or trigger GET-only syncs. Nothing in this module can send a mutating request to Infloww.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.analytics import fans as F
from app.analytics import finance as FI
from app.api.deps import Auth
from app.api.routes.avatars import index as avatar_index
from app.core.config import get_settings
from app.core.dates import today_utc
from app.infloww.client import InflowwError
from app.infloww.registry import ENDPOINTS

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "time": time.time()}


@router.get("/auth/check", dependencies=[Auth])
def auth_check():
    return {"ok": True}


@router.get("/health/infloww", dependencies=[Auth])
async def infloww_health(request: Request):
    """Live probe: one tiny GET to /v1/creators. Verifies auth AND that business data comes back."""
    s = get_settings()
    if not s.configured:
        return {"status": "not_configured", "detail": "INFLOWW_API_KEY / INFLOWW_AGENCY_OID missing in backend environment"}
    t0 = time.perf_counter()
    try:
        body = await request.app.state.client.get("/v1/creators", {"platformCode": s.infloww_platform_code, "limit": 1})
    except InflowwError as e:
        return {"status": "error", "error": e.to_dict(), "ms": round((time.perf_counter() - t0) * 1000)}
    lst = (body.get("data") or {}).get("list")
    return {"status": "ok" if isinstance(lst, list) else "unexpected_shape", "ms": round((time.perf_counter() - t0) * 1000),
            "has_business_data": bool(lst), "has_more": body.get("hasMore")}


@router.get("/status", dependencies=[Auth])
def status(request: Request):
    s = get_settings()
    db = request.app.state.db
    eng = request.app.state.sync
    snap = request.app.state.monitor.snapshot()
    by_path = {e["path"]: e for e in snap["endpoints"]}
    endpoints = []
    for p, ep in ENDPOINTS.items():
        st = by_path.get(p, {})
        endpoints.append({"path": p, "category": ep.category, "window": ep.window.value, "latency_note": ep.latency_note, **st})
    end = today_utc()
    start = end - timedelta(days=s.default_lookback_days - 1)
    cids = eng.creator_ids()
    eids = [str(e) for e in eng.employee_ids()]
    coverage = [eng.coverage_summary(d, sc, start, end) for d, sc in
                (("transactions", cids), ("refunds", cids), ("creator_reports", cids), ("sales_records", eng.creator_ids(True)),
                 ("emp_sales", eids), ("emp_chat", eids))]
    oid = s.infloww_agency_oid
    return {
        "configured": s.configured,
        "fixture_mode": s.fixture_mode,
        "agency_oid": (oid[:4] + "…" + oid[-4:]) if len(oid) > 8 else ("set" if oid else None),
        "base_url": s.infloww_base_url,
        "array_style": s.infloww_array_style,
        "qpm_budget": s.infloww_qpm,
        "endpoints": endpoints,
        "recent_calls": snap["recent_calls"],
        "datasets": db.query("SELECT * FROM dataset_sync ORDER BY dataset, scope"),
        "coverage_default_window": {"start": start.isoformat(), "end": end.isoformat(), "items": coverage},
        "sync_errors": db.query("SELECT * FROM sync_errors ORDER BY ts DESC LIMIT 50"),
        "capabilities": eng.capabilities,
        "jobs": [vars(j) for j in sorted(eng.jobs.values(), key=lambda j: -j.started)][:10],
        "record_counts": {t: db.scalar(f"SELECT COUNT(*) FROM {t}") for t in
                          ("creators", "employees", "transactions", "refunds", "sales_records", "emp_sales_daily", "emp_chat_daily",
                           "creator_daily", "links", "messages", "invoices")},
        "unsupported_metrics": [
            {"metric": "Shift / clocked hours, revenue per hour", "reason": "Not exposed by the Infloww API"},
            {"metric": "Promotional spend (CPC, CPS, ROI)", "reason": "Not exposed; entered locally in Settings"},
            {"metric": "Per-fan subscription status / expiry", "reason": "No fan-list endpoint; only aggregate counts"},
            {"metric": "Chargebacks vs refunds", "reason": "Reversals ('undo') are not labelled by cause"},
            {"metric": "Agency commission / payroll", "reason": "Business rules not in API; configured locally"},
            {"metric": "History older than ~366 days", "reason": "API retention limit"},
        ],
        "server_time": time.time(),
    }


class SyncRequest(BaseModel):
    start: date | None = None
    end: date | None = None
    datasets: list[str] | None = None
    include_links: bool = True
    force_reference: bool = False


@router.post("/sync", dependencies=[Auth])
async def trigger_sync(body: SyncRequest, request: Request):
    s = get_settings()
    if not s.configured:
        raise HTTPException(409, "Infloww credentials not configured on the backend")
    eng = request.app.state.sync
    end = min(body.end or today_utc(), today_utc())
    start = body.start or end - timedelta(days=s.default_lookback_days - 1)
    if body.force_reference:
        await eng.sync_reference(force=True)
    job = eng.trigger(start, end, body.datasets, include_links=body.include_links)
    return vars(job)


# ------------------------------------------------------------------ local settings
class FinanceSettings(BaseModel):
    agency_commission_pct: float | None = Field(None, ge=0, le=100)
    chatter_commission_pct: float | None = Field(None, ge=0, le=100)
    other_monthly_costs_cents: int | None = Field(None, ge=0)
    commission_base: str = Field("net", pattern="^(net|gross)$")


class FanSettings(BaseModel):
    vip_cents: int = Field(F.DEFAULTS["vip_cents"], ge=0)
    high_value_cents: int = Field(F.DEFAULTS["high_value_cents"], ge=0)
    new_days: int = Field(F.DEFAULTS["new_days"], ge=1, le=180)
    at_risk_active_days: int = Field(F.DEFAULTS["at_risk_active_days"], ge=1, le=180)
    at_risk_lookback_days: int = Field(F.DEFAULTS["at_risk_lookback_days"], ge=2, le=365)


class CampaignCost(BaseModel):
    cost_cents: int = Field(..., ge=0)
    spent_on: date | None = None
    note: str | None = Field(None, max_length=200)


@router.get("/settings", dependencies=[Auth])
def get_local_settings(request: Request):
    db = request.app.state.db
    return {"finance": FI.local_settings(db), "fans": F.thresholds(db),
            "campaign_costs": db.query("SELECT * FROM campaign_costs ORDER BY updated_at DESC"),
            "note": "Local settings are stored in this dashboard's database only and are never sent to Infloww."}


@router.put("/settings/finance", dependencies=[Auth])
def put_finance(body: FinanceSettings, request: Request):
    db = request.app.state.db
    for k, v in body.model_dump().items():
        db.set_setting(f"finance.{k}", v)
    return FI.local_settings(db)


@router.put("/settings/fans", dependencies=[Auth])
def put_fans(body: FanSettings, request: Request):
    db = request.app.state.db
    if body.high_value_cents > body.vip_cents:
        raise HTTPException(400, "High-value threshold must not exceed VIP threshold")
    for k, v in body.model_dump().items():
        db.set_setting(f"fans.{k}", v)
    return F.thresholds(db)


@router.put("/settings/campaign-costs/{link_type}/{link_id}", dependencies=[Auth])
def put_cost(link_type: str, link_id: str, body: CampaignCost, request: Request):
    if link_type not in ("TRACKING", "TRIAL", "CAMPAIGN") or not link_id.isdigit():
        raise HTTPException(400, "invalid link")
    db = request.app.state.db
    with db.write() as c:
        c.execute("INSERT INTO campaign_costs VALUES (?,?,?,?,?,?) ON CONFLICT(link_type, link_id) DO UPDATE SET "
                  "cost_cents=excluded.cost_cents, spent_on=excluded.spent_on, note=excluded.note, updated_at=excluded.updated_at",
                  (link_type, link_id, body.cost_cents, body.spent_on.isoformat() if body.spent_on else None, body.note, time.time()))
    return {"ok": True}


@router.delete("/settings/campaign-costs/{link_type}/{link_id}", dependencies=[Auth])
def delete_cost(link_type: str, link_id: str, request: Request):
    with request.app.state.db.write() as c:
        c.execute("DELETE FROM campaign_costs WHERE link_type=? AND link_id=?", (link_type, link_id))
    return {"ok": True}


@router.get("/meta", dependencies=[Auth])
def meta(request: Request):
    db = request.app.state.db
    s = get_settings()
    return {
        "configured": s.configured,
        "fixture_mode": s.fixture_mode,
        "creators": db.query("SELECT id, name, user_name, connected, status FROM creators ORDER BY connected DESC, name"),
        "employees": db.query("SELECT employee_id, name, status FROM employees ORDER BY name"),
        "currency": db.scalar("SELECT currency FROM transactions WHERE currency IS NOT NULL GROUP BY currency ORDER BY COUNT(*) DESC LIMIT 1") or "USD",
        "today_utc": today_utc().isoformat(),
        "default_lookback_days": s.default_lookback_days,
        "syncing": bool(request.app.state.sync.running()),
        "avatars": avatar_index(),
        "alerts": db.scalar("SELECT COUNT(*) FROM dataset_sync WHERE status='error'") or 0,
    }
