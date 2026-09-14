"""Shared music-service link cache: raw ICY title -> a track's public page
URL on the active music service (Spotify/Deezer/...).

Shared across all users rather than per-user, same rationale as cache.py:
the same raw ICY title on the same service resolves to the same URL
regardless of who's asking, since the lookup carries no per-user state
(no OAuth, no personalization). Keyed by (service, raw_title) — no
language dimension, since a track URL isn't localized the way AI trivia
text is.

Misses are cached too (stored as {"url": None}), not just hits — without
this, a track with no confident match on the active service would get
re-searched on every reconnect or service-switch for as long as it's
playing. get_cached() returning None (the Python value, not the dict key)
means "never looked up"; a cached {"url": None} means "looked up, no
match" — these are deliberately distinguishable."""

import asyncio

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json

CACHE_FILE = DATA_DIR / "music_link_cache.json"
MAX_ENTRIES = 800

# Single-process deployment (one FastAPI worker) — this lock only needs to
# serialize concurrent requests within that one process, same as cache.py.
_lock = asyncio.Lock()


def _key(service: str, raw_title: str) -> str:
    return f"{service}::{raw_title}"


def _load_sync() -> dict:
    data = read_json(CACHE_FILE)
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in list(data.items())[-MAX_ENTRIES:] if isinstance(v, dict)}


def _save_sync(cache: dict) -> bool:
    return atomic_write_json(CACHE_FILE, cache)


async def get_cached(service: str, raw_title: str) -> dict | None:
    cache = await asyncio.to_thread(_load_sync)
    return cache.get(_key(service, raw_title))


async def store(service: str, raw_title: str, url: str | None) -> None:
    """Read-modify-write under a lock so concurrent requests (from
    different users) can't clobber each other's writes."""
    async with _lock:
        cache = await asyncio.to_thread(_load_sync)
        cache[_key(service, raw_title)] = {"url": url}
        if len(cache) > MAX_ENTRIES:
            cache.pop(next(iter(cache)))
        await asyncio.to_thread(_save_sync, cache)
