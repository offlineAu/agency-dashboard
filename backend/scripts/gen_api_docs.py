"""Generate docs/INFLOWW_API_INVENTORY.md and docs/API_RESPONSE_SCHEMAS.md from docs/spec/infloww-openapi.yaml.

    cd backend && .venv/bin/python -m scripts.gen_api_docs     (requires pyyaml from requirements-dev.txt)
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.infloww.registry import ENDPOINTS

ROOT = Path(__file__).resolve().parents[2]
SPEC = yaml.safe_load((ROOT / "docs/spec/infloww-openapi.yaml").read_text())
USED = {
    "/v1/creators": "Creator directory, filters, sync reference", "/v1/all-creators": "Creator status incl. deleted (scope-dependent)",
    "/v1/transactions": "All revenue metrics, fan intelligence", "/v1/refunds": "Refunds (financials, creators)",
    "/v1/links": "Marketing module", "/v1/linkfans": "Marketing → fans per link (live, on demand)",
    "/v1/automated-messages": "Analytics → message performance", "/v1/priority-mass-messages": "Analytics → message performance",
    "/v1/transaction-perf/details": "Chatter attribution quality (salesRule)", "/v1/invoice-data/monthly-billing": "Financials → Infloww invoices",
    "/v1/transaction-perf/manual-assignment/details": "Not surfaced yet (audit trail of reassignments) — probed only",
    "/v1/creator-report/chat-summary": "Creator detail → engagement (live, per range)",
    "/v1/creator-report/fans/count": "Active / expired fans", "/v1/creator-report/fans/subscriber-count": "New subscribers / renewals",
    "/v1/creator-report/fans/renew-on": "Auto-renew %", "/v1/creator-report/fans/avg-subscription-length": "Avg subscription length",
    "/v1/creator-report/reach/profile-visitor-count": "Profile visitors", "/v1/creator-report/rank": "Performance rank",
    "/v1/creator/status-change-log": "Not surfaced yet — probed only", "/v1/employees": "Chatter directory",
    "/v1/employees/assigned-creators": "Chatter → creator assignments", "/v1/employee-report/employee-sales-summary": "Chatter sales (attributed)",
    "/v1/employee-report/employee-chat-summary": "Chatter productivity / response time", "/v1/scripts": "Not used (tag/sequence stats used instead)",
    "/v1/script/statistics": "Not used", "/v1/script-tag": "Analytics → script performance", "/v1/script-tag/statistics": "Analytics → script performance",
    "/v1/script-sequence": "Analytics → script performance", "/v1/script-sequence/statistics": "Analytics → script performance",
}
PRIORITY = {"revenue": "Critical", "attribution": "Critical", "employee-report": "Critical", "marketing": "Critical", "creators": "Critical",
            "creator-report": "High", "employees": "High", "messages": "Medium", "billing": "Medium", "scripts": "Low"}


def ref(o):
    if isinstance(o, dict) and "$ref" in o:
        t = SPEC
        for k in o["$ref"].split("/")[1:]:
            t = t[k]
        return ref(t)
    return o


def params(op):
    out = []
    for p in map(ref, op.get("parameters", [])):
        if p["in"] == "header":
            continue
        sc = p.get("schema", {})
        bits = [sc.get("type", "")]
        if sc.get("enum"):
            bits.append("enum " + "/".join(map(str, sc["enum"])))
        if "maximum" in sc:
            bits.append(f"max {sc['maximum']}")
        if "maxItems" in sc:
            bits.append(f"≤{sc['maxItems']} items")
        out.append(f"`{p['name']}`{'*' if p.get('required') else ''} ({', '.join(b for b in bits if b)})")
    return ", ".join(out)


def fields(s, pre="", depth=0, out=None):
    out = [] if out is None else out
    s = ref(s)
    if not isinstance(s, dict) or depth > 6:
        return out
    for c in ("allOf", "oneOf", "anyOf"):
        for i, x in enumerate(s.get(c, [])):
            x = ref(x)
            if c == "oneOf" and x.get("title"):
                out.append((f"{pre} — variant **{x['title']}**", "", ""))
            fields(x, pre, depth + 1, out)
    if "items" in s:
        fields(s["items"], pre + "[]", depth + 1, out)
    for k, v in (s.get("properties") or {}).items():
        v = ref(v)
        t = v.get("type", "object") if isinstance(v, dict) else ""
        en = f" enum: {', '.join(map(str, v['enum']))}" if isinstance(v, dict) and v.get("enum") else ""
        out.append((f"{pre}.{k}", str(t), ((v.get("description") or "") if isinstance(v, dict) else "").replace("\n", " ").replace("|", "\\|")[:180] + en))
        fields(v, pre + "." + k, depth + 1, out)
    return out


def main():
    inv = ["# Infloww API Inventory", "", "_Generated from `docs/spec/infloww-openapi.yaml` (Infloww API v"
           f"{SPEC['info']['version']}) by `backend/scripts/gen_api_docs.py`. Do not edit by hand._", "",
           "## Global conventions (from the spec)", "",
           "- **Base URL:** `https://openapi.infloww.com` (paths include `/v1`).",
           "- **Auth headers (every request):** `Authorization: <raw API key>` (no `Bearer` prefix) and `x-oid: <agency OID>`.",
           "- **Methods:** every documented operation is `GET`. The spec contains no POST/PUT/PATCH/DELETE (verified by `tests/test_registry_and_security.py`).",
           "- **Rate limit:** 1,000 queries/minute per agency across all keys; `/v1/invoice-data/monthly-billing` is 10 QPM.",
           "- **Pagination:** `cursor` + `limit` request params; response `cursor` + `hasMore`. `limit` default 10, max 100 (max 10 for message endpoints).",
           "- **Time windows:** max 31 days per request. Revenue/report data retained ~1 year (366 days). Datetime endpoints take unix ms or ISO-8601 UTC; report endpoints take `YYYY-MM-DD`.",
           "- **Errors:** JSON `{\"errorMessage\": \"…\"}` with 400 / 401 (`invalid api key`) / 403 (incl. `Your ip address is not allowed`) / 429 / 500. Include response header `x-request-id` when contacting support.",
           "- **Latency:** OnlyFans→Infloww sync (1h–24h depending on data) + ~1h Infloww→API.",
           "- **Key scope:** creators must be explicitly added to the key; only `/v1/transaction-perf/details` returns deleted/unlinked creators.", "",
           "## Endpoints", "",
           "| Method | Path | Summary | Query params (`*` required) | Window | Paginated | Read-only | Priority | Used for |",
           "|---|---|---|---|---|---|---|---|---|"]
    for path, ops in SPEC["paths"].items():
        for m, op in ops.items():
            if m not in ("get", "post", "put", "patch", "delete"):
                continue
            ep = ENDPOINTS.get(path)
            inv.append(f"| {m.upper()} | `{path}` | {op.get('summary', '')} | {params(op)} | {ep.window.value if ep else '?'} | "
                       f"{'yes' if ep and ep.paginated else 'no'} | {'yes (GET)' if m == 'get' else '**NO**'} | {PRIORITY.get(ep.category, '') if ep else ''} | {USED.get(path, '')} |")
    inv += ["", "## Endpoint notes (verbatim from spec descriptions)", ""]
    for path, ops in SPEC["paths"].items():
        op = ops.get("get", {})
        inv.append(f"- **`{path}`** — {(op.get('description') or '').strip().replace(chr(10), ' ')[:600]}")
    (ROOT / "docs/INFLOWW_API_INVENTORY.md").write_text("\n".join(inv) + "\n")

    sch = ["# API Response Schemas", "", "_Generated from the OpenAPI spec. Amounts are in the smallest currency unit (cents). Times are unix ms unless noted._", ""]
    for path, ops in SPEC["paths"].items():
        op = ops.get("get", {})
        body = ref(op.get("responses", {}).get("200", {})).get("content", {}).get("application/json", {}).get("schema")
        sch += [f"## `GET {path}` — {op.get('summary', '')}", "", "| Field | Type | Description |", "|---|---|---|"]
        for f, t, d in fields(body or {}):
            sch.append(f"| `{f}` | {t} | {d} |" if t or d else f"| {f} | | |")
        sch.append("")
    (ROOT / "docs/API_RESPONSE_SCHEMAS.md").write_text("\n".join(sch) + "\n")
    print("wrote docs/INFLOWW_API_INVENTORY.md and docs/API_RESPONSE_SCHEMAS.md")


if __name__ == "__main__":
    main()
