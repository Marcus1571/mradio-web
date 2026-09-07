"""In-memory hub that hands ICY title changes from an active stream-proxy
connection off to whatever's listening for them.

The frontend generates a session id (`sid`) per player instance and passes
it to both `/api/stream?sid=...` and the WebSocket endpoint (task #5) that
pushes now-playing updates to that browser tab. This is what lets a single
proxied connection to the origin station serve both audio playback and
metadata, per the plan — no second connection to the station just to poll
for the title.

The audio stream (GET /api/stream) and the metadata socket (GET /api/ws)
are two independent requests with no ordering guarantee between them —
over a real network (vs. localhost) the stream's `station`/`title` events
can easily arrive before the socket has subscribed. `publish()` used to
just drop events with no subscriber, which left the frontend stuck showing
"Connecting…" until the track next changed or the user hit Reconnect. Since
`station` and `title` are "latest value wins" state, not a delivery-order-
sensitive event stream, the fix is to remember the latest one per sid and
replay it immediately to a new subscriber.

One `sid` lives for the whole player session (see usePlayer.ts), reused
across every station switch — not one per stream connection. Switching
stations reassigns `audio.src`, which aborts the old /api/stream fetch
client-side, but the server only learns of that asynchronously (a
GeneratorExit the old request's `finally` handles in a shielded background
task — see stream.py). That leaves a real window where the old station's
proxy connection is still alive and can emit one more `title`/`station`
event for a station the user already left, with nothing to tell it apart
from the new one sharing the same sid. `begin_generation()` mints a token
per /api/stream connection; publish() tags every event with it and
`current_generation()` lets a caller confirm before publishing that its
connection is still the active one for that sid, so a late straggler from
an abandoned connection is dropped instead of corrupting the new one's
state."""

import asyncio
import logging
import time
import uuid

logger = logging.getLogger("mradio.nowplaying")

_queues: dict[str, list[asyncio.Queue]] = {}
_last_station: dict[str, dict] = {}
_last_title: dict[str, dict] = {}
_last_no_title: dict[str, dict] = {}
_generation: dict[str, str] = {}

# Who's actually connected right now, for the admin analytics page's
# "Live now" view — keyed by sid, populated/cleared from routers/stream.py
# at connect/disconnect. Deliberately separate from _queues/_last_*
# above: those exist for metadata replay to a *specific* browser tab,
# this is a flat snapshot across *all* sessions for the admin view, and
# doesn't need a DB round-trip since it's inherently transient (lost on
# restart is fine — a restart also drops every active stream connection).
_live_sessions: dict[str, dict] = {}


def session_started(sid: str, user_id: int, username: str, station: str,
                    genre: str, city: str | None, country: str | None,
                    lat: float | None = None, lon: float | None = None,
                    full_name: str | None = None) -> None:
    _live_sessions[sid] = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "station": station,
        "genre": genre,
        "city": city,
        "country": country,
        "lat": lat,
        "lon": lon,
        "connected_at": time.time(),
    }


def session_ended(sid: str) -> None:
    _live_sessions.pop(sid, None)


def live_snapshot() -> list[dict]:
    now = time.time()
    return [
        {**s, "elapsed_seconds": int(now - s["connected_at"])}
        for s in _live_sessions.values()
    ]


def begin_generation(sid: str) -> str:
    """Call once at the start of a new /api/stream connection for `sid`,
    before publishing its `station` event. Returns a token the connection
    must pass to is_current_generation() before each subsequent publish —
    if a stale connection for the same sid is still draining in the
    background (see module docstring), its token no longer matches and its
    leftover events are dropped instead of clobbering the new one's."""
    gen = uuid.uuid4().hex
    _generation[sid] = gen
    return gen


def is_current_generation(sid: str, gen: str) -> bool:
    return _generation.get(sid) == gen


def publish(sid: str, event: dict) -> None:
    if not sid:
        return
    if event.get("type") == "station":
        _last_station[sid] = event
        _last_no_title.pop(sid, None)  # a new station connection supersedes any prior no-title notice
    elif event.get("type") == "title":
        _last_title[sid] = event
        _last_no_title.pop(sid, None)  # a real title arrived — any earlier "no title" notice is stale
    elif event.get("type") == "no_title":
        _last_no_title[sid] = event
    subscribers = _queues.get(sid, [])
    if not subscribers:
        logger.info(
            "publish sid=%s type=%s had no subscriber yet — cached for replay on subscribe",
            sid, event.get("type"),
        )
    for q in subscribers:
        q.put_nowait(event)


def subscribe(sid: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues.setdefault(sid, []).append(q)
    replayed = []
    if sid in _last_station:
        q.put_nowait(_last_station[sid])
        replayed.append("station")
    if sid in _last_title:
        q.put_nowait(_last_title[sid])
        replayed.append("title")
    if sid in _last_no_title:
        q.put_nowait(_last_no_title[sid])
        replayed.append("no_title")
    logger.info("subscribe sid=%s replayed=%s", sid, replayed or "none")
    return q


def unsubscribe(sid: str, q: asyncio.Queue) -> None:
    lst = _queues.get(sid)
    if not lst:
        return
    if q in lst:
        lst.remove(q)
    if not lst:
        _queues.pop(sid, None)
        _last_station.pop(sid, None)
        _last_title.pop(sid, None)
        _last_no_title.pop(sid, None)
        _generation.pop(sid, None)
        logger.info("unsubscribe sid=%s — no subscribers left, cache cleared", sid)
