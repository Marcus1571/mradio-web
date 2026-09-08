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
    "api_model": "minimaxai/minimax-m3",
    "api_timeout": 30,
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
}

_SECRET_FIELDS = {"api_key", "grok_api_key", "gemini_api_key"}


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
