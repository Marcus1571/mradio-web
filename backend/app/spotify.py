"""Spotify per-user playlist integration.

OAuth Authorization Code flow (no PKCE — server stores the refresh token
securely and exchanges the code itself). Each user gets their own encrypted
refresh token and a private "mradio-web" playlist. The playlist contents are
mirrored locally so the player can show a filled star without hitting Spotify
on every UI tick.

Client credentials live in settings.json (admin UI). The redirect URI and the
encryption key are env vars (MRADIO_SPOTIFY_REDIRECT_URI and
MRADIO_SPOTIFY_TOKEN_KEY) because they are infrastructure-level and must not
be editable from the UI."""

from __future__ import annotations

import base64
import os
import re
import secrets
import string
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

import httpx

from . import settings as settings_store
from .crypto import decrypt, encrypt
from .db import get_db
from .textutil import split_title

# Spotify endpoints
SPOTIFY_ACCOUNTS = "https://accounts.spotify.com"
SPOTIFY_API = "https://api.spotify.com/v1"

REQUIRED_SCOPES = " ".join(
    [
        "playlist-modify-private",
        "playlist-modify-public",
        "user-read-private",
    ]
)

_PLAYLIST_NAME = "mradio-web"
_PLAYLIST_DESCRIPTION = "Tracks I liked on mradio-web"


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def _redirect_uri() -> str | None:
    uri = (os.environ.get("MRADIO_SPOTIFY_REDIRECT_URI") or "").strip()
    return uri or None


def _client_creds() -> tuple[str, str] | None:
    s = settings_store.load()
    cid = (s.get("spotify_client_id") or "").strip()
    secret = (s.get("spotify_client_secret") or "").strip()
    if not cid or not secret:
        return None
    return cid, secret


def is_admin_configured() -> bool:
    return _client_creds() is not None and _redirect_uri() is not None


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------


def generate_state() -> str:
    return secrets.token_urlsafe(32)


def authorization_url(state: str) -> str | None:
    creds = _client_creds()
    redirect = _redirect_uri()
    if not creds or not redirect:
        return None
    cid, _ = creds
    params = {
        "client_id": cid,
        "response_type": "code",
        "redirect_uri": redirect,
        "scope": REQUIRED_SCOPES,
        "state": state,
    }
    return f"{SPOTIFY_ACCOUNTS}/authorize?{urllib.parse.urlencode(params)}"


async def _token_request(data: dict[str, str]) -> dict[str, Any] | None:
    creds = _client_creds()
    redirect = _redirect_uri()
    if not creds or not redirect:
        return None
    cid, secret = creds
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{SPOTIFY_ACCOUNTS}/api/token",
            data=data,
            headers={"Authorization": f"Basic {auth}"},
        )
    if r.status_code != 200:
        return None
    return r.json()


async def exchange_code(code: str) -> dict[str, Any] | None:
    redirect = _redirect_uri()
    if not redirect:
        return None
    return await _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
        }
    )


async def refresh_access_token(refresh_token: str) -> dict[str, Any] | None:
    return await _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------


_SPOTIFY_COLS = "access_token, refresh_token, expires_at, market, playlist_id, created_at, updated_at"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at(expires_in: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()


def _is_expired(expires_at: str, margin_seconds: int = 120) -> bool:
    try:
        dt = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) + timedelta(seconds=margin_seconds) >= dt
    except Exception:
        return True


# ---------------------------------------------------------------------------
# OAuth state helpers
# ---------------------------------------------------------------------------


STATE_TTL = timedelta(minutes=10)


async def create_oauth_state(user_id: int) -> str:
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db = get_db()
    await db.execute(
        "INSERT INTO spotify_oauth_states (state, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (state, user_id, now.isoformat(), (now + STATE_TTL).isoformat()),
    )
    await db.commit()
    return state


