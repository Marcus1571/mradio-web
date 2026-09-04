from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .. import userdata
from ..deps import get_active_user

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


class FavoriteAddRequest(BaseModel):
    url: str
    name: str = ""


class FavoriteMoveRequest(BaseModel):
    src: int
    dst: int


def _validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "url must start with http:// or https://")
    return url


@router.get("")
async def get_favorites(user: dict = Depends(get_active_user)):
    return {"favorites": await userdata.load_favorites(user["id"])}


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_favorite(body: FavoriteAddRequest, user: dict = Depends(get_active_user)):
    url = _validate_url(body.url)
    favs = await userdata.load_favorites(user["id"])
    favs2, added = userdata.upsert_favorite(favs, url, body.name)
    if added:
        await userdata.save_favorites(user["id"], favs2)
    return {"favorites": favs2, "added": added}


@router.delete("")
async def remove_favorite(url: str = Query(...), user: dict = Depends(get_active_user)):
    favs = await userdata.load_favorites(user["id"])
    favs2, removed = userdata.delete_favorite(favs, url.strip())
    if removed:
        await userdata.save_favorites(user["id"], favs2)
    return {"favorites": favs2, "removed": removed}


@router.post("/move")
async def move_favorite(body: FavoriteMoveRequest, user: dict = Depends(get_active_user)):
    favs = await userdata.load_favorites(user["id"])
    favs2 = userdata.move_favorite(favs, body.src, body.dst)
    await userdata.save_favorites(user["id"], favs2)
    return {"favorites": favs2}
