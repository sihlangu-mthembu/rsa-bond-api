"""Storage for yield quotes: PostgreSQL when DATABASE_URL is set, otherwise SQLite.

- DATABASE_URL (e.g. postgresql://user:pass@host:5432/bonds) selects PostgreSQL via psycopg 3.
- Without it, the standard library's sqlite3 is used, with the file path taken from BOND_API_DB
  (default: quotes.db), so tests and local runs need no database server.

Both back ends run the same SQL. The only differences are the placeholder style (? vs %s) and the
id column definition, handled in one place below.
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

COLUMNS = """
    code TEXT NOT NULL,
    settle TEXT NOT NULL,
    ytm_percent DOUBLE PRECISION NOT NULL,
    clean_price DOUBLE PRECISION NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
"""
SQLITE_SCHEMA = f"CREATE TABLE IF NOT EXISTS quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, {COLUMNS})"
POSTGRES_SCHEMA = f"CREATE TABLE IF NOT EXISTS quotes (id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, {COLUMNS})"


def database_url() -> str | None:
    """The PostgreSQL connection string, or None to use SQLite."""
    return os.environ.get("DATABASE_URL") or None


def backend() -> str:
    return "postgresql" if database_url() else "sqlite"


def db_path() -> str:
    return os.environ.get("BOND_API_DB", "quotes.db")


class _Conn:
    """A thin wrapper so the query functions below can be written once for both databases."""

    def __init__(self, raw: Any, placeholder: str) -> None:
        self.raw = raw
        self.placeholder = placeholder

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        if self.placeholder != "?":
            sql = sql.replace("?", self.placeholder)   # the SQL below never contains a literal "?"
        return self.raw.execute(sql, params)


@contextmanager
def connect() -> Iterator[_Conn]:
    url = database_url()
    if url:
        import psycopg  # imported lazily: only needed for PostgreSQL
        from psycopg.rows import dict_row

        raw: Any = psycopg.connect(url, row_factory=dict_row)
        conn = _Conn(raw, "%s")
        schema = POSTGRES_SCHEMA
    else:
        raw = sqlite3.connect(db_path())
        raw.row_factory = sqlite3.Row                   # rows behave like dictionaries
        conn = _Conn(raw, "?")
        schema = SQLITE_SCHEMA
    try:
        conn.execute(schema)
        yield conn
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def insert_quote(code: str, settle: str, ytm_percent: float, clean_price: float, source: str) -> dict[str, Any]:
    created = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO quotes (code, settle, ytm_percent, clean_price, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) RETURNING *",          # placeholders prevent SQL injection
            (code, settle, ytm_percent, clean_price, source, created),
        ).fetchone()
    return dict(row)


def list_quotes(code: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    with connect() as conn:
        if code:
            cur = conn.execute("SELECT * FROM quotes WHERE code = ? ORDER BY id DESC LIMIT ?", (code, limit))
        else:
            cur = conn.execute("SELECT * FROM quotes ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_quote(quote_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    return dict(row) if row else None


def delete_quote(quote_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        deleted: int = cur.rowcount
    return deleted > 0