async def consume_oauth_state(state: str) -> int | None:
    db = get_db()
    cur = await db.execute(
        "SELECT user_id FROM spotify_oauth_states WHERE state = ? AND expires_at > ?",
        (state, datetime.now(timezone.utc).isoformat()),
    )
    row = await cur.fetchone()
    if not row:
        return None
    await db.execute("DELETE FROM spotify_oauth_states WHERE state = ?", (state,))
    await db.commit()
    return row["user_id"]


async def delete_expired_oauth_states() -> None:
    db = get_db()
    await db.execute(
        "DELETE FROM spotify_oauth_states WHERE expires_at <= ?",
        (datetime.now(timezone.utc).isoformat(),),
    )
    await db.commit()


async def load_token_row(user_id: int) -> dict[str, Any] | None:
    db = get_db()
    cur = await db.execute(
        "SELECT * FROM spotify_tokens WHERE user_id = ?", (user_id,)
    )
    row = await cur.fetchone()
    return dict(row) if row else None


async def save_tokens(
    user_id: int,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    market: str = "",
    playlist_id: str = "",
) -> None:
    db = get_db()
    now = _now_iso()
    await db.execute(
        f"""
        INSERT INTO spotify_tokens (user_id, {_SPOTIFY_COLS})
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            expires_at=excluded.expires_at,
            market=excluded.market,
            playlist_id=excluded.playlist_id,
            updated_at=excluded.updated_at
        """,
        (
            user_id,
            access_token,
            encrypt(refresh_token),
            _expires_at(expires_in),
            market,
            playlist_id,
            now,
            now,
        ),
    )
    await db.commit()


async def ensure_access_token(user_id: int) -> str | None:
    """Return a valid access token, refreshing if necessary."""
    row = await load_token_row(user_id)
    if not row:
        return None
    access_token = row["access_token"]
    if not _is_expired(row["expires_at"]):
        return access_token
    refresh = decrypt(row["refresh_token"])
    if not refresh:
        return None
    refreshed = await refresh_access_token(refresh)
    if not refreshed:
        return None
    new_access = refreshed["access_token"]
    new_refresh = refreshed.get("refresh_token") or refresh
    expires_in = refreshed.get("expires_in", 3600)
    await save_tokens(
        user_id,
        new_access,
        new_refresh,
        expires_in,
        market=row.get("market") or "",
        playlist_id=row.get("playlist_id") or "",
    )
    return new_access


async def disconnect_user(user_id: int) -> None:
    db = get_db()
    await db.execute("DELETE FROM spotify_tokens WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM spotify_playlist_tracks WHERE user_id = ?", (user_id,))
    await db.commit()


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------


async def _api(
    access_token: str,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=30) as client:
        return await client.request(
            method,
            f"{SPOTIFY_API}{path}",
            params=params,
            json=json_body,
            headers={"Authorization": f"Bearer {access_token}"},
        )


async def get_profile(access_token: str) -> dict[str, Any] | None:
    r = await _api(access_token, "GET", "/me")
    if r.status_code != 200:
        return None
    return r.json()


async def create_playlist(access_token: str, user_spotify_id: str) -> str | None:
    body = {
        "name": _PLAYLIST_NAME,
        "public": False,
        "description": _PLAYLIST_DESCRIPTION,
    }
    r = await _api(access_token, "POST", f"/users/{user_spotify_id}/playlists", json_body=body)
    if r.status_code not in (200, 201):
        return None
    data = r.json()
    return data.get("id")


async def add_tracks_to_playlist(
    access_token: str, playlist_id: str, uris: list[str]
) -> bool:
    if not uris:
        return True
    r = await _api(
        access_token,
        "POST",
        f"/playlists/{playlist_id}/tracks",
        json_body={"uris": uris},
    )
    return r.status_code in (200, 201)


