from fastapi import APIRouter, Depends, Query, Response

from .. import deezer, music_link_cache, spotify
from ..deps import get_active_user
from ..textutil import split_title
from ..userdata import load_cfg

router = APIRouter(prefix="/api/music-link", tags=["music-link"])


@router.get("")
async def get_music_link(
    response: Response,
    raw_title: str = Query(...),
    user: dict = Depends(get_active_user),
) -> dict:
    """Returns {"url": <track page URL> | None} for the current user's
    active music service (music_service in their config — resolved here,
    server-side, NOT trusted from a client query param). This closes a
    real correctness gap: a stale client-side service value in the brief
    window after switching services could otherwise return a URL for a
    service the UI no longer thinks is active. Read-only, no OAuth, no
    per-user connection state — see AI.md/findings.md's "search-only
    music-service links" entry for the full design rationale.

    Cache-Control: no-store is mandatory here, not optional — the query
    string is just raw_title, deliberately excluding the service (see the
    server-side-resolution reasoning above), so this endpoint returns a
    DIFFERENT answer for the SAME URL depending on server-side state the
    browser can't see. Without an explicit no-store, a browser's default
    heuristic HTTP caching (RFC 7234 — GET responses with no cache
    directives may still be cached and reused for an identical URL) can
    silently serve a stale answer from before a service switch, with the
    server never even seeing the second request. Confirmed as the real
    cause of a 2026-09-14 production bug report: switching to Deezer and
    clicking the (correctly Deezer-colored) icon opened a stale Spotify
    URL for a track that had been looked up under Spotify moments
    earlier, in the same page session, before the switch."""
    response.headers["Cache-Control"] = "no-store"
    raw_title = (raw_title or "").strip()
    if not raw_title:
        return {"url": None}

    cfg = await load_cfg(user["id"])
    service = cfg.get("music_service")
    # No silent default to "spotify" here — a user who hasn't picked a
    # service yet (or explicitly has none set) gets no lookup at all,
    # matching the frontend's own useMusicLink() behavior of skipping the
    # request entirely when no service is active. There's nothing to
    # search against without a chosen service.
    if service not in ("spotify", "deezer"):
        return {"url": None}

    cached = await music_link_cache.get_cached(service, raw_title)
    if cached is not None:
        return {"url": cached.get("url")}

    artist, title, performer = split_title(raw_title)
    url = await _lookup(service, artist, title, performer)
    await music_link_cache.store(service, raw_title, url)
    return {"url": url}


async def _lookup(service: str, artist: str, title: str, performer: str) -> str | None:
    if service == "spotify":
        token = await spotify.get_app_token()
        if not token:
            return None
        match = await spotify.find_best_track(token, "", artist, title, performer)
        if not match:
            return None
        return f"https://open.spotify.com/track/{match.track_id}"
    if service == "deezer":
        match = await deezer.find_best_track("", artist, title, performer)
        if not match:
            return None
        return f"https://www.deezer.com/track/{match.track_id}"
    return None
