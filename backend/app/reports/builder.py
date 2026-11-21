"""Report definitions + exporters (CSV, XLSX, PDF).

Every report carries: agency identifier, reporting period, generated timestamp (UTC), applied filters,
data source / coverage, and metric definitions. Figures are produced by the same analytics functions
the dashboard uses, so exports and screens cannot disagree.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.analytics import creators as C
from app.analytics import employees as E
from app.analytics import fans as F
from app.analytics import marketing as M
from app.analytics import revenue as R
from app.analytics.common import Filters
from app.core.dates import UTC
from app.store.db import Database

MONEY = "money"
PCT = "pct"
NUM = "num"
TEXT = "text"


@dataclass
class Report:
    key: str
    title: str
    columns: list[tuple[str, str, str]]          # (key, label, kind)
    rows: list[dict]
    definitions: list[str] = field(default_factory=list)
    totals: dict | None = None


def _rev_period(db: Database, f: Filters, gran: str, title: str, key: str) -> Report:
    rows = R.trend(db, f, gran, by_type=True)
    for r in rows:
        r["subscriptions"] = (r.get("Subscription") or 0) + (r.get("Recurring Subscription") or 0)
        r["ppv"] = (r.get("Messages") or 0) + (r.get("Posts") or 0)
        r["tips"] = r.get("Tips") or 0
        r["other"] = r["value"] - r["subscriptions"] - r["ppv"] - r["tips"]
    cols = [("bucket", {"day": "Date", "week": "Week starting", "month": "Month"}[gran], TEXT), ("gross", "Gross", MONEY),
            ("net", "Net", MONEY), ("subscriptions", f"Subscriptions ({f.basis})", MONEY), ("ppv", f"PPV ({f.basis})", MONEY),
            ("tips", f"Tips ({f.basis})", MONEY), ("other", f"Other ({f.basis})", MONEY), ("count", "Transactions", NUM)]
    tot = {c[0]: sum(r.get(c[0]) or 0 for r in rows) for c in cols[1:]}
    tot["bucket"] = "Total"
    return Report(key, title, cols, rows, [
        "Gross = transaction amount; Net = amount after OnlyFans platform fee (Infloww 'net').",
        "Recognised revenue = transactions with status 'done' or 'loading'. 'undo' / 'pending_return' are excluded.",
        "Days are UTC.",
    ], tot)


def build(db: Database, kind: str, f: Filters) -> Report:
    if kind == "daily":
        return _rev_period(db, f, "day", "Daily revenue report", kind)
    if kind == "weekly":
        return _rev_period(db, f, "week", "Weekly performance report", kind)
    if kind == "monthly":
        return _rev_period(db, f, "month", "Monthly agency report", kind)
    if kind == "revenue-sources":
        rows = R.breakdown(db, f)
        return Report(kind, "Revenue source report", [("label", "Source", TEXT), ("gross", "Gross", MONEY), ("net", "Net", MONEY),
                      ("count", "Transactions", NUM), ("share", f"Share of {f.basis} %", PCT)], rows,
                      ["Source = Infloww transaction type. PPV messages = 'Messages', PPV posts = 'Posts'."])
    if kind == "creators":
        rows = C.directory(db, f)
        for r in rows:
            r["growth_pct"] = r["growth"]["value"]
        return Report(kind, "Creator comparison report", [
            ("name", "Creator", TEXT), ("id", "Creator ID", TEXT), ("status", "Status", TEXT), ("revenue", f"Revenue ({f.basis})", MONEY),
            ("growth_pct", "Growth vs prev. %", PCT), ("subscription_revenue", "Subscriptions", MONEY), ("ppv_revenue", "PPV", MONEY),
            ("tips", "Tips", MONEY), ("refunds", "Refunds", MONEY), ("paying_fans", "Paying fans", NUM),
            ("avg_revenue_per_paying_fan", "Avg / paying fan", MONEY), ("active_fans", "Active fans", NUM),
            ("new_subscribers", "New subs", NUM), ("renewals", "Renewals", NUM), ("auto_renew_pct", "Auto-renew %", PCT),
            ("share_of_agency", "Share of agency %", PCT)], rows,
            ["Active fans / auto-renew = latest day in period from Infloww creator reports.",
             "Growth compares with the immediately preceding period of equal length; blank when the baseline is zero."])
    if kind == "employees":
        rows = E.leaderboard(db, f)
        for r in rows:
            r["avg_response_min"] = r["avg_response_clocked_ms"] / 60000 if r["avg_response_clocked_ms"] else None
            r["assigned"] = ", ".join(c["name"] or c["id"] for c in r["assigned_creators"])
        return Report(kind, "Chatter performance report", [
            ("rank", "#", NUM), ("name", "Employee", TEXT), ("sales", "Attributed sales", MONEY), ("ppv_sales", "PPV sales", MONEY),
            ("tips_sales", "Tip sales", MONEY), ("messages_sent", "Messages sent", NUM), ("ppvs_sent", "PPVs sent", NUM),
            ("unlock_rate", "Unlock rate %", PCT), ("golden_ratio", "Golden ratio %", PCT), ("sales_per_message", "Sales / message", MONEY),
            ("avg_response_min", "Avg reply (min, clocked)", NUM), ("assigned", "Assigned creators", TEXT)], rows,
            ["Sales are attributed by Infloww per the agency's sales settings; unattributed revenue is not assigned to anyone.",
             "Revenue per hour is unavailable: the API exposes no worked hours."])
    if kind == "fans":
        res = F.top_spenders(db, f, 1, 500)
        return Report(kind, "Fan spending report (top 500, pseudonymised)", [
            ("fan_ref", "Fan ref", TEXT), ("segment", "Segment", TEXT), ("lifecycle", "Lifecycle", TEXT), ("lifetime", "Spend (synced history)", MONEY),
            ("period_spend", "Spend in period", MONEY), ("purchases", "Purchases", NUM), ("ppv_purchases", "PPV purchases", NUM),
            ("tips", "Tips", MONEY), ("first_day", "First purchase", TEXT), ("last_day", "Last purchase", TEXT)], res.get("items", []),
            [f"Synced history: {res.get('history', {}).get('start')} → {res.get('history', {}).get('end')}.",
             "Fan names/IDs are masked. Segments use thresholds configured in Settings."])
    if kind == "campaigns":
        res = M.links(db, f.creator_ids, f.basis)
        return Report(kind, "Campaign ROI report", [
            ("name", "Link", TEXT), ("type_label", "Type", TEXT), ("creator_name", "Creator", TEXT), ("source", "Source", TEXT),
            ("clicks", "Clicks", NUM), ("subscribers", "Subs / claims", NUM), ("subscription_cvr", "Sub CVR %", PCT),
            ("earnings", f"Earnings ({f.basis})", MONEY), ("cost", "Cost (local)", MONEY), ("cpc", "CPC", MONEY), ("cps", "CPS", MONEY),
            ("epc", "EPC", MONEY), ("aeps", "AEPS", MONEY), ("profit", "Profit", MONEY), ("roi", "ROI %", PCT)], res["items"], res["notes"])
    raise KeyError(kind)


KINDS = {"daily": "Daily revenue", "weekly": "Weekly performance", "monthly": "Monthly agency", "creators": "Creator comparison",
         "employees": "Chatter performance", "fans": "Fan spending", "campaigns": "Campaign ROI", "revenue-sources": "Revenue sources"}


def header_lines(rep: Report, f: Filters, agency: str, coverage_note: str, currency: str) -> list[tuple[str, str]]:
    return [
        ("Report", rep.title), ("Agency", agency), ("Reporting period", f"{f.start.isoformat()} → {f.end.isoformat()} (UTC)"),
        ("Generated", datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")),
        ("Filters", f"creators={','.join(f.creator_ids) if f.creator_ids else 'all connected'}; basis={f.basis}"),
        ("Currency", f"{currency} (amounts in major units)"), ("Source", "Infloww API v1 (read-only) via local sync"),
        ("Coverage", coverage_note),
    ]


def _fmt(v, kind):
    if v is None:
        return ""
    if kind == MONEY:
        return round(v / 100, 2)
    if kind == PCT:
        return round(v, 2)
    if kind == NUM and isinstance(v, float):
        return round(v, 2)
    return v


def to_csv(rep: Report, header: list[tuple[str, str]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    for k, v in header:
        w.writerow([f"# {k}", v])
    w.writerow([])
    w.writerow([c[1] for c in rep.columns])
    for r in rep.rows:
        w.writerow([_fmt(r.get(c[0]), c[2]) for c in rep.columns])
    if rep.totals:
        w.writerow([_fmt(rep.totals.get(c[0]), c[2]) for c in rep.columns])
    w.writerow([])
    for d in rep.definitions:
        w.writerow(["# Definition", d])
    return buf.getvalue().encode("utf-8-sig")


def to_xlsx(rep: Report, header: list[tuple[str, str]]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = rep.key[:30]
    for k, v in header:
        ws.append([k, v])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
    ws.append([])
    ws.append([c[1] for c in rep.columns])
    hdr_row = ws.max_row
    for i in range(1, len(rep.columns) + 1):
        ws.cell(hdr_row, i).font = Font(bold=True, color="FFFFFF")
        ws.cell(hdr_row, i).fill = PatternFill("solid", fgColor="312E81")
    for r in rep.rows:
        ws.append([_fmt(r.get(c[0]), c[2]) for c in rep.columns])
    if rep.totals:
        ws.append([_fmt(rep.totals.get(c[0]), c[2]) for c in rep.columns])
        for i in range(1, len(rep.columns) + 1):
            ws.cell(ws.max_row, i).font = Font(bold=True)
    for i, c in enumerate(rep.columns, 1):
        fmt = "#,##0.00" if c[2] == MONEY else "0.00" if c[2] == PCT else None
        if fmt:
            for row in ws.iter_rows(min_row=hdr_row + 1, min_col=i, max_col=i):
                row[0].number_format = fmt
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(40, len(c[1]) + 4))
    ws.freeze_panes = ws.cell(hdr_row + 1, 1)
    d = wb.create_sheet("Definitions")
    for line in rep.definitions:
        d.append([line])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def to_pdf(rep: Report, header: list[tuple[str, str]]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=rep.title)
    ss = getSampleStyleSheet()
    small = ss["BodyText"].clone("small", fontSize=7.5, leading=9)
    story = [Paragraph(rep.title, ss["Title"])]
    meta = Table([[Paragraph(f"<b>{k}</b>", small), Paragraph(str(v), small)] for k, v in header[1:]], colWidths=[35 * mm, 220 * mm])
    meta.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    story += [meta, Spacer(1, 5 * mm)]

    def cell(v, kind):
        x = _fmt(v, kind)
        if x == "":
            return "—"
        if kind == MONEY:
            return f"{x:,.2f}"
        if kind == PCT:
            return f"{x:.1f}%"
        return str(x)[:40]

    data = [[Paragraph(f"<b>{c[1]}</b>", small) for c in rep.columns]]
    for r in rep.rows[:1000]:
        data.append([Paragraph(cell(r.get(c[0]), c[2]), small) for c in rep.columns])
    if rep.totals:
        data.append([Paragraph(f"<b>{cell(rep.totals.get(c[0]), c[2])}</b>", small) for c in rep.columns])
    width = (297 - 24) * mm / len(rep.columns)
    t = Table(data, colWidths=[width] * len(rep.columns), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312E81")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [t, Spacer(1, 5 * mm), Paragraph("<b>Definitions</b>", small)]
    story += [Paragraph(f"• {d}", small) for d in rep.definitions]
    doc.build(story)
    return buf.getvalue()
