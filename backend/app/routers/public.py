"""Public, unauthenticated stats — deliberately the data endpoints in
this app with no Depends(...) auth. Scoped so they're safe to expose
to an external dashboard widget with no API key.

- GET /stats: aggregate counts only (no names).
- GET /now-playing: who's listening right now, with display name
  (full_name, else username), station, current artist/track, and a
  cached station logo URL. No login usernames-as-logins when a
  display name exists, no IPs, no locations. Logo is cache-only —
  never triggers a SearXNG/Radio-Browser lookup from this route.
"""

from fastapi import APIRouter, Response
from pydantic import BaseModel

from .. import history, nowplaying, station_logos

router = APIRouter(prefix="/api/public", tags=["public"])


class PublicStats(BaseModel):
    live_listeners: int
    unique_listeners_today: int
    ai_requests_today: int
    music_link_requests_this_hour: int


class PublicNowPlaying(BaseModel):
    display_name: str
    station: str
    artist: str | None = None
    title: str | None = None
    logo: str | None = None


@router.get("/stats", response_model=PublicStats)
async def public_stats(response: Response):
    # No-store: the count changes continuously, and a caching proxy
    # serving a stale number defeats the point of a live-stats widget —
    # same reasoning as stream.py/music_link.py's own no-store headers.
    response.headers["Cache-Control"] = "no-store"
    return {
        "live_listeners": len(nowplaying.live_snapshot()),
        "unique_listeners_today": await history.unique_listeners_today(),
        "ai_requests_today": await history.ai_requests_today(),
        "music_link_requests_this_hour": await history.music_link_requests_this_hour(),
    }


@router.get("/now-playing", response_model=list[PublicNowPlaying])
async def public_now_playing(response: Response):
    response.headers["Cache-Control"] = "no-store"
    sessions = []
    for s in nowplaying.live_now_playing():
        logo = None
        if s.get("station_url"):
            cached = await station_logos.get_cached(s["station_url"])
            if cached:
                logo = cached.get("logo")
        sessions.append({
            "display_name": s["display_name"],
            "station": s["station"],
            "artist": s.get("artist"),
            "title": s.get("title"),
            "logo": logo,
        })
    return sessions
