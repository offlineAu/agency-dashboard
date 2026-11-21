"""Read-only guarantees and spec conformance."""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

import httpx
import pytest
import yaml

from app.infloww.client import InflowwClient, InflowwError, ReadOnlyViolation
from app.infloww.monitor import Monitor
from app.infloww.registry import ENDPOINTS
from tests.fake_infloww import KEY, OID

ROOT = Path(__file__).resolve().parents[2]
SPEC = yaml.safe_load((ROOT / "docs/spec/infloww-openapi.yaml").read_text())


def test_spec_is_get_only_and_registry_matches_spec():
    methods = {(p, m) for p, ops in SPEC["paths"].items() for m in ops if m in ("get", "post", "put", "patch", "delete")}
    assert all(m == "get" for _, m in methods), "spec unexpectedly contains mutating methods"
    assert {p for p, _ in methods} == set(ENDPOINTS), "registry drifted from the OpenAPI spec"


def test_registry_limits_match_spec():
    for path, ep in ENDPOINTS.items():
        params = SPEC["paths"][path]["get"].get("parameters", [])
        for p in params:
            if "$ref" in p:
                p = SPEC["components"]["parameters"][p["$ref"].split("/")[-1]]
            if p.get("name") == "limit":
                assert p["schema"].get("maximum", 100) == ep.max_limit, path


def test_exact_auth_headers(client, fake):
    asyncio.run(client.get("/v1/creators", {"limit": 1}))
    req_headers = None

    captured = {}

    def h(request: httpx.Request):
        captured.update(request.headers)
        return fake.handle(request)

    c = InflowwClient(client.settings, Monitor(), transport=httpx.MockTransport(h))
    asyncio.run(c.get("/v1/creators", {"limit": 1}))
    assert captured["authorization"] == KEY          # raw key, no "Bearer"
    assert not captured["authorization"].lower().startswith("bearer")
    assert captured["x-oid"] == OID
    assert req_headers is None


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_client_refuses_mutating_methods(client, method, fake):
    with pytest.raises(ReadOnlyViolation):
        asyncio.run(client.request(method, "/v1/creators"))
    # defence in depth: even the underlying httpx client refuses
    with pytest.raises(ReadOnlyViolation):
        asyncio.run(client._http.request(method, "/v1/creators"))
    assert not any(m != "GET" for m, _, _ in fake.calls)


def test_client_refuses_unlisted_endpoint(client):
    with pytest.raises(ReadOnlyViolation):
        asyncio.run(client.get("/v1/creators/delete"))


def test_no_mutating_http_calls_in_source():
    """Static guard: no code path issues non-GET verbs to Infloww."""
    src = (ROOT / "backend/app").rglob("*.py")
    bad = []
    for f in src:
        t = f.read_text()
        for m in re.finditer(r"self\.(?:client|_http)\.(post|put|patch|delete)\(", t):
            bad.append(f"{f}:{m.group(0)}")
        for m in re.finditer(r"\.client\.(post|put|patch|delete)\(", t):
            bad.append(f"{f}:{m.group(0)}")
    assert not bad, bad


def test_credentials_never_logged_or_recorded(client, fake, caplog):
    caplog.set_level(logging.DEBUG)
    asyncio.run(client.paginate("/v1/creators", {}))
    fake.fail_next["/v1/employees"] = [401]
    with pytest.raises(InflowwError):
        asyncio.run(client.get("/v1/employees"))
    blob = caplog.text + repr(client.monitor.snapshot())
    assert KEY not in blob and OID not in blob


def test_retry_on_429_and_500_then_success(client, fake):
    fake.fail_next["/v1/employees"] = [429, 500]
    body = asyncio.run(client.get("/v1/employees"))
    assert body["data"]["list"]
    st = {e["path"]: e for e in client.monitor.snapshot()["endpoints"]}["/v1/employees"]
    assert st["rate_limit_errors"] == 1 and st["failures"] == 2 and st["successes"] == 1


