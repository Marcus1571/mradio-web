"""Async LLM provider calls for AI liner-note enrichment, ported from
mradio's Enricher._llm_ollama/_llm_openai/_llm_opencode. Credentials are
global (settings.py, admin-managed) — every user picks from the same set
of configured providers, none of them hold their own keys."""

import asyncio
import json
import logging
import shutil
import time
import urllib.parse

import httpx

from . import codex_oauth, codex_settings, grok_oauth, grok_settings
from . import settings as settings_store

logger = logging.getLogger("mradio.providers")

# codex/grok first (subscription-backed, admin-only), then mistral —
# user's explicit ordering request (2026-09-09): "the three with
# subscription at the top, Mistral being the third" — a dropdown/list
# order preference, not a functional grouping (mistral is a free-tier
# key, not a subscription).
PROVIDERS = ("codex", "grok", "mistral", "opencode", "ollama", "openai", "gemini", "openrouter")

# Providers restricted to admins only. Three different reasons feed this
# set: codex/grok (2026-09-07, user's explicit request) because a
# regular user picking one would spend the admin's real money with no
# visibility into it — both of Grok's modes are included, not just its
# subscription mode, since Grok's API-key mode is still tied to the
# admin's own paid xAI account, same as ChatGPT. openrouter
# (2026-09-08) for a different reason — it's genuinely free, but its
# free tier is a single shared daily quota (50 requests/day, confirmed
# live) across every account using that one saved key; with several
# users able to pick it, that quota could be exhausted by midday.
# mistral (2026-09-09, user's explicit request: "let's have Mistral
# only available to admins for now") — a temporary, deliberately
# unexplained restriction rather than a quota-driven one like
# openrouter's; revisit if the user says why later. Deliberately NOT
# applied to gemini, whose free-tier daily caps are per-model and
# comfortably higher (500/day on the Lite model this app defaults to,
# see settings.py) — no shared-quota concern there.
ADMIN_ONLY_PROVIDERS = frozenset({"codex", "grok", "openrouter", "mistral"})

_OC_ONPATH: bool | None = None

# Global "all providers just failed" cooldown, shared across every user's
# Enricher — credentials are global now, so if every provider is down,
# every user backing off together (instead of each hammering it on their
# own schedule) matches mradio's own single-instance behavior.
_offline_until = 0.0


def is_offline() -> bool:
    return time.time() < _offline_until


def mark_offline(seconds: float = 120) -> None:
    global _offline_until
    _offline_until = time.time() + seconds


def clear_offline() -> None:
    global _offline_until
    _offline_until = 0.0


# Per-provider auto-hide on failure, scoped to the quota-prone providers
# only (the same set that already got the manual enable/disable toggle
# in 1.7.1) — Ollama/NIM failures are almost always a config mistake
# (wrong URL/key) that won't self-heal on a timer, so auto-hiding them
# would just mask something the admin needs to go fix, not something
# that recovers on its own. Distinct from _offline_until above: that's
# a single global "everything just failed" cooldown; this is per-
# provider, driven by real enrichment failures (not a proactive health
# check — no extra API calls for a provider nobody's using), and comes
# back only after a real background retest passes, not blindly after a
# timer (see health_retry_loop() below for the retest).
AUTO_HIDE_PROVIDERS = frozenset({"codex", "grok", "gemini", "openrouter", "mistral"})
_RETRY_COOLDOWN_SECONDS = 30 * 60

_provider_next_retry: dict[str, float] = {}


def mark_provider_failed(name: str) -> None:
    if name not in AUTO_HIDE_PROVIDERS:
        return
    _provider_next_retry[name] = time.time() + _RETRY_COOLDOWN_SECONDS


def mark_provider_recovered(name: str) -> None:
    _provider_next_retry.pop(name, None)


def provider_hidden_by_failure(name: str) -> bool:
    next_retry = _provider_next_retry.get(name)
    return next_retry is not None and time.time() < next_retry


def providers_due_for_retry() -> list[str]:
    now = time.time()
    return [name for name, next_retry in _provider_next_retry.items() if now >= next_retry]


_HEALTH_CHECK_INTERVAL_SECONDS = 5 * 60


