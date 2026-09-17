"""Public, unauthenticated stats — deliberately the one data endpoint in
this app with no Depends(...) auth. Scoped to aggregate counts only (no
usernames, IPs, or locations, unlike routers/analytics.py's admin-only
routes) so it's safe to expose to an external dashboard widget (e.g. a
gethomepage.dev customapi tile) with no API key. See KB.md."""

from fastapi import APIRouter, Response
from pydantic import BaseModel

from .. import history, nowplaying

router = APIRouter(prefix="/api/public", tags=["public"])


class PublicStats(BaseModel):
    live_listeners: int
    unique_listeners_today: int
    ai_requests_today: int
    music_link_requests_this_hour: int


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
