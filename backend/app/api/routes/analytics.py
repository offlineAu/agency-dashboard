"""Dashboard data routes (internal API consumed by the frontend). Read-only with respect to Infloww."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.analytics import creators as C
from app.analytics import employees as E
from app.analytics import fans as F
from app.analytics import finance as FI
from app.analytics import marketing as M
from app.analytics import messages as MS
from app.analytics import revenue as R
from app.analytics.common import Filters
from app.api.deps import Auth, freshness, parse_filters, prev_ok
from app.infloww.client import InflowwError

router = APIRouter(prefix="/api", dependencies=[Auth])

REV = ["transactions", "refunds"]
AUD = ["creator_reports"]
EMP = ["emp_sales", "emp_chat"]


def _db(req: Request):
    return req.app.state.db


# ------------------------------------------------------------------ overview / revenue
@router.get("/dashboard/overview")
def overview(request: Request, f: Filters = Depends(parse_filters)):
    db = _db(request)
    meta = freshness(request, f, REV + AUD + EMP)
    ok = prev_ok(meta)
    rev = R.with_comparison(db, f, ok)
    aud = F.audience_totals(db, f)
    emps = E.leaderboard(db, f, ok)
    attributed = sum(e["sales"] or 0 for e in emps) if any(e["sales"] is not None for e in emps) else None
    camp = M.links(db, f.creator_ids, f.basis)
    creators = C.directory(db, f, ok)
    return {
        "meta": meta,
        "kpis": {
            "revenue": rev,
            "active_creators": sum(1 for c in creators if c["connected"]),
            "creators_with_revenue": sum(1 for c in creators if c["revenue"] > 0),
            "team_members": db.scalar("SELECT COUNT(*) FROM employees WHERE status='Activated'"),
            "active_fans": aud["active_fans"], "expired_fans": aud["expired_fans"], "new_subscribers": aud["new_subscribers"],
            "renewals": aud["renewals"], "auto_renew_pct": aud["auto_renew_pct"],
            "audience_creators_reporting": aud["creators_reporting"], "audience_creators_total": aud["creators_total"],
            "employee_attributed_sales": attributed,
            "campaign_earnings_lifetime": camp["summary"]["earnings"],
            "marketing_cost_entered": camp["summary"]["cost"],
        },
        "trend": R.trend(db, f),
        "breakdown": R.breakdown(db, f),
        "top_creators": creators[:8],
        "top_employees": emps[:8],
        "top_campaigns": camp["items"][:6],
        "subscriber_trend": aud["trend"],
    }


@router.get("/dashboard/revenue")
def revenue_trend(request: Request, f: Filters = Depends(parse_filters), granularity: str = Query("day", pattern="^(day|week|month)$")):
    db = _db(request)
    meta = freshness(request, f, REV)
    return {"meta": meta, "trend": R.trend(db, f, granularity, by_type=True),
            "breakdown": R.breakdown(db, f), "by_creator": R.by_creator(db, f), "totals": R.with_comparison(db, f, prev_ok(meta))}


@router.get("/earnings/breakdown")
def earnings_breakdown(request: Request, f: Filters = Depends(parse_filters)):
    return {"meta": freshness(request, f, REV), "breakdown": R.breakdown(_db(request), f)}


# ------------------------------------------------------------------ creators
@router.get("/creators")
def creators(request: Request, f: Filters = Depends(parse_filters)):
    meta = freshness(request, f, REV + AUD)
    return {"meta": meta, "items": C.directory(_db(request), f, prev_ok(meta))}


@router.get("/creators/compare")
def compare(request: Request, ids: str, f: Filters = Depends(parse_filters)):
    id_list = [i for i in ids.split(",") if i.strip().isdigit()][:6]
    if len(id_list) < 2:
        raise HTTPException(400, "Provide 2–6 creator ids")
    db = _db(request)
    sub = Filters(f.start, f.end, tuple(id_list), f.basis)
    meta = freshness(request, sub, REV + AUD)
    return {"meta": meta, "items": C.directory(db, sub, prev_ok(meta)),
            "trends": {cid: R.trend(db, Filters(f.start, f.end, (cid,), f.basis)) for cid in id_list}}


@router.get("/creators/{creator_id}")
def creator_detail(creator_id: str, request: Request, f: Filters = Depends(parse_filters)):
    if not creator_id.isdigit():
        raise HTTPException(400, "invalid creator id")
    db = _db(request)
    meta = freshness(request, Filters(f.start, f.end, (creator_id,), f.basis), REV + AUD)
    d = C.detail(db, f, creator_id, prev_ok(meta))
    if not d:
        raise HTTPException(404, "creator not found (has the creator list synced yet?)")
    camp = M.links(db, (creator_id,), f.basis)
    return {"meta": meta, **d, "campaigns": camp["summary"], "top_links": camp["items"][:5]}


@router.get("/creators/{creator_id}/chat")
async def creator_chat(creator_id: str, request: Request, f: Filters = Depends(parse_filters)):
    eng = request.app.state.sync
    try:
        rows = await eng.creator_chat_summary([creator_id], f.start, f.end)
    except InflowwError as e:
        return {"available": False, "error": e.to_dict()}
    return {"available": True, "fetched": "live", "rows": rows}


@router.get("/creators/{creator_id}/scripts")
async def creator_scripts(creator_id: str, request: Request):
    try:
        return {"available": True, **(await request.app.state.sync.script_stats_cached(creator_id))}
    except InflowwError as e:
        return {"available": False, "error": e.to_dict()}


# ------------------------------------------------------------------ employees
@router.get("/employees")
def employees(request: Request, f: Filters = Depends(parse_filters)):
    db = _db(request)
    meta = freshness(request, f, EMP + ["sales_records"])
    return {"meta": meta, "items": E.leaderboard(db, f, prev_ok(meta)), "trend": E.trend(db, f),
            "attribution": E.attribution(db, f),
            "limitations": ["Revenue per hour / shift hours are not exposed by the Infloww API.",
                            "'Fans chatted' is the sum of daily unique fans (a fan chatted on 3 days counts 3 times).",
                            "Sales are Infloww-attributed sales per your Infloww sales settings — creator revenue is never redistributed to chatters."]}


@router.get("/employees/matrix")
def employee_matrix(request: Request, f: Filters = Depends(parse_filters)):
    return {"meta": freshness(request, f, EMP), **E.matrix(_db(request), f)}


@router.get("/employees/{employee_id}")
def employee_detail(employee_id: int, request: Request, f: Filters = Depends(parse_filters)):
    meta = freshness(request, f, EMP)
    d = E.detail(_db(request), f, employee_id, prev_ok(meta))
    if not d:
        raise HTTPException(404, "employee not found")
    return {"meta": meta, **d}


# ------------------------------------------------------------------ fans
@router.get("/fans")
def fans(request: Request, f: Filters = Depends(parse_filters)):
    db = _db(request)
    meta = freshness(request, f, ["transactions", "creator_reports"])
    res = F.analyze(db, f)
    res.pop("_rows", None)
    return {"meta": meta, "audience": F.audience_totals(db, f), **res}


@router.get("/fans/top-spenders")
def top_spenders(request: Request, f: Filters = Depends(parse_filters), page: int = Query(1, ge=1), page_size: int = Query(25, ge=5, le=100),
                 sort: str = "lifetime", segment: str | None = None, search: str | None = Query(None, max_length=64)):
    return F.top_spenders(_db(request), f, page, page_size, sort, segment, search)


# ------------------------------------------------------------------ marketing
@router.get("/campaigns")
def campaigns(request: Request, f: Filters = Depends(parse_filters), link_type: str | None = Query(None, pattern="^(TRACKING|TRIAL|CAMPAIGN)$")):
    eng = request.app.state.sync
    db = _db(request)
    if eng.s.configured and eng.links_stale(list(f.creator_ids) if f.creator_ids else None):
        eng.trigger(f.start, f.end, [], include_links=True)  # links-only job; stale rows stay visible meanwhile
    meta = freshness(request, f, [], kick=False)
    scopes = [f"{c}:{lt}" for c in (f.creator_ids or eng.creator_ids()) for lt in ("TRACKING", "TRIAL", "CAMPAIGN")]
    rows = {r["scope"]: r for r in db.query("SELECT scope, fetched_at, status FROM dataset_sync WHERE dataset='links'")}
    got = [rows[s] for s in scopes if s in rows]
    ok = [r for r in got if r["status"] == "ok"]
    meta.update({
        "syncing": eng.syncing(links=True),
        "complete": bool(scopes) and len(ok) == len(scopes),
        "oldest_fetch": min((r["fetched_at"] for r in got), default=None),
        "newest_fetch": max((r["fetched_at"] for r in got), default=None),
        "coverage": {"links": {"dataset": "links", "complete": len(ok) == len(scopes), "covered": len(ok), "expected": len(scopes),
                               "missing_days": len(scopes) - len(ok), "oldest_fetch": None, "newest_fetch": None}},
    })
    return {"meta": meta, **M.links(db, f.creator_ids, f.basis, link_type)}


@router.get("/campaigns/{link_type}/{link_id}/fans")
async def campaign_fans(link_type: str, link_id: str, creator_id: str, request: Request):
    if link_type not in ("TRACKING", "TRIAL", "CAMPAIGN") or not link_id.isdigit() or not creator_id.isdigit():
        raise HTTPException(400, "invalid parameters")
    eng = request.app.state.sync
    try:
        items = await eng.client.paginate("/v1/linkfans", {"platformCode": eng.s.infloww_platform_code, "creatorId": creator_id,
                                                           "linkType": link_type, "linkId": link_id}, max_pages=20)
    except InflowwError as e:
        return {"available": False, "error": e.to_dict()}
    return {"available": True, "fetched": "live", "items": M.link_fans(items)[:200], "total": len(items)}


# ------------------------------------------------------------------ finance
@router.get("/finance")
def finance(request: Request, f: Filters = Depends(parse_filters)):
    eng = request.app.state.sync
    if eng.s.configured and not eng._dataset_fresh("invoices", "agency", 6 * 3600):
        eng.trigger(f.start, f.end, [], include_links=True)
    meta = freshness(request, f, REV + EMP)
    return {"meta": meta, **FI.overview(_db(request), f, prev_ok(meta))}


# ------------------------------------------------------------------ messages
@router.get("/messages")
async def messages(request: Request, f: Filters = Depends(parse_filters)):
    eng = request.app.state.sync
    errors = eng.message_errors[-10:]
    meta = freshness(request, f, [], kick=False)
    if eng.s.configured:
        meta["syncing"] = eng.refresh_messages(f.start, f.end, list(f.creator_ids) if f.creator_ids else None)
    return {"meta": meta, "errors": errors, **MS.overview(_db(request), f)}
