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
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""

_db: aiosqlite.Connection | None = None


async def init_db():
    global _db
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA foreign_keys = ON")
    await _db.executescript(SCHEMA)
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
