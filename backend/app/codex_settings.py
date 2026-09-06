"""ChatGPT/Codex subscription tokens — admin-managed (Settings -> AI
Providers page), mirrors settings.py/smtp_settings.py's shape. Populated
by the OAuth device-code flow in codex_oauth.py, not typed in by hand.

Unofficial mechanism: this authenticates the same way `codex login` does
in a terminal, and the resulting token only works against OpenAI's
internal Codex backend (chatgpt.com/backend-api/codex/responses), not the
public documented API. OpenAI could change or block this without notice
(Anthropic did the equivalent for Claude in early 2026) — see KB.md for
the full disclosure. No env-var seeding: there's nothing to carry
forward, and secrets here always come from a live OAuth grant."""

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json

SETTINGS_FILE = DATA_DIR / "codex_settings.json"

_DEFAULTS = {
    "access_token": "",
    "refresh_token": "",
    "expires_at": 0,
    "account_id": "",
    "chatgpt_plan_type": "",
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
