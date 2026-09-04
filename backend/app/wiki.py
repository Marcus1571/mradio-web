"""Wikipedia article resolution for a work title the Enricher returned.
Ported from mradio's Enricher._resolve_wiki/_relevant, made async via
httpx instead of urllib."""

import re

import httpx

_HEADERS = {"User-Agent": "mradio-web/1.0 (educational music enrichment)"}
_API = "https://en.wikipedia.org/w/api.php"


async def resolve(query: str, surname: str = "") -> dict | str:
    """Return {"title":..., "url":...} for the best-matching English
    Wikipedia article, or "" if nothing sufficiently relevant is found."""
    async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
        candidates = await _search(client, query)
        seen = set()
        for title, url in candidates:
            if url in seen:
                continue
            seen.add(url)
            if not await _relevant(client, title, query, surname):
                continue
            try:
                r = await client.head(url)
                if r.status_code == 200:
                    return {"title": url.rsplit("/", 1)[-1].replace("_", " "),
                            "url": url}
            except httpx.HTTPError:
                continue
    return ""


async def _search(client: httpx.AsyncClient, query: str) -> list[tuple[str, str]]:
    cand: list[tuple[str, str]] = []
    try:
        r = await client.get(_API, params={
            "action": "opensearch", "format": "json", "limit": 5, "search": query})
        res = r.json()
        if len(res) > 3:
            cand.extend((res[1][i], res[3][i])
                       for i in range(min(len(res[1]), len(res[3]))))
    except (httpx.HTTPError, ValueError, IndexError):
        pass
    if cand:
        return cand
    try:
        r = await client.get(_API, params={
            "action": "query", "list": "search", "format": "json",
            "srlimit": 5, "srsearch": query})
        hits = r.json().get("query", {}).get("search", [])
        for h in hits:
            t = h.get("title")
            if not t:
                continue
            ir = await client.get(_API, params={
                "action": "query", "prop": "info", "inprop": "url",
                "format": "json", "titles": t})
            pages = ir.json().get("query", {}).get("pages", {})
            for pg in pages.values():
                if pg.get("fullurl"):
                    cand.append((pg.get("title", t), pg["fullurl"]))
    except (httpx.HTTPError, ValueError):
        pass
    return cand


async def _relevant(client: httpx.AsyncClient, title: str, query: str, surname: str) -> bool:
    try:
        r = await client.get(_API, params={
            "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
            "exchars": 600, "format": "json", "redirects": 1, "titles": title})
        pages = r.json().get("query", {}).get("pages", {})
        intro = ""
        for pg in pages.values():
            if "missing" not in pg:
                intro = pg.get("extract") or ""
        intro = intro.lower()
    except (httpx.HTTPError, ValueError):
        return False

    def toks(s):
        return set(re.findall(r"[a-zà-ÿ]+", s.lower()))

    qt, tt = toks(query), toks(title)
    if not qt or not tt:
        return False
    overlap = bool(qt & tt)
    surname_hit = (bool(surname) and surname.lower() in intro) or not surname
    return overlap and surname_hit
