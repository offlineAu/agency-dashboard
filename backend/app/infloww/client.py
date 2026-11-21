"""Centralised, READ-ONLY Infloww API client.

Guarantees (each covered by tests/test_client.py):
  * Only HTTP GET is ever sent; any other method raises ReadOnlyViolation before a socket is opened,
    both in this class and in an httpx request hook (defence in depth).
  * Only paths in app.infloww.registry.ENDPOINTS may be requested.
  * Auth uses exactly the documented headers: `Authorization: <raw key>` (no Bearer) and `x-oid`.
  * Credentials are never logged or recorded in telemetry.
  * 429 / 5xx / network errors are retried with backoff; 400/401/403 are not.
  * Cursor pagination follows `cursor` + `hasMore` until exhausted.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

import httpx

from app.core.config import Settings
from app.infloww.monitor import CallRecord, Monitor
from app.infloww.registry import ALLOWED_METHODS, ENDPOINTS

log = logging.getLogger("infloww")

SENSITIVE_PARAM_KEYS = {"authorization", "x-oid", "api_key", "apikey", "key", "token"}


class ReadOnlyViolation(RuntimeError):
    """Raised when code attempts a non-GET request or an unlisted endpoint."""


class InflowwError(Exception):
    def __init__(self, kind: str, message: str, status: int | None = None, request_id: str | None = None):
        super().__init__(message)
        self.kind = kind            # config | auth | forbidden | bad_request | rate_limit | server | network | invalid_response
        self.status = status
        self.request_id = request_id

    def to_dict(self) -> dict:
        return {"kind": self.kind, "message": str(self), "status": self.status, "request_id": self.request_id}


def _retry_after(resp: httpx.Response) -> float | None:
    v = resp.headers.get("retry-after")
    try:
        return max(0.0, float(v)) if v is not None else None
    except ValueError:
        return None


def _classify(status: int) -> str:
    if status == 401:
        return "auth"
    if status == 403:
        return "forbidden"
    if status == 429:
        return "rate_limit"
    if status >= 500:
        return "server"
    return "bad_request"


def _sanitize(params: dict) -> dict:
    return {k: ("<redacted>" if k.lower() in SENSITIVE_PARAM_KEYS else v) for k, v in params.items()}


async def _enforce_get(request: httpx.Request) -> None:
    if request.method.upper() not in ALLOWED_METHODS:
        raise ReadOnlyViolation(f"Blocked non-GET request to Infloww: {request.method}")


class RateLimiter:
    """At most `qpm` acquisitions per 60s, evenly spaced.

    Infloww throttles short bursts even when the per-minute total is under its limit (observed live:
    6 concurrent requests at ~300ms latency drew 429s). Spacing starts by 60/qpm seconds keeps the
    instantaneous rate at the average rate, so we never trip it; the sliding window is kept as a backstop.
    """

    def __init__(self, qpm: int) -> None:
        self.qpm = max(1, qpm)
        self.interval = 60.0 / self.qpm
        self._next = 0.0
        self._stamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                self._stamps = [t for t in self._stamps if now - t < 60]
                if len(self._stamps) < self.qpm and now >= self._next:
                    self._stamps.append(now)
                    self._next = now + self.interval
                    return
                wait = max(self._next - now, 60 - (now - self._stamps[0]) + 0.01 if len(self._stamps) >= self.qpm else 0.0)
            await asyncio.sleep(max(wait, 0.001))


class InflowwClient:
    def __init__(self, settings: Settings, monitor: Monitor, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.monitor = monitor
        self._http = httpx.AsyncClient(
            base_url=settings.infloww_base_url.rstrip("/"),
            timeout=settings.infloww_timeout_s,
            transport=transport,
            event_hooks={"request": [_enforce_get]},
            headers={"Accept": "application/json", "User-Agent": "agency-dashboard/1.0 (read-only)"},
        )
        self._global_limiter = RateLimiter(settings.infloww_qpm)
        self._endpoint_limiters = {p: RateLimiter(e.qpm) for p, e in ENDPOINTS.items() if e.qpm}
        self._sem = asyncio.Semaphore(settings.infloww_concurrency)

    async def aclose(self) -> None:
        await self._http.aclose()

    # -- request building -------------------------------------------------------------------------
    def _auth_headers(self) -> dict[str, str]:
        if not self.settings.configured:
            raise InflowwError("config", "INFLOWW_API_KEY / INFLOWW_AGENCY_OID are not configured on the backend")
        return {
            "Authorization": self.settings.infloww_api_key.get_secret_value(),
            "x-oid": self.settings.infloww_agency_oid,
        }

    def _encode_params(self, params: dict[str, Any]) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for k, v in params.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                if self.settings.infloww_array_style == "comma":
                    out.append((k, ",".join(str(x) for x in v)))
                else:
                    out.extend((k, str(x)) for x in v)
            elif isinstance(v, bool):
                out.append((k, "true" if v else "false"))
            else:
                out.append((k, str(v)))
        return out

    # -- core request -----------------------------------------------------------------------------
    async def request(self, method: str, path: str, params: dict[str, Any] | None = None) -> dict:
        if method.upper() not in ALLOWED_METHODS:
            raise ReadOnlyViolation(f"Infloww client is read-only; refused {method} {path}")
        if path not in ENDPOINTS:
            raise ReadOnlyViolation(f"Endpoint not in allowlist: {path}")
        return await self.get(path, params or {})

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        if path not in ENDPOINTS:
            raise ReadOnlyViolation(f"Endpoint not in allowlist: {path}")
        params = dict(params or {})
        headers = self._auth_headers()
        encoded = self._encode_params(params)
        attempts = self.settings.infloww_max_retries + 1
        last_exc: InflowwError | None = None

        for attempt in range(1, attempts + 1):
            retry_after: float | None = None
            await self._global_limiter.acquire()
            if path in self._endpoint_limiters:
                await self._endpoint_limiters[path].acquire()
            t0 = time.perf_counter()
            status = None
            req_id = None
            try:
                async with self._sem:
                    resp = await self._http.get(path, params=encoded, headers=headers)
                status = resp.status_code
                req_id = resp.headers.get("x-request-id")
                dur = (time.perf_counter() - t0) * 1000
                if status == 200:
                    try:
                        body = resp.json()
                    except ValueError:
                        raise InflowwError("invalid_response", "Response was not JSON", status, req_id)
                    if not isinstance(body, dict) or "data" not in body:
                        raise InflowwError("invalid_response", "Response missing 'data' envelope", status, req_id)
                    n = _count_records(body)
                    self.monitor.record(CallRecord(time.time(), path, _sanitize(params), status, dur, n, request_id=req_id, attempt=attempt))
                    log.info("infloww GET %s status=%s records=%s ms=%.0f req_id=%s", path, status, n, dur, req_id)
                    return body
                msg = _error_message(resp)
                err = InflowwError(_classify(status), msg, status, req_id)
                retry_after = _retry_after(resp)
            except InflowwError as e:
                err = e
                dur = (time.perf_counter() - t0) * 1000
            except httpx.HTTPError as e:
                dur = (time.perf_counter() - t0) * 1000
                err = InflowwError("network", f"{type(e).__name__}: {e}", None, None)

            self.monitor.record(CallRecord(time.time(), path, _sanitize(params), status, dur, None, err.kind, str(err), err.request_id, attempt))
            log.warning("infloww GET %s failed kind=%s status=%s req_id=%s msg=%s", path, err.kind, status, err.request_id, str(err)[:200])
            last_exc = err
            if err.kind not in ("rate_limit", "server", "network") or attempt == attempts:
                raise err
            backoff = min(30.0, (2 ** attempt) + random.random())
            if err.kind == "rate_limit" and retry_after is not None:
                backoff = min(60.0, retry_after + random.random())
            await asyncio.sleep(backoff)
        raise last_exc  # pragma: no cover

    async def paginate(self, path: str, params: dict[str, Any] | None = None, max_pages: int = 2000) -> list[dict]:
        """Follow cursor/hasMore until exhausted. Raises if pagination cannot complete."""
        ep = ENDPOINTS[path]
        params = dict(params or {})
        params["limit"] = ep.max_limit
        items: list[dict] = []
        cursor = None
        seen: set[str] = set()
        for _ in range(max_pages):
            if cursor is not None:
                params["cursor"] = cursor
            body = await self.get(path, params)
            data = body.get("data") or {}
            items.extend(data.get("list") or [])
            has_more = bool(body.get("hasMore"))
            cursor = body.get("cursor")
            if not has_more:
                return items
            if cursor in (None, "") or str(cursor) in seen:
                self.monitor.pagination_incomplete(path)
                raise InflowwError("invalid_response", f"hasMore=true but cursor missing/repeated on {path}")
            seen.add(str(cursor))
        self.monitor.pagination_incomplete(path)
        raise InflowwError("invalid_response", f"Pagination exceeded {max_pages} pages on {path}")


def _count_records(body: dict) -> int | None:
    data = body.get("data")
    if isinstance(data, dict) and isinstance(data.get("list"), list):
        return len(data["list"])
    return 1 if data else 0


def _error_message(resp: httpx.Response) -> str:
    try:
        j = resp.json()
        if isinstance(j, dict) and j.get("errorMessage"):
            return str(j["errorMessage"])[:300]
    except ValueError:
        pass
    ctype = resp.headers.get("content-type", "")
    if "html" in ctype and "cloudflare" in resp.text[:3000].lower():
        return f"HTTP {resp.status_code} blocked by Cloudflare edge (not an Infloww JSON error)"
    return f"HTTP {resp.status_code}"
