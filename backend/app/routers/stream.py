"""Audio stream proxy — the fix for browsers silently blocking playback of
HTTP-only stations from an HTTPS page. Every station goes through this one
route, not just the HTTP-only ones: same code path for all, and it's also
the only connection made to the origin station, since ICY metadata is
parsed off the same bytes as they pass through (see icy.py)."""

import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from .. import nowplaying
from ..deps import get_active_user
from ..icy import IcyDemuxer, parse_metaint

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
async def stream(url: str = Query(..., description="the station's real stream URL"),
                 sid: str | None = Query(
                     None, description="player session id for now-playing push"),
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
    if sid and station_name:
        nowplaying.publish(sid, {
            "type": "station",
            "name": station_name,
            "bitrate": icy_br,
            "sample_rate": icy_sr,
            "format": content_type,
        })

    async def body():
        try:
            if metaint:
                demux = IcyDemuxer(metaint)
                async for chunk in upstream.aiter_bytes():
                    audio, title = demux.feed(chunk)
                    if title and sid:
                        nowplaying.publish(sid, {"type": "title", "title": title})
                    if audio:
                        yield audio
            else:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(
        body(), media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )
