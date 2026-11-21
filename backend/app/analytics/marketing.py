"""Marketing analytics: tracking links, free-trial links and profile promotions (/v1/links).

* Earnings/clicks/subs on a link are CUMULATIVE figures as reported by Infloww (not period-bound).
* Attribution follows Infloww's rules: a fan's revenue is credited to their MOST RECENT tracking /
  free-trial link — not necessarily the first source that introduced them.
* Promotional cost is NOT available from the API. Costs are entered locally (Settings → Campaign costs)
  and every cost-based metric (CPC, CPS, profit, ROI) is flagged as using local input.
"""
from __future__ import annotations

import statistics

from app.analytics.common import ratio
from app.store.db import Database

TYPE_LABELS = {"TRACKING": "Tracking link", "TRIAL": "Free trial link", "CAMPAIGN": "Profile promotion"}


def compute(link: dict, cost: int | None, basis: str) -> dict:
    earn = link["earnings_net"] if basis == "net" else link["earnings_gross"]
    clicks, subs = link["click_count"], link["sub_count"]
    profit = earn - cost if (earn is not None and cost is not None) else None
    return {
        "earnings": earn,
        "cost": cost,
        "cost_source": "local" if cost is not None else None,
        # rates (API-provided where documented, else derived)
        "subscription_cvr": link["subscription_cvr"] if link["subscription_cvr"] is not None else ratio(subs, clicks, 100),
        "spending_cvr": link["spending_cvr"],
        "epc": (link["epc_net"] if basis == "net" else link["epc_gross"]) if link["link_type"] == "TRACKING" else ratio(earn, clicks),
        "aeps": (link["aeps_net"] if basis == "net" else link["aeps_gross"]) if link["aeps_gross"] is not None else ratio(earn, subs),
        "cpc": ratio(cost, clicks), "cps": ratio(cost, subs),
        "profit": profit, "roi": ratio(profit, cost, 100) if cost else None,
    }


