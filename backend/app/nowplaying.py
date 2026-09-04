"""In-memory hub that hands ICY title changes from an active stream-proxy
connection off to whatever's listening for them.

The frontend generates a session id (`sid`) per player instance and passes
it to both `/api/stream?sid=...` and the WebSocket endpoint (task #5) that
pushes now-playing updates to that browser tab. This is what lets a single
proxied connection to the origin station serve both audio playback and
metadata, per the plan — no second connection to the station just to poll
for the title."""

import asyncio

_queues: dict[str, list[asyncio.Queue]] = {}


def publish(sid: str, event: dict) -> None:
    if not sid:
        return
    for q in _queues.get(sid, []):
        q.put_nowait(event)


def subscribe(sid: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _queues.setdefault(sid, []).append(q)
    return q


def unsubscribe(sid: str, q: asyncio.Queue) -> None:
    lst = _queues.get(sid)
    if not lst:
        return
    if q in lst:
        lst.remove(q)
    if not lst:
        _queues.pop(sid, None)
