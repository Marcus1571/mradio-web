"""Per-user AI liner-notes enrichment (mradio's Enricher class, ported to
asyncio). One instance per active user — see enrichers.py — because each
user picks their own active provider from the globally-configured set
(settings.py). The trivia cache itself is shared (cache.py): the LLM call
and Wikipedia lookup are the slow part, and a track queried by one user
benefits every other user on the same provider."""

import asyncio
import time
from typing import Awaitable, Callable

from . import cache as cache_store
from . import providers
from . import settings as settings_store
from . import wiki
from .textutil import apply_provider_rules, elide, extract_json_item
from .userdata import load_cfg, persist_cfg

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
}

_FAIL_ITEM = {"work": "", "trivia": "", "wiki": "", "movement": 0, "fail": True}

# One shared opencode subprocess for the whole app (opencode config is
# global, same as every other provider here).
_opencode = providers.OpencodeSession()


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
        self._task: asyncio.Task | None = None
        self.on_result: Callable[[str, dict], Awaitable[None] | None] | None = None

    async def start(self) -> None:
        cfg = await load_cfg(self.user_id)
        p = cfg.get("provider", "")
        self.provider = p if p in PROVIDERS else ""
        lang = cfg.get("language", "en")
        self.language = lang if lang in _LANGUAGE_INSTRUCTIONS else "en"
        self._task = asyncio.create_task(self._worker())

    async def shutdown(self) -> None:
        if self._task is not None:
            self._task.cancel()

    async def active_provider(self) -> str:
        settings = settings_store.load()
        order = ([self.provider] if providers.provider_enabled(self.provider, settings)
                 else []) + [n for n in PROVIDERS if n != self.provider
                             and providers.provider_enabled(n, settings)]
        return order[0] if order else ""

    async def switch_provider(self, name: str) -> bool:
        settings = settings_store.load()
        if name not in PROVIDERS or not providers.provider_enabled(name, settings):
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

    async def invalidate(self, raw_title: str, artist: str, title: str, performer: str) -> None:
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
        order = ([self.provider] if providers.provider_enabled(self.provider, settings)
                 else []) + [n for n in PROVIDERS if n != self.provider
                             and providers.provider_enabled(n, settings)]
        for name in order:
            if name == "ollama":
                out = await providers.llm_ollama(settings, prompt)
            elif name == "openai":
                out = await providers.llm_openai(settings, prompt)
            elif name == "opencode":
                out = await _opencode.ask(settings, prompt)
            else:
                out = None
            if out:
                return out
        return None

