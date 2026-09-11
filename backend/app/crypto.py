"""Small encryption helpers for sensitive per-user OAuth tokens.

Refresh tokens are long-lived credentials that grant persistent access to a
user's third-party account. We encrypt them at rest with Fernet (symmetric
AES-128-CBC + HMAC) using a key from the MRADIO_SPOTIFY_TOKEN_KEY env var.
Access tokens expire quickly and are stored plaintext.

If no key is configured, encryption falls back to a no-op identity so local
dev/test still works — but production should always set the key."""

import os

from cryptography.fernet import Fernet, InvalidToken

_TOKEN_KEY = os.environ.get("MRADIO_SPOTIFY_TOKEN_KEY", "")

_fernet: Fernet | None = None


def _get_fernet() -> Fernet | None:
    global _fernet
    if _fernet is not None:
        return _fernet
    key = (_TOKEN_KEY or "").strip()
    if not key:
        return None
    try:
        _fernet = Fernet(key.encode())
    except Exception:
        return None
    return _fernet


def encrypt(value: str) -> str:
    """Encrypt a string, returning "fernet:<base64>". If no key is set,
    returns the original plaintext prefixed with "plain:"."""
    if not value:
        return ""
    f = _get_fernet()
    if f is None:
        return f"plain:{value}"
    return f"fernet:{f.encrypt(value.encode()).decode()}"


def decrypt(value: str) -> str:
    """Decrypt a value produced by encrypt(). Plaintext prefixes pass
    through. Returns "" on any failure so a bad key doesn't crash the app."""
    if not value:
        return ""
    if value.startswith("plain:"):
        return value[6:]
    if not value.startswith("fernet:"):
        return value
    f = _get_fernet()
    if f is None:
        return ""
    try:
        return f.decrypt(value[7:].encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        return ""


def is_configured() -> bool:
    """True if a valid encryption key is available."""
    return _get_fernet() is not None