async def health_retry_loop() -> None:
    """Runs for the lifetime of the server process (started from
    main.py's lifespan, independent of any user session — a provider
    hidden by failure recovers on its own even if nobody is logged in
    to trigger it). Every _HEALTH_CHECK_INTERVAL_SECONDS, checks which
    auto-hidden providers are past their cooldown and makes one real
    run_provider_test() call each — the same call the Test button
    makes — to confirm they're actually working again before un-hiding
    them, rather than blindly un-hiding after a timer with no check."""
    while True:
        await asyncio.sleep(_HEALTH_CHECK_INTERVAL_SECONDS)
        due = providers_due_for_retry()
        if not due:
            continue
        settings = settings_store.load()
        for name in due:
            try:
                ok, _message = await run_provider_test(name, settings)
            except Exception:
                logger.exception("health retest crashed for provider=%s", name)
                mark_provider_failed(name)
                continue
            if ok:
                logger.info("provider=%s recovered on background retest", name)
                mark_provider_recovered(name)
            else:
                logger.info("provider=%s still failing on background retest", name)
                mark_provider_failed(name)


def oc_binary_present() -> bool:
    global _OC_ONPATH
    if _OC_ONPATH is None:
        try:
            _OC_ONPATH = shutil.which("opencode") is not None
        except OSError:
            _OC_ONPATH = False
    return _OC_ONPATH


def oc_port(settings: dict) -> int:
    oc = settings.get("opencode")
    if oc:
        if str(oc).strip() in ("1", "on", "yes", "true"):
            return 4096
        try:
            return int(oc)
        except (TypeError, ValueError):
            return 4096
    if oc_binary_present():
        return 4096
    return 0


def grok_enabled(settings: dict) -> bool:
    """True if EITHER of Grok's two mutually-exclusive modes (settings.py's
    grok_mode radio choice) is actually configured — an API key typed in
    for "api_key" mode, or a completed OAuth login for "subscription"
    mode. Only the mode currently selected is checked, matching how the
    other providers only count as enabled when their one credential
    field is filled."""
    mode = settings.get("grok_mode") or "api_key"
    if mode == "subscription":
        return bool(grok_settings.load().get("access_token"))
    return bool(settings.get("grok_api_key"))


def provider_enabled(name: str, settings: dict) -> bool:
    # codex/grok/gemini/openrouter all also need their manual switch on
    # — an admin can hide a still-configured provider from the player
    # dropdown the moment it hits its usage quota (see providers.py's
    # _format_codex_error and _format_gemini/_gemini_error_message,
    # plus OpenRouter's shared-quota concern — see ADMIN_ONLY_PROVIDERS'
    # comment), without disconnecting/losing the saved credential, and
    # flip it back on once the quota resets. Defaults to True, so a
    # provider that's never had the switch touched behaves exactly as
    # it always has (visible whenever configured). Ollama/NIM don't get
    # this — no quota to hit against a self-hosted or bring-your-own-key
    # endpoint the same way.
    probe = {
        "opencode": bool(oc_port(settings)),
        "ollama": bool(settings.get("ollama_url")),
        "openai": bool(settings.get("api_key")),
        "codex": bool(codex_settings.load().get("access_token"))
                 and settings.get("codex_manually_enabled", True),
        "grok": grok_enabled(settings) and settings.get("grok_manually_enabled", True),
        "gemini": bool(settings.get("gemini_api_key"))
                  and settings.get("gemini_manually_enabled", True),
        "openrouter": bool(settings.get("openrouter_api_key"))
                      and settings.get("openrouter_manually_enabled", True),
        "mistral": bool(settings.get("mistral_api_key"))
                   and settings.get("mistral_manually_enabled", True),
    }
    # Auto-hide on failure (see AUTO_HIDE_PROVIDERS) is a separate gate
    # from the manual switch above — a provider that just failed a real
    # request gets hidden here regardless of the manual toggle's own
    # state, and comes back only once a background retest passes (see
    # enrichers.py's _health_retry_loop()), not on a blind timer.
    return probe.get(name, False) and not provider_hidden_by_failure(name)


def ai_configured(settings: dict) -> bool:
    return bool(settings.get("ollama_url")) or bool(settings.get("api_key")) \
        or bool(oc_port(settings)) or bool(codex_settings.load().get("access_token")) \
        or grok_enabled(settings) or bool(settings.get("gemini_api_key")) \
        or bool(settings.get("openrouter_api_key")) or bool(settings.get("mistral_api_key"))