async def remove_track_from_playlist(
    access_token: str, playlist_id: str, uri: str
) -> bool:
    r = await _api(
        access_token,
        "DELETE",
        f"/playlists/{playlist_id}/tracks",
        json_body={"tracks": [{"uri": uri}]},
    )
    return r.status_code == 200


async def fetch_playlist_tracks(
    access_token: str, playlist_id: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    limit = 100
    offset = 0
    while True:
        r = await _api(
            access_token,
            "GET",
            f"/playlists/{playlist_id}/tracks",
            params={"limit": limit, "offset": offset, "fields": "items(track(id,uri,isrc))"},
        )
        if r.status_code != 200:
            break
        data = r.json()
        items = data.get("items") or []
        out.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return out


async def search_tracks(
    access_token: str, query: str, market: str, limit: int = 20
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"q": query, "type": "track", "limit": limit}
    if market:
        params["market"] = market
    r = await _api(access_token, "GET", "/search", params=params)
    if r.status_code != 200:
        return []
    return r.json().get("tracks", {}).get("items", [])


# ---------------------------------------------------------------------------
# Playlist mirror
# ---------------------------------------------------------------------------


async def sync_mirror(user_id: int, access_token: str, playlist_id: str) -> None:
    items = await fetch_playlist_tracks(access_token, playlist_id)
    db = get_db()
    await db.execute("DELETE FROM spotify_playlist_tracks WHERE user_id = ?", (user_id,))
    rows = []
    for item in items:
        track = item.get("track") or {}
        tid = track.get("id")
        if not tid:
            continue
        rows.append(
            (
                user_id,
                tid,
                (track.get("isrc") or "").upper(),
                _now_iso(),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO spotify_playlist_tracks (user_id, spotify_track_id, isrc, added_at) VALUES (?, ?, ?, ?)",
            rows,
        )
    await db.commit()


async def add_to_mirror(user_id: int, track_id: str, isrc: str) -> None:
    db = get_db()
    await db.execute(
        """
        INSERT INTO spotify_playlist_tracks (user_id, spotify_track_id, isrc, added_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, spotify_track_id) DO NOTHING
        """,
        (user_id, track_id, (isrc or "").upper(), _now_iso()),
    )
    await db.commit()


async def remove_from_mirror(user_id: int, track_id: str) -> None:
    db = get_db()
    await db.execute(
        "DELETE FROM spotify_playlist_tracks WHERE user_id = ? AND spotify_track_id = ?",
        (user_id, track_id),
    )
    await db.commit()


async def is_in_mirror(user_id: int, track_id: str, isrc: str) -> bool:
    if not track_id and not isrc:
        return False
    db = get_db()
    if track_id:
        cur = await db.execute(
            "SELECT 1 FROM spotify_playlist_tracks WHERE user_id = ? AND spotify_track_id = ?",
            (user_id, track_id),
        )
        if await cur.fetchone():
            return True
    if isrc:
        cur = await db.execute(
            "SELECT 1 FROM spotify_playlist_tracks WHERE user_id = ? AND isrc = ?",
            (user_id, isrc.upper()),
        )
        if await cur.fetchone():
            return True
    return False


# ---------------------------------------------------------------------------
# Executive-decision track matching
# ---------------------------------------------------------------------------


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


_ALBUM_TYPE_RANK = {"album": 3, "single": 2, "compilation": 1}


def _album_type_score(album_type: str) -> int:
    return _ALBUM_TYPE_RANK.get((album_type or "").lower(), 0)


def _artist_names(track: dict[str, Any]) -> list[str]:
    return [a.get("name", "") for a in track.get("artists", []) if a.get("name")]


def _artist_match(query_artist: str, query_performer: str, track: dict[str, Any]) -> bool:
    names = " ".join(_artist_names(track)).lower()
    q_artist = _normalize(query_artist)
    q_performer = _normalize(query_performer)
    if q_artist and q_artist in names:
        return True
    if q_performer and q_performer in names:
        return True
    return False


@dataclass(frozen=True)
class MatchResult:
    track_id: str
    uri: str
    isrc: str
    title: str
    artists: list[str]
    album_type: str
    popularity: int
    score: float


def _dedupe_tracks(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for t in tracks:
        key = (t.get("isrc") or t.get("id") or "").upper()
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
    tid = track.get("id")
    uri = track.get("uri")
    if not tid or not uri:
        return None
    candidate_title = track.get("name") or ""
    title_sim = _title_score(query_title, candidate_title)
    artist_ok = _artist_match(query_artist, query_performer, track)
    album_type = (track.get("album") or {}).get("album_type", "")
    album_score = _album_type_score(album_type)
    popularity = track.get("popularity") or 0

    # Require at least moderate title similarity; if the artist doesn't match,
    # demand higher title similarity (covers the rare case where the title is
    # very distinctive and the artist field is unreliable).
    if title_sim < 0.55:
        return None
    if not artist_ok and title_sim < 0.85:
        return None

    score = (
        title_sim * 10.0
        + (2.0 if artist_ok else 0.0)
        + album_score * 0.5
        + min(popularity, 100) / 100.0
    )
    return MatchResult(
        track_id=tid,
        uri=uri,
        isrc=(track.get("isrc") or "").upper(),
        title=candidate_title,
        artists=_artist_names(track),
        album_type=album_type,
        popularity=popularity,
        score=round(score, 3),
    )


async def find_best_track(
    access_token: str,
    market: str,
    artist: str,
    title: str,
    performer: str,
) -> MatchResult | None:
    """Search Spotify and make a single executive-decision match.

    Builds queries from the clean metadata, deduplicates by ISRC, scores, and
    returns the best candidate only if it clears a conservative threshold.
    """
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
        all_tracks.extend(await search_tracks(access_token, q, market))

    candidates: list[MatchResult] = []
    for track in _dedupe_tracks(all_tracks):
        scored = _score_candidate(artist, title, performer, track)
        if scored:
            candidates.append(scored)

    if not candidates:
        return None
    candidates.sort(key=lambda c: c.score, reverse=True)
    best = candidates[0]
    # Conservative acceptance threshold: title must be close and artist/performer
    # must be present, OR title is an extremely strong match.
    if best.score < 7.0:
        return None
    return best


# ---------------------------------------------------------------------------
# High-level user operations
# ---------------------------------------------------------------------------


async def user_status(user_id: int) -> dict[str, Any]:
    if not is_admin_configured():
        return {"configured": False, "connected": False}
    row = await load_token_row(user_id)
    if not row:
        return {"configured": True, "connected": False}
    return {
        "configured": True,
        "connected": True,
        "playlist_id": row.get("playlist_id") or "",
        "market": row.get("market") or "",
    }


async def connect_user(user_id: int, code: str) -> bool:
    token_resp = await exchange_code(code)
    if not token_resp:
        return False
    access = token_resp["access_token"]
    refresh = token_resp["refresh_token"]
    expires_in = token_resp.get("expires_in", 3600)

    profile = await get_profile(access)
    if not profile:
        return False
    market = (profile.get("country") or "").upper()
    spotify_user_id = profile.get("id")

    playlist_id = ""
    # Try to reuse existing playlist id from a prior connect first.
    row = await load_token_row(user_id)
    if row and row.get("playlist_id"):
        playlist_id = row["playlist_id"]
    if not playlist_id and spotify_user_id:
        playlist_id = await create_playlist(access, spotify_user_id)

    await save_tokens(
        user_id,
        access,
        refresh,
        expires_in,
        market=market,
        playlist_id=playlist_id or "",
    )

    if playlist_id:
        await sync_mirror(user_id, access, playlist_id)
    return True


async def toggle_track(
    user_id: int,
    raw_title: str,
    add: bool,
) -> dict[str, Any]:
    """Add or remove the currently-playing track from the user's playlist.

    Returns {"ok": bool, "in_playlist": bool, "track_id": str|None,
    "message": str|None}.
    """
    access = await ensure_access_token(user_id)
    if not access:
        return {"ok": False, "in_playlist": False, "track_id": None, "message": "not connected"}

    row = await load_token_row(user_id)
    playlist_id = row.get("playlist_id") if row else ""
    if not playlist_id:
        return {"ok": False, "in_playlist": False, "track_id": None, "message": "no playlist"}

    artist, title, performer = split_title(raw_title)
    market = (row.get("market") or "").upper()

    match = await find_best_track(access, market, artist, title, performer)
    if not match:
        return {"ok": False, "in_playlist": False, "track_id": None, "message": "not found on Spotify"}

    in_mirror = await is_in_mirror(user_id, match.track_id, match.isrc)

    if add:
        if in_mirror:
            return {"ok": True, "in_playlist": True, "track_id": match.track_id, "message": None}
        ok = await add_tracks_to_playlist(access, playlist_id, [match.uri])
        if ok:
            await add_to_mirror(user_id, match.track_id, match.isrc)
            return {"ok": True, "in_playlist": True, "track_id": match.track_id, "message": None}
        return {"ok": False, "in_playlist": False, "track_id": match.track_id, "message": "failed to add"}

    # remove
    if not in_mirror:
        return {"ok": True, "in_playlist": False, "track_id": match.track_id, "message": None}
    ok = await remove_track_from_playlist(access, playlist_id, match.uri)
    if ok:
        await remove_from_mirror(user_id, match.track_id)
        return {"ok": True, "in_playlist": False, "track_id": match.track_id, "message": None}
    return {"ok": False, "in_playlist": True, "track_id": match.track_id, "message": "failed to remove"}


async def membership(
    user_id: int,
    raw_title: str,
) -> dict[str, Any]:
    """Check whether the currently-playing track is already in the playlist.

    Returns {"in_playlist": bool, "track_id": str|None}.
    """
    access = await ensure_access_token(user_id)
    if not access:
        return {"in_playlist": False, "track_id": None}

    row = await load_token_row(user_id)
    playlist_id = row.get("playlist_id") if row else ""
    if not playlist_id:
        return {"in_playlist": False, "track_id": None}

    artist, title, performer = split_title(raw_title)
    market = (row.get("market") or "").upper()
    match = await find_best_track(access, market, artist, title, performer)
    if not match:
        return {"in_playlist": False, "track_id": None}

    in_mirror = await is_in_mirror(user_id, match.track_id, match.isrc)
    return {"in_playlist": in_mirror, "track_id": match.track_id}


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------


def _demo() -> None:
    # Pure scoring sanity checks, no network.
    def make_track(name: str, artists: list[str], album_type: str, isrc: str, popularity: int = 50) -> dict[str, Any]:
        return {
            "id": secrets.token_urlsafe(8),
            "uri": f"spotify:track:{secrets.token_urlsafe(8)}",
            "name": name,
            "artists": [{"name": a} for a in artists],
            "album": {"album_type": album_type},
            "isrc": isrc,
            "popularity": popularity,
        }

    tracks = [
        make_track("Every Breath You Take", ["The Police"], "album", "GBAMX8300001", 85),
        make_track("Every Breath You Take", ["The Police"], "compilation", "GBAMX8300002", 60),
        make_track("Roxanne", ["The Police"], "album", "GBAMX7800001", 70),
    ]
    best = _score_candidate("The Police", "Every Breath You Take", "", tracks[0])
    assert best is not None and best.album_type == "album", best
    assert _artist_match("The Police", "", tracks[0])
    assert not _artist_match("Sting", "", tracks[0])
    assert _title_score("Every Breath You Take", "Every Breath You Take") > 0.95
    print("spotify scoring self-checks ok")


if __name__ == "__main__":
    _demo()
