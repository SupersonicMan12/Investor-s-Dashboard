"""SQLite persistence for quote caching, watchlist, and portfolio holdings."""

from __future__ import annotations

import sqlite3

from app import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS quote_cache (
    symbol TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    fetched_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol TEXT PRIMARY KEY,
    added_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    shares REAL NOT NULL,
    cost_basis REAL NOT NULL,
    added_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);
"""


def get_connection() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def get_watchlist_symbols() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT symbol FROM watchlist ORDER BY added_at"
        ).fetchall()
    return [row["symbol"] for row in rows]


def add_to_watchlist(symbol: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (symbol.upper(),)
        )
        conn.commit()


def remove_from_watchlist(symbol: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        conn.commit()


def get_holdings() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, symbol, shares, cost_basis FROM holdings ORDER BY added_at"
        ).fetchall()


def add_holding(symbol: str, shares: float, cost_basis: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO holdings (symbol, shares, cost_basis) VALUES (?, ?, ?)",
            (symbol.upper(), shares, cost_basis),
        )
        conn.commit()


def remove_holding(holding_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
        conn.commit()
