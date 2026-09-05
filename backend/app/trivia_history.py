"""Per-user trivia history (SQLite) — the last 10 AI liner-note blurbs
each account has received, kept for re-reading while something else
plays. Persisted (unlike 0.3.2's session-only in-memory version) so it
survives logout/reload, and personal per user (not shared/global, same
scoping as favorites/config)."""

from datetime import datetime, timezone

from .db import get_db, tx

MAX_ENTRIES = 10


async def record(user_id: int, raw_title: str, station_name: str, artist: str,
                 title: str, performer: str, item: dict) -> None:
    """A re-ask for the same raw_title replaces the existing row (moves it
    to newest) rather than adding a duplicate — same dedupe behavior the
    0.3.2 in-memory version had, now enforced in SQL."""
    now = datetime.now(timezone.utc).isoformat()
    async with tx() as db:
        await db.execute(
            "DELETE FROM trivia_history WHERE user_id = ? AND raw_title = ?",
            (user_id, raw_title),
        )
        await db.execute(
            "INSERT INTO trivia_history (user_id, raw_title, station_name, artist, "
            "title, performer, work, trivia, wiki, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, raw_title, station_name, artist, title, performer,
             item.get("work") or "", item.get("trivia") or "", item.get("wiki") or "", now),
        )
        await db.execute(
            "DELETE FROM trivia_history WHERE user_id = ? AND id NOT IN ("
            "SELECT id FROM trivia_history WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?)",
            (user_id, user_id, MAX_ENTRIES),
        )


async def recent(user_id: int, limit: int = MAX_ENTRIES) -> list[dict]:
    db = get_db()
    cur = await db.execute(
        "SELECT * FROM trivia_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]
