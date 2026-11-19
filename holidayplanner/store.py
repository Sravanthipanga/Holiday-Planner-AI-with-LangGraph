"""Plan persistence.

Default backend: SQLite (stdlib sqlite3) at data/holidayplanner.db
(override with HOLIDAYPLANNER_DB). If DATABASE_URL is set to a postgres://
URL, the same schema is used via psycopg (optional dependency:
`pip install "psycopg[binary]"`).

Exercised locally: SQLite — yes (test suite + live server runs).
PostgreSQL: implemented against the same schema but NOT exercised locally;
there is no Postgres server in the development sandbox.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    thread_id TEXT PRIMARY KEY,
    request TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


class SqliteStore:
    backend = "sqlite"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def save(self, thread_id: str, request: str, plan: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO plans VALUES (?, ?, ?, ?)",
                (thread_id, request, json.dumps(plan), datetime.now().isoformat(timespec="seconds")),
            )

    def get(self, thread_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT plan_json FROM plans WHERE thread_id = ?", (thread_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None


class PostgresStore:
    backend = "postgres"

    def __init__(self, dsn: str):
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "DATABASE_URL points to PostgreSQL but psycopg is not installed; "
                'run: pip install "psycopg[binary]"'
            ) from exc
        self._psycopg = psycopg
        self.dsn = dsn
        with self._psycopg.connect(self.dsn) as conn:
            conn.execute(SCHEMA)

    def save(self, thread_id: str, request: str, plan: dict) -> None:
        with self._psycopg.connect(self.dsn) as conn:
            conn.execute(
                "INSERT INTO plans VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (thread_id) DO UPDATE SET request = EXCLUDED.request, "
                "plan_json = EXCLUDED.plan_json, created_at = EXCLUDED.created_at",
                (thread_id, request, json.dumps(plan), datetime.now().isoformat(timespec="seconds")),
            )

    def get(self, thread_id: str) -> dict | None:
        with self._psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                "SELECT plan_json FROM plans WHERE thread_id = %s", (thread_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None


_STORE = None


def get_store():
    global _STORE
    if _STORE is None:
        dsn = os.environ.get("DATABASE_URL", "")
        if dsn.startswith("postgres"):
            _STORE = PostgresStore(dsn)
        else:
            default = Path(__file__).resolve().parent.parent / "data" / "holidayplanner.db"
            _STORE = SqliteStore(os.environ.get("HOLIDAYPLANNER_DB", str(default)))
    return _STORE
