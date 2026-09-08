"""Registry of live Enricher instances — one per user who has actually
used enrichment, created lazily and kept for the app process's lifetime
(not per-request: submit/pending/epoch state needs to persist between
polls)."""

from . import enricher as enricher_mod
from .enricher import Enricher

_enrichers: dict[int, Enricher] = {}


async def get_enricher(user: dict) -> Enricher:
    e = _enrichers.get(user["id"])
    if e is None:
        e = Enricher(user["id"])
        await e.start()
        _enrichers[user["id"]] = e
    # Refresh on every call (not just at creation) so a mid-session
    # admin promotion/demotion takes effect immediately — every caller
    # already has a freshly-loaded `user` dict from get_active_user's
    # dependency, so this is free, not an extra DB round-trip.
    e.is_admin = bool(user["is_admin"])
    return e


async def shutdown_all() -> None:
    for e in _enrichers.values():
        await e.shutdown()
    _enrichers.clear()
    await enricher_mod._opencode.kill()
