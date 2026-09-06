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
    station_name = (upstream.headers.get("icy-name") or "").strip()
    icy_br = upstream.headers.get("icy-br")
    icy_sr = upstream.headers.get("icy-sr")
    logger.info(
        "connected sid=%s station=%r bitrate=%s sample_rate=%s format=%s metaint=%s",
        sid, station_name, icy_br, icy_sr, content_type, metaint,
    )
    if sid and station_name:
        nowplaying.publish(sid, {
            "type": "station",
            "name": station_name,
            "bitrate": icy_br,
            "sample_rate": icy_sr,
            "format": content_type,
        })

    history_row_id: int | None = None
    if station_name:
        client_ip = request.client.host if request.client else None
        resolved_genre = genre if genre in stations.GENRES else stations.genre_of(station_name)
        history_row_id, loc = await history.start_session(
            user["id"], station_name, url, resolved_genre, client_ip)
        if sid:
            nowplaying.session_started(
                sid, user["id"], user["username"], station_name, resolved_genre,
                (loc or {}).get("city"), (loc or {}).get("country"),
                (loc or {}).get("lat"), (loc or {}).get("lon"),
                full_name=user["full_name"])

    async def cleanup():
        logger.info("disconnected sid=%s station=%r", sid, station_name)
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
                async for chunk in upstream.aiter_bytes():
                    audio, title = demux.feed(chunk)
                    if title and sid:
                        logger.info("title sid=%s title=%r", sid, title)
                        nowplaying.publish(sid, {"type": "title", "title": title})
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
