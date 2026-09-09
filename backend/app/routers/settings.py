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


@router.get("/ai/ollama-models")
async def list_ollama_models(url: str | None = None, admin: dict = Depends(require_admin)):
    """Backs the AI providers page's Ollama model dropdown. Takes an
    optional `url` query param rather than always reading the saved
    setting — mirrors the Test button's own pattern of probing
    whatever's currently typed in the form, including a URL the admin
    hasn't saved yet."""
    target = url or settings_store.load().get("ollama_url") or ""
    models = await providers.list_ollama_models(target)
    if models is None:
        return {"models": [], "reachable": False}
    return {"models": models, "reachable": True}


@router.patch("/ai")
async def update_ai_settings(body: AISettingsUpdate, admin: dict = Depends(require_admin)):
    fields = body.model_dump(exclude_unset=True)
    settings_store.save(**fields)
    return settings_store.redacted(settings_store.load())


@router.post("/ai/test", response_model=AITestResult)
async def test_ai_provider(
    provider: Literal["ollama", "openai", "opencode", "grok", "gemini", "openrouter", "mistral"],
    overrides: AISettingsUpdate,
    admin: dict = Depends(require_admin),
) -> AITestResult:
    merged = {**settings_store.load(), **overrides.model_dump(exclude_unset=True)}
    ok, message = await providers.run_provider_test(provider, merged)
    return AITestResult(ok=ok, message=message)
