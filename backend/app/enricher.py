"""Per-user AI liner-notes enrichment (mradio's Enricher class, ported to
asyncio). One instance per active user — see enrichers.py — because each
user picks their own active provider from the globally-configured set
(settings.py). The trivia cache itself is shared (cache.py): the LLM call
and Wikipedia lookup are the slow part, and a track queried by one user
benefits every other user on the same provider."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from typing import Awaitable, Callable

from . import cache as cache_store
from . import db
from . import providers
from . import settings as settings_store
from . import wiki
from .textutil import apply_provider_rules, elide, extract_json_item
from .userdata import load_cfg, persist_cfg

logger = logging.getLogger("mradio.enricher")

PROVIDERS = providers.PROVIDERS

_PROMPT_TEMPLATE = (
    "You enrich now-playing metadata for a live radio stream — classical, "
    "jazz, rock, pop, or any other genre.\n"
    "{question}\n"
    "Reply with ONLY a single raw JSON object, nothing else. No markdown, "
    "no code fences, no reasoning, no explanations, no text before or "
    "after. Use exactly this shape:\n"
    '{{"movement": 0, "work": "", "wiki": "", "trivia": ""}}\n'
    "Rules:\n"
    '- "movement": 1 ONLY if the tagged name is a movement, part, section '
    'or fragment of a larger complete work (e.g. "1. Allegro", "Adagio", '
    '"Finale", "Menuetto", "II."). A short standalone piece such as a '
    'mazurka, prelude, song, waltz or individual character piece IS the '
    'whole work: use 0 and leave "work" empty.\n'
    '- "work": the canonical name of the WHOLE work with opus/catalogue '
    'number, ONLY when "movement" is 1; otherwise "".\n'
    '- "wiki": the exact English Wikipedia article title to link the '
    'listener to, if a suitable one exists — return "" if not. For a '
    'classical work, use the whole work with its disambiguator, e.g. '
    '"Mazurkas, Op. 67 (Chopin)" or "Sonata da camera No. 3 (Corelli)". '
    'For a song, single, or other non-classical track, use the article '
    'about that song/track itself if one exists, e.g. "Hate That I Made '
    'You Love Me" or "Who\'s Zoomin\' Who"; only fall back to "" if no '
    'article about the specific track exists (do not substitute the '
    "artist's own article as a fallback).\n"
    '- "trivia": 6-9 short plain sentences that weave together BOTH '
    '(a) the composer — who they were, their era/place in music '
    'history, notable relations or legacy — and (b) the piece being '
    'played — date, catalogue number, structure/movements, dedication, '
    'premiere, notable performers or recordings, where one may have '
    'heard it. Flow naturally from one to the other (either order, no '
    'headings, no labels). Aim for 750-850 characters with a hard '
    'maximum of 850 — if your draft runs long, tighten it. Always end '
    'on a complete, natural final sentence; never trail off mid-thought.\n'
    '- Any date given as day/month/year: write it as "8 December 1813", '
    'never "12/8/1813" or "August 8" — do not silently swap day and '
    'month between US (MM/DD) and international (DD/MM) conventions.\n'
    "{language_instruction}"
    "Output the JSON object and nothing else."
)

# English is the model's natural default, so it costs nothing to leave
# implicit. Only "trivia" changes language — "work"/"wiki" must stay as
# specified above regardless (wiki.resolve() looks up the ENGLISH
# Wikipedia specifically, see _worker() below).
_LANGUAGE_INSTRUCTIONS = {
    "en": "",
    "es": (
        '- Write the "trivia" field in Spanish (Español). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "it": (
        '- Write the "trivia" field in Italian (Italiano). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "pt": (
        '- Write the "trivia" field in Portuguese (Português). Keep "work" '
        'and "wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "fr": (
        '- Write the "trivia" field in French (Français). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "ru": (
        '- Write the "trivia" field in Russian (Русский). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "de": (
        '- Write the "trivia" field in German (Deutsch). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "el": (
        '- Write the "trivia" field in Greek (Ελληνικά). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "nl": (
        '- Write the "trivia" field in Dutch (Nederlands). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "da": (
        '- Write the "trivia" field in Danish (Dansk). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "sv": (
        '- Write the "trivia" field in Swedish (Svenska). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "nb": (
        '- Write the "trivia" field in Norwegian Bokmål (Norsk bokmål). '
        'Keep "work" and "wiki" exactly as specified above regardless of '
        'language — "wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "ja": (
        '- Write the "trivia" field in Japanese (日本語). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "tr": (
        '- Write the "trivia" field in Turkish (Türkçe). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
    "he": (
        '- Write the "trivia" field in Hebrew (עברית). Keep "work" and '
        '"wiki" exactly as specified above regardless of language — '
        '"wiki" MUST remain the English Wikipedia article title.\n'
    ),
}

_FAIL_ITEM = {"work": "", "trivia": "", "wiki": "", "movement": 0, "fail": True}

# One shared opencode subprocess for the whole app (opencode config is
# global, same as every other provider here).
_opencode = providers.OpencodeSession()

# settings.py's model keys aren't a uniform "{provider}_model" pattern
# (openai's is "api_model", not "openai_model"; codex/opencode have no
# configurable model at all — codex is a fixed subscription model,
# opencode picks its own). Explicit map instead of guessing the key.
_MODEL_SETTINGS_KEY = {
    "ollama": "ollama_model",
    "openai": "api_model",
    "grok": "grok_model",
    "gemini": "gemini_model",
    "openrouter": "openrouter_model",
    "mistral": "mistral_model",
}


async def _record_ai_request(provider: str, model: str, elapsed_ms: int, outcome: str) -> None:
    """Best-effort stats logging for AI.md's speed/reliability numbers —
    see backend/app/ai_stats.py for the reader side. Every llm_* function
    already catches its own exceptions and returns None on any failure
    (HTTP error, timeout, parse error alike — see providers.py), so from
    here a call is only ever `success` or `no_output`; the DB schema
    keeps room for a finer-grained outcome if a provider function is
    later changed to surface the real failure reason instead of
    swallowing it. Never allowed to break enrichment itself — a stats
    write failing is a lost data point, not a reason to fail the user's
    trivia request."""
    try:
        async with db.tx() as conn:
            await conn.execute(
                "INSERT INTO ai_requests (provider, model, started_at, elapsed_ms, outcome) "
                "VALUES (?, ?, ?, ?, ?)",
                (provider, model, datetime.now(timezone.utc).isoformat(), elapsed_ms, outcome),
            )
    except Exception:
        logger.warning("failed to record ai_requests row for provider=%s", provider, exc_info=True)


class Enricher:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self.last_key: str | None = None
        self.last_artist: str = ""
        self.last_title: str = ""
        self.last_performer: str = ""
        self.started: dict[str, float] = {}
        self.epoch = 0
        self.provider = ""
        self.language = "en"
        # Set by enrichers.get_enricher() on every fetch (creation and
        # every subsequent call), never guessed here — Enricher itself
        # has no way to look up admin status on its own, and re-querying
        # the DB here would risk going stale between requests anyway.
        self.is_admin = False
        self._task: asyncio.Task | None = None
        self.on_result: Callable[[str, dict], Awaitable[None] | None] | None = None

    async def start(self) -> None:
        cfg = await load_cfg(self.user_id)
        p = cfg.get("provider", "")
        # A non-admin's persisted `provider` choice could be one of
        # ADMIN_ONLY_PROVIDERS from before this restriction existed (or
        # from being demoted after picking it) — is_admin isn't known
        # yet at this point (set right after get_enricher() constructs
        # this instance), so this can't filter admin-only providers out
        # yet. _usable_provider_order() below is what actually enforces
        # the restriction on every real use; this just seeds a sane
        # starting value.
        self.provider = p if p in PROVIDERS else ""
        lang = cfg.get("language", "en")
        self.language = lang if lang in _LANGUAGE_INSTRUCTIONS else "en"
        self._task = asyncio.create_task(self._worker())

    async def shutdown(self) -> None:
        if self._task is not None:
            self._task.cancel()

    def _usable_providers(self) -> tuple[str, ...]:
        """PROVIDERS, minus admin-only ones for a non-admin user — the
        single choke point every provider-order computation (active_provider,
        switch_provider, _llm's fallback chain) goes through, so a
        regular user can never end up on ChatGPT/Grok via any path,
        including automatic fallback when their own pick fails."""
        if self.is_admin:
            return PROVIDERS
        return tuple(n for n in PROVIDERS if n not in providers.ADMIN_ONLY_PROVIDERS)

    async def active_provider(self) -> str:
        settings = settings_store.load()
        usable = self._usable_providers()
        order = ([self.provider] if self.provider in usable
                 and providers.provider_enabled(self.provider, settings)
                 else []) + [n for n in usable
                             if n != self.provider and providers.provider_enabled(n, settings)]
        return order[0] if order else ""

    async def switch_provider(self, name: str) -> bool:
        settings = settings_store.load()
        if name not in self._usable_providers() or not providers.provider_enabled(name, settings):
            return False
        self.provider = name
        providers.clear_offline()
        await persist_cfg(self.user_id, provider=name)
        return True

    async def blurb(self, raw_title: str) -> dict | None:
        if not self.provider or not raw_title:
            return None
        item = await cache_store.get_cached(self.provider, self.language, raw_title)
        return item if item and not item.get("fail") else None

    def pending(self, raw_title: str) -> bool:
        return self.last_key == raw_title and raw_title in self.started

    def elapsed(self, raw_title: str) -> int:
        t = self.started.get(raw_title)
        return int(time.time() - t) if t else 0

    async def submit(self, raw_title: str, artist: str, title: str, performer: str) -> None:
        if not raw_title:
            return
        self.last_key = raw_title
        self.last_artist = artist
        self.last_title = title
        self.last_performer = performer
        if self.provider:
            cached = await cache_store.get_cached(self.provider, self.language, raw_title)
            if cached and not cached.get("fail"):
                return
        self.started[raw_title] = time.time()
        await self.queue.put((raw_title, artist, title, performer))

    async def invalidate(self, raw_title: str, artist: str, title: str, performer: str,
                          force: bool = False) -> None:
        """Two distinct callers share this method with two distinct
        intents, both keyed off the currently-set self.provider/language:
        a language switch or a provider switch (force=False, the
        default) wants whatever's already cached for the *new*
        provider/language if it exists — re-running the LLM would just
        reproduce the same cached answer at the cost of a real API call
        and a long wait. The "Re-ask AI" button (force=True) wants a
        genuinely fresh answer even if one is cached — that's the whole
        point of the button.

        Bug fixed here (2026-09-07): force=False used to go straight to
        submit(), whose own cache check only prevents re-queuing — it
        silently returns on a cache hit without ever telling the caller,
        so nothing pushed the cached result to the frontend. The panel
        was left showing "Asking the AI provider..." forever with no
        network call ever happening, which from the user's side looked
        indistinguishable from "it's searching again" (confirmed live:
        switching en -> he -> en -> he left the panel stuck on the
        placeholder on the second return to he, despite a real cached
        he entry already sitting in cache.json for that exact track).
        """
        if not force and self.provider and raw_title:
            cached = await cache_store.get_cached(self.provider, self.language, raw_title)
            if cached and not cached.get("fail"):
                self.last_key = raw_title
                self.last_artist = artist
                self.last_title = title
                self.last_performer = performer
                if self.on_result:
                    result = self.on_result(raw_title, cached)
                    if result is not None:
                        await result
                return
        # A deliberate re-ask (the "Re-ask AI" button, or a fresh provider
        # switch below) is exactly the case the global offline cooldown
        # shouldn't block — it exists to stop automatic background retries
        # from hammering a genuinely down provider, not to veto a human
        # explicitly asking again. Without this, one transient failure from
        # ANY user on ANY provider silently no-ops every retry for 2
        # minutes, which is indistinguishable from "AI is just broken."
        providers.clear_offline()
        self.epoch += 1
        self.started.pop(raw_title, None)
        if force:
            # Bypass submit()'s own cache check too — force means force,
            # even if the LLM will (validly) return the same answer again.
            self.last_key = raw_title
            self.last_artist = artist
            self.last_title = title
            self.last_performer = performer
            self.started[raw_title] = time.time()
            await self.queue.put((raw_title, artist, title, performer))
        else:
            await self.submit(raw_title, artist, title, performer)

    async def _worker(self) -> None:
        while True:
            raw_title, artist, title, performer = await self.queue.get()
            epoch = self.epoch
            settings = settings_store.load()
            if not providers.ai_configured(settings):
                await self._finish(raw_title, epoch, dict(_FAIL_ITEM))
                continue
            if providers.is_offline():
                await self._finish(raw_title, epoch, dict(_FAIL_ITEM))
                continue
            item = await self._ask(settings, artist, title, performer)
            if item is None:
                providers.mark_offline()
                item = dict(_FAIL_ITEM)
            elif item.get("wiki"):
                surname = (artist.split("(")[0].split()[-1] if artist else "") or ""
                resolved = await wiki.resolve(item["wiki"], surname)
                item["wiki"] = resolved["url"] if resolved else ""
            await self._finish(raw_title, epoch, item)

    async def _finish(self, raw_title: str, epoch: int, item: dict) -> None:
        self.started.pop(raw_title, None)
        if epoch != self.epoch:
            return  # stale reply discarded (provider/selection changed since submit)
        if not item.get("fail") and self.provider:
            await cache_store.store(self.provider, self.language, raw_title, item)
        if self.on_result:
            result = self.on_result(raw_title, item)
            if result is not None:
                await result

    async def _ask(self, settings: dict, artist: str, title: str, performer: str) -> dict | None:
        question = (
            f"Artist/Composer: {artist or 'unknown'} · "
            f"Tagged name: {title or 'unknown'} · "
            f"Performer (if present): {performer or 'none'}"
        )
        prompt = apply_provider_rules(
            _PROMPT_TEMPLATE.format(
                question=question,
                language_instruction=_LANGUAGE_INSTRUCTIONS.get(self.language, ""),
            ),
            self.provider,
            model=settings.get("ollama_model", "") if self.provider == "ollama" else "",
        )
        raw = await self._llm(settings, prompt)
        if raw is None:
            return None
        item = extract_json_item(raw)
        if not item["movement"]:
            item["work"] = ""
        item["trivia"] = elide((item["trivia"] or "").replace('"', ""))
        return item

    async def _llm(self, settings: dict, prompt: str) -> str | None:
        usable = self._usable_providers()
        order = ([self.provider] if self.provider in usable
                 and providers.provider_enabled(self.provider, settings)
                 else []) + [n for n in usable
                             if n != self.provider and providers.provider_enabled(n, settings)]
        for name in order:
            started = time.perf_counter()
            if name == "ollama":
                out = await providers.llm_ollama(settings, prompt)
            elif name == "openai":
                out = await providers.llm_openai(settings, prompt)
            elif name == "codex":
                out = await providers.llm_codex(settings, prompt)
            elif name == "grok":
                out = await providers.llm_grok(settings, prompt)
            elif name == "gemini":
                out = await providers.llm_gemini(settings, prompt)
            elif name == "openrouter":
                out = await providers.llm_openrouter(settings, prompt)
            elif name == "mistral":
                out = await providers.llm_mistral(settings, prompt)
            elif name == "opencode":
                out = await _opencode.ask(settings, prompt)
            else:
                out = None
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            model = settings.get(_MODEL_SETTINGS_KEY.get(name, ""), "")
            await _record_ai_request(name, model, elapsed_ms, "success" if out else "no_output")
            if out:
                if name in providers.AUTO_HIDE_PROVIDERS:
                    providers.mark_provider_recovered(name)
                return out
            if name in providers.AUTO_HIDE_PROVIDERS:
                providers.mark_provider_failed(name)
        return None

