"""Per-user trivia history (SQLite) — up to 100 AI liner-note blurbs
kept per account for provider/quality analysis (see AI.md), of which the
UI only ever shows/requests the most recent 10 by default (see
RECENT_DEFAULT_LIMIT). Persisted (unlike 0.3.2's session-only in-memory
version) so it survives logout/reload, and personal per user (not
shared/global, same scoping as favorites/config)."""

from datetime import datetime, timezone

from .db import get_db, tx

# How many rows are kept on disk per user — independent of how many the
# UI actually shows (RECENT_DEFAULT_LIMIT below). Widened from 10 to 100
# on 2026-09-10 for the AI provider investigation (see AI.md /
# ai_stats.py) — more retained history to analyze without changing what
# a normal user sees by default.
STORAGE_LIMIT = 100

# Default for recent()'s `limit` param — what the trivia-history UI
# actually requests. Deliberately kept separate from STORAGE_LIMIT: the
# UI's own product decision to show 10 shouldn't silently cap how much
# data is available for analysis, and widening storage shouldn't
# silently change what a normal user sees.
RECENT_DEFAULT_LIMIT = 10


async def record(user_id: int, raw_title: str, station_name: str, artist: str,
                 title: str, performer: str, item: dict, provider: str = "") -> None:
    """A re-ask for the same raw_title replaces the existing row (moves it
    to newest) rather than adding a duplicate — same dedupe behavior the
    0.3.2 in-memory version had, now enforced in SQL.

    provider defaults to "" (unknown) rather than being required, so
    existing callers/tests that don't yet have a provider to pass don't
    break — but every real call site (routers/ws.py) should pass the
    real value from item["provider"] (set by enricher.py's _ask(), the
    one place that actually knows which provider's fallback-chain
    attempt succeeded — see enricher.py's _llm()/_ask() for why this
    can't be recomputed reliably downstream)."""
    now = datetime.now(timezone.utc).isoformat()
    async with tx() as db:
        await db.execute(
            "DELETE FROM trivia_history WHERE user_id = ? AND raw_title = ?",
            (user_id, raw_title),
        )
        await db.execute(
            "INSERT INTO trivia_history (user_id, raw_title, station_name, artist, "
            "title, performer, work, trivia, wiki, created_at, provider) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, raw_title, station_name, artist, title, performer,
             item.get("work") or "", item.get("trivia") or "", item.get("wiki") or "", now,
             provider),
        )
        await db.execute(
            "DELETE FROM trivia_history WHERE user_id = ? AND id NOT IN ("
            "SELECT id FROM trivia_history WHERE user_id = ? "
            "ORDER BY id DESC LIMIT ?)",
            (user_id, user_id, STORAGE_LIMIT),
        )


async def recent(user_id: int, limit: int = RECENT_DEFAULT_LIMIT) -> list[dict]:
    db = get_db()
    cur = await db.execute(
        "SELECT * FROM trivia_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]
