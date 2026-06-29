"""
backend/database/supabase_client.py
─────────────────────────────────────
Database client with Supabase primary and SQLite fallback.

In development (no Supabase credentials): uses SQLite + mock data.
In production: swap to real Supabase credentials in .env.

The get_supabase_client() function returns a client that mimics the
Supabase Python SDK interface so agent nodes don't need to change.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from functools import lru_cache

import structlog
from backend.config import settings

log = structlog.get_logger(__name__)


# ── SQLite mock client for local dev ──────────────────────────────────────────

class MockTable:
    """Minimal Supabase table interface backed by SQLite."""

    def __init__(self, conn: sqlite3.Connection, table_name: str):
        self._conn = conn
        self._table = table_name
        self._where_clauses: list[tuple] = []
        self._select_cols = "*"
        self._limit_val: int | None = None
        self._order_col: str | None = None
        self._order_desc = False
        self._single = False

    def select(self, cols: str) -> "MockTable":
        self._select_cols = cols
        return self

    def eq(self, column: str, value) -> "MockTable":
        self._where_clauses.append((column, "=", value))
        return self

    def limit(self, n: int) -> "MockTable":
        self._limit_val = n
        return self

    def order(self, col: str, desc: bool = False) -> "MockTable":
        self._order_col = col
        self._order_desc = desc
        return self

    def single(self) -> "MockTable":
        self._single = True
        return self

    def execute(self):
        cursor = self._conn.cursor()

        # Build query
        sql = f"SELECT {self._select_cols} FROM {self._table}"
        params = []
        if self._where_clauses:
            conditions = " AND ".join(f"{col} {op} ?" for col, op, _ in self._where_clauses)
            params = [val for _, _, val in self._where_clauses]
            sql += f" WHERE {conditions}"

        if self._order_col:
            direction = "DESC" if self._order_desc else "ASC"
            sql += f" ORDER BY {self._order_col} {direction}"

        if self._limit_val:
            sql += f" LIMIT {self._limit_val}"

        try:
            cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            log.error("sqlite_query_failed", sql=sql, error=str(e))
            rows = []

        class MockResult:
            def __init__(self, data):
                self.data = data

        if self._single:
            return MockResult(rows[0] if rows else None)
        return MockResult(rows)


class MockSupabaseClient:
    """Supabase-compatible client backed by SQLite."""

    def __init__(self, db_path: str = "./data/dev.db"):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        log.info("using_sqlite_fallback", db_path=db_path)

    def table(self, name: str) -> MockTable:
        return MockTable(self._conn, name)


# ── Real Supabase client ───────────────────────────────────────────────────────

def _create_supabase_client():
    """Creates a real Supabase client if credentials are available."""
    try:
        from supabase import create_client
        client = create_client(settings.supabase_url, settings.supabase_service_key)
        log.info("supabase_client_connected")
        return client
    except Exception as exc:
        log.warning("supabase_connection_failed", error=str(exc), fallback="sqlite")
        return None


# ── Public factory ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_supabase_client():
    """
    Returns the appropriate database client:
      - Real Supabase client if SUPABASE_URL + SUPABASE_SERVICE_KEY are set
      - MockSupabaseClient (SQLite) for local development

    Usage in agent nodes:
        client = get_supabase_client()
        result = client.table("applicants").select("*").eq("id", applicant_id).single().execute()
        data = result.data
    """
    if settings.supabase_url and settings.supabase_service_key:
        client = _create_supabase_client()
        if client:
            return client

    # Fallback to SQLite
    db_path = "./data/dev.db"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return MockSupabaseClient(db_path=db_path)