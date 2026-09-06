from fastapi import APIRouter, Depends, HTTPException, status

from .. import codex_oauth, codex_settings, providers
from .. import settings as settings_store
from ..deps import require_admin
from ..models import AITestResult

router = APIRouter(prefix="/api/settings/codex", tags=["settings"])


def _status_payload() -> dict:
    cfg = codex_settings.load()
    pending = codex_oauth.pending_status()
    return {
        # A refresh_token means we can always get back a working access
        # token via ensure_fresh_token() — that's "connected" regardless
        # of whether the current access_token has already expired.
        "connected": bool(cfg["access_token"] and cfg["refresh_token"]),
        "pending": pending is not None,
        "chatgpt_plan_type": cfg.get("chatgpt_plan_type") or "",
    }


@router.get("")
async def get_codex_settings(admin: dict = Depends(require_admin)):
    return _status_payload()


@router.get("/status")
async def codex_status(admin: dict = Depends(require_admin)):
    return _status_payload()


@router.post("/connect")
async def connect_codex(admin: dict = Depends(require_admin)):
    result = await codex_oauth.start_device_flow()
    if not result:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY,
                            "Could not start sign-in — see server logs.")
    return {
        "user_code": result["user_code"],
        "verification_uri": result["verification_uri"],
    }


@router.post("/disconnect")
async def disconnect_codex(admin: dict = Depends(require_admin)):
    codex_settings.clear()
    return _status_payload()


@router.post("/test", response_model=AITestResult)
async def test_codex(admin: dict = Depends(require_admin)) -> AITestResult:
    settings = settings_store.load()
    ok, message = await providers.run_provider_test("codex", settings)
    return AITestResult(ok=ok, message=message)
