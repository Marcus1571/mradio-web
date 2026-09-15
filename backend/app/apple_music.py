"""Apple Music search-only track links via the free, keyless iTunes Search
API (itunes.apple.com/search) — not MusicKit, no Apple Developer Program
membership required. See findings.md's 2026-09-14 iTunes Search API entry
for the investigation this implements.

Read-only catalog lookup only, same shape as spotify.get_app_token()'s
Client Credentials search and deezer's unauthenticated search: no OAuth, no
per-user connection, no playlist. Reuses the same scoring approach as
spotify.py/deezer.py's find_best_track(), adapted for this API's field
names and its one real gap (no ISRC field to dedupe on)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import httpx

ITUNES_SEARCH = "https://itunes.apple.com/search"


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _token_set_ratio(a: str, b: str) -> float:
    a_tokens = set(_normalize(a).split())
    b_tokens = set(_normalize(b).split())
    if not a_tokens or not b_tokens:
        return 0.0
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return len(intersection) / len(union)


def _partial_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _title_score(query_title: str, candidate_title: str) -> float:
    return max(_partial_ratio(query_title, candidate_title), _token_set_ratio(query_title, candidate_title))


def _artist_match(query_artist: str, query_performer: str, track: dict[str, Any]) -> bool:
    name = _normalize(track.get("artistName") or "")
    q_artist = _normalize(query_artist)
    q_performer = _normalize(query_performer)
    if q_artist and q_artist in name:
        return True
    if q_performer and q_performer in name:
        return True
    return False


@dataclass(frozen=True)
class MatchResult:
    track_id: str
    url: str
    title: str
    artist: str
    score: float


def _dedupe_tracks(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # No ISRC field on this API (confirmed gap, findings.md) — trackId is
    # the next-best unique key.
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for t in tracks:
        key = str(t.get("trackId") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def _score_candidate(
    query_artist: str,
    query_title: str,
    query_performer: str,
    track: dict[str, Any],
) -> MatchResult | None:
    tid = track.get("trackId")
    url = track.get("trackViewUrl")
    if not tid or not url:
        return None
    candidate_title = track.get("trackName") or ""
    title_sim = _title_score(query_title, candidate_title)
    artist_ok = _artist_match(query_artist, query_performer, track)

    # Same conservative thresholds as spotify.py/deezer.py's scoring.
    if title_sim < 0.55:
        return None
    if not artist_ok and title_sim < 0.85:
        return None

    score = title_sim * 10.0 + (2.0 if artist_ok else 0.0)
    return MatchResult(
        track_id=str(tid),
        url=url,
        title=candidate_title,
        artist=track.get("artistName") or "",
        score=round(score, 3),
    )


async def search_tracks(query: str, limit: int = 10) -> list[dict[str, Any]]:
    params = {"term": query, "entity": "song", "limit": limit}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(ITUNES_SEARCH, params=params)
    if r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    return data.get("results", []) if isinstance(data, dict) else []


async def find_best_track(artist: str, title: str, performer: str) -> MatchResult | None:
    """Search the iTunes catalog and make a single executive-decision match."""
    queries: list[str] = []
    artist = artist or ""
    title = title or ""
    performer = performer or ""

    def add(q: str) -> None:
        q = q.strip()
        if q and q not in queries:
            queries.append(q)

    if artist and title:
        add(f"{artist} {title}")
    if performer and title:
        add(f"{title} {performer}")
    if title:
        add(title)
    if not queries:
        return None

    all_tracks: list[dict[str, Any]] = []
    for q in queries:
        all_tracks.extend(await search_tracks(q))

    candidates: list[MatchResult] = []
    for track in _dedupe_tracks(all_tracks):
        scored = _score_candidate(artist, title, performer, track)
        if scored:
            candidates.append(scored)

    if not candidates:
        return None
    candidates.sort(key=lambda c: c.score, reverse=True)
    best = candidates[0]
    if best.score < 7.0:
        return None
    return best


def _demo() -> None:
    track = {
        "trackId": 1425290697,
        "trackName": "Every Kinda People",
        "artistName": "Robert Palmer",
        "trackViewUrl": "https://music.apple.com/us/album/every-kinda-people/1425289735?i=1425290697",
    }
    best = _score_candidate("Robert Palmer", "Every Kinda People", "", track)
    assert best is not None and best.track_id == "1425290697", best
    assert _artist_match("Robert Palmer", "", track)
    assert not _artist_match("Someone Else", "", track)
    assert _score_candidate("Someone Else", "Totally Different Song", "", track) is None
    print("apple_music scoring self-checks ok")


if __name__ == "__main__":
    _demo()