def api_endpoint(base: str, suffix: str) -> str:
    """Join an API path onto a base URL, tolerating a base that already
    carries the full endpoint or an arbitrary path prefix."""
    base = (base or "").rstrip("/")
    if not base:
        return suffix
    if base.endswith("/" + suffix):
        return base
    return urllib.parse.urljoin(base + "/", suffix)


async def llm_ollama(settings: dict, prompt: str) -> str | None:
    url = api_endpoint(settings.get("ollama_url", ""), "api/generate")
    payload = {
        "model": settings.get("ollama_model") or "gemma3:4b",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 1200,
                    "num_gpu": int(settings.get("ollama_gpu", -1))},
    }
    timeout = float(settings.get("ollama_timeout", 75))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        return (data.get("response") or "").strip() or None
    except (httpx.HTTPError, ValueError):
        return None


async def _llm_openai_compatible(base_url: str, model: str, api_key: str,
                                 timeout: float, prompt: str) -> str | None:
    """Shared request/response shape for any OpenAI-compatible
    chat/completions endpoint — used by both llm_openai (NIM/generic) and
    llm_gemini (Google's own OpenAI-compat layer, confirmed live reachable
    at generativelanguage.googleapis.com/v1beta/openai/, a real documented
    endpoint, not a workaround). Kept as one function rather than two
    near-identical copies now that a second real caller exists."""
    base = api_endpoint(base_url, "chat/completions")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content":
                "You are a helpful classical-music metadata assistant. "
                "Reply ONLY with the requested JSON, no markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1200,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(base, json=payload, headers={
                "Authorization": f"Bearer {api_key}"})
            r.raise_for_status()
            data = r.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return content.strip() or None
    except (httpx.HTTPError, ValueError, IndexError):
        return None


async def llm_openai(settings: dict, prompt: str) -> str | None:
    return await _llm_openai_compatible(
        settings.get("api_base") or "https://api.openai.com/v1",
        settings.get("api_model") or "gpt-4o-mini",
        settings.get("api_key") or "",
        float(settings.get("api_timeout", 30)),
        prompt,
    )


_GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
_GEMINI_API_REVISION = "2026-05-20"


def _gemini_output_text(data: dict) -> str | None:
    """Extracts the model's reply from an Interactions API response.
    Confirmed live (2026-09-08): steps is a list mixing "thought" steps
    (reasoning tokens, no visible text — see usage.total_thought_tokens)
    and "model_output" steps (the actual reply, as content[].text) — skip
    the former, concatenate the latter. Google changed this response
    shape in a May 2026 breaking change (previously a flat "outputs"
    list); this reads the current shape only, gated by Api-Revision."""
    parts: list[str] = []
    for step in data.get("steps") or []:
        if step.get("type") != "model_output":
            continue
        for block in step.get("content") or []:
            if block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])
    return "".join(parts).strip() or None


