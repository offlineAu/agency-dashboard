"""Date helpers. All Infloww windows and all dashboard day buckets are UTC."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

UTC = timezone.utc


def today_utc() -> date:
    return datetime.now(UTC).date()


def parse_day(s: str | date) -> date:
    return s if isinstance(s, date) else date.fromisoformat(str(s)[:10])


def day_start_ms(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp() * 1000)


def day_end_ms(d: date) -> int:
    """Inclusive last millisecond of the UTC day."""
    return day_start_ms(d + timedelta(days=1)) - 1


def window_end_ms(d: date) -> int:
    """endTime for a unix-ms request window ending on day d, capped at now.

    Infloww rejects future endTime values ("must be a past or present time"), so a window that
    includes today must stop at the current moment. A small margin absorbs clock skew.
    """
    import time
    return min(day_end_ms(d), int(time.time() * 1000) - 5_000)


def ms_to_day(ms: int | str | None) -> str | None:
    if ms in (None, ""):
        return None
    return datetime.fromtimestamp(int(ms) / 1000, UTC).date().isoformat()


def iso_to_ms(s: str | None) -> int | None:
    if not s:
        return None
    s = str(s)
    if s.isdigit():
        return int(s)
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)


def days_between(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def contiguous_runs(days: list[date], max_len: int = 31) -> list[tuple[date, date]]:
    """Group sorted days into contiguous runs no longer than max_len days."""
    runs: list[tuple[date, date]] = []
    for d in sorted(set(days)):
        if runs and (d - runs[-1][1]).days == 1 and (d - runs[-1][0]).days < max_len:
            runs[-1] = (runs[-1][0], d)
        else:
            runs.append((d, d))
    return runs


def previous_period(start: date, end: date) -> tuple[date, date]:
    n = (end - start).days + 1
    return start - timedelta(days=n), start - timedelta(days=1)
