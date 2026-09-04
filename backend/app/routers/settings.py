from fastapi import APIRouter, Depends

from .. import settings as settings_store
from ..deps import require_admin
from ..models import AISettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/ai")
async def get_ai_settings(admin: dict = Depends(require_admin)):
    return settings_store.redacted(settings_store.load())


@router.patch("/ai")
async def update_ai_settings(body: AISettingsUpdate, admin: dict = Depends(require_admin)):
    fields = body.model_dump(exclude_unset=True)
    settings_store.save(**fields)
    return settings_store.redacted(settings_store.load())