async def llm_gemini(settings: dict, prompt: str) -> str | None:
    """Uses Google's Interactions API (v1beta/interactions), not the
    OpenAI-compatibility shim — confirmed live that the compat shim's own
    GET /models listing omitted gemini-3.8-flash even though the model
    works fine on this endpoint, which is what produced the "model not
    found on this endpoint" Test failure this replaces. See
    _gemini_output_text()'s docstring for the response shape. Default
    model is gemini-3.5-flash-lite, not the newer 3.8 — see settings.py's
    _DEFAULTS for why (a 25x-smaller daily quota on non-Lite models)."""
    api_key = settings.get("gemini_api_key")
    if not api_key:
        return None
    payload = {
        "model": settings.get("gemini_model") or "gemini-3.5-flash-lite",
        "input": prompt,
        # Confirmed live: "system_instruction" is the real field name on
        # this API (not "instructions", the OpenAI Responses API's name
        # for the same concept, wrongly copied from llm_codex() at
        # first) — a request with "instructions" gets a 400
        # "Unknown parameter" error.
        "system_instruction": "You are a helpful classical-music metadata assistant. "
                              "Reply ONLY with the requested JSON, no markdown.",
    }
    headers = {"x-goog-api-key": api_key, "Api-Revision": _GEMINI_API_REVISION}
    timeout = float(settings.get("gemini_timeout", 30))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(_GEMINI_INTERACTIONS_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    return _gemini_output_text(data)


_OPENROUTER_BASE = "https://openrouter.ai/api/v1"


async def llm_openrouter(settings: dict, prompt: str) -> str | None:
    """OpenRouter is genuinely OpenAI-compatible in the standard
    choices[0].message.content shape (confirmed live) — unlike Gemini,
    no dedicated request/response handling needed, just the existing
    shared helper. Default model "openrouter/free" is OpenRouter's own
    router that auto-picks among whichever models are currently free,
    rather than pinning to one specific free model ID that could be
    pulled from the free lineup later (a real, observed risk — see
    findings.md's notes on how often the free-model roster changes)."""
    if not settings.get("openrouter_api_key"):
        return None
    return await _llm_openai_compatible(
        _OPENROUTER_BASE,
        settings.get("openrouter_model") or "openrouter/free",
        settings["openrouter_api_key"],
        float(settings.get("openrouter_timeout", 30)),
        prompt,
    )


_MISTRAL_BASE = "https://api.mistral.ai/v1"


async def llm_mistral(settings: dict, prompt: str) -> str | None:
    """Mistral's La Plateforme "Experiment" free tier — genuinely
    OpenAI-compatible (confirmed live), so this just reuses the shared
    helper like OpenRouter. Default model "open-mistral-nemo": a live
    key check (2026-09-09) found "mistral-small-latest" gated to 0
    requests/minute on the free tier, while ministral-3b/8b and
    open-mistral-nemo all get real, generous quota (625K-1.3M
    tokens/min, 188-750 req/min) — Nemo (12B) is the largest model
    that's actually open on this tier. See textutil.py's
    apply_provider_rules() for the extra anti-hallucination prompt
    rules this provider also gets."""
    if not settings.get("mistral_api_key"):
        return None
    return await _llm_openai_compatible(
        _MISTRAL_BASE,
        settings.get("mistral_model") or "open-mistral-nemo",
        settings["mistral_api_key"],
        float(settings.get("mistral_timeout", 30)),
        prompt,
    )


async def llm_grok(settings: dict, prompt: str) -> str | None:
    """Two mutually-exclusive auth modes, chosen by settings["grok_mode"]
    (the radio toggle in the AI providers page's Grok bubble) — both call
    the exact same public, documented api.x.ai chat/completions endpoint,
    OpenAI-compatible request/response shape, differing only in how the
    Bearer token is obtained: a typed-in API key, or a subscription OAuth
    token from grok_oauth.py. Unlike llm_codex, there's no internal/
    undocumented backend API involved in either mode — see grok_oauth.py
    for the full reasoning on why that distinction matters here."""
    mode = settings.get("grok_mode") or "api_key"
    if mode == "subscription":
        token = await grok_oauth.ensure_fresh_token()
        if not token:
            return None
        base_url = "https://api.x.ai/v1"
        model = settings.get("grok_model") or "grok-4.3"
        timeout = float(settings.get("grok_timeout", 30))
    else:
        token = settings.get("grok_api_key") or ""
        if not token:
            return None
        base_url = settings.get("grok_api_base") or "https://api.x.ai/v1"
        model = settings.get("grok_model") or "grok-4.3"
        timeout = float(settings.get("grok_timeout", 30))
    url = api_endpoint(base_url, "chat/completions")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content":
                "You are a helpful classical-music metadata assistant. "
                "Reply ONLY with the requested JSON, no markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1200,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload,
                                  headers={"Authorization": f"Bearer {token}"})
            r.raise_for_status()
            data = r.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return content.strip() or None
    except (httpx.HTTPError, ValueError, IndexError):
        return None


_CODEX_API_URL = "https://chatgpt.com/backend-api/codex/responses"
_CODEX_MODEL = "gpt-5.6-terra"
# Observed live: 23-70s response times (vs. NIM/Ollama's usual 5-20s) —
# routed through OpenAI's own subscription-tier backend, not a direct
# model endpoint, so it's slower and more variable. Matches opencode's
# 180s ceiling rather than a tighter one, for the same "this mediates
# through something heavier than a plain API call" reason.
_CODEX_TIMEOUT = 180


