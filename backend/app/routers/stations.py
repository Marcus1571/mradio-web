from fastapi import APIRouter, Depends, HTTPException, status

from .. import radio_browser, station_logos
from .. import stations as stations_mod
from .. import userdata
from ..deps import get_active_user

router = APIRouter(prefix="/api/stations", tags=["stations"])


@router.get("/genres")
async def list_genres(user: dict = Depends(get_active_user)):
    favs = await userdata.load_favorites(user["id"])
    counts = stations_mod.genre_station_counts(favs)
    return {"genres": [
        {"genre": g, "label": stations_mod.GENRE_LABELS[g], "count": counts[g]}
        for g in stations_mod.GENRES if counts[g]
    ]}


@router.get("/genres/{genre}")
async def genre_stations(genre: str, user: dict = Depends(get_active_user)):
    if genre not in stations_mod.GENRES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown genre")
    favs = await userdata.load_favorites(user["id"])
    return {"genre": genre, "stations": stations_mod.genre_stations_for(favs, genre)}


@router.get("/logo")
async def station_logo(url: str, name: str, user: dict = Depends(get_active_user)):
    cached = await station_logos.get_cached(url)
    if cached is not None:
        return {"logo": cached["logo"]}
    logo = await radio_browser.find_logo(url, name)
    await station_logos.store(url, logo)
    return {"logo": logo}
