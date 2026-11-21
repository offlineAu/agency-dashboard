"""In-process telemetry for outbound Infloww calls (powers the API Status page).

Records never contain credentials: only path, sanitised params, status, timing and counts.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import asdict, dataclass, field
from threading import Lock


@dataclass
class CallRecord:
    ts: float
    path: str
    params: dict
    status: int | None
    duration_ms: float
    records: int | None
    error_kind: str | None = None
    error_message: str | None = None
    request_id: str | None = None
    attempt: int = 1


@dataclass
class EndpointStats:
    path: str
    calls: int = 0
    successes: int = 0
    failures: int = 0
    records: int = 0
    total_ms: float = 0.0
    last_success: float | None = None
    last_failure: float | None = None
    last_error: str | None = None
    last_error_kind: str | None = None
    last_status: int | None = None
    auth_errors: int = 0
    rate_limit_errors: int = 0
    pages_incomplete: int = 0
    durations: deque = field(default_factory=lambda: deque(maxlen=50))

    def to_dict(self) -> dict:
        d = asdict(self)
        durs = sorted(self.durations)
        d.pop("durations")
        d["avg_ms"] = round(self.total_ms / self.calls, 1) if self.calls else None
        d["p95_ms"] = round(durs[int(len(durs) * 0.95) - 1 if len(durs) > 1 else 0], 1) if durs else None
        return d


class Monitor:
    def __init__(self, max_log: int = 500) -> None:
        self._lock = Lock()
        self.log: deque[CallRecord] = deque(maxlen=max_log)
        self.stats: dict[str, EndpointStats] = {}
        self.started = time.time()

    def record(self, rec: CallRecord) -> None:
        with self._lock:
            self.log.appendleft(rec)
            st = self.stats.setdefault(rec.path, EndpointStats(rec.path))
            st.calls += 1
            st.total_ms += rec.duration_ms
            st.durations.append(rec.duration_ms)
            st.last_status = rec.status
            if rec.error_kind is None:
                st.successes += 1
                st.records += rec.records or 0
                st.last_success = rec.ts
            else:
                st.failures += 1
                st.last_failure = rec.ts
                st.last_error = rec.error_message
                st.last_error_kind = rec.error_kind
                if rec.error_kind in ("auth", "forbidden"):
                    st.auth_errors += 1
                if rec.error_kind == "rate_limit":
                    st.rate_limit_errors += 1

    def pagination_incomplete(self, path: str) -> None:
        with self._lock:
            self.stats.setdefault(path, EndpointStats(path)).pages_incomplete += 1

    def snapshot(self, log_limit: int = 100) -> dict:
        with self._lock:
            return {
                "started": self.started,
                "endpoints": [s.to_dict() for s in sorted(self.stats.values(), key=lambda s: s.path)],
                "recent_calls": [asdict(r) for r in list(self.log)[:log_limit]],
            }


monitor = Monitor()