def test_no_retry_on_auth_error(settings, fake):
    settings2 = settings.model_copy(update={"infloww_agency_oid": "wrong"})
    c = InflowwClient(settings2, Monitor(), transport=fake.transport())
    with pytest.raises(InflowwError) as ei:
        asyncio.run(c.get("/v1/creators"))
    assert ei.value.kind == "auth"
    assert len(fake.calls) == 1


def test_not_configured_raises_config_error(settings, fake):
    c = InflowwClient(settings.model_copy(update={"infloww_api_key": type(settings.infloww_api_key)("")}), Monitor(), transport=fake.transport())
    with pytest.raises(InflowwError) as ei:
        asyncio.run(c.get("/v1/creators"))
    assert ei.value.kind == "config" and not fake.calls


def test_pagination_collects_all_pages(client, fake):
    rows = asyncio.run(client.paginate("/v1/transactions", {"creatorId": "1000", "startTime": 0, "endTime": 30 * 86400_000}))
    assert rows == []  # far past -> empty, single call
    from app.core.dates import day_start_ms, today_utc, window_end_ms as day_end_ms
    from datetime import timedelta
    a, b = today_utc() - timedelta(days=30), today_utc()
    rows = asyncio.run(client.paginate("/v1/transactions", {"creatorId": "1000", "startTime": day_start_ms(a), "endTime": day_end_ms(b)}))
    expected = [t for t in fake.tx["1000"] if day_start_ms(a) <= int(t["createdTime"]) <= day_end_ms(b)]
    assert len(rows) == len(expected) > 100
    assert len({r["id"] for r in rows}) == len(rows)
    pages = [c for c in fake.calls if c[1] == "/v1/transactions"]
    assert all(c[2]["limit"] == ["100"] for c in pages)


def test_array_param_styles(settings, fake):
    seen = []

    def h(request):
        seen.append(str(request.url))
        return fake.handle(request)

    c = InflowwClient(settings, Monitor(), transport=httpx.MockTransport(h))
    asyncio.run(c.get("/v1/creator-report/rank", {"creatorIds": ["1000", "1001"], "startTime": "2026-01-01", "endTime": "2026-01-02"}))
    assert "creatorIds=1000&creatorIds=1001" in seen[-1]
    c2 = InflowwClient(settings.model_copy(update={"infloww_array_style": "comma"}), Monitor(), transport=httpx.MockTransport(h))
    asyncio.run(c2.get("/v1/creator-report/rank", {"creatorIds": ["1000", "1001"], "startTime": "2026-01-01", "endTime": "2026-01-02"}))
    assert "creatorIds=1000%2C1001" in seen[-1]


def test_base_url_trailing_v1_is_stripped():
    from app.core.config import Settings
    for v in ("https://openapi.infloww.com/v1", "https://openapi.infloww.com/v1/", "https://openapi.infloww.com/"):
        assert Settings(infloww_base_url=v, _env_file=None).infloww_base_url == "https://openapi.infloww.com"


def test_window_end_never_in_future():
    import time
    from app.core.dates import day_end_ms, today_utc, window_end_ms
    from datetime import timedelta
    now = time.time() * 1000
    assert window_end_ms(today_utc()) <= now
    y = today_utc() - timedelta(days=1)
    assert window_end_ms(y) == day_end_ms(y)  # past days are untouched


def test_rate_limiter_spaces_requests():
    import time
    from app.infloww.client import RateLimiter

    async def run():
        rl = RateLimiter(600)  # 10/s -> 100ms spacing
        t0 = time.monotonic()
        for _ in range(4):
            await rl.acquire()
        return time.monotonic() - t0
    assert asyncio.run(run()) >= 0.29  # 3 gaps of 100ms; no burst


def test_retry_after_header_is_honored():
    import httpx
    from app.infloww.client import _retry_after
    assert _retry_after(httpx.Response(429, headers={"retry-after": "3"})) == 3.0
    assert _retry_after(httpx.Response(429)) is None
