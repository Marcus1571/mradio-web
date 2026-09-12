from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from .. import deezer as deezer_client
from ..deps import get_active_user, require_admin

router = APIRouter(prefix="/api/deezer", tags=["deezer"])

_FRONTEND_CALLBACK_PATH = "/deezer-callback"


class ToggleRequest(BaseModel):
    raw_title: str
    add: bool


@router.get("/status")
async def deezer_status(user: dict = Depends(get_active_user)):
    return await deezer_client.user_status(user["id"])


@router.get("/auth-url")
async def deezer_auth_url(user: dict = Depends(get_active_user)):
    if not deezer_client.is_admin_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "deezer not configured")
    state = await deezer_client.create_oauth_state(user["id"])
    url = deezer_client.authorization_url(state)
    if not url:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "deezer not configured")
    return {"url": url}


@router.get("/callback")
async def deezer_callback(code: str = "", state: str = "", error: str = ""):
    """OAuth redirect handler. Deezer sends the browser here with `code` and
    `state`; we resolve the mradio session cookie independently and validate
    that the state belongs to the same user. After handling the result we
    redirect to a tiny page that closes the popup, so the player stays open
    and its polling loop updates the star."""
    if error:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail={error}")
    if not code or not state:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail=missing_params")

    await deezer_client.delete_expired_oauth_states()
    user_id = await deezer_client.consume_oauth_state(state)
    if not user_id:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail=invalid_state")

    ok = await deezer_client.connect_user(user_id, code)
    if not ok:
        return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=error&detail=connect_failed")
    return RedirectResponse(f"{_FRONTEND_CALLBACK_PATH}?status=connected")


@router.post("/disconnect")
async def deezer_disconnect(user: dict = Depends(get_active_user)):
    await deezer_client.disconnect_user(user["id"])
    return await deezer_client.user_status(user["id"])


@router.get("/membership")
async def deezer_membership(
    raw_title: str = Query(..., min_length=1),
    user: dict = Depends(get_active_user),
):
    return await deezer_client.membership(user["id"], raw_title)


@router.post("/toggle")
async def deezer_toggle(body: ToggleRequest, user: dict = Depends(get_active_user)):
    result = await deezer_client.toggle_track(user["id"], body.raw_title, body.add)
    if not result["ok"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, result.get("message") or "deezer action failed")
    return result


@router.post("/admin/sync-mirror")
async def deezer_admin_sync_mirror(user: dict = Depends(require_admin)):
    row = await deezer_client.load_token_row(user["id"])
    if not row:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not connected")
    access = await deezer_client.ensure_access_token(user["id"])
    if not access:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "token refresh failed")
    playlist_id = row.get("playlist_id")
    if not playlist_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no playlist")
    await deezer_client.sync_mirror(user["id"], access, playlist_id)
    return {"ok": True}
