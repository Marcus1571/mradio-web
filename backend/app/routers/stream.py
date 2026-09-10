"""Audio stream proxy — the fix for browsers silently blocking playback of
HTTP-only stations from an HTTPS page. Every station goes through this one
route, not just the HTTP-only ones: same code path for all, and it's also
the only connection made to the origin station, since ICY metadata is
parsed off the same bytes as they pass through (see icy.py)."""

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from .. import history, nowplaying, stations
from ..deps import get_active_user
from ..icy import IcyDemuxer, parse_metaint

logger = logging.getLogger("mradio.stream")

router = APIRouter(prefix="/api", tags=["stream"])

_USER_AGENT = "mradio-web/1.0"


async def _reject_private_targets(hostname: str) -> None:
    """Best-effort SSRF guard. mradio itself lets you play any http(s) URL
    (the `i` "add a stream" key) with no such check, because that fetch
    happened client-side via mpv on the user's own machine. Here the fetch
    happens server-side, from a container with LAN access — so refuse
    anything that resolves to a private/loopback/link-local address rather
    than letting the proxy be turned into a pivot into the LAN."""
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(400, "could not resolve station host")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(400, "station host is not a public address")


@router.get("/stream")
async def stream(request: Request,
                 url: str = Query(..., description="the station's real stream URL"),
                 sid: str | None = Query(
                     None, description="player session id for now-playing push"),
                 genre: str | None = Query(
                     None, description="the station's known genre, if any "
                     "(favorites/curated list already have one — avoids "
                     "re-guessing it from the station name for analytics)"),
                 station_name: str | None = Query(
                     None, description="the station's known name, if any "
                     "(favorites/curated list already have one) — many real "
                     "stations never send an icy-name header at all "
                     "(confirmed live: the majority of observed sessions have "
                     "an empty ICY name), which used to silently skip history/"
                     "live-session tracking entirely for those; this lets the "
                     "frontend's own known name stand in so those sessions "
                     "still get recorded"),
                 user: dict = Depends(get_active_user)):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(400, "url must be a valid http(s) stream URL")
    await _reject_private_targets(parsed.hostname)

    client = httpx.AsyncClient(follow_redirects=True,
                               timeout=httpx.Timeout(10.0, read=None))
    try:
        req = client.build_request(
            "GET", url, headers={"Icy-MetaData": "1", "User-Agent": _USER_AGENT})
        upstream = await client.send(req, stream=True)
    except httpx.HTTPError as e:
        await client.aclose()
        raise HTTPException(502, f"could not reach station: {e}")

    if upstream.status_code >= 400:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(502, f"station returned HTTP {upstream.status_code}")

    metaint = parse_metaint(upstream.headers)
    content_type = upstream.headers.get("content-type") or "audio/mpeg"
    icy_name = (upstream.headers.get("icy-name") or "").strip()
    icy_br = upstream.headers.get("icy-br")
    icy_sr = upstream.headers.get("icy-sr")
    # The name actually used for history/live-session tracking and genre
    # resolution below — prefers the frontend's own known name (curated/
    # favorites list) over whatever the origin stream's icy-name header
    # says, or lack thereof. Confirmed live: most real stations here send
    # an empty icy-name (station='' in the logs) despite streaming fine
    # and sending real StreamTitle metadata — the old `if station_name:`
    # gate (station_name being the ICY value alone) silently skipped
    # history/live tracking for the majority of actual listening
    # sessions, not just an edge case. The ICY value is still used as-is
    # for the WS "station" event below (a different concern — reflecting
    # what the stream itself reports, not what gates analytics).
    tracked_name = (station_name or icy_name or "").strip()
    logger.info(
        "connected sid=%s station=%r bitrate=%s sample_rate=%s format=%s metaint=%s",
        sid, icy_name, icy_br, icy_sr, content_type, metaint,
    )
    # A fresh generation per connection: `sid` is reused across station
    # switches (see nowplaying.py docstring), and setting it here — before
    # this connection's own `station` event — invalidates any earlier
    # connection for the same sid that might still be draining its last
    # buffered bytes in the background, so a stale title/station event it
    # emits after this point gets dropped instead of overwriting this one's.
    gen = nowplaying.begin_generation(sid) if sid else None
    if sid and icy_name:
        nowplaying.publish(sid, {
            "type": "station",
            "name": icy_name,
            "bitrate": icy_br,
            "sample_rate": icy_sr,
            "format": content_type,
            "has_icy": metaint is not None,
        })

    history_row_id: int | None = None
    if tracked_name:
        client_ip = request.client.host if request.client else None
        resolved_genre = genre if genre in stations.GENRES else stations.genre_of(tracked_name)
        history_row_id, loc = await history.start_session(
            user["id"], tracked_name, url, resolved_genre, client_ip)
        if sid:
            nowplaying.session_started(
                sid, user["id"], user["username"], tracked_name, resolved_genre,
                (loc or {}).get("city"), (loc or {}).get("country"),
                (loc or {}).get("lat"), (loc or {}).get("lon"),
                full_name=user["full_name"])

    async def cleanup():
        logger.info("disconnected sid=%s station=%r", sid, tracked_name)
        if history_row_id is not None:
            await history.end_session(history_row_id)
        if sid:
            nowplaying.session_ended(sid)
        await upstream.aclose()
        await client.aclose()

    async def body():
        try:
            if metaint:
                demux = IcyDemuxer(metaint)
                # Some stations implement full ICY framing (metaint present,
                # confirmed reachable) but never populate StreamTitle at all
                # (confirmed live: TSF Jazz always sends `StreamTitle='';`)
                # — indistinguishable from "no ICY support" to a listener,
                # but has_icy alone reports true, so the frontend would
                # otherwise wait forever for a title that's never coming.
                # Once we've seen a metadata field with no usable title,
                # tell the frontend explicitly rather than staying silent.
                # But only before a real title has ever landed on THIS
                # connection: confirmed live (Heart 70s (UK)) that a
                # station can send a genuine title once, then an empty
                # StreamTitle='' a few milliseconds later on the very next
                # metadata block (some encoder buffering/cycling quirk,
                # not a station that "has no metadata" at all) — without
                # this guard, that immediately following empty block
                # published a stale no_title right after a good title,
                # which nowplaying.py cached for replay alongside it, and
                # the frontend could apply on a WS reconnect (see
                # ensureWsConnected() in usePlayer.ts) in the wrong
                # order relative to a fresh title event, leaving hasIcy
                # incorrectly downgraded. A station that has proven it
                # CAN send a real title should never be reclassified as
                # "no track info," period, for the life of this
                # connection.
                no_title_reported = False
                saw_real_title = False
                async for chunk in upstream.aiter_bytes():
                    audio, title, saw_metadata_field = demux.feed(chunk)
                    if title and sid and nowplaying.is_current_generation(sid, gen):
                        saw_real_title = True
                        logger.info("title sid=%s title=%r", sid, title)
                        nowplaying.publish(sid, {"type": "title", "title": title})
                    elif (saw_metadata_field and not title and not no_title_reported
                          and not saw_real_title
                          and sid and nowplaying.is_current_generation(sid, gen)):
                        no_title_reported = True
                        logger.info("no usable title sid=%s station=%r — "
                                    "station sends empty StreamTitle", sid, tracked_name)
                        nowplaying.publish(sid, {"type": "no_title"})
                    if audio:
                        yield audio
            else:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
        finally:
            # A client disconnect closes this generator via GeneratorExit at
            # whatever await point it's suspended on — any `await` written
            # directly in this `finally` can get cut off mid-cleanup (e.g.
            # the history-end-session write landing or not landing was
            # observed to depend on exact timing, confirmed via a live
            # Playwright test that found rows with a null `ended_at` despite
            # the disconnect being logged). Shielding the cleanup in its own
            # task, independent of this generator's cancellation, is the
            # standard fix — see asyncio.shield() docs.
            await asyncio.shield(asyncio.create_task(cleanup()))

    return StreamingResponse(
        body(), media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )
