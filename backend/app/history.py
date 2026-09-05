"""Play-session history (SQLite) — one row per stream connection, written
by routers/stream.py at connect/disconnect. Powers the admin analytics
page: recent history table and aggregate stats. Live "who's playing now"
is served straight from nowplaying.py's in-memory registry instead (no
DB round-trip needed for that), so this module only deals with sessions
that have already started."""

from datetime import datetime, timezone

from . import geoip
from .db import get_db, tx


async def start_session(user_id: int, station_name: str, station_url: str,
                        genre: str, ip: str | None) -> tuple[int, dict | None]:
    """Returns (row_id, location) — location is the same dict persisted to
    the row, handed back so callers (routers/stream.py) don't need a
    second geoip lookup for the live-session registry."""
    loc = geoip.lookup(ip)
    now = datetime.now(timezone.utc).isoformat()
    async with tx() as db:
        cur = await db.execute(
            "INSERT INTO play_history (user_id, station_name, station_url, "
            "genre, started_at, ip, country, country_code, city, lat, lon) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, station_name, station_url, genre, now, ip,
             (loc or {}).get("country"), (loc or {}).get("country_code"),
             (loc or {}).get("city"), (loc or {}).get("lat"), (loc or {}).get("lon")),
        )
        row_id = cur.lastrowid
    return row_id, loc


async def end_session(row_id: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    async with tx() as db:
        await db.execute(
            "UPDATE play_history SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
            (now, row_id),
        )


async def recent_history(limit: int = 50, offset: int = 0) -> list[dict]:
    db = get_db()
    cur = await db.execute(
        "SELECT h.*, u.username FROM play_history h "
        "JOIN users u ON u.id = h.user_id "
        "ORDER BY h.started_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]


_SINCE_CLAUSES = {
    "7d": "started_at >= datetime('now', '-7 days')",
    "30d": "started_at >= datetime('now', '-30 days')",
    "all": "1=1",
}


async def stats(since: str = "30d") -> dict:
    db = get_db()
    where = _SINCE_CLAUSES.get(since, _SINCE_CLAUSES["30d"])

    def duration_expr() -> str:
        return ("SUM((julianday(COALESCE(ended_at, strftime('%Y-%m-%dT%H:%M:%fZ', "
                "'now'))) - julianday(started_at)) * 86400)")

    cur = await db.execute(
        f"SELECT station_name, COUNT(*) AS plays, {duration_expr()} AS seconds "
        f"FROM play_history WHERE {where} "
        "GROUP BY station_name ORDER BY plays DESC LIMIT 5"
    )
    top_stations = [dict(r) for r in await cur.fetchall()]

    cur = await db.execute(
        f"SELECT genre, COUNT(*) AS plays, {duration_expr()} AS seconds "
        f"FROM play_history WHERE {where} "
        "GROUP BY genre ORDER BY plays DESC LIMIT 5"
    )
    top_genres = [dict(r) for r in await cur.fetchall()]

    cur = await db.execute(
        f"SELECT u.username, COUNT(*) AS plays, {duration_expr()} AS seconds "
        f"FROM play_history h JOIN users u ON u.id = h.user_id WHERE {where} "
        "GROUP BY u.username ORDER BY seconds DESC LIMIT 5"
    )
    top_users = [dict(r) for r in await cur.fetchall()]

    cur = await db.execute(
        f"SELECT date(started_at) AS day, COUNT(*) AS plays "
        f"FROM play_history WHERE {where} "
        "GROUP BY day ORDER BY day"
    )
    by_day = [dict(r) for r in await cur.fetchall()]

    return {
        "top_stations": top_stations,
        "top_genres": top_genres,
        "top_users": top_users,
        "by_day": by_day,
    }
