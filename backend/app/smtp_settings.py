"""SMTP settings for the self-service "forgot password" email flow —
admin-managed (Settings -> Email page), mirrors settings.py's shape.
No env-var seeding: unlike the AI providers, there's no prior
mradio-terminal SMTP config to carry forward."""

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json

SETTINGS_FILE = DATA_DIR / "smtp_settings.json"

_DEFAULTS = {
    "host": "",
    "port": 587,
    "username": "",
    "password": "",
    "from_address": "",
    "use_tls": True,
    # Optional override for the reset-link's base URL. Left blank, the
    # link is built from the request's own Host/X-Forwarded-Host header
    # instead — correct automatically no matter which domain a listener
    # used to reach the app, without per-domain configuration.
    "public_url": "",
}

_SECRET_FIELDS = {"password"}


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


def redacted(d: dict) -> dict:
    out = dict(d)
    for field in _SECRET_FIELDS:
        v = out.get(field) or ""
        out[field] = (v[:4] + "…" + v[-4:]) if len(v) > 8 else ("…" if v else "")
    return out
