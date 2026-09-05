"""WebSocket that ties the stream proxy's now-playing events (icy.py via
nowplaying.py) to AI enrichment (enricher.py) and pushes both to the
browser as they happen — no polling.

The frontend generates a session id (`sid`) per player instance and
passes it both here and to /api/stream?sid=..., so the audio proxy and
this socket share one "now playing" pipe.

Simplification: one active push target per user (the callback the
Enricher notifies on completion is a single overwritable attribute, not
a fan-out list) — matches mradio's own one-station-at-a-time model. A
second simultaneous tab for the same account will steal AI-completion
pushes from the first; both still get now-playing text and cached
blurbs immediately, which covers the actual multi-listener use case
this app is for (different accounts, not one account in two tabs)."""

import asyncio

from fastapi import APIRouter, Query, WebSocket
from starlette.websockets import WebSocketDisconnect

from .. import nowplaying
from ..auth import SESSION_COOKIE_NAME, resolve_session
from ..enrichers import get_enricher
from ..textutil import split_title

router = APIRouter(tags=["ws"])


@router.websocket("/api/ws")
async def now_playing_ws(websocket: WebSocket, sid: str = Query(...)):
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    user = await resolve_session(token) if token else None
    if user is None or user["disabled"] or user["must_change_password"]:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    enricher = await get_enricher(user["id"])
    queue = nowplaying.subscribe(sid)
    state = {"raw_title": ""}

    async def send(payload: dict) -> None:
        try:
            await websocket.send_json(payload)
        except Exception:
            pass

    async def push_enrichment(raw_title: str, item: dict) -> None:
        if raw_title != state["raw_title"]:
            return  # stale — the user has since moved to a different track
        await send({"type": "enrichment", "raw_title": raw_title, "item": item})

    enricher.on_result = push_enrichment

    async def pump_nowplaying() -> None:
        while True:
            event = await queue.get()
            if event["type"] == "station":
                await send({
                    "type": "station",
                    "name": event["name"],
                    "bitrate": event.get("bitrate"),
                    "sample_rate": event.get("sample_rate"),
                    "format": event.get("format"),
                })
            elif event["type"] == "title":
                raw = event["title"]
                state["raw_title"] = raw
                artist, title, performer = split_title(raw)
                await send({"type": "now_playing", "raw_title": raw,
                           "artist": artist, "title": title, "performer": performer})
                cached = await enricher.blurb(raw)
                if cached:
                    await send({"type": "enrichment", "raw_title": raw, "item": cached})
                else:
                    await enricher.submit(raw, artist, title, performer)

    async def pump_client() -> None:
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") == "reenrich" and state["raw_title"]:
                raw = state["raw_title"]
                artist, title, performer = split_title(raw)
                await enricher.invalidate(raw, artist, title, performer)

    pump_task = asyncio.create_task(pump_nowplaying())
    client_task = asyncio.create_task(pump_client())
    try:
        done, _pending = await asyncio.wait(
            [pump_task, client_task], return_when=asyncio.FIRST_COMPLETED)
        for t in done:
            exc = t.exception()
            if exc and not isinstance(exc, WebSocketDisconnect):
                raise exc
    finally:
        pump_task.cancel()
        client_task.cancel()
        for t in (pump_task, client_task):
            try:
                await t
            except (asyncio.CancelledError, WebSocketDisconnect, Exception):
                pass
        nowplaying.unsubscribe(sid, queue)
        if enricher.on_result is push_enrichment:
            enricher.on_result = None
