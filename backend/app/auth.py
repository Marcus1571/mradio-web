"""Password hashing (stdlib PBKDF2-HMAC-SHA256, no extra crypto dependency)
and server-side sessions (opaque random token, stored hashed; a cookie
holds the raw token so a leaked DB alone can't be replayed)."""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from .db import get_db, tx

PBKDF2_ITERATIONS = 600_000
SESSION_COOKIE_NAME = "mradio_session"
SESSION_TTL = timedelta(days=int(os.environ.get("MRADIO_SESSION_TTL_DAYS", "30")))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
    return hmac.compare_digest(dk, expected)


def _token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_session(user_id: int) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + SESSION_TTL
    async with tx() as db:
        await db.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_token_hash(raw_token), user_id, now.isoformat(), expires.isoformat()),
        )
    return raw_token


async def resolve_session(raw_token: str) -> dict | None:
    """Return the session's user row, or None if missing/expired. Expired
    sessions are pruned lazily on lookup."""
    if not raw_token:
        return None
    db = get_db()
    token_hash = _token_hash(raw_token)
    cur = await db.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE s.token_hash = ? AND s.expires_at > ?",
        (token_hash, datetime.now(timezone.utc).isoformat()),
    )
    row = await cur.fetchone()
    if row is None:
        return None
    return dict(row)


async def delete_session(raw_token: str) -> None:
    async with tx() as db:
        await db.execute("DELETE FROM sessions WHERE token_hash = ?",
                         (_token_hash(raw_token),))


async def delete_expired_sessions() -> None:
    async with tx() as db:
        await db.execute("DELETE FROM sessions WHERE expires_at <= ?",
                         (datetime.now(timezone.utc).isoformat(),))
