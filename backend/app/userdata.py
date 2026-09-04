"""Per-user JSON data: stations.json (favorites) and config.json (theme/
volume/provider). Same file shapes mradio already used, just one
directory per user instead of a single shared set of files.

The AI trivia cache (cache.json) is NOT here — it's shared across all
users on purpose (see cache.py), not per-user.

File I/O is synchronous (these are small files) but run off the event
loop via asyncio.to_thread so a slow disk never blocks other requests.
The pure list-transform helpers (upsert/delete/move) do no I/O — callers
load, mutate, then save, same pattern as the original mradio."""

import asyncio
from pathlib import Path

from .db import DATA_DIR
from .jsonstore import atomic_write_json, read_json
from .stations import DEFAULT_STATIONS, MAX_FAV, GENRES, genre_of, is_empty_slot


def user_dir(user_id: int) -> Path:
    d = DATA_DIR / "users" / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stations_file(user_id: int) -> Path:
    return user_dir(user_id) / "stations.json"


def _config_file(user_id: int) -> Path:
    return user_dir(user_id) / "config.json"


# ---- favorites (stations.json) --------------------------------------------

def _norm_favorites(lst: list) -> list:
    out = []
    for x in lst:
        if is_empty_slot(x):
            out.append(None)
            continue
        x = x or {}
        u = str(x.get("url") or "").strip()
        if not u:
            out.append(None)
            continue
        g = str(x.get("genre") or "").strip().lower()
        if g not in GENRES:
            g = genre_of(str(x.get("name") or ""))
        name = str(x.get("name") or (u.split("/")[2] if "/" in u else u)).strip()
        out.append({"name": name, "url": u, "genre": g})
    return out


def _load_favorites_sync(user_id: int) -> list:
    data = read_json(_stations_file(user_id))
    lst = data.get("favorites") if isinstance(data, dict) else None
    if isinstance(lst, list):
        out = _norm_favorites(lst)
        out.extend([None] * (MAX_FAV - len(out)))
        return out[:MAX_FAV]
    # first run for this user: seed from the curated list
    seeded = list(DEFAULT_STATIONS)[:MAX_FAV]
    _save_favorites_sync(user_id, seeded)
    return seeded


def _save_favorites_sync(user_id: int, lst: list) -> bool:
    return atomic_write_json(_stations_file(user_id), {"favorites": list(lst)})


async def load_favorites(user_id: int) -> list:
    return await asyncio.to_thread(_load_favorites_sync, user_id)


async def save_favorites(user_id: int, lst: list) -> bool:
    return await asyncio.to_thread(_save_favorites_sync, user_id, lst)


def upsert_favorite(favs: list, url: str, name: str) -> tuple[list, bool]:
    """Return (list, added) — a copy of favs with a URL-new favorite added:
    fills the first empty slot, else appends. A URL already present is left
    untouched (added=False)."""
    favs = list(favs or [])
    if any(not is_empty_slot(x) and str(x.get("url") or "").strip() == url
           for x in favs):
        return favs, False
    ent = {"name": name or "", "url": url, "genre": genre_of(name or "")}
    for i, x in enumerate(favs):
        if is_empty_slot(x):
            favs[i] = ent
            return favs, True
    if len(favs) < MAX_FAV:
        favs.append(ent)
        return favs, True
    return favs, False


def delete_favorite(favs: list, url: str) -> tuple[list, bool]:
    """Return (list, removed) — the favorite whose URL matches is replaced
    with an empty slot (None), so numbering never shifts."""
    out = []
    removed = False
    for x in favs or []:
        if is_empty_slot(x):
            out.append(x)
        elif str((x or {}).get("url") or "").strip() == url and not removed:
            removed = True
            out.append(None)
        else:
            out.append(x)
    return out, removed


def move_favorite(favs: list, src: int, dst: int) -> list:
    """Move the favorite at slot src into slot dst, sliding the rest down."""
    favs = list(favs or [])
    if src < 0 or src >= len(favs) or is_empty_slot(favs[src]):
        return favs
    ent = favs.pop(src)
    dst = max(0, min(dst, len(favs)))
    favs.insert(dst, ent)
    favs = (favs + [None] * MAX_FAV)[:MAX_FAV]
    return favs


# ---- config (config.json) --------------------------------------------------

def _load_cfg_sync(user_id: int) -> dict:
    data = read_json(_config_file(user_id))
    return data if isinstance(data, dict) else {}


def _persist_cfg_sync(user_id: int, **fields) -> bool:
    d = _load_cfg_sync(user_id)
    for k, v in fields.items():
        if v is not None:
            d[k] = v
    return atomic_write_json(_config_file(user_id), d)


async def load_cfg(user_id: int) -> dict:
    return await asyncio.to_thread(_load_cfg_sync, user_id)


async def persist_cfg(user_id: int, **fields) -> bool:
    return await asyncio.to_thread(_persist_cfg_sync, user_id, **fields)
