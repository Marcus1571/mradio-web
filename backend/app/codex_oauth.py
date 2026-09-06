"""OpenAI Codex CLI login — lets an admin sign in with their ChatGPT/Codex
subscription instead of typing an API key.

Login itself is delegated to the real `codex` CLI binary (bundled in the
Docker image, same pattern as opencode in providers.py's OpencodeSession):
confirmed live that `auth.openai.com/oauth/device/code` sits behind a
Cloudflare bot challenge that flatly rejects plain HTTP clients (curl,
httpx) with a 403 + `cf-mitigated: challenge` header — no header
combination fixes this, it's a TLS/JS fingerprint check. The real CLI
passes it because it's a genuine, trusted client. `codex login
--device-auth` prints a device code + verification URL to stdout, then
blocks until the browser flow completes and writes tokens to
`$CODEX_HOME/auth.json`.

Everything downstream of a valid token — refreshing it, and the actual
liner-notes API call in providers.py's llm_codex — was confirmed live to
work fine as plain httpx requests (no Cloudflare block on
auth.openai.com/oauth/token's refresh grant, nor on
chatgpt.com/backend-api/codex/responses with a valid Bearer token). Only
the device-code entry point needed the real-binary workaround.

Unofficial/unstable by nature regardless: the resulting token only works
against OpenAI's internal Codex backend, not the public documented API,
and OpenAI could change or block any part of this without notice. See
KB.md for the full disclosure — this is a deliberate, accepted
trade-off, not an oversight.

One pending device-flow session at a time, in memory only (mirrors
providers.py's in-memory _offline_until cooldown) — this app expects one
admin configuring settings at a time, not concurrent OAuth attempts."""

import asyncio
import base64
import json
import logging
import os
import re
import time

import httpx

from . import codex_settings
from .db import DATA_DIR

logger = logging.getLogger("mradio.codex_oauth")

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
TOKEN_URL = "https://auth.openai.com/oauth/token"
SCOPE = "openid profile email offline_access"

_TIMEOUT = 15.0
_HEADERS = {"User-Agent": "codex_cli_rs/0.1.0"}

CODEX_HOME = DATA_DIR / "codex_home"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_CODE_RE = re.compile(r"\b[A-Z0-9]{4}-[A-Z0-9]{4,6}\b")
_URL_RE = re.compile(r"https://\S+")

# The one in-flight device-flow attempt, if any.
_pending: dict | None = None
_login_task: asyncio.Task | None = None
_lock = asyncio.Lock()


def decode_jwt_claims(token: str) -> dict:
    """Base64url-decode a JWT's payload segment. No signature check — the
    token is only ever used as a bearer credential sent straight back to
    OpenAI's own servers, which do the real verification; we just need
    the exp/plan-type claims client-side."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload = parts[1]
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, TypeError, json.JSONDecodeError):
        return {}


def _extract_plan_type(claims: dict) -> str:
    auth = claims.get("https://api.openai.com/auth")
    if isinstance(auth, dict):
        return str(auth.get("chatgpt_plan_type") or "")
    return ""


def _read_cli_auth() -> dict | None:
    auth_file = CODEX_HOME / "auth.json"
    try:
        data = json.loads(auth_file.read_text())
    except (OSError, ValueError):
        return None
    tokens = data.get("tokens") or {}
    if not tokens.get("access_token"):
        return None
    return tokens


def _store_from_cli_auth(tokens: dict) -> None:
    claims = decode_jwt_claims(tokens.get("access_token", ""))
    codex_settings.save(
        access_token=tokens.get("access_token", ""),
        refresh_token=tokens.get("refresh_token", ""),
        # The CLI's auth.json doesn't carry an explicit expiry — decode it
        # from the access token's own exp claim instead.
        expires_at=int(claims.get("exp") or 0),
        account_id=tokens.get("account_id", ""),
        chatgpt_plan_type=_extract_plan_type(claims),
    )


async def _run_device_login() -> None:
    """Spawns `codex login --device-auth`, captures the device code/URL
    from its stdout as soon as they appear, and waits for it to finish.
    On success, reads the CLI's own auth.json into codex_settings."""
    global _pending
    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CODEX_HOME": str(CODEX_HOME)}
    try:
        proc = await asyncio.create_subprocess_exec(
            "codex", "login", "--device-auth",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
    except OSError as exc:
        logger.error("could not spawn codex login --device-auth: %s", exc)
        _pending = None
        return

    assert proc.stdout is not None
    buf = ""
    async for raw_line in proc.stdout:
        line = _ANSI_RE.sub("", raw_line.decode(errors="replace"))
        buf += line
        if _pending and _pending.get("user_code"):
            continue
        code_match = _CODE_RE.search(buf)
        url_match = _URL_RE.search(buf)
        if code_match and url_match and _pending is not None:
            _pending["user_code"] = code_match.group(0)
            _pending["verification_uri"] = url_match.group(0)

    await proc.wait()
    if proc.returncode == 0:
        tokens = _read_cli_auth()
        if tokens:
            _store_from_cli_auth(tokens)
            logger.info("codex login succeeded")
        else:
            logger.error("codex login exited 0 but auth.json had no usable token")
    else:
        logger.error("codex login --device-auth exited %s: %s", proc.returncode, buf[-2000:])
    _pending = None


async def start_device_flow() -> dict | None:
    """Kicks off the login subprocess and waits (briefly) for it to print
    the device code, then returns it — the actual sign-in completion
    keeps running in the background task."""
    global _pending, _login_task
    async with _lock:
        if _pending is not None:
            return None
        _pending = {"user_code": None, "verification_uri": None,
                    "started_at": time.time()}
        _login_task = asyncio.create_task(_run_device_login())

    for _ in range(40):
        await asyncio.sleep(0.5)
        if _pending is None:
            return None  # process exited early (error) before printing a code
        if _pending.get("user_code"):
            return dict(_pending)
    return None


def pending_status() -> dict | None:
    return dict(_pending) if _pending else None


async def refresh(refresh_token: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            r = await client.post(TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CLIENT_ID,
                "scope": SCOPE,
            })
            r.raise_for_status()
            tokens = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    claims = decode_jwt_claims(tokens.get("access_token", ""))
    codex_settings.save(
        access_token=tokens.get("access_token", ""),
        refresh_token=tokens.get("refresh_token") or refresh_token,
        expires_at=int(time.time()) + int(tokens.get("expires_in", 0) or 0),
        chatgpt_plan_type=_extract_plan_type(claims),
    )
    return codex_settings.load()


async def ensure_fresh_token() -> str | None:
    """Return a usable access token, refreshing first if it's expired or
    about to be. Returns None if not connected or refresh fails."""
    cfg = codex_settings.load()
    if not cfg["access_token"]:
        return None
    if time.time() < cfg["expires_at"] - 60:
        return cfg["access_token"]
    if not cfg["refresh_token"]:
        return None
    refreshed = await refresh(cfg["refresh_token"])
    return refreshed["access_token"] if refreshed else None
