"""Async LLM provider calls for AI liner-note enrichment, ported from
mradio's Enricher._llm_ollama/_llm_openai/_llm_opencode. Credentials are
global (settings.py, admin-managed) — every user picks from the same set
of configured providers, none of them hold their own keys."""

import asyncio
import shutil
import time
import urllib.parse

import httpx

PROVIDERS = ("opencode", "openai", "ollama")

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


def provider_enabled(name: str, settings: dict) -> bool:
    probe = {
        "opencode": bool(oc_port(settings)),
        "ollama": bool(settings.get("ollama_url")),
        "openai": bool(settings.get("api_key")),
    }
    return probe.get(name, False)


def ai_configured(settings: dict) -> bool:
    return bool(settings.get("ollama_url")) or bool(settings.get("api_key")) \
        or bool(oc_port(settings))


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


async def llm_openai(settings: dict, prompt: str) -> str | None:
    base = api_endpoint(settings.get("api_base") or "https://api.openai.com/v1",
                        "chat/completions")
    payload = {
        "model": settings.get("api_model") or "gpt-4o-mini",
        "messages": [
            {"role": "system", "content":
                "You are a helpful classical-music metadata assistant. "
                "Reply ONLY with the requested JSON, no markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1200,
    }
    timeout = float(settings.get("api_timeout", 30))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(base, json=payload, headers={
                "Authorization": "Bearer " + (settings.get("api_key") or "")})
            r.raise_for_status()
            data = r.json()
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        return content.strip() or None
    except (httpx.HTTPError, ValueError, IndexError):
        return None


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
