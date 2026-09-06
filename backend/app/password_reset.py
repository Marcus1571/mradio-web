"""Self-service password reset tokens — mirrors auth.py's session token
pattern exactly (opaque random token, stored hashed, short TTL) rather
than inventing new crypto. A token is single-use: consuming it marks
`used_at`, and a second attempt with the same raw token is rejected."""

import secrets
from datetime import datetime, timedelta, timezone

from .auth import _token_hash
from .db import get_db, tx

RESET_TTL = timedelta(hours=1)


async def create_reset_token(user_id: int) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + RESET_TTL
    async with tx() as db:
        await db.execute(
            "INSERT INTO password_resets (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_token_hash(raw_token), user_id, now.isoformat(), expires.isoformat()),
        )
    return raw_token


async def consume_reset_token(raw_token: str) -> int | None:
    """Validates hash match + not expired + not already used, marking it
    used in the same step. Returns the user_id, or None if invalid."""
    if not raw_token:
        return None
    db = get_db()
    token_hash = _token_hash(raw_token)
    cur = await db.execute(
        "SELECT user_id, expires_at, used_at FROM password_resets WHERE token_hash = ?",
        (token_hash,),
    )
    row = await cur.fetchone()
    if row is None or row["used_at"] is not None:
        return None
    if row["expires_at"] <= datetime.now(timezone.utc).isoformat():
        return None
    async with tx() as db:
        await db.execute(
            "UPDATE password_resets SET used_at = ? WHERE token_hash = ?",
            (datetime.now(timezone.utc).isoformat(), token_hash),
        )
    return row["user_id"]
