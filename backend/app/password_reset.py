"""Self-service password reset tokens — mirrors auth.py's session token
pattern exactly (opaque random token, stored hashed, short TTL) rather
than inventing new crypto. A token is single-use: consuming it marks
`used_at`, and a second attempt with the same raw token is rejected."""

import secrets
from datetime import datetime, timedelta, timezone

from .auth import _token_hash
from .db import get_db, tx

RESET_TTL = timedelta(hours=1)
# Invite links (new-account welcome email) reuse this same token
# mechanism but need a much longer window than "I forgot my password
# right now" — an invited person checks their email on their own
# schedule, not necessarily same-day.
INVITE_TTL = timedelta(days=7)


async def create_reset_token(user_id: int, ttl: timedelta = RESET_TTL) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + ttl
    async with tx() as db:
        await db.execute(
            "INSERT INTO password_resets (token_hash, user_id, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_token_hash(raw_token), user_id, now.isoformat(), expires.isoformat()),
        )
    return raw_token


async def _validate(raw_token: str):
    """Shared hash-match + not-expired + not-already-used check used by
    both consume_reset_token() (which also marks it used) and
    peek_reset_token() (read-only, for showing the account's username on
    the set-password page before the user submits anything)."""
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
    return row


async def consume_reset_token(raw_token: str) -> int | None:
    """Validates the token, marking it used in the same step. Returns
    the user_id, or None if invalid."""
    row = await _validate(raw_token)
    if row is None:
        return None
    async with tx() as db:
        await db.execute(
            "UPDATE password_resets SET used_at = ? WHERE token_hash = ?",
            (datetime.now(timezone.utc).isoformat(), _token_hash(raw_token)),
        )
    return row["user_id"]


async def peek_reset_token(raw_token: str) -> int | None:
    """Same validation as consume_reset_token() but does NOT mark the
    token used — a read-only lookup so the set-password page can show
    "signing in as <username>" before the user has actually submitted a
    new password. Safe to call any number of times; only the real
    consume_reset_token() call (on form submit) burns the single use."""
    row = await _validate(raw_token)
    return row["user_id"] if row is not None else None
