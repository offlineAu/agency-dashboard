"""Allowlist of Infloww endpoints this application may call.

Derived from docs/spec/infloww-openapi.yaml (Infloww API v1.4). tests/test_registry.py verifies this
list against the spec so it cannot drift. ONLY the GET method is ever permitted.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Window(str, Enum):
    NONE = "none"          # no time range
    DATETIME = "datetime"  # startTime/endTime as unix ms (UTC), <= 31 days
    DATE = "date"          # startTime/endTime as YYYY-MM-DD, <= 31 days, <= 366 days back
    MONTH = "month"        # billing months, <= 1 year


@dataclass(frozen=True)
class Endpoint:
    path: str
    window: Window
    paginated: bool
    max_limit: int = 100
    qpm: int | None = None          # endpoint-specific rate limit
    category: str = ""
    latency_note: str = ""


ENDPOINTS: dict[str, Endpoint] = {e.path: e for e in [
    Endpoint("/v1/creators", Window.NONE, True, category="creators", latency_note="up to 1h"),
    Endpoint("/v1/all-creators", Window.NONE, True, category="creators", latency_note="requires 'All Creators' scope"),
    Endpoint("/v1/transactions", Window.DATETIME, True, category="revenue", latency_note="up to 1h; 'loading' rows re-synced every 12h"),
    Endpoint("/v1/refunds", Window.DATETIME, True, category="revenue", latency_note="up to 1h"),
    Endpoint("/v1/links", Window.DATETIME, True, category="marketing", latency_note="up to 2h"),
    Endpoint("/v1/linkfans", Window.NONE, True, category="marketing", latency_note="up to 4h"),
    Endpoint("/v1/automated-messages", Window.DATETIME, True, max_limit=10, category="messages"),
    Endpoint("/v1/priority-mass-messages", Window.DATETIME, True, max_limit=10, category="messages"),
    Endpoint("/v1/transaction-perf/details", Window.DATETIME, True, category="attribution"),
    Endpoint("/v1/invoice-data/monthly-billing", Window.MONTH, False, qpm=10, category="billing"),
    Endpoint("/v1/transaction-perf/manual-assignment/details", Window.DATETIME, True, category="attribution"),
    Endpoint("/v1/creator-report/chat-summary", Window.DATE, False, category="creator-report", latency_note="up to 24h"),
    Endpoint("/v1/creator-report/fans/count", Window.DATE, False, category="creator-report", latency_note="up to 24h"),
    Endpoint("/v1/creator-report/fans/subscriber-count", Window.DATE, False, category="creator-report", latency_note="up to 24h"),
    Endpoint("/v1/creator-report/fans/renew-on", Window.DATE, False, category="creator-report", latency_note="up to 24h"),
    Endpoint("/v1/creator-report/fans/avg-subscription-length", Window.DATE, False, category="creator-report", latency_note="up to 24h"),
    Endpoint("/v1/creator-report/reach/profile-visitor-count", Window.DATE, False, category="creator-report", latency_note="up to 24h"),
    Endpoint("/v1/creator-report/rank", Window.DATE, False, category="creator-report", latency_note="up to 24h"),
    Endpoint("/v1/creator/status-change-log", Window.DATETIME, True, category="creators"),
    Endpoint("/v1/employees", Window.NONE, True, category="employees"),
    Endpoint("/v1/employees/assigned-creators", Window.NONE, True, category="employees"),
    Endpoint("/v1/employee-report/employee-sales-summary", Window.DATE, False, category="employee-report", latency_note="up to 24h"),
    Endpoint("/v1/employee-report/employee-chat-summary", Window.DATE, False, category="employee-report", latency_note="up to 24h"),
    Endpoint("/v1/scripts", Window.NONE, True, category="scripts"),
    Endpoint("/v1/script/statistics", Window.NONE, False, category="scripts"),
    Endpoint("/v1/script-tag", Window.NONE, True, category="scripts"),
    Endpoint("/v1/script-tag/statistics", Window.NONE, False, category="scripts"),
    Endpoint("/v1/script-sequence", Window.NONE, True, category="scripts"),
    Endpoint("/v1/script-sequence/statistics", Window.NONE, False, category="scripts"),
]}

ALLOWED_METHODS = frozenset({"GET"})
MAX_WINDOW_DAYS = 31
MAX_HISTORY_DAYS = 366
MAX_REPORT_IDS = 10
