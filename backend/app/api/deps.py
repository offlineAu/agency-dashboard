"""Shared request dependencies: auth, filter parsing, freshness metadata."""
from __future__ import annotations

import hmac
import time
from datetime import date, timedelta

from fastapi import Depends, HTTPException, Query, Request

from app.analytics.common import Filters
from app.core.config import get_settings
from app.core.dates import previous_period, today_utc
from app.infloww.registry import MAX_HISTORY_DAYS


def require_access(request: Request) -> None:
    """Optional shared-token protection for every /api route (set DASHBOARD_ACCESS_TOKEN in production)."""
    token = get_settings().dashboard_access_token.get_secret_value()
    if not token:
        return
    supplied = request.headers.get("x-dashboard-token") or ""
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        supplied = supplied or auth[7:]
    if not hmac.compare_digest(supplied.encode(), token.encode()):
        raise HTTPException(status_code=401, detail="Dashboard access token required")


def parse_filters(
    start: date | None = Query(None, description="UTC start day (inclusive)"),
    end: date | None = Query(None, description="UTC end day (inclusive)"),
    creators: str | None = Query(None, description="Comma-separated creator IDs"),
    basis: str = Query("gross", pattern="^(gross|net)$"),
) -> Filters:
    end = end or today_utc()
    start = start or end - timedelta(days=get_settings().default_lookback_days - 1)
    if start > end:
        raise HTTPException(400, "start must be on or before end")
    if end > today_utc():
        end = today_utc()
    if (end - start).days > MAX_HISTORY_DAYS:
        raise HTTPException(400, f"Range longer than {MAX_HISTORY_DAYS} days (Infloww retains ~1 year)")
    ids = tuple(sorted({c.strip() for c in creators.split(",") if c.strip()})) if creators else None
    if ids and not all(c.isdigit() for c in ids):
        raise HTTPException(400, "creator IDs must be numeric")
    return Filters(start, end, ids, basis)


def engine(request: Request):
    return request.app.state.sync


def db(request: Request):
    return request.app.state.db


def freshness(request: Request, f: Filters, datasets: list[str], kick: bool = True) -> dict:
    """Coverage + freshness for a response; starts a background sync for anything missing/stale."""
    eng = request.app.state.sync
    settings = get_settings()
    scopes_c = list(f.creator_ids) if f.creator_ids else eng.creator_ids()
    scopes = {
        "transactions": scopes_c, "refunds": scopes_c, "creator_reports": scopes_c,
        "sales_records": list(f.creator_ids) if f.creator_ids else eng.creator_ids(include_disconnected=True),
        "emp_sales": [str(e) for e in eng.employee_ids()], "emp_chat": [str(e) for e in eng.employee_ids()],
    }
    cov = {d: eng.coverage_summary(d, scopes.get(d, []), f.start, f.end) for d in datasets}
    ps, _ = previous_period(f.start, f.end)
    prev_cov = {d: eng.coverage_summary(d, scopes.get(d, []), ps, f.start - timedelta(days=1)) for d in datasets}
    syncing = False
    # Sync the selected period AND the previous equal-length period (needed for growth comparisons).
    if kick and settings.configured and eng.needs_sync(datasets, ps, f.end):
        eng.trigger(ps, f.end, datasets)
        syncing = True
    syncing = syncing or eng.syncing(datasets)
    newest = [c["newest_fetch"] for c in cov.values() if c.get("newest_fetch")]
    oldest = [c["oldest_fetch"] for c in cov.values() if c.get("oldest_fetch")]
    complete = all(c["complete"] for c in cov.values())
    unavailable = {d: eng.capabilities[d]["reason"] for d in datasets if d in eng.capabilities and not eng.capabilities[d]["available"]}
    return {
        "source": "infloww-sync",
        "configured": settings.configured,
        "complete": complete,
        "previous_complete": all(c["complete"] for c in prev_cov.values()),
        "syncing": syncing,
        "coverage": cov,
        "oldest_fetch": min(oldest) if oldest else None,
        "newest_fetch": max(newest) if newest else None,
        "age_s": time.time() - min(oldest) if oldest else None,
        "unavailable": unavailable,
        "period": {"start": f.start.isoformat(), "end": f.end.isoformat(), "timezone": "UTC"},
        "basis": f.basis,
    }


Auth = Depends(require_access)


def prev_ok(meta: dict) -> bool:
    return bool(meta.get("previous_complete", True))
