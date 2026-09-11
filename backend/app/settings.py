"""Global AI provider settings — Ollama URL, NIM/OpenAI-compatible API key,
opencode toggle. One shared configuration, admin-managed (Settings ->
AI Providers page), not per-user: friends pick which of these is active
for them, but don't hold their own credentials.

Seeded from env vars on first run (same variable names mradio itself
used), then lives in settings.json and is edited via the admin API from
here on — env vars only matter before that file exists."""

import os

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json

SETTINGS_FILE = DATA_DIR / "settings.json"

_DEFAULTS = {
    "ollama_url": "",
    "ollama_model": "gemma3:4b",
    "ollama_timeout": 75,
    "ollama_gpu": -1,
    "api_base": "https://integrate.api.nvidia.com/v1",
    "api_key": "",
    # minimaxai/minimax-m3 (the old default) was retired by NVIDIA on
    # 2026-09-09 (confirmed live: a real call returns 410 Gone, "has
    # reached its end of life"). A live probe of all 80 models NVIDIA's
    # own /v1/models lists for a real account found only a handful
    # actually invokable — most return 404 "Function not found for
    # account", several of the rest are reasoning models that leak
    # chain-of-thought and burn the token budget before reaching real
    # JSON (same failure mode as OpenRouter's free auto-router), and
    # mistralai/mistral-nemotron — the previous replacement — had
    # become unreliable by 2026-09-11 (timeouts and HTTP 500s). Of the
    # models that actually responded, meta/llama-3.2-11b-vision-instruct
    # was the only one that was consistently available, returned valid
    # JSON within the 30s timeout, and completed the prompt end-to-end.
    # It is a vision-capable instruct model, but it accepts text prompts
    # normally. Accuracy on niche facts is mediocre and is expected to
    # improve once Wikipedia grounding is injected. If this model is ever
    # retired, re-probe NVIDIA's actual account-enabled model list rather
    # than trusting the public /v1/models catalog — most of it 404s.
    "api_model": "meta/llama-3.2-11b-vision-instruct",
    "api_timeout": 45,
    "opencode": "",
    "opencode_timeout": 180,
    # "api_key" (metered, per-token) or "subscription" (OAuth against a
    # SuperGrok/X Premium+ account, see grok_oauth.py) — the two are
    # mutually exclusive; grok_settings.json holds the OAuth token
    # itself, mirroring codex_settings.json's separate file.
    "grok_mode": "api_key",
    "grok_api_base": "https://api.x.ai/v1",
    "grok_api_key": "",
    "grok_model": "grok-4.3",
    "grok_timeout": 30,
    # Manual kill switches for the player dropdown, independent of
    # whether credentials/OAuth are configured — lets an admin hide a
    # subscription provider the moment it hits its usage quota, without
    # disconnecting/losing the saved token, and flip it back on once the
    # quota resets. Default True: existing installs keep today's
    # behavior (visible whenever configured) until an admin touches it.
    "codex_manually_enabled": True,
    "grok_manually_enabled": True,
    # Google Gemini via its Interactions API (v1beta/interactions, see
    # providers.py's llm_gemini) — genuinely free tier (Flash-family
    # models), not admin-only (unlike ChatGPT/Grok) since it isn't tied
    # to anyone's personal paid subscription. No api_base field: unlike
    # Ollama/NIM, this endpoint isn't user-swappable, so there's nothing
    # meaningful to configure there.
    "gemini_api_key": "",
    # gemini-3.5-flash-lite, not gemini-3.8-flash: confirmed live via the
    # user's own AI Studio rate-limit dashboard that every non-Lite Flash
    # model on the free tier (2.5/3/3.5/3.6/3.7/3.8) shares the same
    # 20-requests-PER-DAY cap (resets at midnight Pacific, not rolling) —
    # trivially exhausted by more than one or two liner-notes requests.
    # The Lite variants (3.1/3.5 flash-lite) get 500 RPD instead, 25x the
    # headroom, same free tier, same account.
    "gemini_model": "gemini-3.5-flash-lite",
    # 45s, not the 30s other providers default to — confirmed live that
    # Gemini's "thinking" models' reasoning tokens can push a simple
    # reply's latency well past 30s, and a request that times out here
    # just silently falls through llm_gemini()'s except clause to the
    # next provider in the fallback chain (or fails outright if Gemini
    # is the only one configured) rather than erroring loudly.
    "gemini_timeout": 45,
    # Manual kill switch for Gemini's player-dropdown visibility — same
    # mechanism as codex/grok's (see provider_enabled()'s docstring),
    # despite Gemini not being admin-only: its free-tier daily quota can
    # still be hit, and this lets an admin hide it without losing the
    # saved key.
    "gemini_manually_enabled": True,
    # OpenRouter — free tier (its own :free-suffixed models, confirmed
    # live cost: 0), no credit card needed to sign up, but admin-only
    # (2026-09-08, changed from the original non-admin-only build) —
    # unlike Gemini's free tier, OpenRouter's is a single SHARED daily
    # quota (50 requests/day, confirmed live) across every account using
    # the one saved key, not a per-user allowance; with several accounts
    # able to pick it, that shared quota could be exhausted by midday.
    # See providers.py's ADMIN_ONLY_PROVIDERS for the full reasoning.
    # Default model is "openrouter/free", OpenRouter's own router that
    # auto-picks among whichever models are currently free rather than
    # pinning to one model ID — see providers.py's llm_openrouter() for
    # why that matters (the free-model roster changes over time; Groq
    # and Cerebras were both struck from findings.md's candidate list
    # for reasons unrelated to this, but OpenRouter's own free lineup is
    # explicitly documented as rotating). Free tier: 50 requests/day (no
    # spend), 1,000/day once $10 has ever been spent on the account
    # (doesn't expire).
    "openrouter_api_key": "",
    "openrouter_model": "openrouter/free",
    # 90s, not 30s — a live provider-comparison battery (2026-09-09)
    # found the free lineup's actually-working models are reasoning
    # models with real variance in how long they take: as fast as ~3s
    # with the categorical hardening applied (see textutil.py's
    # _CATEGORICAL_PROVIDERS), but the auto-router ("openrouter/free")
    # was observed taking 84s on one run even with that same hardening
    # — a shorter timeout would have thrown away a correct, complete
    # answer and fallen through to the next provider unnecessarily. See
    # providers.py's llm_openrouter() for the matching max_tokens bump
    # — reasoning tokens count against the same budget as content.
    "openrouter_timeout": 90,
    "openrouter_manually_enabled": True,
    # Mistral AI's La Plateforme "Experiment" free tier (2026-09-09) —
    # genuinely free, no card needed (phone verification only), not
    # admin-only (same reasoning as Gemini: not tied to anyone's
    # personal paid subscription). Default model "open-mistral-nemo",
    # not "mistral-small-latest": a live key check found Small gated to
    # 0 requests/minute on this tier, while Nemo (12B) and the Ministral
    # 3B/8B family get real quota (625K-1.3M tokens/min). A live
    # spot-check also found real fabrication on niche classical-music
    # facts at this model size, so it gets the same SINCERITY_RULES
    # hardening as the NIM provider — see textutil.py.
    "mistral_api_key": "",
    "mistral_model": "open-mistral-nemo",
    "mistral_timeout": 30,
    "mistral_manually_enabled": True,
}

