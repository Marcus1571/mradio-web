"""Station logo lookup via Radio-Browser (api.radio-browser.info), a
free, open, community-maintained internet radio directory. Best-effort
enrichment, same posture as wiki.py's Wikipedia lookup — every failure
mode degrades to None, never raises.

Lookup order: exact stream-URL match first (most reliable when it hits —
confirmed live that Radio-Browser indexes this app's curated stations by
their actual stream URL, even third-party CDN ones), then a fallback name
search (needed because not every curated station's exact URL is indexed,
e.g. WQXR's)."""

import httpx

_API_BASE = "https://de1.api.radio-browser.info/json"
_HEADERS = {"User-Agent": "mradio-web/1.0 (station logo lookup)"}
_TIMEOUT = 5


async def _first_working_favicon(client: httpx.AsyncClient, results: list[dict]) -> str | None:
    for r in results:
        favicon = r.get("favicon")
        if not favicon:
            continue
        # Radio-Browser is community-maintained and can hold stale
        # favicon URLs (confirmed live: a station's own site had
        # reorganized its paths since being indexed) — a HEAD check
        # before caching stops a permanently-broken image from being
        # served on every future play, same verification wiki.py already
        # does for article URLs before returning one.
        try:
            head = await client.head(favicon, follow_redirects=True)
            if head.status_code == 200:
                return favicon
        except httpx.HTTPError:
            continue
    return None


async def find_logo(stream_url: str, station_name: str) -> str | None:
    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
        try:
            r = await client.get(f"{_API_BASE}/stations/byurl", params={"url": stream_url})
            if r.status_code == 200:
                logo = await _first_working_favicon(client, r.json())
                if logo:
                    return logo
        except (httpx.HTTPError, ValueError):
            pass

        try:
            r = await client.get(
                f"{_API_BASE}/stations/search",
                params={"name": station_name, "limit": 5},
            )
            if r.status_code == 200:
                return await _first_working_favicon(client, r.json())
        except (httpx.HTTPError, ValueError):
            pass

    return None
