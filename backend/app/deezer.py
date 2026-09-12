"""Deezer per-user playlist integration.

OAuth 2.0 flow with server-stored access token. Each user gets their own
encrypted token and a private "mradio-web" playlist. The playlist contents are
mirrored locally so the player can show a filled star without hitting Deezer on
every UI tick.

Client credentials live in settings.json (admin UI). The redirect URI and the
encryption key are env vars (MRADIO_DEEZER_REDIRECT_URI and MRADIO_TOKEN_KEY)."""

from __future__ import annotations

import logging
import os
import re
import secrets
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

logger = logging.getLogger("mradio.deezer")

DEEZER_CONNECT = "https://connect.deezer.com/oauth"
DEEZER_API = "https://api.deezer.com"

# Deezer scopes: basic_access for profile, manage_library for playlist write,
# delete_library for track removal.
REQUIRED_PERMS = "basic_access,manage_library,delete_library"

_PLAYLIST_NAME = "mradio-web"

# Deezer access tokens do not expire by default. Store a far-future expiry so
# the same token plumbing works if Deezer ever starts returning expires_in.
_FAR_FUTURE_SECONDS = 365 * 24 * 3600


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def _redirect_uri() -> str | None:
    uri = (os.environ.get("MRADIO_DEEZER_REDIRECT_URI") or "").strip()
    return uri or None


def _client_creds() -> tuple[str, str] | None:
    s = settings_store.load()
    app_id = (s.get("deezer_app_id") or "").strip()
    secret = (s.get("deezer_secret") or "").strip()
    if not app_id or not secret:
        return None
    return app_id, secret


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
    app_id, _ = creds
    params = {
        "app_id": app_id,
        "redirect_uri": redirect,
        "perms": REQUIRED_PERMS,
        "state": state,
    }
    return f"{DEEZER_CONNECT}/auth.php?{urllib.parse.urlencode(params)}"


