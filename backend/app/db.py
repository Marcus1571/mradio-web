"""SQLite-backed accounts and sessions. Per-user radio data (favorites,
config, AI cache) lives in JSON files under userdata.py instead — this
module only owns who can log in."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

DATA_DIR = Path(os.environ.get("MRADIO_DATA_DIR", "/data"))
DB_PATH = Path(os.environ.get("MRADIO_DB_PATH", str(DATA_DIR / "mradio.db")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    disabled INTEGER NOT NULL DEFAULT 0,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS play_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    station_name TEXT NOT NULL,
    station_url TEXT NOT NULL,
    genre TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    ip TEXT,
    country TEXT,
    country_code TEXT,
    city TEXT,
    lat REAL,
    lon REAL
);
CREATE INDEX IF NOT EXISTS idx_play_history_started ON play_history(started_at);
CREATE INDEX IF NOT EXISTS idx_play_history_user ON play_history(user_id);
CREATE TABLE IF NOT EXISTS trivia_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    raw_title TEXT NOT NULL,
    station_name TEXT NOT NULL,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    performer TEXT NOT NULL,
    work TEXT NOT NULL,
    trivia TEXT NOT NULL,
    wiki TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trivia_history_user ON trivia_history(user_id, id);
"""

_db: aiosqlite.Connection | None = None


async def _ensure_column(db: aiosqlite.Connection, table: str, column: str,
                         coltype: str) -> None:
    """SQLite has no `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` — check via
    PRAGMA first. Idempotent, safe to call on every startup against a
    pre-existing DB that already has real rows. Table/column/type are always
    hardcoded call-site literals, never user input, so the f-string is safe
    despite not being parameterized (SQLite doesn't allow parameterizing
    identifiers anyway). This is the reusable pattern for any future column
    added to a table that may already exist in production — every past
    schema change here was either a brand-new table or a column present
    since the very first commit, so there was no precedent for this until
    now."""
    cur = await db.execute(f"PRAGMA table_info({table})")
    cols = {row["name"] for row in await cur.fetchall()}
    if column not in cols:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


async def init_db():
    global _db
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA foreign_keys = ON")
    await _db.executescript(SCHEMA)
    await _ensure_column(_db, "users", "full_name", "TEXT")
    await _db.commit()


async def close_db():
    global _db
    if _db is not None:
        await _db.close()
        _db = None


def get_db() -> aiosqlite.Connection:
    if _db is None:
        raise RuntimeError("database not initialized")
    return _db


@asynccontextmanager
async def tx():
    """Commit on success, roll back on exception."""
    db = get_db()
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
