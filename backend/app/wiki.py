"""Wikipedia article resolution for a work title the Enricher returned.
Ported from mradio's Enricher._resolve_wiki/_relevant, made async via
httpx instead of urllib."""

import asyncio
import re
import time

import httpx

_HEADERS = {"User-Agent": "mradio-web/1.0 (educational music enrichment)"}
_API = "https://en.wikipedia.org/w/api.php"

# In-memory cache for resolved + extracted articles. Production often asks
# about the same track repeatedly (fallback chain, retries, multiple users
# listening to the same radio program), and Wikipedia's API will throttle
# rapid repeated calls. Cache hits avoid that entirely.
_CACHE: dict[str, tuple[float, dict | None]] = {}
_CACHE_LOCK = asyncio.Lock()
_CACHE_TTL = 3600  # seconds
_CACHE_MAX_SIZE = 200

# Throttle calls to Wikipedia's Action API. A shared semaphore plus a
# minimum interval keeps us well under rate limits even when the fallback
# chain or the battery fires several lookups in quick succession.
_API_SEMAPHORE = asyncio.Semaphore(1)
_MIN_INTERVAL = 0.5  # seconds between API calls
_LAST_CALL_AT = 0.0
_LAST_CALL_LOCK = asyncio.Lock()

# Coalesce concurrent ground() calls for the same key so a burst of
# enrichment requests for one track (fallback chain, multiple users,
# multiple workers are still separate) does not each fire its own
# Wikipedia lookup.
_IN_FLIGHT: dict[str, asyncio.Task] = {}
_IN_FLIGHT_LOCK = asyncio.Lock()


async def _api_get(client: httpx.AsyncClient, params: dict) -> httpx.Response:
    """Make a throttled GET to the Wikipedia Action API.

    Retries transient 5xx and 429 responses with backoff, and raises on
    hard 4xx/5xx so callers can distinguish real failures from empty
    result sets."""
    global _LAST_CALL_AT
    for attempt in range(3):
        async with _API_SEMAPHORE:
            async with _LAST_CALL_LOCK:
                now = time.monotonic()
                elapsed = now - _LAST_CALL_AT
                if elapsed < _MIN_INTERVAL:
                    await asyncio.sleep(_MIN_INTERVAL - elapsed)
                _LAST_CALL_AT = time.monotonic()
            try:
                r = await client.get(_API, params=params)
                r.raise_for_status()
                return r
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429 or status >= 500:
                    if attempt == 2:
                        raise
                    # Backoff before retrying: 2s, then 4s.
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                raise


async def resolve(query: str, surname: str = "") -> dict | str:
    """Return {"title":..., "url":...} for the best-matching English
    Wikipedia article, or "" if nothing sufficiently relevant is found."""
    async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
        candidates = await _search(client, query)
        seen = set()
        for title, url, extract in candidates[:3]:
            if url in seen:
                continue
            seen.add(url)
            if not _relevant_extract(extract, title, query, surname):
                continue
            try:
                r = await client.head(url)
                if r.status_code == 200:
                    return {"title": url.rsplit("/", 1)[-1].replace("_", " "),
                            "url": url}
            except httpx.HTTPError:
                continue
    return ""


async def _extract_multi(client: httpx.AsyncClient, titles: list[str]) -> dict[str, str]:
    """Fetch extracts for several titles in one API call."""
    if not titles:
        return {}
    try:
        r = await _api_get(client, {
            "action": "query", "prop": "extracts", "exintro": 1,
            "explaintext": 1, "exchars": 600, "format": "json",
            "redirects": 1, "titles": "|".join(titles)})
        pages = r.json().get("query", {}).get("pages", {})
        out: dict[str, str] = {}
        for pg in pages.values():
            if "missing" not in pg:
                out[pg.get("title", "")] = (pg.get("extract") or "").strip()
        return out
    except (httpx.HTTPError, ValueError):
        return {}


