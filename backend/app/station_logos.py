"""Station logo cache: stream URL -> resolved logo image URL (or a
confirmed miss). Global, not per-user — a station's logo isn't a
per-listener concept, same reasoning as the AI trivia cache (cache.py),
whose JSON-file shape this mirrors closely.

A confirmed miss is cached as {"logo": None}, not simply omitted — this
is what stops a station with no findable logo from re-querying
Radio-Browser on every single play."""

import asyncio

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json

CACHE_FILE = DATA_DIR / "station_logos.json"
MAX_ENTRIES = 500

# Single-process deployment (one FastAPI worker) — this lock only needs
# to serialize concurrent requests within that one process.
_lock = asyncio.Lock()


def _load_sync() -> dict:
    data = read_json(CACHE_FILE)
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in list(data.items())[-MAX_ENTRIES:] if isinstance(v, dict)}


def _save_sync(cache: dict) -> bool:
    return atomic_write_json(CACHE_FILE, cache)


async def get_cached(url: str) -> dict | None:
    cache = await asyncio.to_thread(_load_sync)
    return cache.get(url)


async def store(url: str, logo: str | None) -> None:
    """Read-modify-write under a lock so concurrent requests (from
    different users hitting the same uncached station) can't clobber
    each other's writes."""
    async with _lock:
        cache = await asyncio.to_thread(_load_sync)
        cache[url] = {"logo": logo}
        if len(cache) > MAX_ENTRIES:
            cache.pop(next(iter(cache)))
        await asyncio.to_thread(_save_sync, cache)
