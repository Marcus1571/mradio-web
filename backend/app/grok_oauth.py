"""xAI Grok subscription login — lets an admin sign in with their
SuperGrok or X Premium+ subscription instead of typing an API key.

Unlike codex_oauth.py, this needs no bundled CLI binary. Confirmed live
before writing this module (2026-09-07): auth.x.ai's OIDC discovery
document, its device-code endpoint (POST /oauth2/device/code), and its
token endpoint are all reachable with a plain `curl`/httpx client — real
200 responses, no Cloudflare bot/TLS-fingerprint challenge of the kind
that blocked auth.openai.com and forced the Codex CLI workaround. This
is a genuine, standard RFC 8628 device-authorization-grant flow, not an
undocumented internal one.

Endpoint values below (issuer, device-code URL, client_id, scope) are
lifted from a real, working open-source implementation
(piex-dev/piex's extensions/xai-oauth, itself ported from
NousResearch/hermes-agent) rather than guessed or reverse-engineered —
client_id b1a00492-073a-47ea-816f-4c329264a828 is that same public
client identifier, not a secret tied to any one account (same reasoning
as codex_oauth.py's hardcoded CLIENT_ID).

Once a token is obtained, it's used as a Bearer credential against
api.x.ai — the same public, documented API base the "API key" mode also
calls (see providers.py's llm_grok) — not an internal backend-api route
like ChatGPT's chatgpt.com/backend-api/codex/responses. Still an
unofficial-for-third-parties mechanism in the sense that xAI's own
terms govern what an OAuth token is entitled to do, and community
projects note occasional tier/entitlement mismatches even on an active
subscription — disclosed in KB.md alongside ChatGPT/Codex's own caveat,
just with a materially lower technical-risk profile since there's no
bot-detection workaround involved at all.

One pending device-flow attempt at a time, in memory only (mirrors
codex_oauth.py's _pending) — this app expects one admin configuring
settings at a time, not concurrent OAuth attempts."""

import time

import httpx

from . import grok_settings

ISSUER = "https://auth.x.ai"
DISCOVERY_URL = f"{ISSUER}/.well-known/openid-configuration"
DEVICE_CODE_URL = f"{ISSUER}/oauth2/device/code"
# Fallback token URL if discovery fails for some reason — matches the
# discovery document's own advertised token_endpoint, confirmed live.
_FALLBACK_TOKEN_URL = f"{ISSUER}/oauth2/token"
CLIENT_ID = "b1a00492-073a-47ea-816f-4c329264a828"
SCOPE = "openid profile email offline_access grok-cli:access api:access"

_TIMEOUT = 15.0
_MIN_POLL_INTERVAL = 1.0

# The one in-flight device-flow attempt, if any: device_code (needed to
# poll), user_code/verification_uri (shown to the admin), and the poll
# interval/deadline xAI told us to respect.
_pending: dict | None = None


async def _discover_token_endpoint() -> str:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(DISCOVERY_URL, headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
        endpoint = data.get("token_endpoint")
        if isinstance(endpoint, str) and endpoint.startswith("https://"):
            return endpoint
    except (httpx.HTTPError, ValueError):
        pass
    return _FALLBACK_TOKEN_URL


async def start_device_flow() -> dict | None:
    """Requests a device code from xAI and returns it immediately for
    display — unlike codex_oauth.py's subprocess-based flow, there's no
    CLI stdout to wait on, so this returns as soon as the HTTP response
    arrives. The caller is responsible for polling via poll_once()
    (see routers/grok.py's status endpoint, which the frontend's
    useGrokStatus hook already polls on an interval)."""
    global _pending
    if _pending is not None:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                DEVICE_CODE_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json"},
                data={"client_id": CLIENT_ID, "scope": SCOPE},
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    device_code = data.get("device_code")
    user_code = data.get("user_code")
    verification_uri = data.get("verification_uri_complete") or data.get("verification_uri")
    expires_in = data.get("expires_in")
    interval = data.get("interval")
    if not (device_code and user_code and verification_uri
            and isinstance(expires_in, (int, float)) and isinstance(interval, (int, float))):
        return None
    _pending = {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": verification_uri,
        "deadline": time.time() + expires_in,
        "interval": max(_MIN_POLL_INTERVAL, float(interval)),
        "next_poll_at": 0.0,
    }
    return {"user_code": user_code, "verification_uri": verification_uri}


def pending_status() -> dict | None:
    if _pending is None:
        return None
    return {"user_code": _pending["user_code"], "verification_uri": _pending["verification_uri"]}


async def poll_once() -> bool:
    """Polls the token endpoint once, respecting the interval xAI asked
    for. Called by routers/grok.py's status endpoint (itself polled by
    the frontend every few seconds while a login is pending) rather than
    driving its own background loop — keeps this module's concurrency
    model as simple as codex_oauth.py's, just event-driven from the HTTP
    layer instead of a spawned asyncio.Task. Returns True once connected
    (clears _pending), False while still pending or on a hard failure
    (also clears _pending on a hard failure, so a dead flow doesn't
    block a fresh attempt forever)."""
    global _pending
    if _pending is None:
        return False
    now = time.time()
    if now >= _pending["deadline"]:
        _pending = None
        return False
    if now < _pending["next_poll_at"]:
        return False
    token_url = await _discover_token_endpoint()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json"},
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": CLIENT_ID,
                    "device_code": _pending["device_code"],
                },
            )
            data = r.json()
    except (httpx.HTTPError, ValueError):
        _pending["next_poll_at"] = now + _pending["interval"]
        return False

    if r.status_code == 200 and data.get("access_token"):
        grok_settings.save(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expires_at=int(time.time()) + int(data.get("expires_in", 0) or 0),
        )
        _pending = None
        return True

    error = data.get("error") if isinstance(data, dict) else None
    if error == "slow_down":
        _pending["interval"] += 5.0
    elif error != "authorization_pending":
        # Any other error (access_denied, expired_token, invalid_grant,
        # etc.) means this attempt is dead — clear it so the admin can
        # retry with a fresh Connect click instead of silently polling
        # a flow that can never succeed.
        _pending = None
        return False
    _pending["next_poll_at"] = now + _pending["interval"]
    return False


async def refresh(refresh_token: str) -> dict | None:
    token_url = await _discover_token_endpoint()
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json"},
                data={
                    "grant_type": "refresh_token",
                    "client_id": CLIENT_ID,
                    "refresh_token": refresh_token,
                },
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    access_token = data.get("access_token")
    if not access_token:
        return None
    grok_settings.save(
        access_token=access_token,
        refresh_token=data.get("refresh_token") or refresh_token,
        expires_at=int(time.time()) + int(data.get("expires_in", 0) or 0),
    )
    return grok_settings.load()


async def ensure_fresh_token() -> str | None:
    """Return a usable access token, refreshing first if it's expired or
    about to be. Returns None if not connected or refresh fails — mirrors
    codex_oauth.py's ensure_fresh_token() exactly."""
    cfg = grok_settings.load()
    if not cfg["access_token"]:
        return None
    if time.time() < cfg["expires_at"] - 60:
        return cfg["access_token"]
    if not cfg["refresh_token"]:
        return None
    refreshed = await refresh(cfg["refresh_token"])
    return refreshed["access_token"] if refreshed else None
