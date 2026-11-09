"""SQLite storage for yield quotes, using only the standard library's sqlite3 module.

The database path comes from the BOND_API_DB environment variable (default: quotes.db),
so tests can point at a temporary file and a deployment can point at a persistent disk.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    settle TEXT NOT NULL,
    ytm_percent REAL NOT NULL,
    clean_price REAL NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def db_path() -> str:
    return os.environ.get("BOND_API_DB", "quotes.db")


@contextmanager
def connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row          # rows behave like dictionaries
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_quote(code: str, settle: str, ytm_percent: float, clean_price: float, source: str) -> dict:
    created = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO quotes (code, settle, ytm_percent, clean_price, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",                 # placeholders prevent SQL injection
            (code, settle, ytm_percent, clean_price, source, created),
        )
        row = conn.execute("SELECT * FROM quotes WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def list_quotes(code: str | None = None, limit: int = 100) -> list[dict]:
    with connect() as conn:
        if code:
            rows = conn.execute("SELECT * FROM quotes WHERE code = ? ORDER BY id DESC LIMIT ?", (code, limit))
        else:
            rows = conn.execute("SELECT * FROM quotes ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows.fetchall()]


def get_quote(quote_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
    return dict(row) if row else None


def delete_quote(quote_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
    return cur.rowcount > 0
