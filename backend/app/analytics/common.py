"""Shared analytics primitives: filters, revenue recognition rules, safe ratios."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# ---------------------------------------------------------------- revenue recognition (documented in METRIC_DEFINITIONS.md)
# Infloww transaction statuses: loading | done | undo | pending_return
RECOGNIZED_STATUSES = ("done", "loading")   # earned; 'loading' = not yet cleared on OnlyFans (re-synced every 12h)
REVERSED_STATUS = "undo"                    # reversed after the fact (refund / chargeback — the API does not say which)
PENDING_RETURN_STATUS = "pending_return"    # reversal in progress

TYPE_LABELS = {
    "Subscription": "New subscriptions",
    "Recurring Subscription": "Recurring subscriptions",
    "Messages": "PPV messages",
    "Posts": "PPV posts",
    "Tips": "Tips",
    "Streams": "Live streams",
    "Referrals": "Referrals",
    "Unknown": "Unknown",
}
SUBSCRIPTION_TYPES = ("Subscription", "Recurring Subscription")
PPV_TYPES = ("Messages", "Posts")


@dataclass(frozen=True)
class Filters:
    start: date
    end: date
    creator_ids: tuple[str, ...] | None = None
    basis: str = "gross"   # gross | net

    @property
    def money_col(self) -> str:
        return "net" if self.basis == "net" else "amount"


def creator_clause(f: Filters, col: str = "creator_id") -> tuple[str, list]:
    if not f.creator_ids:
        return "", []
    return f" AND {col} IN ({','.join('?' * len(f.creator_ids))})", list(f.creator_ids)


def recognized_clause(alias: str = "") -> str:
    a = f"{alias}." if alias else ""
    return f"{a}status IN ('done','loading')"


def ratio(n, d, scale: float = 1.0):
    if n is None or d in (None, 0):
        return None
    return n / d * scale


def growth(cur, prev) -> dict:
    """Growth vs previous period. Returns value=None with a reason instead of a misleading %."""
    if cur is None or prev is None:
        return {"value": None, "reason": "comparison data unavailable"}
    if prev == 0:
        return {"value": None, "reason": "previous period was zero" if cur else "no activity in either period"}
    return {"value": (cur - prev) / abs(prev) * 100, "reason": None}


def withhold(keys, reason: str = "previous period not fully synced yet") -> dict:
    return {k: {"value": None, "reason": reason} for k in keys}


def mask_name(name: str | None) -> str | None:
    """Fan names are personal data: show only an initial + length hint by default."""
    if not name:
        return None
    n = name.strip()
    return n[:1] + "•" * min(6, max(2, len(n) - 1))


def mask_id(fan_id: str | None) -> str | None:
    if not fan_id:
        return None
    return fan_id[:-4].rsplit("-", 1)[0] + "-…" + fan_id[-4:] if len(fan_id) > 6 else fan_id
