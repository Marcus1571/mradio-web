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
    enricher = await get_enricher(user["id"])
    return {
        # The user's own pick (enricher.provider) can be empty/disabled
        # while enrichment still succeeds via the fallback chain — show
        # the provider actually doing the work, not just the raw
        # preference, so "Asking <name>..." names something real.
        "active": await enricher.active_provider(),
        "providers": [
            {"name": name, "enabled": providers.provider_enabled(name, settings)}
            for name in providers.PROVIDERS
        ],
    }


@router.post("/providers/activate")
async def activate_provider(body: ProviderSwitchRequest,
                            user: dict = Depends(get_active_user)):
    enricher = await get_enricher(user["id"])
    if not await enricher.switch_provider(body.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            f"provider {body.name!r} is not configured")
    # Without this, switching providers silently left the panel showing
    # whatever the previous (often failed/empty) result was until a
    # separate manual "Re-ask AI" click — the switch itself should
    # produce a fresh attempt against the newly-active provider.
    if enricher.last_key:
        await enricher.invalidate(
            enricher.last_key, enricher.last_artist,
            enricher.last_title, enricher.last_performer)
    return {"active": enricher.provider}
