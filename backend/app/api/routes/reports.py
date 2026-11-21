from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.analytics.common import Filters
from app.api.deps import Auth, freshness, parse_filters
from app.core.config import get_settings
from app.reports import builder as B

router = APIRouter(prefix="/api/reports", dependencies=[Auth])

MEDIA = {"csv": "text/csv; charset=utf-8", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "pdf": "application/pdf"}


@router.get("")
def list_reports():
    return {"reports": [{"key": k, "title": v} for k, v in B.KINDS.items()], "formats": list(MEDIA)}


@router.get("/{kind}")
def report(kind: str, request: Request, f: Filters = Depends(parse_filters), format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$")):
    if kind not in B.KINDS:
        raise HTTPException(404, "unknown report")
    db = request.app.state.db
    datasets = {"employees": ["emp_sales", "emp_chat"], "campaigns": []}.get(kind, ["transactions", "refunds", "creator_reports"])
    meta = freshness(request, f, datasets, kick=False)
    rep = B.build(db, kind, f)
    cov = meta["coverage"]
    note = "complete" if meta["complete"] else "INCOMPLETE — " + "; ".join(
        f"{d}: {c.get('covered', 0)}/{c.get('expected', 0)} creator-days synced" for d, c in cov.items() if not c["complete"])
    currency = db.scalar("SELECT currency FROM transactions WHERE currency IS NOT NULL GROUP BY currency ORDER BY COUNT(*) DESC LIMIT 1") or "USD"
    oid = get_settings().infloww_agency_oid
    header = B.header_lines(rep, f, f"Infloww agency …{oid[-4:]}" if oid else "Infloww agency", note, currency)
    if format == "json":
        return {"meta": meta, "header": header, "title": rep.title, "columns": rep.columns, "rows": rep.rows, "totals": rep.totals,
                "definitions": rep.definitions}
    data = {"csv": B.to_csv, "xlsx": B.to_xlsx, "pdf": B.to_pdf}[format](rep, header)
    fname = f"{kind}_{f.start.isoformat()}_{f.end.isoformat()}.{format}"
    return Response(data, media_type=MEDIA[format], headers={"Content-Disposition": f'attachment; filename="{fname}"'})
