from fastapi import APIRouter, Depends, Query, Response

from .. import apple_music, deezer, music_link_cache, spotify
from ..deps import get_active_user
from ..textutil import split_title

router = APIRouter(prefix="/api/music-link", tags=["music-link"])

_VALID_SERVICES = ("spotify", "deezer", "apple")


@router.get("")
async def get_music_link(
    response: Response,
    raw_title: str = Query(...),
    service: str | None = Query(None),
    user: dict = Depends(get_active_user),
) -> dict:
    """Returns {"url": <track page URL> | None} for the requested music
    service. `service` is session-only on the client (useMusicService.ts
    never persists it — the operator's explicit call, 2026-09-15: every
    app launch starts at "no service" rather than remembering a prior
    pick, to avoid spending search-API quota on listeners who don't use
    the feature), so it's sent per-request rather than resolved from the
    user's stored config the way it was before that change. Read-only,
    no OAuth, no per-user connection state — see AI.md/findings.md's
    "search-only music-service links" entry for the full design
    rationale.

    Cache-Control: no-store is kept even though `service` is now part of
    the query string (so the URL itself already varies per service,
    unlike before) — cheap insurance against any intermediate cache that
    might ignore query params, matching the same defensive posture
    stream.py already uses."""
    response.headers["Cache-Control"] = "no-store"
    raw_title = (raw_title or "").strip()
    if not raw_title or service not in _VALID_SERVICES:
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
    if service == "apple":
        match = await apple_music.find_best_track(artist, title, performer)
        if not match:
            return None
        return match.url
    return None