_SECRET_FIELDS = {"api_key", "grok_api_key", "gemini_api_key", "openrouter_api_key",
                  "mistral_api_key"}


def _seed_from_env() -> dict:
    return {
        "ollama_url": os.environ.get("MRADIO_OLLAMA", _DEFAULTS["ollama_url"]),
        "ollama_model": os.environ.get("MRADIO_OLLAMA_MODEL", _DEFAULTS["ollama_model"]),
        "ollama_timeout": int(os.environ.get("MRADIO_OLLAMA_TIMEOUT",
                                             _DEFAULTS["ollama_timeout"])),
        "ollama_gpu": int(os.environ.get("MRADIO_OLLAMA_NUM_GPU", _DEFAULTS["ollama_gpu"])),
        "api_base": os.environ.get("MRADIO_API_BASE", _DEFAULTS["api_base"]),
        "api_key": os.environ.get("MRADIO_API_KEY", _DEFAULTS["api_key"]),
        "api_model": os.environ.get("MRADIO_MODEL", _DEFAULTS["api_model"]),
        "api_timeout": int(os.environ.get("MRADIO_API_TIMEOUT", _DEFAULTS["api_timeout"])),
        "opencode": os.environ.get("MRADIO_OPENCODE", _DEFAULTS["opencode"]),
        "opencode_timeout": int(os.environ.get("MRADIO_OPENCODE_TIMEOUT",
                                               _DEFAULTS["opencode_timeout"])),
    }


def load() -> dict:
    data = read_json(SETTINGS_FILE)
    if isinstance(data, dict):
        merged = dict(_DEFAULTS)
        merged.update(data)
        return merged
    seeded = _seed_from_env()
    atomic_write_json(SETTINGS_FILE, seeded)
    return seeded


def save(**fields) -> dict:
    d = load()
    for k, v in fields.items():
        if k in _DEFAULTS and v is not None:
            d[k] = v
    atomic_write_json(SETTINGS_FILE, d)
    return d


def redacted(d: dict) -> dict:
    """For display: mask secrets the same way mradio's --settings did
    (first 4 / last 4 chars only)."""
    out = dict(d)
    for field in _SECRET_FIELDS:
        v = out.get(field) or ""
        out[field] = (v[:4] + "…" + v[-4:]) if len(v) > 8 else ("…" if v else "")
    return out
