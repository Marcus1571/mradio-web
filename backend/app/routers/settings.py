from typing import Literal

from fastapi import APIRouter, Depends

from .. import providers
from .. import settings as settings_store
from ..deps import require_admin
from ..models import AISettingsUpdate, AITestResult

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/ai")
async def get_ai_settings(admin: dict = Depends(require_admin)):
    return settings_store.redacted(settings_store.load())


@router.patch("/ai")
async def update_ai_settings(body: AISettingsUpdate, admin: dict = Depends(require_admin)):
    fields = body.model_dump(exclude_unset=True)
    settings_store.save(**fields)
    return settings_store.redacted(settings_store.load())


@router.post("/ai/test", response_model=AITestResult)
async def test_ai_provider(
    provider: Literal["ollama", "openai", "opencode"],
    overrides: AISettingsUpdate,
    admin: dict = Depends(require_admin),
) -> AITestResult:
    merged = {**settings_store.load(), **overrides.model_dump(exclude_unset=True)}
    ok, message = await providers.run_provider_test(provider, merged)
    return AITestResult(ok=ok, message=message)