async def _search(client: httpx.AsyncClient, query: str) -> list[tuple[str, str, str]]:
    """Search English Wikipedia for candidate articles.

    Returns a list of (title, url, extract). Opensearch is tried first
    because it is the most predictable for exact title matches (e.g.
    "Symphony No. 9 in D minor, Op. 125"). Falls back to the combined
    generator search and then the legacy list=search."""

    # Primary: opensearch, then fetch extracts in one batched call.
    try:
        r = await _api_get(client, {
            "action": "opensearch", "format": "json", "limit": 5, "search": query})
        res = r.json()
        if len(res) > 3 and res[1]:
            # Only process the top 3 results; beyond that the signal is
            # usually noise.
            limit = min(3, len(res[1]), len(res[3]))
            titles_urls = [(res[1][i], res[3][i]) for i in range(limit)]
            titles = [t for t, _ in titles_urls]
            extracts = await _extract_multi(client, titles)
            return [(t, u, extracts.get(t, "")) for t, u in titles_urls]
    except (httpx.HTTPError, ValueError, IndexError):
        pass

    # Fallback 1: combined generator search (search + extracts + URLs).
    try:
        r = await _api_get(client, {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": 5,
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "exchars": 600,
            "inprop": "url",
            "format": "json",
            "redirects": 1,
        })
        pages = r.json().get("query", {}).get("pages", {})
        cand = []
        for pg in pages.values():
            title = pg.get("title")
            url = pg.get("fullurl")
            extract = (pg.get("extract") or "").strip()
            if title and url and "missing" not in pg:
                cand.append((title, url, extract))
        if cand:
            return cand
    except (httpx.HTTPError, ValueError):
        pass

    # Fallback 2: legacy list=search + prop=info + extracts.
    try:
        r = await _api_get(client, {
            "action": "query", "list": "search", "format": "json",
            "srlimit": 5, "srsearch": query})
        hits = r.json().get("query", {}).get("search", [])
        cand = []
        for h in hits:
            t = h.get("title")
            if not t:
                continue
            ir = await _api_get(client, {
                "action": "query", "prop": "info|extracts",
                "exintro": 1, "explaintext": 1, "exchars": 600,
                "inprop": "url", "format": "json", "titles": t})
            pages = ir.json().get("query", {}).get("pages", {})
            for pg in pages.values():
                if pg.get("fullurl"):
                    cand.append((
                        pg.get("title", t),
                        pg["fullurl"],
                        (pg.get("extract") or "").strip(),
                    ))
        return cand
    except (httpx.HTTPError, ValueError):
        pass
    return []


def _relevant_extract(extract: str, title: str, query: str, surname: str) -> bool:
    """Return True if the article extract looks relevant to the query.
    This is a pure function so callers that already have the extract can
    avoid an extra API round-trip."""
    if not extract:
        return False
    intro_lower = extract.lower()

    def toks(s):
        return set(re.findall(r"[a-zà-ÿ]+", s.lower()))

    qt, tt = toks(query), toks(title)
    if not qt or not tt:
        return False
    overlap = bool(qt & tt)
    surname_hit = (bool(surname) and surname.lower() in intro_lower) or not surname
    if not overlap or not surname_hit:
        return False

    # In strict mode (a surname is provided), require that the article
    # shares at least one non-surname query token with the *title*. This
    # prevents e.g. "Maria Muldaur Empty Bed Blues" from matching the
    # "Diana Muldaur" article just because the surname appears.
    if surname:
        surname_toks = toks(surname)
        non_surname_qt = qt - surname_toks
        if non_surname_qt and not (non_surname_qt & tt):
            return False
    return True


async def _relevant(client: httpx.AsyncClient, title: str, query: str, surname: str) -> tuple[bool, str]:
    """Backwards-compatible helper: return (is_relevant, extract)."""
    extract = await _extract(client, title)
    return _relevant_extract(extract, title, query, surname), extract


async def _extract(client: httpx.AsyncClient, title: str) -> str:
    try:
        r = await _api_get(client, {
            "action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
            "exchars": 600, "format": "json", "redirects": 1, "titles": title})
        pages = r.json().get("query", {}).get("pages", {})
        for pg in pages.values():
            if "missing" not in pg:
                return (pg.get("extract") or "").strip()
    except (httpx.HTTPError, ValueError):
        pass
    return ""


async def ground(artist: str, title: str, surname: str = "") -> dict | None:
    """Return the best-matching English Wikipedia article as
    {"title": str, "url": str, "extract": str}, or None if nothing
    sufficiently relevant is found. The extract is the article's intro
    (up to ~600 chars), suitable for injecting into an LLM prompt.

    The lookup tries several query strategies because Wikipedia often has
    an article for the work title but not for a specific artist's version
    (e.g. "Empty Bed Blues" exists, "Maria Muldaur Empty Bed Blues" does
    not). A strict artist+title search is tried first; if it fails the
    title alone is tried with relaxed relevance.

    Results are cached in memory for one hour; this protects both
    Wikipedia's API and our own latency when the same work is enriched
    more than once. Calls are throttled to avoid tripping Wikipedia's
    rate limits."""
    artist = (artist or "").strip()
    title = (title or "").strip()
    cache_key = f"{artist.lower()}|{title.lower()}|{surname.lower()}"
    async with _CACHE_LOCK:
        now = time.monotonic()
        cached = _CACHE.get(cache_key)
        if cached is not None:
            expires, value = cached
            if expires > now:
                return value
            del _CACHE[cache_key]

    async with _IN_FLIGHT_LOCK:
        existing = _IN_FLIGHT.get(cache_key)
        if existing is not None:
            return await existing
        task = asyncio.create_task(_ground_with_retry(artist, title, surname))
        _IN_FLIGHT[cache_key] = task

    try:
        result = await task
    finally:
        async with _IN_FLIGHT_LOCK:
            _IN_FLIGHT.pop(cache_key, None)

    async with _CACHE_LOCK:
        now = time.monotonic()
        # Don't poison the cache with hard misses caused by transient
        # Wikipedia errors; use a short TTL for None so the next caller
        # can retry without hammering the API.
        ttl = _CACHE_TTL if result is not None else 60
        _CACHE[cache_key] = (now + ttl, result)
        while len(_CACHE) > _CACHE_MAX_SIZE:
            _CACHE.pop(next(iter(_CACHE)))
    return result