def _codex_request_payload(prompt: str, account_id: str, token: str) -> tuple[dict, dict]:
    payload = {
        "model": _CODEX_MODEL,
        "instructions": "You are a helpful classical-music metadata assistant. "
                        "Reply ONLY with the requested JSON, no markdown.",
        "input": [{"role": "user", "content": prompt}],
        "stream": True,
        "store": False,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "originator": "codex_cli_rs",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id
    return payload, headers


async def llm_codex(settings: dict, prompt: str) -> str | None:
    """Calls OpenAI's internal Codex backend using a ChatGPT/Codex
    subscription's OAuth token instead of an API key — see codex_oauth.py
    for the important caveats about this being an unofficial mechanism."""
    token = await codex_oauth.ensure_fresh_token()
    if not token:
        return None
    cfg = codex_settings.load()
    payload, headers = _codex_request_payload(prompt, cfg.get("account_id", ""), token)
    text_parts: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=_CODEX_TIMEOUT) as client:
            async with client.stream("POST", _CODEX_API_URL, json=payload, headers=headers) as r:
                if r.status_code != 200:
                    return None
                event = ""
                async for line in r.aiter_lines():
                    if line.startswith("event:"):
                        event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        raw = line[len("data:"):].strip()
                        if raw == "[DONE]" or not raw:
                            continue
                        try:
                            data = json.loads(raw)
                        except ValueError:
                            continue
                        if event == "response.output_text.delta":
                            delta = data.get("delta")
                            if delta:
                                text_parts.append(delta)
    except httpx.HTTPError:
        return None
    text = "".join(text_parts).strip()
    return text or None


def _format_codex_error(status_code: int, body: bytes) -> str:
    """Turn Codex's structured error body into a real, specific message
    instead of the generic "did not respond" the Test button used to show
    for every failure alike. Confirmed live (2026-09-08): a plan's
    Codex-specific usage limit (x-codex-primary-used-percent header /
    error.type "usage_limit_reached" in the body) is a SEPARATE quota
    from the ChatGPT app/CLI's own token-usage graph — a user can see
    plenty of headroom there and still get a 429 here, because this hits
    a distinct Codex-API allowance on the subscription. resets_at is a
    Unix timestamp telling the user exactly when it clears."""
    try:
        data = json.loads(body)
        err = data.get("error") or {}
    except ValueError:
        err = {}
    err_type = err.get("type") or ""
    message = err.get("message") or ""
    if err_type == "usage_limit_reached":
        resets_at = err.get("resets_at")
        if isinstance(resets_at, (int, float)):
            reset_str = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(resets_at))
            return (f"Codex usage limit reached (separate from your ChatGPT app's own usage — "
                    f"resets {reset_str}).")
        return "Codex usage limit reached (separate from your ChatGPT app's own usage)."
    if status_code == 429:
        return f"Rate limited by ChatGPT/Codex ({message or 'too many requests'})."
    if status_code in (401, 403):
        return "ChatGPT/Codex rejected the connection — try Disconnect and Connect again."
    return f"ChatGPT/Codex returned an error ({status_code}{': ' + message if message else ''})."


async def _test_codex_call(prompt: str) -> tuple[bool, str]:
    """Makes the real request (unlike llm_codex, doesn't discard the
    error body on failure) so the Test button can show the actual reason
    instead of a generic failure — see _format_codex_error()."""
    token = await codex_oauth.ensure_fresh_token()
    if not token:
        return False, "Not connected — use the Connect button above."
    cfg = codex_settings.load()
    payload, headers = _codex_request_payload(prompt, cfg.get("account_id", ""), token)
    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            async with client.stream("POST", _CODEX_API_URL, json=payload, headers=headers) as r:
                if r.status_code != 200:
                    body = await r.aread()
                    return False, _format_codex_error(r.status_code, body)
                event = ""
                text_parts: list[str] = []
                async for line in r.aiter_lines():
                    if line.startswith("event:"):
                        event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        raw = line[len("data:"):].strip()
                        if raw == "[DONE]" or not raw:
                            continue
                        try:
                            data = json.loads(raw)
                        except ValueError:
                            continue
                        if event == "response.output_text.delta":
                            delta = data.get("delta")
                            if delta:
                                text_parts.append(delta)
    except httpx.HTTPError as exc:
        return False, f"Could not reach ChatGPT/Codex: {_exc_reason(exc)}"
    text = "".join(text_parts).strip()
    if not text:
        return False, "ChatGPT/Codex returned an empty response."
    plan = cfg.get("chatgpt_plan_type")
    return True, f"Connected ({plan})." if plan else "Connected."


