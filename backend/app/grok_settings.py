"""Grok subscription tokens — admin-managed (Settings -> AI Providers
page), mirrors codex_settings.py's shape exactly. Populated by the OAuth
device-code flow in grok_oauth.py, not typed in by hand.

Unlike ChatGPT/Codex, this is a genuinely documented mechanism: xAI's
auth.x.ai exposes a real, discoverable OIDC/RFC 8628 device-code flow
(confirmed live via plain curl — no Cloudflare bot/TLS-fingerprint block,
unlike auth.openai.com), and the resulting token is used against
api.x.ai, the same public documented API the "API key" mode also calls —
not an internal/backend-api route like ChatGPT's. Still inherently
tied to whatever xAI decides an OAuth token is entitled to (community
reports note tier/entitlement mismatches even on an active subscription,
see grok_oauth.py) — treated with the same disclosure as ChatGPT/Codex
in KB.md, just with a materially lower technical-risk profile."""

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json

SETTINGS_FILE = DATA_DIR / "grok_settings.json"

_DEFAULTS = {
    "access_token": "",
    "refresh_token": "",
    "expires_at": 0,
}

_SECRET_FIELDS = {"access_token", "refresh_token"}


def load() -> dict:
    data = read_json(SETTINGS_FILE)
    merged = dict(_DEFAULTS)
    if isinstance(data, dict):
        merged.update(data)
    else:
        atomic_write_json(SETTINGS_FILE, merged)
    return merged


def save(**fields) -> dict:
    d = load()
    for k, v in fields.items():
        if k in _DEFAULTS and v is not None:
            d[k] = v
    atomic_write_json(SETTINGS_FILE, d)
    return d


def clear() -> dict:
    """Disconnect: reset every field back to its default."""
    atomic_write_json(SETTINGS_FILE, dict(_DEFAULTS))
    return dict(_DEFAULTS)


def redacted(d: dict) -> dict:
    out = dict(d)
    for field in _SECRET_FIELDS:
        v = out.get(field) or ""
        out[field] = (v[:4] + "…" + v[-4:]) if len(v) > 8 else ("…" if v else "")
    return out
