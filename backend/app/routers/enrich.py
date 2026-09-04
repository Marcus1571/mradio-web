from fastapi import APIRouter, Depends, HTTPException, status

from .. import providers
from .. import settings as settings_store
from ..deps import get_active_user
from ..enrichers import get_enricher
from ..models import ProviderSwitchRequest

router = APIRouter(prefix="/api/enrich", tags=["enrich"])


@router.get("/providers")
async def list_providers(user: dict = Depends(get_active_user)):
    settings = settings_store.load()
    enricher = await get_enricher(user["id"])
    return {
        "active": enricher.provider,
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
    return {"active": enricher.provider}