async def exchange_code(code: str) -> dict[str, Any] | None:
    creds = _client_creds()
    redirect = _redirect_uri()
    if not creds or not redirect:
        return None
    app_id, secret = creds
    url = f"{DEEZER_CONNECT}/access_token.php"
    params = {
        "app_id": app_id,
        "secret": secret,
        "code": code,
        "output": "json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
    if r.status_code != 200:
        logger.warning("deezer token endpoint returned %s: %s", r.status_code, r.text[:500])
        return None
    try:
        data = r.json()
    except Exception:
        logger.warning("deezer token endpoint returned non-JSON: %s", r.text[:500])
        return None
    if "access_token" not in data:
        logger.warning("deezer token endpoint returned error: %s", data)
        return None
    return data


# ---------------------------------------------------------------------------
# Token storage
# ---------------------------------------------------------------------------


_DEEZER_COLS = "access_token, refresh_token, expires_at, playlist_id, created_at, updated_at"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _is_expired(expires_at: str, margin_seconds: int = 120) -> bool:
    try:
        dt = datetime.fromisoformat(expires_at)
        return datetime.now(timezone.utc) + timedelta(seconds=margin_seconds) >= dt
    except Exception:
        return True


STATE_TTL = timedelta(minutes=10)


async def create_oauth_state(user_id: int) -> str:
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db = get_db()
    await db.execute(
        "INSERT INTO deezer_oauth_states (state, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (state, user_id, now.isoformat(), (now + STATE_TTL).isoformat()),
    )
    await db.commit()
    return state


async def consume_oauth_state(state: str) -> int | None:
    db = get_db()
    cur = await db.execute(
        "SELECT user_id FROM deezer_oauth_states WHERE state = ? AND expires_at > ?",
        (state, datetime.now(timezone.utc).isoformat()),
    )
    row = await cur.fetchone()
    if not row:
        return None
    await db.execute("DELETE FROM deezer_oauth_states WHERE state = ?", (state,))
    await db.commit()
    return row["user_id"]


async def delete_expired_oauth_states() -> None:
    db = get_db()
    await db.execute(
        "DELETE FROM deezer_oauth_states WHERE expires_at <= ?",
        (datetime.now(timezone.utc).isoformat(),),
    )
    await db.commit()


async def load_token_row(user_id: int) -> dict[str, Any] | None:
    db = get_db()
    cur = await db.execute("SELECT * FROM deezer_tokens WHERE user_id = ?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def save_tokens(
    user_id: int,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    playlist_id: str = "",
) -> None:
    db = get_db()
    now = _now_iso()
    await db.execute(
        f"""
        INSERT INTO deezer_tokens (user_id, {_DEEZER_COLS})
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            access_token=excluded.access_token,
            refresh_token=excluded.refresh_token,
            expires_at=excluded.expires_at,
            playlist_id=excluded.playlist_id,
            updated_at=excluded.updated_at
        """,
        (
            user_id,
            access_token,
            encrypt(refresh_token),
            _expires_at(expires_in),
            playlist_id,
            now,
            now,
        ),
    )
    await db.commit()


async def ensure_access_token(user_id: int) -> str | None:
    """Return a valid access token. Deezer tokens do not currently expire, so
    this is mostly a presence check."""
    row = await load_token_row(user_id)
    if not row:
        return None
    access_token = row["access_token"]
    if not _is_expired(row["expires_at"]):
        return access_token
    # If Deezer ever starts returning expires_in, refresh plumbing can go here.
    return None


async def disconnect_user(user_id: int) -> None:
    db = get_db()
    await db.execute("DELETE FROM deezer_tokens WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM deezer_playlist_tracks WHERE user_id = ?", (user_id,))
    await db.commit()


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------


async def _api(
    access_token: str,
    method: str,
    path: str,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    params = dict(params or {})
    params["access_token"] = access_token
    async with httpx.AsyncClient(timeout=30) as client:
        return await client.request(method, f"{DEEZER_API}{path}", params=params)


async def get_profile(access_token: str) -> dict[str, Any] | None:
    r = await _api(access_token, "GET", "/user/me")
    if r.status_code != 200:
        logger.warning("deezer /user/me returned %s: %s", r.status_code, r.text[:500])
        return None
    try:
        return r.json()
    except Exception:
        return None


async def create_playlist(access_token: str) -> str | None:
    r = await _api(access_token, "POST", "/user/me/playlists", params={"title": _PLAYLIST_NAME})
    if r.status_code not in (200, 201):
        logger.warning("deezer create playlist returned %s: %s", r.status_code, r.text[:500])
        return None
    try:
        data = r.json()
    except Exception:
        return None
    # Deezer returns the new id directly as the response body for some formats,
    # or wrapped in an object for others.
    if isinstance(data, int):
        return str(data)
    if isinstance(data, dict):
        return str(data.get("id", "")) or None
    return None


async def add_tracks_to_playlist(access_token: str, playlist_id: str, track_ids: list[str]) -> bool:
    if not track_ids:
        return True
    r = await _api(
        access_token,
        "POST",
        f"/playlist/{playlist_id}/tracks",
        params={"songs": ",".join(track_ids)},
    )
    # Deezer returns 200 with an empty body on success.
    return r.status_code in (200, 201)


async def remove_track_from_playlist(access_token: str, playlist_id: str, track_id: str) -> bool:
    r = await _api(
        access_token,
        "DELETE",
        f"/playlist/{playlist_id}/tracks",
        params={"songs": track_id},
    )
    return r.status_code in (200, 201, 204)


async def fetch_playlist_tracks(
    access_token: str, playlist_id: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    index = 0
    while True:
        r = await _api(
            access_token,
            "GET",
            f"/playlist/{playlist_id}/tracks",
            params={"index": index, "limit": 100},
        )
        if r.status_code != 200:
            break
        try:
            data = r.json()
        except Exception:
            break
        items = data.get("data") or []
        out.extend(items)
        if len(items) < 100:
            break
        if not data.get("next"):
            break
        index += 100
    return out


async def search_tracks(
    access_token: str, query: str, limit: int = 20
) -> list[dict[str, Any]]:
    r = await _api(access_token, "GET", "/search/track", params={"q": query, "limit": limit})
    if r.status_code != 200:
        return []
    try:
        data = r.json()
    except Exception:
        return []
    return data.get("data", []) if isinstance(data, dict) else []


# ---------------------------------------------------------------------------
# Playlist mirror
# ---------------------------------------------------------------------------


async def sync_mirror(user_id: int, access_token: str, playlist_id: str) -> None:
    items = await fetch_playlist_tracks(access_token, playlist_id)
    db = get_db()
    await db.execute("DELETE FROM deezer_playlist_tracks WHERE user_id = ?", (user_id,))
    rows = []
    for item in items:
        tid = item.get("id")
        if not tid:
            continue
        rows.append(
            (
                user_id,
                str(tid),
                (item.get("isrc") or "").upper(),
                _now_iso(),
            )
        )
    if rows:
        await db.executemany(
            "INSERT INTO deezer_playlist_tracks (user_id, deezer_track_id, isrc, added_at) VALUES (?, ?, ?, ?)",
            rows,
        )
    await db.commit()


async def add_to_mirror(user_id: int, track_id: str, isrc: str) -> None:
    db = get_db()
    await db.execute(
        """
        INSERT INTO deezer_playlist_tracks (user_id, deezer_track_id, isrc, added_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, deezer_track_id) DO NOTHING
        """,
        (user_id, track_id, (isrc or "").upper(), _now_iso()),
    )
    await db.commit()


async def remove_from_mirror(user_id: int, track_id: str) -> None:
    db = get_db()
    await db.execute(
        "DELETE FROM deezer_playlist_tracks WHERE user_id = ? AND deezer_track_id = ?",
        (user_id, track_id),
    )
    await db.commit()


async def is_in_mirror(user_id: int, track_id: str, isrc: str) -> bool:
    if not track_id and not isrc:
        return False
    db = get_db()
    if track_id:
        cur = await db.execute(
            "SELECT 1 FROM deezer_playlist_tracks WHERE user_id = ? AND deezer_track_id = ?",
            (user_id, track_id),
        )
        if await cur.fetchone():
            return True
    if isrc:
        cur = await db.execute(
            "SELECT 1 FROM deezer_playlist_tracks WHERE user_id = ? AND isrc = ?",
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


def _artist_names(track: dict[str, Any]) -> list[str]:
    artist = track.get("artist")
    if isinstance(artist, dict):
        name = artist.get("name")
        return [name] if name else []
    return []


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
    isrc: str
    title: str
    artists: list[str]
    duration: int
    rank: int
    score: float


def _dedupe_tracks(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for t in tracks:
        key = (t.get("isrc") or str(t.get("id")) or "").upper()
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
    if not tid:
        return None
    candidate_title = track.get("title") or ""
    title_sim = _title_score(query_title, candidate_title)
    artist_ok = _artist_match(query_artist, query_performer, track)

    if title_sim < 0.55:
        return None
    if not artist_ok and title_sim < 0.85:
        return None

    duration = track.get("duration") or 0
    rank = track.get("rank") or 0
    score = (
        title_sim * 10.0
        + (2.0 if artist_ok else 0.0)
        + min(rank, 1_000_000) / 1_000_000.0
    )
    return MatchResult(
        track_id=str(tid),
        isrc=(track.get("isrc") or "").upper(),
        title=candidate_title,
        artists=_artist_names(track),
        duration=int(duration),
        rank=int(rank),
        score=round(score, 3),
    )


async def find_best_track(
    access_token: str,
    artist: str,
    title: str,
    performer: str,
) -> MatchResult | None:
    """Search Deezer and make a single executive-decision match."""
    queries: list[str] = []
    artist = artist or ""
    title = title or ""
    performer = performer or ""

    def add(q: str) -> None:
        q = q.strip()
        if q and q not in queries:
            queries.append(q)

    if artist and title:
        add(f'artist:"{artist}" track:"{title}"')
        add(f"{artist} {title}")
    if performer and title:
        add(f"{title} {performer}")
    if title:
        add(title)
    if not queries:
        return None

    all_tracks: list[dict[str, Any]] = []
    for q in queries:
        all_tracks.extend(await search_tracks(access_token, q))

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
    }


async def connect_user(user_id: int, code: str) -> bool:
    token_resp = await exchange_code(code)
    if not token_resp:
        logger.warning("deezer connect_user: token exchange failed for user_id=%s", user_id)
        return False
    access = token_resp["access_token"]
    expires_in = token_resp.get("expires", 0) or _FAR_FUTURE_SECONDS

    profile = await get_profile(access)
    if not profile:
        logger.warning("deezer connect_user: /user/me failed for user_id=%s", user_id)
        return False

    playlist_id = ""
    row = await load_token_row(user_id)
    if row and row.get("playlist_id"):
        playlist_id = row["playlist_id"]
    if not playlist_id:
        playlist_id = await create_playlist(access) or ""

    await save_tokens(
        user_id,
        access,
        "",
        expires_in,
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
    """Add or remove the currently-playing track from the user's Deezer playlist."""
    access = await ensure_access_token(user_id)
    if not access:
        return {"ok": False, "in_playlist": False, "track_id": None, "message": "not connected"}

    row = await load_token_row(user_id)
    playlist_id = row.get("playlist_id") if row else ""
    if not playlist_id:
        return {"ok": False, "in_playlist": False, "track_id": None, "message": "no playlist"}

    artist, title, performer = split_title(raw_title)
    match = await find_best_track(access, artist, title, performer)
    if not match:
        return {"ok": False, "in_playlist": False, "track_id": None, "message": "not found on Deezer"}

    in_mirror = await is_in_mirror(user_id, match.track_id, match.isrc)

    if add:
        if in_mirror:
            return {"ok": True, "in_playlist": True, "track_id": match.track_id, "message": None}
        ok = await add_tracks_to_playlist(access, playlist_id, [match.track_id])
        if ok:
            await add_to_mirror(user_id, match.track_id, match.isrc)
            return {"ok": True, "in_playlist": True, "track_id": match.track_id, "message": None}
        return {"ok": False, "in_playlist": False, "track_id": match.track_id, "message": "failed to add"}

    # remove
    if not in_mirror:
        return {"ok": True, "in_playlist": False, "track_id": match.track_id, "message": None}
    ok = await remove_track_from_playlist(access, playlist_id, match.track_id)
    if ok:
        await remove_from_mirror(user_id, match.track_id)
        return {"ok": True, "in_playlist": False, "track_id": match.track_id, "message": None}
    return {"ok": False, "in_playlist": True, "track_id": match.track_id, "message": "failed to remove"}


async def membership(
    user_id: int,
    raw_title: str,
) -> dict[str, Any]:
    """Check whether the currently-playing track is already in the playlist."""
    access = await ensure_access_token(user_id)
    if not access:
        return {"in_playlist": False, "track_id": None}

    row = await load_token_row(user_id)
    playlist_id = row.get("playlist_id") if row else ""
    if not playlist_id:
        return {"in_playlist": False, "track_id": None}

    artist, title, performer = split_title(raw_title)
    match = await find_best_track(access, artist, title, performer)
    if not match:
        return {"in_playlist": False, "track_id": None}

    in_mirror = await is_in_mirror(user_id, match.track_id, match.isrc)
    return {"in_playlist": in_mirror, "track_id": match.track_id}
