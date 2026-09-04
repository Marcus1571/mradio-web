"""Registry of live Enricher instances — one per user who has actually
used enrichment, created lazily and kept for the app process's lifetime
(not per-request: submit/pending/epoch state needs to persist between
polls)."""

from . import enricher as enricher_mod
from .enricher import Enricher

_enrichers: dict[int, Enricher] = {}


async def get_enricher(user_id: int) -> Enricher:
    e = _enrichers.get(user_id)
    if e is None:
        e = Enricher(user_id)
        await e.start()
        _enrichers[user_id] = e
    return e


async def shutdown_all() -> None:
    for e in _enrichers.values():
        await e.shutdown()
    _enrichers.clear()
    await enricher_mod._opencode.kill()