class OpencodeSession:
    """Manages one lazily-spawned, shared `opencode serve` subprocess.
    Ported from mradio's _oc_health/_oc_start/_llm_opencode, minus the
    pidfile machinery that existed only because the original was a fresh
    CLI process every run with no persistent memory of its own — here the
    process (and this session) lives for the FastAPI app's lifetime, so an
    in-memory handle is enough. One shared instance for the whole app:
    opencode credentials/config are global, same as every other provider
    here, so there's exactly one to manage, not one per user."""

    def __init__(self):
        self._proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()

    async def _health(self, port: int, timeout: float = 2.0) -> bool:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(f"http://127.0.0.1:{port}/global/health")
                return r.json().get("healthy") is True
        except (httpx.HTTPError, ValueError):
            return False

    async def _ensure_started(self, port: int) -> bool:
        async with self._lock:
            if await self._health(port):
                return True
            if self._proc is None or self._proc.returncode is not None:
                try:
                    self._proc = await asyncio.create_subprocess_exec(
                        "opencode", "serve", "--port", str(port),
                        "--hostname", "127.0.0.1",
                        stdin=asyncio.subprocess.DEVNULL,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                except OSError:
                    return False
            for _ in range(20):
                if await self._health(port):
                    return True
                await asyncio.sleep(0.5)
            await self.kill()
            return False

    async def ask(self, settings: dict, prompt: str) -> str | None:
        port = oc_port(settings)
        if not port or not await self._ensure_started(port):
            return None
        timeout = float(settings.get("opencode_timeout", 180))
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(f"http://127.0.0.1:{port}/session",
                                      json={"title": "mradio-web"})
                sid = r.json().get("id")
                if not sid:
                    return None
                try:
                    r = await client.post(
                        f"http://127.0.0.1:{port}/session/{sid}/message",
                        json={"parts": [{"type": "text", "text": prompt}]})
                    data = r.json()
                    texts = " ".join(
                        p.get("text", "") for p in data.get("parts", [])
                        if p.get("type") == "text" and p.get("text"))
                    return texts.strip() or None
                finally:
                    try:
                        await client.delete(f"http://127.0.0.1:{port}/session/{sid}")
                    except httpx.HTTPError:
                        pass
        except (httpx.HTTPError, ValueError):
            return None

    async def kill(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            await asyncio.wait_for(self._proc.wait(), timeout=2)
        except (ProcessLookupError, asyncio.TimeoutError):
            try:
                self._proc.kill()
            except ProcessLookupError:
                pass
        self._proc = None


_TEST_TIMEOUT = 10.0


def _exc_reason(exc: Exception) -> str:
    """httpx's timeout/connection exceptions often stringify to '' (the
    class itself is the only signal) — fall back to its name so the pill
    never shows a message with nothing after the colon."""
    return str(exc) or type(exc).__name__


async def _test_ollama(settings: dict) -> tuple[bool, str]:
    url = settings.get("ollama_url")
    if not url:
        return False, "No server URL configured."
    model = settings.get("ollama_model") or "gemma3:4b"
    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            r = await client.get(api_endpoint(url, "api/tags"))
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        return False, f"Could not reach {url}: {_exc_reason(exc)}"
    names = {m.get("name") for m in data.get("models", [])}
    if model not in names and not any(n.startswith(model + ":") for n in names if n):
        return False, f'Server reachable, but model "{model}" is not pulled there.'
    return True, "Connected."


async def _test_openai_compatible(base_url: str, api_key: str, model: str,
                                  key_rejected_statuses: tuple[int, ...] = (401, 403)) -> tuple[bool, str]:
    """Shared GET /models probe for any OpenAI-compatible endpoint.
    key_rejected_statuses lets a caller widen which HTTP status counts as
    "bad key" beyond the standard 401/403 — confirmed live that Gemini's
    OpenAI-compat layer returns 400 INVALID_ARGUMENT for a bad key
    instead, per its own docs, not the 401 a typical OpenAI-shaped API
    uses."""
    if not api_key:
        return False, "No API key configured."
    models_url = api_endpoint(base_url, "models")
    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            r = await client.get(models_url, headers={"Authorization": f"Bearer {api_key}"})
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in key_rejected_statuses:
            return False, "Server rejected the API key."
        return False, f"Server responded with an error ({exc.response.status_code})."
    except httpx.HTTPError as exc:
        return False, f"Could not reach {models_url}: {_exc_reason(exc)}"
    except ValueError:
        # Some OpenAI-compatible servers don't implement /models at all —
        # a non-JSON 2xx response still proves the key/base URL work.
        return True, "Connected."
    ids = {m.get("id") for m in data.get("data", [])}
    if ids and model not in ids:
        return False, f'Connected, but model "{model}" was not found on this endpoint.'
    return True, "Connected."


async def _test_openai(settings: dict) -> tuple[bool, str]:
    return await _test_openai_compatible(
        settings.get("api_base") or "https://api.openai.com/v1",
        settings.get("api_key") or "",
        settings.get("api_model") or "gpt-4o-mini",
    )


def _gemini_error_message(status_code: int, body: bytes) -> str:
    """Extracts Google's own error message from an Interactions API
    error body — confirmed live (2026-09-08) the shape differs by
    status: a 404 (bad model) is a flat {"error": {"message": ...}},
    a 400 (bad key) is [{"error": {"message": ...}}] (wrapped in an
    array, unlike every other status seen)."""
    try:
        data = json.loads(body)
        if isinstance(data, list) and data:
            data = data[0]
        message = ((data.get("error") or {}).get("message") or "").strip()
    except (ValueError, AttributeError, IndexError):
        message = ""
    if message:
        return f"Gemini rejected the request: {message}"
    return f"Gemini returned an error ({status_code})."


async def _test_gemini(settings: dict) -> tuple[bool, str]:
    """Makes a real request against the Interactions API (the same one
    llm_gemini() uses) rather than probing GET /models — confirmed live
    that the OpenAI-compat shim's /models listing omitted gemini-3.8-flash
    even though the model works fine, which is exactly what produced the
    "model not found on this endpoint" false failure this replaces."""
    api_key = settings.get("gemini_api_key")
    if not api_key:
        return False, "No API key configured."
    payload = {
        "model": settings.get("gemini_model") or "gemini-3.5-flash-lite",
        "input": 'Reply with exactly: {"trivia": "pong"}',
    }
    headers = {"x-goog-api-key": api_key, "Api-Revision": _GEMINI_API_REVISION}
    try:
        # Unlike every other provider's Test button (a lightweight GET
        # /models probe), this makes a real generation call — Gemini's
        # "thinking" models can take noticeably longer than the shared
        # 10s _TEST_TIMEOUT (confirmed live: one test request burned
        # 364 reasoning tokens before replying), so this gets its own
        # longer budget rather than raising the shared constant for
        # every provider's test.
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(_GEMINI_INTERACTIONS_URL, json=payload, headers=headers)
            if r.status_code != 200:
                return False, _gemini_error_message(r.status_code, r.content)
            data = r.json()
    except httpx.HTTPError as exc:
        return False, f"Could not reach Gemini: {_exc_reason(exc)}"
    except ValueError:
        return False, "Gemini returned an unreadable response."
    text = _gemini_output_text(data)
    if not text:
        return False, "Gemini returned an empty response."
    return True, "Connected."


async def _test_openrouter(settings: dict) -> tuple[bool, str]:
    """Makes a real chat/completions call rather than probing GET
    /models — confirmed live that OpenRouter's /models listing is
    public and unauthenticated (returns 200 even with an invalid key),
    so it can't validate a key the way _test_openai_compatible() relies
    on for NIM/OpenAI. A bad key only surfaces as a 401 on the actual
    completions call."""
    api_key = settings.get("openrouter_api_key")
    if not api_key:
        return False, "No API key configured."
    model = settings.get("openrouter_model") or "openrouter/free"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": 'Reply with exactly: {"trivia": "pong"}'}],
        "temperature": 0.1,
        "max_tokens": 1200,
    }
    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            r = await client.post(
                api_endpoint(_OPENROUTER_BASE, "chat/completions"),
                json=payload, headers={"Authorization": f"Bearer {api_key}"})
            if r.status_code != 200:
                try:
                    message = (r.json().get("error") or {}).get("message") or ""
                except ValueError:
                    message = ""
                if r.status_code in (401, 403):
                    return False, "OpenRouter rejected the API key."
                return False, (f"OpenRouter returned an error ({r.status_code}"
                               f"{': ' + message if message else ''}).")
            data = r.json()
    except httpx.HTTPError as exc:
        return False, f"Could not reach OpenRouter: {_exc_reason(exc)}"
    except ValueError:
        return False, "OpenRouter returned an unreadable response."
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not content.strip():
        return False, "OpenRouter returned an empty response."
    return True, "Connected."


async def _test_mistral(settings: dict) -> tuple[bool, str]:
    """A real chat/completions call, not GET /models — Mistral's
    /models does validate the key (confirmed live: 401 on a bad key,
    unlike OpenRouter's public listing), but a valid key alone doesn't
    mean the configured MODEL is actually usable: a live check
    (2026-09-09) found "mistral-small-latest" returns a valid 200 from
    /models yet is rate-limited to 0 requests/minute on the free
    "Experiment" tier — only a real completion call surfaces that."""
    api_key = settings.get("mistral_api_key")
    if not api_key:
        return False, "No API key configured."
    model = settings.get("mistral_model") or "open-mistral-nemo"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": 'Reply with exactly: {"trivia": "pong"}'}],
        "temperature": 0.1,
        "max_tokens": 1200,
    }
    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            r = await client.post(
                api_endpoint(_MISTRAL_BASE, "chat/completions"),
                json=payload, headers={"Authorization": f"Bearer {api_key}"})
            if r.status_code != 200:
                try:
                    message = r.json().get("message") or ""
                except ValueError:
                    message = ""
                if r.status_code in (401, 403):
                    return False, "Mistral rejected the API key."
                if r.status_code == 429:
                    return False, (f'Mistral has this model rate-limited to 0 on '
                                   f'the free tier — try a smaller model (e.g. '
                                   f'"open-mistral-nemo").')
                return False, (f"Mistral returned an error ({r.status_code}"
                               f"{': ' + message if message else ''}).")
            data = r.json()
    except httpx.HTTPError as exc:
        return False, f"Could not reach Mistral: {_exc_reason(exc)}"
    except ValueError:
        return False, "Mistral returned an unreadable response."
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not content.strip():
        return False, "Mistral returned an empty response."
    return True, "Connected."


