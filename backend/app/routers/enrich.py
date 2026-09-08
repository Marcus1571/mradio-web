from fastapi import APIRouter, Depends, HTTPException, status

from .. import providers
from .. import settings as settings_store
from .. import trivia_history
from ..deps import get_active_user
from ..enrichers import get_enricher
from ..models import ProviderSwitchRequest, TriviaHistoryEntry

router = APIRouter(prefix="/api/enrich", tags=["enrich"])


@router.get("/trivia-history", response_model=list[TriviaHistoryEntry])
async def get_trivia_history(user: dict = Depends(get_active_user)):
    return await trivia_history.recent(user["id"])


@router.get("/providers")
async def list_providers(user: dict = Depends(get_active_user)):
    settings = settings_store.load()
    enricher = await get_enricher(user)
    # Admin-only providers (ChatGPT, Grok — see providers.py's
    # ADMIN_ONLY_PROVIDERS) are omitted entirely for a non-admin, not
    # just shown disabled — a regular user shouldn't see them as
    # options at all, since picking one would spend the admin's own
    # real subscription/API budget with no visibility into it.
    visible = providers.PROVIDERS if user["is_admin"] else [
        n for n in providers.PROVIDERS if n not in providers.ADMIN_ONLY_PROVIDERS]
    return {
        # The user's own pick (enricher.provider) can be empty/disabled
        # while enrichment still succeeds via the fallback chain — show
        # the provider actually doing the work, not just the raw
        # preference, so "Asking <name>..." names something real.
        "active": await enricher.active_provider(),
        "providers": [
            {
                "name": name,
                "enabled": providers.provider_enabled(name, settings),
                # True only while auto-hidden by a real failure (see
                # providers.py's AUTO_HIDE_PROVIDERS/health_retry_loop),
                # not for a manual toggle-off — lets the settings page
                # show a distinct "temporarily hidden, retrying
                # automatically" state instead of looking identical to
                # an admin having switched it off on purpose.
                "auto_hidden": providers.provider_hidden_by_failure(name),
            }
            for name in visible
        ],
    }


@router.post("/providers/activate")
async def activate_provider(body: ProviderSwitchRequest,
                            user: dict = Depends(get_active_user)):
    if body.name in providers.ADMIN_ONLY_PROVIDERS and not user["is_admin"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            f"provider {body.name!r} is admin-only")
    enricher = await get_enricher(user)
    if not await enricher.switch_provider(body.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"provider {body.name!r} is not configured")
    # Without this, switching providers silently left the panel showing
    # whatever the previous (often failed/empty) result was until a
    # separate manual "Re-ask AI" click — the switch itself should
    # produce an attempt against the newly-active provider. force=False
    # (the default): if that provider already has a cached answer for
    # this track/language, use it instead of paying for a redundant
    # LLM call — see invalidate()'s docstring for the full reasoning.
    if enricher.last_key:
        await enricher.invalidate(
            enricher.last_key, enricher.last_artist,
            enricher.last_title, enricher.last_performer)
    return {"active": enricher.provider}