def links(db: Database, creator_ids: tuple[str, ...] | None, basis: str = "gross", link_type: str | None = None) -> dict:
    where, params = ["1=1"], []
    if creator_ids:
        where.append(f"l.creator_id IN ({','.join('?' * len(creator_ids))})")
        params += list(creator_ids)
    if link_type:
        where.append("l.link_type=?")
        params.append(link_type)
    rows = db.query(
        f"""SELECT l.*, c.name creator_name, cc.cost_cents, cc.spent_on, cc.note cost_note
            FROM links l LEFT JOIN creators c ON c.id=l.creator_id
            LEFT JOIN campaign_costs cc ON cc.link_id=l.id AND cc.link_type=l.link_type
            WHERE {' AND '.join(where)}""", params)
    items = []
    for r in rows:
        m = compute(r, r["cost_cents"], basis)
        items.append({
            "id": r["id"], "link_type": r["link_type"], "type_label": TYPE_LABELS.get(r["link_type"], r["link_type"]),
            "name": r["name"] or r["message"] or f"{TYPE_LABELS.get(r['link_type'])} {r['id']}",
            "creator_id": r["creator_id"], "creator_name": r["creator_name"], "source": r["source"], "code": r["code"],
            "clicks": r["click_count"], "subscribers": r["sub_count"], "paying_fans": r["paying_fans"],
            "spend_claim_pct": r["spend_claim"], "finished": r["finished"], "sub_limit": r["sub_limit"],
            "sub_duration_days": r["sub_duration"], "discount_pct": r["discount"], "target_fan_type": r["target_type"],
            "earnings_gross": r["earnings_gross"], "earnings_net": r["earnings_net"], "currency": r["currency"],
            "created_ms": r["created_ms"], "expired_ms": r["expired_ms"], "updated_ms": r["updated_ms"], "fetched_at": r["fetched_at"],
            "spent_on": r["spent_on"], "cost_note": r["cost_note"], **m,
        })
    items.sort(key=lambda x: (x["earnings"] or 0), reverse=True)

    def summarize(group: list[dict]) -> dict:
        clicks = sum(i["clicks"] or 0 for i in group if i["link_type"] == "TRACKING")
        tracked_subs = sum(i["subscribers"] or 0 for i in group if i["link_type"] == "TRACKING")
        subs = sum(i["subscribers"] or 0 for i in group)
        earn = sum(i["earnings"] or 0 for i in group)
        costed = [i for i in group if i["cost"] is not None]
        cost = sum(i["cost"] for i in costed) if costed else None
        costed_earn = sum(i["earnings"] or 0 for i in costed)
        costed_clicks = sum(i["clicks"] or 0 for i in costed)
        costed_subs = sum(i["subscribers"] or 0 for i in costed)
        profit = costed_earn - cost if cost is not None else None
        return {
            "links": len(group), "clicks": clicks, "subscribers": subs, "tracking_subscribers": tracked_subs,
            "trial_claims": sum(i["subscribers"] or 0 for i in group if i["link_type"] == "TRIAL"),
            "paying_fans": sum(i["paying_fans"] or 0 for i in group), "earnings": earn,
            "subscription_cvr": ratio(tracked_subs, clicks, 100), "epc": ratio(sum(i["earnings"] or 0 for i in group if i["link_type"] == "TRACKING"), clicks),
            "aeps": ratio(earn, subs), "cost": cost, "costed_links": len(costed),
            "cpc": ratio(cost, costed_clicks), "cps": ratio(cost, costed_subs), "profit": profit, "roi": ratio(profit, cost, 100) if cost else None,
        }

    by_source: dict[str, list] = {}
    by_creator: dict[str, list] = {}
    by_type: dict[str, list] = {}
    for i in items:
        by_source.setdefault(i["source"] or "(no source)", []).append(i)
        by_creator.setdefault(i["creator_name"] or i["creator_id"], []).append(i)
        by_type.setdefault(i["type_label"], []).append(i)

    tracking = [i for i in items if i["link_type"] == "TRACKING" and (i["clicks"] or 0) >= 100 and i["subscription_cvr"] is not None]
    median_cvr = statistics.median([i["subscription_cvr"] for i in tracking]) if tracking else None
    under = []
    for i in items:
        reasons = []
        if i["roi"] is not None and i["roi"] < 0:
            reasons.append(f"negative ROI ({i['roi']:.0f}%)")
        if median_cvr and i in tracking and i["subscription_cvr"] < median_cvr / 2:
            reasons.append(f"CVR {i['subscription_cvr']:.2f}% < half the median ({median_cvr:.2f}%)")
        if i["link_type"] == "TRACKING" and (i["clicks"] or 0) >= 200 and not i["subscribers"]:
            reasons.append("≥200 clicks with zero subscribers")
        if reasons:
            under.append({"id": i["id"], "link_type": i["link_type"], "name": i["name"], "creator_name": i["creator_name"], "reasons": reasons})

    sync = db.one("SELECT MIN(fetched_at) oldest, MAX(fetched_at) newest, SUM(CASE WHEN status!='ok' THEN 1 ELSE 0 END) failed FROM dataset_sync WHERE dataset='links'")
    return {
        "summary": summarize(items),
        "items": items,
        "by_source": sorted([{"source": k, **summarize(v)} for k, v in by_source.items()], key=lambda x: -(x["earnings"] or 0)),
        "by_creator": sorted([{"creator": k, **summarize(v)} for k, v in by_creator.items()], key=lambda x: -(x["earnings"] or 0)),
        "by_type": [{"type": k, **summarize(v)} for k, v in by_type.items()],
        "underperforming": under,
        "median_tracking_cvr": median_cvr,
        "sync": sync,
        "notes": [
            "Link earnings, clicks and subscribers are cumulative (lifetime of the link), as reported by Infloww.",
            "Attribution uses the fan's most recent tracking/free-trial link, not necessarily the first touch.",
            "Promotional cost is not provided by Infloww — CPC, CPS, profit and ROI use costs entered locally in Settings.",
            "Free-trial 'subscribers' are trial claims, not paid subscriptions.",
        ],
    }


def link_fans(items: list[dict]) -> list[dict]:
    from app.analytics.common import mask_id, mask_name
    out = []
    for f in items:
        tot_g = sum((f.get(k) or 0) for k in ("subscriptionEarningGross", "postsEarningGross", "messagesEarningGross", "streamsEarningGross", "tipsEarningGross"))
        tot_n = sum((f.get(k) or 0) for k in ("subscriptionEarningNet", "postsEarningNet", "messagesEarningNet", "streamsEarningNet", "tipsEarningNet"))
        out.append({"fan_ref": mask_id(f.get("fanId")), "fan_name": mask_name(f.get("fanName")), "subscribed_ms": f.get("subscribedTime"),
                    "earnings_gross": tot_g, "earnings_net": tot_n, "subscription_gross": f.get("subscriptionEarningGross"),
                    "messages_gross": f.get("messagesEarningGross"), "posts_gross": f.get("postsEarningGross"),
                    "tips_gross": f.get("tipsEarningGross"), "streams_gross": f.get("streamsEarningGross"), "currency": f.get("currency")})
    out.sort(key=lambda x: -x["earnings_gross"])
    return out
