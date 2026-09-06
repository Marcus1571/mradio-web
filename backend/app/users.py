"""User account CRUD (SQLite) — admin-managed, no public signup."""

import os
from datetime import datetime, timezone

from .auth import hash_password, verify_password
from .db import get_db, tx

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "mradio"


def _row_to_user(row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"],
        "is_admin": bool(row["is_admin"]),
        "disabled": bool(row["disabled"]),
        "must_change_password": bool(row["must_change_password"]),
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


async def get_by_email(email: str) -> dict | None:
    db = get_db()
    cur = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
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
                       is_admin: bool = False,
                       must_change_password: bool = True,
                       full_name: str | None = None) -> dict:
    """New accounts (bootstrap admin included) start with a forced password
    change on first login — the caller picks the initial password, not the
    person who'll actually use the account."""
    now = datetime.now(timezone.utc).isoformat()
    async with tx() as db:
        cur = await db.execute(
            "INSERT INTO users (username, email, full_name, password_hash, "
            "is_admin, disabled, must_change_password, created_at) "
            "VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (username, email, full_name, hash_password(password), int(is_admin),
             int(must_change_password), now),
        )
        user_id = cur.lastrowid
    return await get_by_id(user_id)


async def set_password(user_id: int, password: str,
                       must_change_password: bool = False) -> None:
    async with tx() as db:
        await db.execute(
            "UPDATE users SET password_hash = ?, must_change_password = ? "
            "WHERE id = ?",
            (hash_password(password), int(must_change_password), user_id),
        )


async def change_own_password(user_id: int, current_password: str,
                               new_password: str) -> bool:
    """Self-service password change (also clears must_change_password).
    Returns False if current_password doesn't match."""
    user = await get_by_id(user_id)
    if user is None or not verify_password(current_password, user["password_hash"]):
        return False
    await set_password(user_id, new_password, must_change_password=False)
    return True


async def set_disabled(user_id: int, disabled: bool) -> None:
    async with tx() as db:
        await db.execute("UPDATE users SET disabled = ? WHERE id = ?",
                         (int(disabled), user_id))


async def set_admin(user_id: int, is_admin: bool) -> None:
    async with tx() as db:
        await db.execute("UPDATE users SET is_admin = ? WHERE id = ?",
                         (int(is_admin), user_id))


async def update_profile(user_id: int, **fields) -> None:
    """Admin-driven edit of full_name/email — only updates keys actually
    passed (the router forwards `model_dump(exclude_unset=True)`, so an
    omitted field is left untouched rather than cleared)."""
    cols = {k: v for k, v in fields.items() if k in ("full_name", "email")}
    if not cols:
        return
    set_clause = ", ".join(f"{k} = ?" for k in cols)
    async with tx() as db:
        await db.execute(f"UPDATE users SET {set_clause} WHERE id = ?",
                         (*cols.values(), user_id))


async def delete_user(user_id: int) -> None:
    async with tx() as db:
        await db.execute("DELETE FROM users WHERE id = ?", (user_id,))


async def bootstrap_admin() -> None:
    """On first run (no users yet), create one admin account so there's a
    way in: admin/mradio by default, overridable via env vars, forced to
    change the password on first login. No public signup — every account
    after this is created by an admin via the Settings -> Users page."""
    if await count_users() > 0:
        return
    username = os.environ.get("MRADIO_ADMIN_USERNAME") or DEFAULT_ADMIN_USERNAME
    password = os.environ.get("MRADIO_ADMIN_PASSWORD") or DEFAULT_ADMIN_PASSWORD
    await create_user(username, password, is_admin=True, must_change_password=True)
