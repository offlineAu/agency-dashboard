"""SQLite store for synced Infloww data.

The Infloww API is the source of truth. This database only caches what the API returned, with
per-day coverage records so the UI can say exactly how fresh/complete each figure is. Rows for a
window are only replaced after that window's fetch fully succeeded (including pagination), so a
failed or partial response never overwrites previously good data.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS creators (
  id TEXT PRIMARY KEY, platform_pid INTEGER, name TEXT, nick_name TEXT, user_name TEXT, tag_name TEXT,
  status TEXT, connected INTEGER NOT NULL DEFAULT 0, created_ms INTEGER, deleted_ms INTEGER, fetched_at REAL
);
CREATE INDEX IF NOT EXISTS ix_creators_pid ON creators(platform_pid);

CREATE TABLE IF NOT EXISTS employees (
  employee_id INTEGER PRIMARY KEY, name TEXT, status TEXT, created_ms INTEGER, deleted_ms INTEGER, fetched_at REAL
);
CREATE TABLE IF NOT EXISTS employee_creators (
  employee_id INTEGER, creator_id TEXT, PRIMARY KEY (employee_id, creator_id)
);

CREATE TABLE IF NOT EXISTS transactions (
  id TEXT PRIMARY KEY, creator_id TEXT NOT NULL, platform_pid INTEGER, transaction_id TEXT,
  fan_id TEXT, fan_name TEXT, created_ms INTEGER NOT NULL, day TEXT NOT NULL,
  type TEXT, tip_source TEXT, status TEXT, amount INTEGER, fee INTEGER, net INTEGER, currency TEXT
);
CREATE INDEX IF NOT EXISTS ix_tx_creator_day ON transactions(creator_id, day);
CREATE INDEX IF NOT EXISTS ix_tx_day ON transactions(day);
CREATE INDEX IF NOT EXISTS ix_tx_fan ON transactions(fan_id);

CREATE TABLE IF NOT EXISTS refunds (
  id TEXT PRIMARY KEY, creator_id TEXT NOT NULL, transaction_id TEXT, fan_id TEXT,
  payment_ms INTEGER, refund_ms INTEGER NOT NULL, day TEXT NOT NULL, status TEXT,
  amount INTEGER, transaction_type TEXT, currency TEXT
);
CREATE INDEX IF NOT EXISTS ix_refunds_creator_day ON refunds(creator_id, day);

CREATE TABLE IF NOT EXISTS sales_records (
  id TEXT PRIMARY KEY, creator_id TEXT NOT NULL, platform_pid INTEGER, transaction_id TEXT, fan_id TEXT,
  created_ms INTEGER, day TEXT NOT NULL, type TEXT, tip_source TEXT, status TEXT,
  amount INTEGER, fee INTEGER, net INTEGER, sales_rule TEXT, employee_id INTEGER, sales_amount INTEGER, currency TEXT
);
CREATE INDEX IF NOT EXISTS ix_sales_creator_day ON sales_records(creator_id, day);
CREATE INDEX IF NOT EXISTS ix_sales_emp_day ON sales_records(employee_id, day);

CREATE TABLE IF NOT EXISTS emp_sales_daily (
  employee_id INTEGER, day TEXT, platform_pid INTEGER,
  sales INTEGER, ppv INTEGER, tips INTEGER, direct_msg INTEGER, priority_mass INTEGER, mass INTEGER, currency TEXT,
  PRIMARY KEY (employee_id, day, platform_pid)
);
CREATE TABLE IF NOT EXISTS emp_chat_daily (
  employee_id INTEGER, day TEXT, platform_pid INTEGER,
  dms_sent INTEGER, dm_ppvs_sent INTEGER, golden_ratio REAL, ppvs_unlocked INTEGER, unlock_rate REAL,
  fans_chatted INTEGER, characters INTEGER, resp_scheduled_ms INTEGER, resp_clocked_ms INTEGER,
  PRIMARY KEY (employee_id, day, platform_pid)
);

-- Daily creator-report metrics (long format): activeFans, expiredFans, newSubscribers, ...
CREATE TABLE IF NOT EXISTS creator_daily (
  platform_pid INTEGER, day TEXT, metric TEXT, value REAL,
  PRIMARY KEY (platform_pid, day, metric)
);

-- chat-summary has no date field: stored per requested range
CREATE TABLE IF NOT EXISTS creator_chat_range (
  platform_pid INTEGER, start_day TEXT, end_day TEXT, reply_ms REAL, fans_chatted INTEGER,
  messages_sent INTEGER, ppvs_sent INTEGER, fetched_at REAL,
  PRIMARY KEY (platform_pid, start_day, end_day)
);

CREATE TABLE IF NOT EXISTS links (
  id TEXT, link_type TEXT, creator_id TEXT, name TEXT, code TEXT, source TEXT, message TEXT, target_type TEXT,
  click_count INTEGER, sub_count INTEGER, sub_limit INTEGER, sub_duration INTEGER, discount INTEGER,
  paying_fans INTEGER, earnings_gross INTEGER, earnings_net INTEGER,
  subscription_cvr REAL, spending_cvr REAL, spend_claim REAL, epc_gross REAL, epc_net REAL, aeps_gross REAL, aeps_net REAL,
  finished INTEGER, currency TEXT, created_ms INTEGER, expired_ms INTEGER, updated_ms INTEGER, fetched_at REAL,
  PRIMARY KEY (link_type, id)
);
CREATE INDEX IF NOT EXISTS ix_links_creator ON links(creator_id);

CREATE TABLE IF NOT EXISTS invoices (
  billing_id TEXT PRIMARY KEY, invoice_id TEXT, period TEXT, currency TEXT, subscription INTEGER, discount INTEGER,
  tax INTEGER, total INTEGER, deductions INTEGER, balance_due INTEGER, paid INTEGER, pending INTEGER, fetched_at REAL
);

CREATE TABLE IF NOT EXISTS messages (
  kind TEXT, id TEXT, creator_id TEXT, employee_id INTEGER, status TEXT, sent_ms INTEGER, day TEXT,
  price INTEGER, times_sent INTEGER, purchases INTEGER, revenue INTEGER, preview TEXT, fail_reason TEXT,
  PRIMARY KEY (kind, id)
);

-- Coverage: one row per (dataset, scope, UTC day) that was fully fetched.
CREATE TABLE IF NOT EXISTS coverage (
  dataset TEXT, scope TEXT, day TEXT, fetched_at REAL, PRIMARY KEY (dataset, scope, day)
);
-- Non-windowed datasets (creators, employees, links...)
CREATE TABLE IF NOT EXISTS dataset_sync (
  dataset TEXT, scope TEXT, fetched_at REAL, status TEXT, error TEXT, records INTEGER, PRIMARY KEY (dataset, scope)
);
CREATE TABLE IF NOT EXISTS sync_errors (
  ts REAL, dataset TEXT, scope TEXT, kind TEXT, message TEXT
);

-- LOCAL settings (never sent to Infloww)
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS campaign_costs (
  link_type TEXT, link_id TEXT, cost_cents INTEGER NOT NULL, spent_on TEXT, note TEXT, updated_at REAL, PRIMARY KEY (link_type, link_id)
);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._write_lock = threading.Lock()
        # shared connection for :memory: (tests)
        self._shared = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None) if self.path == ":memory:" else None
        with self._write_lock:
            self._conn().executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        if self._shared is not None:
            self._shared.row_factory = sqlite3.Row
            return self._shared
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        with self._write_lock:
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def query(self, sql: str, params: tuple | list | dict = ()) -> list[dict]:
        cur = self._conn().execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def one(self, sql: str, params: tuple | list | dict = ()) -> dict | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: tuple | list | dict = ()):
        row = self._conn().execute(sql, params).fetchone()
        return row[0] if row else None

    # settings helpers
    def get_setting(self, key: str, default=None):
        v = self.scalar("SELECT value FROM settings WHERE key=?", (key,))
        return default if v is None else v

    def set_setting(self, key: str, value) -> None:
        with self.write() as c:
            if value is None:
                c.execute("DELETE FROM settings WHERE key=?", (key,))
            else:
                c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
