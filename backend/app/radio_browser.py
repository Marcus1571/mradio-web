"""Station logo lookup via Radio-Browser (api.radio-browser.info), a
free, open, community-maintained internet radio directory. Best-effort
enrichment, same posture as wiki.py's Wikipedia lookup — every failure
mode degrades to None, never raises.

Lookup order: exact stream-URL match first (most reliable when it hits —
confirmed live that Radio-Browser indexes this app's curated stations by
their actual stream URL, even third-party CDN ones), then a fallback name
search (needed because not every curated station's exact URL is indexed,
e.g. WQXR's).

The name search is an exact-ish match on Radio-Browser's side (not
fuzzy — confirmed live "VCR Auditorium" alone matches nothing even
though "VCR | Venice Classic Radio Auditorium" is a real indexed
entry), so this app's own curated display names — which often carry a
" | subtitle" or a trailing "(region)" qualifier for the user's benefit
— regularly miss real entries a human would call an obvious match. A
failed search retries with the name progressively simplified (strip
" | ...", strip a trailing "(...)", the text *after* a " | " on its
own, then just the first word) before giving up.

The " | subtitle" half often carries the actual broadcaster's real
name, distinct from the disambiguating prefix that only exists to tell
this app's own sibling stations apart — e.g. "VCR Auditorium" vs. "VCR
Classica+" are both "| Venice Classic Radio Italia" underneath.
Confirmed live: searching the literal suffix "Venice Classic Radio
Italia" still matches nothing (Radio-Browser doesn't index the
trailing "Italia" as part of the name), but "Venice Classic Radio" —
one word shorter — finds the real station with a live, working logo.
So this tier also retries with its own last word dropped if the full
suffix search comes up empty.

The last tier (bare first word, e.g. "181.FM" out of "181.FM Kickin'
Country") is genuinely ambiguous when that word is a short all-letter
acronym — confirmed live that searching "VCR" alone surfaces two
unrelated stations sharing that same 3-letter token ahead of the real
Venice Classic Radio match, both with their own live, working
favicons, so a naive "first working favicon" rule would confidently
attach the wrong logo (this exact case is now caught earlier by the
pipe-suffix tier above before it would ever reach this one, but the
guard stays — a future curated station without a " | subtitle" could
still hit it). So this tier only fires for a first word that's longer
than 4 characters or contains a digit (numeric station brands like
"181.FM", ".977", "1.FM" are distinctive almost by definition; bare
call-sign-shaped acronyms like "VCR", "WQXR", "KIX" are not) — and
even then, the candidate's own indexed name must still share a real
word with the original curated name, as a cheap extra check against
coincidental collisions. A station that fails all of this ends up with
no logo rather than risk a wrong one."""

import re

import httpx

_API_BASE = "https://de1.api.radio-browser.info/json"
_HEADERS = {"User-Agent": "mradio-web/1.0 (station logo lookup)"}
_TIMEOUT = 5

_PIPE_SUFFIX_RE = re.compile(r"\s*\|.*$")
_TRAILING_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")
_WORD_RE = re.compile(r"[a-z0-9]{3,}")


def _name_variants(name: str) -> list[tuple[str, bool]]:
    """Progressively simpler forms of a curated display name, most
    specific first, deduplicated, for retrying a failed exact search.
    Each entry is (query, loose) — loose marks a term short/generic
    enough that matches need an extra sanity check (see find_logo)."""
    variants: list[tuple[str, bool]] = [(name, False)]
    seen = {name}
    stripped_pipe = _PIPE_SUFFIX_RE.sub("", name).strip()
    if stripped_pipe and stripped_pipe not in seen:
        variants.append((stripped_pipe, False))
        seen.add(stripped_pipe)
    for base, _ in list(variants):
        stripped_paren = _TRAILING_PAREN_RE.sub("", base).strip()
        if stripped_paren and stripped_paren not in seen:
            variants.append((stripped_paren, False))
            seen.add(stripped_paren)
    if "|" in name:
        pipe_suffix = name.split("|", 1)[1].strip()
        if pipe_suffix and pipe_suffix not in seen:
            variants.append((pipe_suffix, False))
            seen.add(pipe_suffix)
        suffix_words = pipe_suffix.split()
        if len(suffix_words) > 1:
            shortened_suffix = " ".join(suffix_words[:-1])
            if shortened_suffix not in seen:
                variants.append((shortened_suffix, False))
                seen.add(shortened_suffix)
    last_base = variants[-1][0]
    first_word = last_base.split()[0] if last_base.split() else ""
    # Bare short all-letter first words are usually a station's call
    # sign or a generic acronym (WQXR, KIX, VCR, BBC...) — confirmed
    # live these collide with unrelated stations that happen to share
    # the same 3-letter token (searching "VCR" alone surfaces an
    # unrelated Congolese station and an unrelated "VCR - 90.6 FM
    # Stereo" ahead of the real Venice Classic Radio match). A longer
    # word, or one containing a digit (station brands like "181.FM",
    # ".977", "1.FM" are numeric almost by definition), is distinctive
    # enough to be worth trying.
    if (len(first_word) > 4 or any(c.isdigit() for c in first_word)) and first_word not in seen:
        variants.append((first_word, True))
    return variants


def _distinguishing_words(name: str) -> set[str]:
    """Real words (3+ alnum chars) from a curated display name, for
    sanity-checking a loose/ambiguous search result against it."""
    return set(_WORD_RE.findall(name.lower()))


async def _first_working_favicon(
    client: httpx.AsyncClient, results: list[dict], require_words: set[str] | None = None,
) -> str | None:
    for r in results:
        favicon = r.get("favicon")
        if not favicon:
            continue
        if require_words and not (_distinguishing_words(r.get("name", "")) & require_words):
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

        distinguishing_words = _distinguishing_words(station_name)
        for name, loose in _name_variants(station_name):
            try:
                r = await client.get(
                    f"{_API_BASE}/stations/search",
                    params={"name": name, "limit": 5},
                )
                if r.status_code == 200:
                    require_words = distinguishing_words if loose else None
                    logo = await _first_working_favicon(client, r.json(), require_words)
                    if logo:
                        return logo
            except (httpx.HTTPError, ValueError):
                continue

    return None
