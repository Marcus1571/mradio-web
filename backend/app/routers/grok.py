from fastapi import APIRouter, Depends, HTTPException, status

from .. import grok_oauth, grok_settings, providers
from .. import settings as settings_store
from ..deps import require_admin
from ..models import AITestResult

router = APIRouter(prefix="/api/settings/grok", tags=["settings"])


def _status_payload() -> dict:
    cfg = grok_settings.load()
    pending = grok_oauth.pending_status()
    return {
        "connected": bool(cfg["access_token"] and cfg["refresh_token"]),
        "pending": pending is not None,
    }


@router.get("")
async def get_grok_settings(admin: dict = Depends(require_admin)):
    return _status_payload()


@router.get("/status")
async def grok_status(admin: dict = Depends(require_admin)):
    # Unlike codex_oauth.py's background asyncio.Task, grok_oauth's device
    # flow has no subprocess to drive itself — this status poll (which the
    # frontend's useGrokStatus hook already calls on an interval while
    # pending, same UX as Codex) is also what actually advances the OAuth
    # poll loop. See grok_oauth.poll_once()'s own docstring for why that's
    # an intentional simplification, not an accident.
    if grok_oauth.pending_status() is not None:
        await grok_oauth.poll_once()
    return _status_payload()


@router.post("/connect")
async def connect_grok(admin: dict = Depends(require_admin)):
    result = await grok_oauth.start_device_flow()
    if not result:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            "Could not start sign-in — see server logs.")
    return {
        "user_code": result["user_code"],
        "verification_uri": result["verification_uri"],
    }


@router.post("/disconnect")
async def disconnect_grok(admin: dict = Depends(require_admin)):
    grok_settings.clear()
    return _status_payload()


@router.post("/test", response_model=AITestResult)
async def test_grok(admin: dict = Depends(require_admin)) -> AITestResult:
    settings = settings_store.load()
    ok, message = await providers.run_provider_test("grok", settings)
    return AITestResult(ok=ok, message=message)