async def _test_opencode(settings: dict) -> tuple[bool, str]:
    from . import enricher  # local import: avoids a circular import at module load

    port = oc_port(settings)
    if not port:
        return False, "opencode is not enabled."
    reply = await enricher._opencode.ask(settings, "Reply with the single word: pong")
    if not reply:
        return False, "opencode did not respond."
    return True, "Connected."


async def _test_codex(settings: dict) -> tuple[bool, str]:
    return await _test_codex_call('Reply with exactly: {"trivia": "pong"}')


async def _test_grok(settings: dict) -> tuple[bool, str]:
    mode = settings.get("grok_mode") or "api_key"
    if mode == "subscription":
        if not grok_settings.load().get("access_token"):
            return False, "Not connected — use the Connect button above."
    elif not settings.get("grok_api_key"):
        return False, "No API key configured."
    reply = await llm_grok(settings, 'Reply with exactly: {"trivia": "pong"}')
    if not reply:
        return False, "Grok did not respond."
    return True, "Connected."


async def run_provider_test(provider: str, settings: dict) -> tuple[bool, str]:
    if provider == "ollama":
        return await _test_ollama(settings)
    if provider == "openai":
        return await _test_openai(settings)
    if provider == "opencode":
        return await _test_opencode(settings)
    if provider == "codex":
        return await _test_codex(settings)
    if provider == "grok":
        return await _test_grok(settings)
    if provider == "gemini":
        return await _test_gemini(settings)
    if provider == "openrouter":
        return await _test_openrouter(settings)
    if provider == "mistral":
        return await _test_mistral(settings)
    return False, "Unknown provider."
