"""User account CRUD (SQLite) — admin-managed, no public signup."""

import os
from datetime import datetime, timezone

from .auth import hash_password
from .db import get_db, tx


def _row_to_user(row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "is_admin": bool(row["is_admin"]),
        "disabled": bool(row["disabled"]),
        "created_at": row["created_at"],
    }


async def count_users() -> int:
    db = get_db()
    cur = await db.execute("SELECT COUNT(*) AS n FROM users")
    row = await cur.fetchone()
    return row["n"]


async def get_by_username(username: str) -> dict | None:
    db = get_db()
    cur = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def get_by_id(user_id: int) -> dict | None:
    db = get_db()
    cur = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def list_users() -> list[dict]:
    db = get_db()
    cur = await db.execute("SELECT * FROM users ORDER BY id")
    rows = await cur.fetchall()
    return [_row_to_user(r) for r in rows]


async def create_user(username: str, password: str, email: str | None = None,
                       is_admin: bool = False) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    async with tx() as db:
        cur = await db.execute(
            "INSERT INTO users (username, email, password_hash, is_admin, "
            "disabled, created_at) VALUES (?, ?, ?, ?, 0, ?)",
            (username, email, hash_password(password), int(is_admin), now),
        )
        user_id = cur.lastrowid
    return await get_by_id(user_id)


async def set_password(user_id: int, password: str) -> None:
    async with tx() as db:
        await db.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                         (hash_password(password), user_id))


async def set_disabled(user_id: int, disabled: bool) -> None:
    async with tx() as db:
        await db.execute("UPDATE users SET disabled = ? WHERE id = ?",
                         (int(disabled), user_id))


async def set_admin(user_id: int, is_admin: bool) -> None:
    async with tx() as db:
        await db.execute("UPDATE users SET is_admin = ? WHERE id = ?",
                         (int(is_admin), user_id))


async def delete_user(user_id: int) -> None:
    async with tx() as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))


async def bootstrap_admin() -> None:
    """On first run (no users yet), create one admin from env vars so
    there's a way in. No public signup — every user after this is
    created by an admin via the Settings -> Users page."""
    if await count_users() > 0:
        return
    username = os.environ.get("MRADIO_ADMIN_USERNAME")
    password = os.environ.get("MRADIO_ADMIN_PASSWORD")
    if not username or not password:
        return
    await create_user(username, password, is_admin=True)