async def _ground_with_retry(artist: str, title: str, surname: str) -> dict | None:
    """Actual uncached Wikipedia lookup with light retry/backoff.
    Wikipedia is generally reliable but will throttle or 5xx under load;
    a short retry loop is cheaper than failing an enrichment entirely.
    Because calls are already throttled, retries use modest extra waits."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _ground_uncached(artist, title, surname)
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            if attempt == 2:
                return None
            await asyncio.sleep(1.0 * (attempt + 1))
    return None


async def _ground_uncached(artist: str, title: str, surname: str) -> dict | None:
    # Build query variants by strategy tier. Title-only search is the most
    # reliable path: Wikipedia's search handles long artist+title queries
    # poorly, often returning a related but wrong article (e.g. "So What"
    # for "Miles Davis Kind of Blue"). Artist-only is a last resort.
    stripped = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()

    title_variants = []
    if title:
        title_variants.append((title, title, ""))
    if stripped and stripped.lower() != title.lower():
        title_variants.append((stripped, stripped, ""))

    tiers = []
    if title_variants:
        tiers.append(("title", title_variants))
    if artist:
        tiers.append(("artist", [(artist, artist, surname)]))

    async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
        for tier_name, queries in tiers:
            tier_best: tuple[int, str, str, str] | None = None
            seen_in_tier = set()
            for q, work_title, q_surname in queries:
                candidates = await _search(client, q)
                for cand_title, url, extract in candidates:
                    if url in seen_in_tier:
                        continue
                    seen_in_tier.add(url)
                    if not _relevant_extract(extract, cand_title, q, q_surname):
                        continue
                    score = _match_score(cand_title, work_title, extract, artist)
                    if tier_best is None or score > tier_best[0]:
                        tier_best = (score, cand_title, url, extract)
            if tier_best is not None:
                _, cand_title, url, extract = tier_best
                return {
                    "title": cand_title.replace("_", " "),
                    "url": url,
                    "extract": extract,
                }
    return None


def _match_score(title: str, work_title: str, extract: str, artist: str = "") -> int:
    """Higher score = closer match to the work title.

    Exact matches and title-prefix matches are preferred, but a strong
    music-specific candidate (e.g. "Chan Chan (song)") can beat a generic
    exact match (e.g. the city "Chan Chan"). Disambiguation pages are
    penalized so the specific article wins."""
    t = title.lower()
    wt = work_title.lower()
    extract_lower = extract.lower()

    if t == wt:
        # Exact title match should almost always win; without this the
        # music-marker bonus lets disambiguated variants like
        # "Kind of Blue (TQ album)" beat the canonical article.
        score = 1000
    elif t.startswith(wt):
        score = 50 - len(t)
    else:
        wt_toks = set(re.findall(r"[a-zà-ÿ]+", wt))
        t_toks = set(re.findall(r"[a-zà-ÿ]+", t))
        shared = wt_toks & t_toks
        score = len(shared) * 10 - len(t) // 10

    # Boost music-specific articles so "Chan Chan (song)" beats "Chan Chan"
    # (the city) and "Symphony No. 9 (Beethoven)" beats "Ludwig van Beethoven".
    music_markers = {"song", "album", "single", "symphony", "composition",
                     "opera", "concerto", "sonata", "recording", "track"}
    t_toks = set(re.findall(r"[a-zà-ÿ]+", t))
    if music_markers & t_toks:
        score += 200

    # Boost if the artist name appears in the candidate title.
    if artist:
        art_toks = set(re.findall(r"[a-zà-ÿ]+", artist.lower()))
        if art_toks & t_toks:
            score += 50

    # Penalize disambiguation pages; their extract starts with "X may refer
    # to:" and we want the actual article.
    if "may refer to" in extract_lower:
        score -= 300

    return score
