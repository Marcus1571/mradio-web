"""Shared AI trivia cache: author/track -> liner-note blurb.

Shared across all users rather than per-user, on purpose — the same
"Sting - Every Breath You Take" result benefits everyone, not just
whoever triggered it first. Entries are keyed by (provider, raw ICY
title): the active AI provider is a per-user choice, so keying in the
provider means two users on different providers never overwrite each
other's cached result for the same track, and each provider's answer for
a track is cached independently."""

import asyncio
from pathlib import Path

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json

CACHE_FILE = DATA_DIR / "cache.json"
MAX_ENTRIES = 800

# Single-process deployment (one FastAPI worker, per the plan) — this lock
# only needs to serialize concurrent requests within that one process.
_lock = asyncio.Lock()


def _key(provider: str, title: str) -> str:
    return f"{provider}::{title}"


def _load_sync() -> dict:
    data = read_json(CACHE_FILE)
    if not isinstance(data, dict):
        return {}
    # keep only the most recent MAX_ENTRIES entries on load
    return {k: v for k, v in list(data.items())[-MAX_ENTRIES:] if isinstance(v, dict)}


def _save_sync(cache: dict) -> bool:
    return atomic_write_json(CACHE_FILE, cache)


async def get_cached(provider: str, title: str) -> dict | None:
    cache = await asyncio.to_thread(_load_sync)
    return cache.get(_key(provider, title))


async def store(provider: str, title: str, item: dict) -> None:
    """Read-modify-write under a lock so concurrent requests (from
    different users) can't clobber each other's writes."""
    async with _lock:
        cache = await asyncio.to_thread(_load_sync)
        cache[_key(provider, title)] = item
        if len(cache) > MAX_ENTRIES:
            cache.pop(next(iter(cache)))
        await asyncio.to_thread(_save_sync, cache)
