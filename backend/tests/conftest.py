from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from app.core import config
from app.core.dates import today_utc
from app.infloww.client import InflowwClient
from app.infloww.monitor import Monitor
from app.store.db import Database
from app.sync.engine import SyncEngine
from tests.fake_infloww import KEY, OID, FakeInfloww


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("INFLOWW_API_KEY", KEY)
    monkeypatch.setenv("INFLOWW_AGENCY_OID", OID)
    monkeypatch.setenv("INFLOWW_BASE_URL", "https://openapi.infloww.test")
    monkeypatch.setenv("BACKGROUND_SYNC", "false")
    monkeypatch.setenv("DASHBOARD_ACCESS_TOKEN", "")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("INFLOWW_MAX_RETRIES", "2")
    monkeypatch.setenv("INFLOWW_QPM", "600000")  # fake API: no pacing needed
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


@pytest.fixture
def settings():
    return config.get_settings()


@pytest.fixture
def fake():
    return FakeInfloww()


@pytest.fixture
def client(settings, fake):
    c = InflowwClient(settings, Monitor(), transport=fake.transport())
    yield c
    asyncio.get_event_loop_policy()


@pytest.fixture
def db(settings):
    return Database(settings.database_path)


@pytest.fixture
def engine(db, client, settings):
    return SyncEngine(db, client, settings)


@pytest.fixture
def synced(engine):
    end = today_utc()
    start = end - timedelta(days=59)
    asyncio.run(engine.ensure(start, end))
    asyncio.run(engine.sync_links())
    asyncio.run(engine.sync_invoices())
    return engine


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Make retry backoff instant in tests."""
    real = asyncio.sleep

    async def fast(d, *a, **k):
        return await real(0)

    monkeypatch.setattr("app.infloww.client.asyncio.sleep", fast)
