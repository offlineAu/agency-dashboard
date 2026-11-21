"""Financial overview. Separates Infloww-reported figures from locally-configured estimates.

Agency commission, chatter pay and marketing costs are NOT available from the API. They are only
computed when the agency enters its own rules in Settings, and are always labelled as estimates.
Gross revenue is never presented as agency profit.
"""
from __future__ import annotations

from app.analytics import revenue
from app.analytics.common import Filters, ratio
from app.store.db import Database


def local_settings(db: Database) -> dict:
    def num(k):
        v = db.get_setting(k)
        return float(v) if v not in (None, "") else None
    return {
        "agency_commission_pct": num("finance.agency_commission_pct"),       # % of creator NET revenue kept by agency
        "chatter_commission_pct": num("finance.chatter_commission_pct"),     # % of employee-attributed sales paid to chatters
        "other_monthly_costs_cents": num("finance.other_monthly_costs_cents"),
        "commission_base": db.get_setting("finance.commission_base", "net"),
    }


def overview(db: Database, f: Filters, prev_ok: bool = True) -> dict:
    t = revenue.with_comparison(db, Filters(f.start, f.end, f.creator_ids, "gross"), prev_ok)
    cur = t["current"]
    s, e = f.start.isoformat(), f.end.isoformat()
    cfg = local_settings(db)
    attributed = db.scalar("SELECT SUM(sales) FROM emp_sales_daily WHERE day BETWEEN ? AND ?", (s, e))
    mk = db.one("SELECT SUM(cost_cents) cost, COUNT(*) n FROM campaign_costs WHERE spent_on BETWEEN ? AND ?", (s, e)) or {}
    mk_undated = db.scalar("SELECT COUNT(*) FROM campaign_costs WHERE spent_on IS NULL OR spent_on=''")
    months = {s[:7], e[:7]}
    inv = db.query("SELECT * FROM invoices WHERE period BETWEEN ? AND ? ORDER BY period", (s[:7], e[:7]))
    days = (f.end - f.start).days + 1

    base = cur["net"] if cfg["commission_base"] == "net" else cur["gross"]
    commission = base * cfg["agency_commission_pct"] / 100 if cfg["agency_commission_pct"] is not None else None
    chatter_pay = (attributed or 0) * cfg["chatter_commission_pct"] / 100 if cfg["chatter_commission_pct"] is not None and attributed is not None else None
    other = cfg["other_monthly_costs_cents"] * days / 30.4375 if cfg["other_monthly_costs_cents"] is not None else None
    infloww_bill = sum((i["total"] or 0) for i in inv) if inv else None
    costs = [c for c in (chatter_pay, mk.get("cost"), other) if c is not None]
    profit = commission - sum(costs) if commission is not None else None

    reported = [
        {"key": "gross", "label": "Gross revenue (fan spend)", "value": cur["gross"], "source": "infloww"},
        {"key": "platform_fees", "label": "OnlyFans platform fees", "value": -cur["platform_fees"], "source": "infloww"},
        {"key": "net", "label": "Net revenue (after platform fees)", "value": cur["net"], "source": "infloww"},
        {"key": "refunds", "label": "Refunds (by refund date)", "value": -cur["refunds"], "source": "infloww"},
        {"key": "reversed", "label": "Reversed transactions (status 'undo')", "value": -cur["reversed"], "source": "infloww"},
        {"key": "pending_return", "label": "Pending return (status 'pending_return')", "value": -cur["pending_return"], "source": "infloww"},
        {"key": "pending_clearance", "label": "Of gross: not yet cleared ('loading')", "value": cur["gross_pending_clearance"], "source": "infloww", "info": True},
        {"key": "attributed_sales", "label": "Employee-attributed sales", "value": attributed, "source": "infloww", "info": True},
        {"key": "infloww_billing", "label": f"Infloww subscription invoices ({', '.join(i['period'] for i in inv) or 'none in range'})",
         "value": -infloww_bill if infloww_bill is not None else None, "source": "infloww", "info": True},
    ]
    estimates = [
        {"key": "agency_commission", "label": f"Agency commission ({cfg['agency_commission_pct']}% of {cfg['commission_base']})" if commission is not None else "Agency commission",
         "value": commission, "source": "estimate", "missing": None if commission is not None else "Set the agency commission % in Settings"},
        {"key": "chatter_pay", "label": f"Chatter commission ({cfg['chatter_commission_pct']}% of attributed sales)" if chatter_pay is not None else "Chatter compensation",
         "value": -chatter_pay if chatter_pay is not None else None, "source": "estimate", "missing": None if chatter_pay is not None else "Set chatter commission % in Settings (no payroll data in API)"},
        {"key": "marketing", "label": "Marketing spend (local entries dated in period)", "value": -(mk.get("cost") or 0) if mk.get("n") else None,
         "source": "local", "missing": None if mk.get("n") else "No dated campaign costs entered for this period"},
        {"key": "other", "label": "Other operating costs (pro-rated)", "value": -other if other is not None else None, "source": "estimate",
         "missing": None if other is not None else "Optional: set monthly operating costs in Settings"},
        {"key": "operating_profit", "label": "Estimated agency operating profit", "value": profit, "source": "estimate",
         "missing": None if profit is not None else "Requires agency commission % (not available from Infloww)"},
    ]
    return {
        "totals": t,
        "breakdown": revenue.breakdown(db, Filters(f.start, f.end, f.creator_ids, "gross")),
        "reported": reported,
        "estimates": estimates,
        "settings": cfg,
        "invoices": inv,
        "undated_campaign_costs": mk_undated,
        "fee_rate": ratio(cur["platform_fees"], cur["gross"], 100),
        "refund_rate": ratio(cur["refunds"], cur["gross"], 100),
        "notes": [
            "Infloww figures come from synced transactions; estimates use rules you configured locally.",
            "The API does not distinguish refunds from chargebacks on reversed ('undo') transactions.",
            "Infloww invoices are the agency's Infloww subscription bill, shown for context; they are included in profit only via 'Other operating costs' if you choose.",
        ],
        "months": sorted(months),
    }
