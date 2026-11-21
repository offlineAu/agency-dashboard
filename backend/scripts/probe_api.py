"""Live, READ-ONLY probe of every Infloww endpoint. Writes docs/API_CONNECTION_REPORT.md.

Usage:  cd backend && .venv/bin/python -m scripts.probe_api
Uses the same InflowwClient as the app (GET-only allowlist). Prints/stores NO credentials and NO fan
names: only status codes, timings, record counts, field names and pagination behaviour.

It also resolves the details the spec leaves ambiguous:
  * array query encoding (repeated keys vs comma-separated) for creatorIds/employeeIds
  * billing month format for /v1/invoice-data/monthly-billing
  * whether chat-summary returns per-day rows
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

from app.core.config import get_settings
from app.core.dates import day_end_ms, day_start_ms, today_utc
from app.infloww.client import InflowwClient, InflowwError
from app.infloww.monitor import Monitor

ROOT = Path(__file__).resolve().parents[2]


def keys_of(body: dict) -> list[str]:
    lst = (body.get("data") or {}).get("list")
    if isinstance(lst, list) and lst:
        return sorted(lst[0].keys())
    d = body.get("data")
    return sorted(d.keys()) if isinstance(d, dict) else []


async def main() -> int:
    s = get_settings()
    if not s.configured:
        print("INFLOWW_API_KEY / INFLOWW_AGENCY_OID not set in backend/.env")
        return 2
    results: list[dict] = []
    findings: list[str] = []

    async def probe(label: str, path: str, params: dict, client: InflowwClient | None = None) -> dict | None:
        c = client or cl
        t0 = time.perf_counter()
        try:
            body = await c.get(path, params)
            lst = (body.get("data") or {}).get("list")
            r = {"label": label, "path": path, "status": 200, "ms": round((time.perf_counter() - t0) * 1000),
                 "records": len(lst) if isinstance(lst, list) else None, "hasMore": body.get("hasMore"),
                 "cursor_present": body.get("cursor") not in (None, ""), "fields": keys_of(body)}
            results.append(r)
            print(f"OK   {path:55s} {r['records']} rows {r['ms']}ms")
            return body
        except InflowwError as e:
            results.append({"label": label, "path": path, "status": e.status, "ms": round((time.perf_counter() - t0) * 1000),
                            "error_kind": e.kind, "error": str(e)[:200], "request_id": e.request_id})
            print(f"FAIL {path:55s} {e.kind} {e.status} {str(e)[:120]}")
            return None

    cl = InflowwClient(s, Monitor())
    pc = s.infloww_platform_code
    end = today_utc() - timedelta(days=1)
    start = end - timedelta(days=6)
    ms = {"startTime": day_start_ms(start), "endTime": day_end_ms(end)}
    dd = {"startTime": start.isoformat(), "endTime": end.isoformat()}

    body = await probe("Connected creators", "/v1/creators", {"platformCode": pc, "limit": 100})
    if body is None:
        print("Cannot continue without creator access (auth/IP/scope).")
    creators = ((body or {}).get("data") or {}).get("list") or []
    await probe("All creators", "/v1/all-creators", {"platformCode": pc, "limit": 100})
    emp_body = await probe("Employees", "/v1/employees", {"limit": 100})
    emps = ((emp_body or {}).get("data") or {}).get("list") or []
    cid = str(creators[0]["id"]) if creators else None
    eid = emps[0]["employeeId"] if emps else None
    if eid is not None:
        await probe("Assigned creators", "/v1/employees/assigned-creators", {"employeeId": eid, "limit": 100})
    if cid:
        await probe("Transactions", "/v1/transactions", {"platformCode": pc, "creatorId": cid, "limit": 100, **ms})
        await probe("Refunds", "/v1/refunds", {"platformCode": pc, "creatorId": cid, "limit": 100, **ms})
        await probe("Sales records", "/v1/transaction-perf/details", {"platformCode": pc, "creatorId": cid, "limit": 100, **ms})
        for lt in ("TRACKING", "TRIAL", "CAMPAIGN"):
            lb = await probe(f"Links {lt}", "/v1/links", {"platformCode": pc, "creatorId": cid, "linkType": lt, "limit": 100,
                                                          "startTime": day_start_ms(end - timedelta(days=30)), "endTime": day_end_ms(end)})
            items = ((lb or {}).get("data") or {}).get("list") or []
            if items:
                created = [int(i["createdTime"]) for i in items if i.get("createdTime")]
                inside = all(day_start_ms(end - timedelta(days=30)) <= c <= day_end_ms(end) for c in created)
                findings.append(f"/v1/links {lt}: all returned createdTime inside requested window = {inside} "
                                f"({'window filters by creation time' if inside else 'window is NOT a creation-time filter'})")
                await probe(f"Link fans {lt}", "/v1/linkfans", {"platformCode": pc, "creatorId": cid, "linkType": lt, "linkId": items[0]["id"], "limit": 100})
        await probe("Automated messages", "/v1/automated-messages", {"platformCode": pc, "creatorId": cid, "limit": 10, **ms})
        await probe("Priority mass messages", "/v1/priority-mass-messages", {"platformCode": pc, "creatorId": cid, "limit": 10, **ms})
        await probe("Script tags", "/v1/script-tag", {"platformCode": pc, "creatorId": cid, "limit": 100})
        await probe("Script sequences", "/v1/script-sequence", {"platformCode": pc, "creatorId": cid, "limit": 100})

        # ---- array encoding: try two creators with repeated keys, then comma
        ids = [str(c["id"]) for c in creators[:2]]
        rep = await probe("Fans count (repeat-array)", "/v1/creator-report/fans/count", {"platformCode": pc, "creatorIds": ids, **dd})
        rep_pids = {r.get("platformPid") for r in ((rep or {}).get("data") or {}).get("list") or []}
        comma_cl = InflowwClient(s.model_copy(update={"infloww_array_style": "comma"}), Monitor())
        com = await probe("Fans count (comma-array)", "/v1/creator-report/fans/count", {"platformCode": pc, "creatorIds": ids, **dd}, comma_cl)
        com_pids = {r.get("platformPid") for r in ((com or {}).get("data") or {}).get("list") or []}
        await comma_cl.aclose()
        findings.append(f"Array encoding: repeat -> {len(rep_pids)} creators returned, comma -> {len(com_pids)} creators returned "
                        f"(requested {len(ids)}). Recommended INFLOWW_ARRAY_STYLE="
                        f"{'repeat' if rep is not None and len(rep_pids) >= len(com_pids) else 'comma'}")
        for path in ("/v1/creator-report/chat-summary", "/v1/creator-report/fans/subscriber-count", "/v1/creator-report/fans/renew-on",
                     "/v1/creator-report/fans/avg-subscription-length", "/v1/creator-report/reach/profile-visitor-count", "/v1/creator-report/rank"):
            b = await probe(path.split("/")[-1], path, {"platformCode": pc, "creatorIds": [cid], **dd})
            if path.endswith("chat-summary") and b:
                n = len((b.get("data") or {}).get("list") or [])
                findings.append(f"chat-summary for 1 creator over 7 days returned {n} row(s) "
                                f"({'per-day rows' if n > 1 else 'one aggregate row'}; fields: {keys_of(b)})")
        await probe("Status change log", "/v1/creator/status-change-log", {"platformCode": pc, "creatorIds": [cid], "limit": 100, **ms})
    if emps:
        eids = [e["employeeId"] for e in emps[:3]]
        await probe("Employee sales summary", "/v1/employee-report/employee-sales-summary", {"platformCode": pc, "employeeIds": eids, **dd})
        await probe("Employee chat summary", "/v1/employee-report/employee-chat-summary", {"platformCode": pc, "employeeIds": eids, **dd})
    await probe("Manual assignments", "/v1/transaction-perf/manual-assignment/details", {"limit": 100, **ms})
    m_end = today_utc().replace(day=1)
    m_start = (m_end - timedelta(days=60)).replace(day=1)
    inv = await probe("Invoices (yyyy-MM)", "/v1/invoice-data/monthly-billing", {"startTime": m_start.strftime("%Y-%m"), "endTime": m_end.strftime("%Y-%m")})
    if inv is None:
        inv2 = await probe("Invoices (ISO date)", "/v1/invoice-data/monthly-billing", {"startTime": m_start.isoformat(), "endTime": m_end.isoformat()})
        findings.append(f"Invoice month format: yyyy-MM failed; ISO date {'works' if inv2 else 'also failed'}")
    else:
        findings.append("Invoice month format: yyyy-MM accepted")
    await cl.aclose()

    ok = sum(1 for r in results if r.get("status") == 200)
    lines = ["# API Connection Report", "", f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}  ",
             f"Base URL: `{s.infloww_base_url}`  ", "Auth: `Authorization: <raw key>` + `x-oid: <agency OID>` (values not recorded)  ",
             f"Result: **{ok}/{len(results)} probes succeeded**", "",
             "Probe window: last 7 complete UTC days. Only GET requests were sent. No fan names or IDs are recorded here.", "",
             "| Probe | Endpoint | Status | ms | Records | hasMore | Fields / error |", "|---|---|---|---|---|---|---|"]
    for r in results:
        detail = ", ".join(r.get("fields", [])) if r.get("status") == 200 else f"**{r.get('error_kind')}** {r.get('error')} (x-request-id {r.get('request_id')})"
        lines.append(f"| {r['label']} | `{r['path']}` | {r.get('status')} | {r['ms']} | {r.get('records', '')} | {r.get('hasMore', '')} | {detail} |")
    lines += ["", "## Findings", ""] + [f"- {f}" for f in findings]
    out = ROOT / "docs" / "API_CONNECTION_REPORT.md"
    out.write_text("\n".join(lines) + "\n")
    (ROOT / "backend" / "data").mkdir(exist_ok=True)
    (ROOT / "backend" / "data" / "probe_results.json").write_text(json.dumps({"results": results, "findings": findings}, indent=1))
    print(f"\n{ok}/{len(results)} OK. Report written to {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
