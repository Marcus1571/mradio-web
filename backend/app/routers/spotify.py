from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from .. import spotify as spotify_client
from ..deps import get_active_user, require_admin

router = APIRouter(prefix="/api/spotify", tags=["spotify"])

_FRONTEND_CALLBACK_PATH = "/spotify-callback"


class ToggleRequest(BaseModel):
    raw_title: str
    add: bool


@router.get("/status")
async def spotify_status(user: dict = Depends(get_active_user)):
    return await spotify_client.user_status(user["id"])


@router.get("/auth-url")
async def spotify_auth_url(user: dict = Depends(get_active_user)):
    if not spotify_client.is_admin_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "spotify not configured")
    state = await spotify_client.create_oauth_state(user["id"])
    url = spotify_client.authorization_url(state)
    if not url:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "spotify not configured")
    return {"url": url}


@router.get("/callback")
async def spotify_callback(code: str = "", state: str = "", error: str = ""):
    """OAuth redirect handler. Spotify sends the browser here with `code` and
    `state`; we resolve the mradio session cookie independently and validate
    that the state belongs to the same user. After handling the result we
    redirect to a tiny page that closes the popup, so the player stays open
    and its polling loop updates the star."""
    if error:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail={error}")
    if not code or not state:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail=missing_params")

    await spotify_client.delete_expired_oauth_states()
    user_id = await spotify_client.consume_oauth_state(state)
    if not user_id:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail=invalid_state")

    ok = await spotify_client.connect_user(user_id, code)
    if not ok:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail=connect_failed")
    return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=connected")


@router.post("/disconnect")
async def spotify_disconnect(user: dict = Depends(get_active_user)):
    await spotify_client.disconnect_user(user["id"])
    return await spotify_client.user_status(user["id"])


@router.get("/membership")
async def spotify_membership(
    raw_title: str = Query(..., min_length=1),
    user: dict = Depends(get_active_user),
):
    return await spotify_client.membership(user["id"], raw_title)


@router.post("/toggle")
async def spotify_toggle(body: ToggleRequest, user: dict = Depends(get_active_user)):
    result = await spotify_client.toggle_track(user["id"], body.raw_title, body.add)
    if not result["ok"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, result.get("message") or "spotify action failed")
    return result


@router.post("/admin/sync-mirror")
async def spotify_admin_sync_mirror(user: dict = Depends(require_admin)):
    row = await spotify_client.load_token_row(user["id"])
    if not row:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not connected")
    access = await spotify_client.ensure_access_token(user["id"])
    if not access:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "token refresh failed")
    playlist_id = row.get("playlist_id")
    if not playlist_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no playlist")
    await spotify_client.sync_mirror(user["id"], access, playlist_id)
    return {"ok": True}
