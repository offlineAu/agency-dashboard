"""DEVELOPMENT ONLY: run the backend against the synthetic fake Infloww (tests/fake_infloww.py).

    cd backend && .venv/bin/python -m scripts.fixture_server

Uses a separate database (data/fixture.db) and sets FIXTURE_MODE so every screen shows a
"FIXTURE DATA — not from Infloww" banner. Never used by the production entrypoint (app.main:app).
"""
from __future__ import annotations

import os

os.environ.update({"FIXTURE_MODE": "true", "INFLOWW_API_KEY": "test-key-0123456789", "INFLOWW_AGENCY_OID": "999000111",
                   "INFLOWW_BASE_URL": "https://fixture.invalid", "DATABASE_PATH": "data/fixture.db", "BACKGROUND_SYNC": "true",
                   "FAN_HISTORY_DAYS": "120", "DASHBOARD_ACCESS_TOKEN": ""})

import uvicorn  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.infloww.client import InflowwClient  # noqa: E402
from app.infloww.monitor import monitor  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.fake_infloww import FakeInfloww  # noqa: E402

fake = FakeInfloww(seed=11, days=130, creators=6, employees=8, tx_per_day=30)
app = create_app()
app.state.client = InflowwClient(get_settings(), monitor, transport=fake.transport())

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
